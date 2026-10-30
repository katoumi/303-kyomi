import asyncio
import datetime
import io
import re
import discord
from discord import app_commands
from discord.ext import commands
from ui_theme import (
    COLOR_AMBER,
    COLOR_CRIMSON,
    COLOR_MINT,
    COLOR_OBSIDIAN,
    kyomi_embed,
    progress_bar,
)


def resolve_emoji(
    bot: commands.Bot, emoji_input: str | None
) -> str | discord.PartialEmoji | None:
    """Resolves standard unicode emojis or custom emojis from ANY server."""
    if not emoji_input:
        return None
    raw = emoji_input.strip()
    if not raw:
        return None

    # Discord custom emoji syntax: <:name:id> or <a:name:id>
    custom_match = re.match(r"^<(a)?:([a-zA-Z0-9_]+):([0-9]+)>$", raw)
    if custom_match:
        animated = bool(custom_match.group(1))
        name = custom_match.group(2)
        emoji_id = int(custom_match.group(3))
        return discord.PartialEmoji(name=name, id=emoji_id, animated=animated)

    # Numeric Discord emoji ID
    if raw.isdigit():
        custom = bot.get_emoji(int(raw))
        if custom:
            return custom
        return discord.PartialEmoji(name="custom_emoji", id=int(raw))

    # Match by name in any joined server
    clean_name = raw.strip(":")
    for guild in bot.guilds:
        found = discord.utils.get(guild.emojis, name=clean_name)
        if found:
            return found

    # Standard Unicode emoji string (e.g. 🦋)
    return raw


async def open_ticket_channel(
    bot: commands.Bot,
    interaction: discord.Interaction,
    category_label: str = "support",
) -> discord.TextChannel | None:
    """Helper to provision a private ticket room and register it in SQLite."""
    assert interaction.guild is not None
    assert isinstance(interaction.user, discord.Member)

    existing = await bot.db.get_open_ticket_by_user(
        interaction.guild.id, interaction.user.id
    )
    if existing:
        ch = interaction.guild.get_channel(existing["channel_id"])
        if ch:
            await interaction.followup.send(
                f"*you already have an open ticket: {ch.mention}*",
                ephemeral=True,
            )
            return None
        else:
            await bot.db.close_ticket_record(existing["channel_id"])

    settings = await bot.db.get_guild_settings(interaction.guild.id)
    category_id = settings.get("ticket_category_id")
    support_role_id = settings.get("ticket_support_role_id")

    discord_category = (
        interaction.guild.get_channel(category_id) if category_id else None
    )
    if not isinstance(discord_category, discord.CategoryChannel):
        discord_category = None

    overwrites: dict[
        discord.Role | discord.Member, discord.PermissionOverwrite
    ] = {
        interaction.guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
        interaction.guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            read_message_history=True,
        ),
    }

    support_role = (
        interaction.guild.get_role(support_role_id) if support_role_id else None
    )
    if support_role:
        overwrites[support_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        )

    safe_name = (
        "".join(
            c for c in interaction.user.name.lower() if c.isalnum() or c == "-"
        )[:16]
        or "user"
    )
    channel_name = f"t-{safe_name}"

    try:
        ticket_channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=discord_category,
            overwrites=overwrites,
            topic=f"303 ticket · {interaction.user.id} · {category_label}",
            reason=f"ticket opened by {interaction.user}",
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "*i need `manage channels` permission to create tickets.*",
            ephemeral=True,
        )
        return None

    ticket_id = await bot.db.create_ticket(
        interaction.guild.id,
        ticket_channel.id,
        interaction.user.id,
        category_label,
    )

    embed = kyomi_embed(
        title=f"ticket #{ticket_id:03d}",
        description=(
            f"hey {interaction.user.mention} — drop what you need below (details, questions, or links) and staff will be right with you.\n\n"
            f"╰ **topic:** `{category_label}`\n"
            f"╰ **user:** {interaction.user.mention} (`{interaction.user.id}`)"
        ),
        color=COLOR_OBSIDIAN,
        tag=None,
        footer=None,
        guild=interaction.guild,
    )

    ping_text = (
        f"{interaction.user.mention} {support_role.mention}"
        if support_role
        else interaction.user.mention
    )
    await ticket_channel.send(
        content=ping_text,
        embed=embed,
        view=TicketControlView(bot),
    )

    await interaction.followup.send(
        f"*opened {ticket_channel.mention}*",
        ephemeral=True,
    )
    return ticket_channel


class AddMemberModal(discord.ui.Modal, title="add member to ticket"):
    user_input = discord.ui.TextInput(
        label="user id or username",
        placeholder="e.g. 1565593696907296901 or username",
        required=True,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        assert isinstance(interaction.channel, discord.TextChannel)

        query = self.user_input.value.strip().replace("<@", "").replace(">", "").replace("!", "")
        member: discord.Member | None = None
        if query.isdigit():
            member = interaction.guild.get_member(int(query))
        if not member:
            member = discord.utils.get(interaction.guild.members, name=query)

        if not member:
            return await interaction.response.send_message(
                f"*member `{query}` not found in this server.*", ephemeral=True
            )

        await interaction.channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        )
        await interaction.response.send_message(
            f"╰ *added {member.mention} to this ticket.*"
        )


class TicketControlView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="✦ claim",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket:claim",
        row=0,
    )
    async def claim_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        assert isinstance(interaction.user, discord.Member)
        assert isinstance(interaction.channel, discord.TextChannel)

        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
        support_role_id = settings.get("ticket_support_role_id")
        is_staff = (
            interaction.user.guild_permissions.manage_channels
            or interaction.user.guild_permissions.moderate_members
            or (
                support_role_id
                and any(r.id == support_role_id for r in interaction.user.roles)
            )
        )
        if not is_staff:
            return await interaction.response.send_message(
                "*only staff can claim tickets.*", ephemeral=True
            )

        await self.bot.db.claim_ticket(interaction.channel.id, interaction.user.id)
        button.disabled = True
        button.label = f"● claimed · {interaction.user.display_name.lower()}"
        await interaction.response.edit_message(view=self)

        notice = kyomi_embed(
            description=f"{interaction.user.mention} *is handling this ticket now.*",
            color=COLOR_OBSIDIAN,
            tag=None,
            footer=None,
        )
        await interaction.channel.send(embed=notice)

    @discord.ui.button(
        label="◈ pin / urgent",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket:priority",
        row=0,
    )
    async def priority_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        assert isinstance(interaction.user, discord.Member)
        assert isinstance(interaction.channel, discord.TextChannel)

        if not (
            interaction.user.guild_permissions.manage_channels
            or interaction.user.guild_permissions.moderate_members
        ):
            return await interaction.response.send_message(
                "*staff only.*", ephemeral=True
            )

        button.disabled = True
        button.label = "● urgent"
        await interaction.response.edit_message(view=self)

        if not interaction.channel.name.startswith("ǃ-"):
            try:
                await interaction.channel.edit(
                    name=f"ǃ-{interaction.channel.name}"[:95]
                )
            except discord.HTTPException:
                pass

        alert = kyomi_embed(
            description=f"*marked as **urgent** by {interaction.user.mention}*",
            color=COLOR_CRIMSON,
            tag=None,
            footer=None,
        )
        await interaction.channel.send(embed=alert)

    @discord.ui.button(
        label="＋ add member",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket:add_member",
        row=0,
    )
    async def add_member_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(AddMemberModal(self.bot))

    @discord.ui.button(
        label="× close",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:close",
        row=0,
    )
    async def close_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        assert isinstance(interaction.channel, discord.TextChannel)

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self)

        bar_init = progress_bar(5, 5, length=10)
        countdown_embed = kyomi_embed(
            description=f"╰ *saving transcript & closing in **`5s`**  `{bar_init}`*",
            color=COLOR_CRIMSON,
            tag=None,
            footer=None,
        )
        status_msg = await interaction.channel.send(embed=countdown_embed)

        lines = [
            f"# 303 kyomi · ticket transcript (#{interaction.channel.name})",
            f"- server: {interaction.guild.name} ({interaction.guild.id})",
            f"- closed by: {interaction.user} ({interaction.user.id})",
            f"- date: {datetime.datetime.now(datetime.timezone.utc).isoformat()}",
            "---\n",
        ]
        async for msg in interaction.channel.history(limit=500, oldest_first=True):
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content = msg.content or ""
            attachments = (
                " [attachments: " + ", ".join(a.url for a in msg.attachments) + "]"
                if msg.attachments
                else ""
            )
            lines.append(
                f"[{timestamp}] {msg.author} ({msg.author.id}): {content}{attachments}"
            )

        transcript_bytes = "\n".join(lines).encode("utf-8")
        ticket_data = await self.bot.db.get_ticket_by_channel(interaction.channel.id)
        await self.bot.db.close_ticket_record(interaction.channel.id)

        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
        log_channel_id = settings.get("ticket_log_channel_id") or settings.get(
            "mod_log_channel_id"
        )
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if isinstance(log_channel, discord.TextChannel):
                owner_str = (
                    f"<@{ticket_data['owner_id']}> (`{ticket_data['owner_id']}`)"
                    if ticket_data
                    else "unknown"
                )
                cat_str = ticket_data["category"] if ticket_data else "support"
                embed = kyomi_embed(
                    description=(
                        f"**closed #{interaction.channel.name}**\n"
                        f"╰ **opened by:** {owner_str}\n"
                        f"╰ **topic:** `{cat_str}`\n"
                        f"╰ **closed by:** {interaction.user.mention}"
                    ),
                    color=COLOR_OBSIDIAN,
                    tag=None,
                    footer=None,
                    guild=interaction.guild,
                )
                file_obj = discord.File(
                    io.BytesIO(transcript_bytes),
                    filename=f"303-{interaction.channel.name}.md",
                )
                try:
                    await log_channel.send(embed=embed, file=file_obj)
                except discord.HTTPException:
                    pass

        for remaining in range(4, -1, -1):
            await asyncio.sleep(1)
            bar = progress_bar(remaining, 5, length=10)
            label_txt = (
                f"╰ *saving transcript & closing in **`{remaining}s`**  `{bar}`*"
                if remaining > 0
                else f"╰ *closed  `{bar}`*"
            )
            countdown_embed.description = label_txt
            try:
                await status_msg.edit(embed=countdown_embed)
            except discord.HTTPException:
                break

        try:
            await interaction.channel.delete(
                reason=f"closed by {interaction.user}"
            )
        except discord.HTTPException:
            pass


class TicketButton(discord.ui.Button):
    def __init__(
        self,
        bot: commands.Bot,
        emoji: str | discord.PartialEmoji | None = "🦋",
        label: str | None = None,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
    ):
        super().__init__(
            style=style,
            emoji=emoji or "🦋",
            label=label,
            custom_id="ticket:btn_open",
            row=0,
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await open_ticket_channel(self.bot, interaction, category_label="support")


class TicketButtonView(discord.ui.View):
    """Persistent button view for custom 1-click ticket panels."""
    def __init__(
        self,
        bot: commands.Bot,
        emoji: str | discord.PartialEmoji | None = "🦋",
        label: str | None = None,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
    ):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(TicketButton(bot, emoji=emoji, label=label, style=style))


class TicketCategorySelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        options = [
            discord.SelectOption(
                label="✦ general help",
                value="general help",
                description="questions, roles, or server help",
            ),
            discord.SelectOption(
                label="◈ report someone",
                value="user report",
                description="privately report a member or rule break",
            ),
            discord.SelectOption(
                label="✧ appeal a warn / mute",
                value="appeal",
                description="talk to staff about a punishment",
            ),
            discord.SelectOption(
                label="◇ partnerships & other",
                value="partnerships",
                description="collabs, events, or speaking with owners",
            ),
        ]
        super().__init__(
            placeholder="✦ choose a topic...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket:category_select",
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        category_label = self.values[0]
        await open_ticket_channel(self.bot, interaction, category_label=category_label)


class TicketPanelView(discord.ui.View):
    """Persistent dropdown view for multi-category ticket panels."""
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect(bot))


class CustomPanelModal(discord.ui.Modal, title="custom ticket panel"):
    panel_text = discord.ui.TextInput(
        label="panel content / text",
        style=discord.TextStyle.paragraph,
        placeholder="type what you want inside the panel...",
        default="@  303",
        required=True,
    )
    emoji_input = discord.ui.TextInput(
        label="button emoji (any server or unicode)",
        placeholder="e.g. 🦋 or paste custom <:name:id>",
        default="🦋",
        required=False,
        max_length=100,
    )
    button_label_input = discord.ui.TextInput(
        label="button text (optional, leave empty for icon)",
        placeholder="e.g. open ticket",
        required=False,
        max_length=80,
    )
    title_input = discord.ui.TextInput(
        label="title (optional, leave empty for none)",
        required=False,
        max_length=100,
    )
    footer_input = discord.ui.TextInput(
        label="footer (optional, leave empty for none)",
        required=False,
        max_length=100,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(interaction.channel, discord.TextChannel)

        resolved_emoji = resolve_emoji(self.bot, self.emoji_input.value) or "🦋"
        btn_label = self.button_label_input.value.strip() or None
        panel_title = self.title_input.value.strip() or None
        panel_footer = self.footer_input.value.strip() or None

        embed = kyomi_embed(
            title=panel_title,
            description=self.panel_text.value.strip(),
            color=COLOR_OBSIDIAN,
            tag=None,
            footer=panel_footer,
            guild=interaction.guild,
        )

        view = TicketButtonView(
            self.bot,
            emoji=resolved_emoji,
            label=btn_label,
            style=discord.ButtonStyle.secondary,
        )

        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            "╰ *custom ticket panel deployed.*", ephemeral=True
        )


class TicketsCog(commands.Cog, name="Tickets"):
    """Minimalist dark ticket panel, custom emojis from any server, and clean transcripts."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(TicketButtonView(self.bot))
        self.bot.add_view(TicketPanelView(self.bot))
        self.bot.add_view(TicketControlView(self.bot))

    ticket_group = app_commands.Group(
        name="ticket",
        description="configure and drop customized support ticket panels.",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @ticket_group.command(
        name="setup",
        description="configure the category, log channel, and staff role for tickets.",
    )
    async def ticket_setup(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
        log_channel: discord.TextChannel,
        support_role: discord.Role | None = None,
    ):
        assert interaction.guild is not None
        await self.bot.db.update_guild_setting(
            interaction.guild.id, "ticket_category_id", category.id
        )
        await self.bot.db.update_guild_setting(
            interaction.guild.id, "ticket_log_channel_id", log_channel.id
        )
        if support_role:
            await self.bot.db.update_guild_setting(
                interaction.guild.id, "ticket_support_role_id", support_role.id
            )

        embed = kyomi_embed(
            description=(
                f"**tickets configured**\n"
                f"╰ **category:** `{category.name.lower()}`\n"
                f"╰ **transcripts:** {log_channel.mention}\n"
                f"╰ **staff role:** {support_role.mention if support_role else '*mods only*'}\n\n"
                "*use `/ticket panel` to drop your custom button or dropdown panel.*"
            ),
            color=COLOR_OBSIDIAN,
            tag=None,
            footer=None,
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ticket_group.command(
        name="panel",
        description="drop a minimalist custom ticket panel with any text and any emoji.",
    )
    @app_commands.choices(
        button_style=[
            app_commands.Choice(name="secondary (dark grey / minimal)", value="secondary"),
            app_commands.Choice(name="primary (blurple)", value="primary"),
            app_commands.Choice(name="success (green)", value="success"),
            app_commands.Choice(name="danger (red)", value="danger"),
        ]
    )
    async def ticket_panel(
        self,
        interaction: discord.Interaction,
        text: str = "@  303",
        emoji: str = "🦋",
        button_label: str | None = None,
        button_style: str = "secondary",
        title: str | None = None,
        footer: str | None = None,
        as_embed: bool = True,
    ):
        assert isinstance(interaction.channel, discord.TextChannel)

        style_map = {
            "secondary": discord.ButtonStyle.secondary,
            "primary": discord.ButtonStyle.primary,
            "success": discord.ButtonStyle.success,
            "danger": discord.ButtonStyle.danger,
        }
        b_style = style_map.get(button_style, discord.ButtonStyle.secondary)
        resolved_emoji = resolve_emoji(self.bot, emoji) or "🦋"

        view = TicketButtonView(
            self.bot,
            emoji=resolved_emoji,
            label=button_label,
            style=b_style,
        )

        if as_embed:
            embed = kyomi_embed(
                title=title,
                description=text,
                color=COLOR_OBSIDIAN,
                tag=None,
                footer=footer,
                guild=interaction.guild,
            )
            await interaction.channel.send(embed=embed, view=view)
        else:
            msg_content = f"**{title}**\n\n{text}" if title else text
            await interaction.channel.send(content=msg_content, view=view)

        await interaction.response.send_message(
            "╰ *ticket panel deployed.*", ephemeral=True
        )

    @ticket_group.command(
        name="builder",
        description="open an interactive popup window to write & preview your custom ticket panel.",
    )
    async def ticket_builder(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CustomPanelModal(self.bot))

    @ticket_group.command(
        name="add",
        description="add a member to the current ticket room.",
    )
    async def ticket_add(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ):
        assert isinstance(interaction.channel, discord.TextChannel)
        ticket = await self.bot.db.get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message(
                "*this channel is not an active ticket room.*", ephemeral=True
            )

        await interaction.channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        )
        await interaction.response.send_message(
            f"╰ *added {member.mention} to this ticket.*"
        )

    @ticket_group.command(
        name="remove",
        description="remove a member from the current ticket room.",
    )
    async def ticket_remove(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ):
        assert isinstance(interaction.channel, discord.TextChannel)
        ticket = await self.bot.db.get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message(
                "*this channel is not an active ticket room.*", ephemeral=True
            )

        if member.id == ticket["owner_id"]:
            return await interaction.response.send_message(
                "*cannot remove the ticket owner.*", ephemeral=True
            )

        await interaction.channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(
            f"╰ *removed {member.mention} from this ticket.*"
        )

    @ticket_group.command(
        name="rename",
        description="rename the current ticket channel.",
    )
    async def ticket_rename(
        self,
        interaction: discord.Interaction,
        new_name: str,
    ):
        assert isinstance(interaction.channel, discord.TextChannel)
        ticket = await self.bot.db.get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message(
                "*this channel is not an active ticket room.*", ephemeral=True
            )

        clean = "".join(c for c in new_name.lower() if c.isalnum() or c in "-_")[:32]
        await interaction.channel.edit(name=clean)
        await interaction.response.send_message(
            f"╰ *renamed ticket to `{clean}`.*"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot))
