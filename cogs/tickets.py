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


def create_clean_embed(
    title: str | None = None,
    description: str | None = None,
    color: discord.Color = COLOR_OBSIDIAN,
    tag: str | None = None,
    footer: str | None = None,
    guild: discord.Guild | None = None,
) -> discord.Embed:
    """Creates a minimal embed with zero timestamps and 0% risk of TypeError."""
    try:
        embed = kyomi_embed(
            title=title,
            description=description,
            color=color,
            tag=tag,
            footer=footer,
            guild=guild,
        )
    except TypeError:
        embed = discord.Embed(title=title, description=description, color=color)
        if tag:
            icon_url = guild.icon.url if (guild and guild.icon) else None
            embed.set_author(name=tag, icon_url=icon_url)
        if footer:
            embed.set_footer(text=footer)
    embed.timestamp = None
    return embed


async def generate_and_log_transcript(
    bot: commands.Bot,
    channel: discord.TextChannel,
    closed_by: discord.Member | discord.User,
    action_name: str = "closed",
) -> None:
    """Generates markdown transcript and sends to configured log channel."""
    lines = [
        f"# 303 kyomi · ticket transcript (#{channel.name})",
        f"- server: {channel.guild.name} ({channel.guild.id})",
        f"- action: {action_name} by {closed_by} ({closed_by.id})",
        f"- date: {datetime.datetime.now(datetime.timezone.utc).isoformat()}",
        "---\n",
    ]
    async for msg in channel.history(limit=500, oldest_first=True):
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        content = msg.content or ""
        attachments = (
            " [attachments: " + ", ".join(a.url for a in msg.attachments) + "]"
            if msg.attachments
            else ""
        )
        lines.append(f"[{timestamp}] {msg.author} ({msg.author.id}): {content}{attachments}")

    transcript_bytes = "\n".join(lines).encode("utf-8")
    ticket_data = await bot.db.get_ticket_by_channel(channel.id)

    settings = await bot.db.get_guild_settings(channel.guild.id)
    log_channel_id = settings.get("ticket_log_channel_id") or settings.get(
        "mod_log_channel_id"
    )
    if log_channel_id:
        log_channel = channel.guild.get_channel(log_channel_id)
        if isinstance(log_channel, discord.TextChannel):
            owner_str = (
                f"<@{ticket_data['owner_id']}> (`{ticket_data['owner_id']}`)"
                if ticket_data
                else "unknown"
            )
            cat_str = ticket_data["category"] if ticket_data else "support"
            embed = kyomi_embed(
                description=(
                    f"**{action_name} #{channel.name}**\n"
                    f"╰ **opened by:** {owner_str}\n"
                    f"╰ **topic:** `{cat_str}`\n"
                    f"╰ **{action_name} by:** {closed_by.mention}"
                ),
                color=COLOR_OBSIDIAN,
                tag=None,
                footer=None,
                guild=channel.guild,
            )
            file_obj = discord.File(
                io.BytesIO(transcript_bytes),
                filename=f"303-{channel.name}.md",
            )
            try:
                await log_channel.send(embed=embed, file=file_obj)
            except discord.HTTPException:
                pass


async def open_ticket_channel(
    bot: commands.Bot,
    interaction: discord.Interaction,
    category_label: str = "support",
    initial_details: str | None = None,
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
            status_str = "archived" if existing.get("status") == "archived" else "active"
            await interaction.followup.send(
                f"*you already have an {status_str} ticket: {ch.mention}. you cannot open a new ticket until staff deletes or closes your existing one.*",
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

    desc_lines = [
        f"hey {interaction.user.mention} — staff will be with you shortly.\n",
        f"╰ **topic:** `{category_label}`",
        f"╰ **user:** {interaction.user.mention} (`{interaction.user.id}`)",
    ]
    if initial_details:
        desc_lines.append(f"╰ **inquiry:** {initial_details}")

    embed = create_clean_embed(
        title=f"ticket #{ticket_id:03d}",
        description="\n".join(desc_lines),
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


class OpenTicketDropdownModal(discord.ui.Modal, title="open ticket"):
    """Modal with a category dropdown and an optional inquiry description input."""
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.category_select = discord.ui.Select(
            placeholder="choose inquiry category...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label="◈ partnership",
                    value="partnership",
                    description="server partnerships, collaborations & events",
                ),
                discord.SelectOption(
                    label="✦ support",
                    value="support",
                    description="general questions, roles, or server help",
                ),
                discord.SelectOption(
                    label="⊘ report",
                    value="report",
                    description="privately report a member, scam, or rule violation",
                ),
                discord.SelectOption(
                    label="✧ staff application",
                    value="staff application",
                    description="apply for trial mod, staff, or helper positions",
                ),
                discord.SelectOption(
                    label="◇ perk claiming",
                    value="perk claiming",
                    description="claim server booster, donor, or event rewards",
                ),
            ],
        )
        self.add_item(self.category_select)
        self.details_input = discord.ui.TextInput(
            label="details / inquiry (optional)",
            style=discord.TextStyle.paragraph,
            placeholder="briefly explain your inquiry or questions...",
            required=False,
            max_length=500,
        )
        self.add_item(self.details_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cat = self.category_select.values[0] if self.category_select.values else "support"
        details = self.details_input.value.strip() or None
        await open_ticket_channel(
            self.bot,
            interaction,
            category_label=cat,
            initial_details=details,
        )


class EphemeralCategorySelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        options = [
            discord.SelectOption(
                label="◈ partnership",
                value="partnership",
                description="server partnerships, collaborations & events",
            ),
            discord.SelectOption(
                label="✦ support",
                value="support",
                description="general questions, roles, or server help",
            ),
            discord.SelectOption(
                label="⊘ report",
                value="report",
                description="privately report a member, scam, or rule violation",
            ),
            discord.SelectOption(
                label="✧ staff application",
                value="staff application",
                description="apply for trial mod, staff, or helper positions",
            ),
            discord.SelectOption(
                label="◇ perk claiming",
                value="perk claiming",
                description="claim server booster, donor, or event rewards",
            ),
        ]
        super().__init__(
            placeholder="choose category...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cat = self.values[0]
        await open_ticket_channel(self.bot, interaction, category_label=cat)


class EphemeralCategorySelectView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=120)
        self.add_item(EphemeralCategorySelect(bot))


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


async def execute_close_sequence(
    bot: commands.Bot,
    channel: discord.TextChannel,
    closed_by: discord.Member | discord.User,
    interaction: discord.Interaction | None = None,
):
    """Handles animated 5-second countdown and deletes channel after logging transcript."""
    bar_init = progress_bar(5, 5, length=10)
    countdown_embed = kyomi_embed(
        description=f"╰ *saving transcript & closing in **`5s`**  `{bar_init}`*",
        color=COLOR_CRIMSON,
        tag=None,
        footer=None,
    )
    status_msg = await channel.send(embed=countdown_embed)

    await generate_and_log_transcript(bot, channel, closed_by, action_name="closed")
    await bot.db.close_ticket_record(channel.id)

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
        await channel.delete(reason=f"closed by {closed_by}")
    except discord.HTTPException:
        pass


class TicketArchivedView(discord.ui.View):
    """Persistent controls shown inside an archived ticket channel."""
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="✦ reopen",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket:reopen",
        row=0,
    )
    async def reopen_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        assert isinstance(interaction.channel, discord.TextChannel)
        assert isinstance(interaction.user, discord.Member)

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
                "*only staff can reopen archived tickets.*", ephemeral=True
            )

        ticket_data = await self.bot.db.get_ticket_by_channel(interaction.channel.id)
        if not ticket_data:
            return await interaction.response.send_message(
                "*ticket record not found.*", ephemeral=True
            )

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self)

        owner = interaction.guild.get_member(ticket_data["owner_id"])
        if owner:
            await interaction.channel.set_permissions(
                owner,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            )

        active_cat_id = settings.get("ticket_category_id")
        active_category = (
            interaction.guild.get_channel(active_cat_id) if active_cat_id else None
        )
        if isinstance(active_category, discord.CategoryChannel):
            try:
                await interaction.channel.edit(category=active_category)
            except discord.HTTPException:
                pass

        clean_name = interaction.channel.name.replace("arch-", "t-")
        try:
            await interaction.channel.edit(name=clean_name)
        except discord.HTTPException:
            pass

        await self.bot.db.reopen_ticket_record(interaction.channel.id)

        embed = create_clean_embed(
            description=f"╰ *ticket reopened by {interaction.user.mention}*",
            color=COLOR_MINT,
            tag=None,
            footer=None,
        )
        await interaction.channel.send(embed=embed, view=TicketControlView(self.bot))
        await interaction.followup.send("*ticket restored to active.*", ephemeral=True)

    @discord.ui.button(
        label="× delete",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:delete",
        row=0,
    )
    async def delete_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert isinstance(interaction.channel, discord.TextChannel)
        assert isinstance(interaction.user, discord.Member)

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
                "*only staff can delete archived tickets.*", ephemeral=True
            )

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self)
        await execute_close_sequence(self.bot, interaction.channel, interaction.user, interaction)


class TicketControlView(discord.ui.View):
    """In-channel action controls for active tickets."""
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

        notice = create_clean_embed(
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

        alert = create_clean_embed(
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
        label="archive",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket:archive",
        row=0,
    )
    async def archive_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        assert isinstance(interaction.channel, discord.TextChannel)

        # Disable current panel
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self)

        # Update database record
        await self.bot.db.archive_ticket_record(interaction.channel.id)

        # Lock channel permissions for ticket owner (read-only)
        ticket_data = await self.bot.db.get_ticket_by_channel(interaction.channel.id)
        if ticket_data:
            owner = interaction.guild.get_member(ticket_data["owner_id"])
            if owner:
                await interaction.channel.set_permissions(
                    owner,
                    view_channel=True,
                    send_messages=False,
                    add_reactions=False,
                    read_message_history=True,
                )

        # Move to archive category if configured
        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
        archive_cat_id = settings.get("ticket_archive_category_id")
        if archive_cat_id:
            arch_cat = interaction.guild.get_channel(archive_cat_id)
            if isinstance(arch_cat, discord.CategoryChannel):
                try:
                    await interaction.channel.edit(category=arch_cat)
                except discord.HTTPException:
                    pass

        # Rename channel with arch- prefix
        if not interaction.channel.name.startswith("arch-"):
            clean_name = f"arch-{interaction.channel.name}"[:95]
            try:
                await interaction.channel.edit(name=clean_name)
            except discord.HTTPException:
                pass

        # Generate and send transcript to log channel
        await generate_and_log_transcript(self.bot, interaction.channel, interaction.user, action_name="archived")

        # Post archive notice with Reopen & Delete controls
        arch_embed = create_clean_embed(
            description=(
                f"**ticket archived**\n"
                f"╰ **archived by:** {interaction.user.mention}\n"
                f"╰ **transcript:** saved & logged\n"
                f"╰ **member status:** read-only (new ticket creation locked)\n\n"
                "*staff can restore or permanently remove this room using the actions below.*"
            ),
            color=COLOR_OBSIDIAN,
            tag=None,
            footer=None,
        )
        await interaction.channel.send(embed=arch_embed, view=TicketArchivedView(self.bot))

    @discord.ui.button(
        label="× close",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:close",
        row=0,
    )
    async def close_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert isinstance(interaction.channel, discord.TextChannel)
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self)
        await execute_close_sequence(self.bot, interaction.channel, interaction.user, interaction)


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
        # Prevent users with open or archived tickets from opening another
        existing = await self.bot.db.get_open_ticket_by_user(
            interaction.guild.id, interaction.user.id
        )
        if existing:
            ch = interaction.guild.get_channel(existing["channel_id"])
            if ch:
                status_str = "archived" if existing.get("status") == "archived" else "active"
                return await interaction.response.send_message(
                    f"*you already have an {status_str} ticket: {ch.mention}. you cannot open a new ticket until staff deletes or closes your existing one.*",
                    ephemeral=True,
                )
            else:
                await self.bot.db.close_ticket_record(existing["channel_id"])

        try:
            await interaction.response.send_modal(OpenTicketDropdownModal(self.bot))
        except discord.HTTPException:
            # Fallback if specific client rejects dropdown directly inside modal
            embed = kyomi_embed(
                description="╰ *choose a category for your ticket below:*",
                color=COLOR_OBSIDIAN,
            )
            await interaction.response.send_message(
                embed=embed,
                view=EphemeralCategorySelectView(self.bot),
                ephemeral=True,
            )


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
                label="◈ partnership",
                value="partnership",
                description="server partnerships, collaborations & events",
            ),
            discord.SelectOption(
                label="✦ support",
                value="support",
                description="general questions, roles, or server help",
            ),
            discord.SelectOption(
                label="⊘ report",
                value="report",
                description="privately report a member, scam, or rule violation",
            ),
            discord.SelectOption(
                label="✧ staff application",
                value="staff application",
                description="apply for trial mod, staff, or helper positions",
            ),
            discord.SelectOption(
                label="◇ perk claiming",
                value="perk claiming",
                description="claim server booster, donor, or event rewards",
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


class CustomPanelModal(discord.ui.Modal, title="ticket panel builder"):
    panel_text = discord.ui.TextInput(
        label="panel content (supports **bold** & spacing)",
        style=discord.TextStyle.paragraph,
        placeholder="write your message here...\n\nuse **bold**, # headers, or blank lines for spacing",
        default="**@  303**\n\nneed assistance, partnerships, or reporting?\nclick below to open a ticket.",
        required=True,
        max_length=2000,
    )
    emoji_input = discord.ui.TextInput(
        label="button emoji (any server or unicode)",
        placeholder="e.g. 🦋 or paste custom <:name:id>",
        default="🦋",
        required=False,
        max_length=100,
    )
    button_label_input = discord.ui.TextInput(
        label="button text (leave empty for icon only)",
        placeholder="e.g. open ticket (or leave blank)",
        required=False,
        max_length=80,
    )
    title_input = discord.ui.TextInput(
        label="header / title (optional, leave blank)",
        placeholder="optional embed title header",
        required=False,
        max_length=100,
    )
    footer_input = discord.ui.TextInput(
        label="footer text (optional, leave blank)",
        placeholder="leave blank for no footer",
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

        # Clean outer newlines while preserving all internal spacing and blank lines
        description = self.panel_text.value.strip("\r\n")

        embed = create_clean_embed(
            title=panel_title,
            description=description,
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
            "╰ *ticket panel deployed.*", ephemeral=True
        )


class TicketsCog(commands.Cog, name="Tickets"):
    """Minimalist dark ticket panel, custom emojis, archive mode, and clean transcripts."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(TicketButtonView(self.bot))
        self.bot.add_view(TicketPanelView(self.bot))
        self.bot.add_view(TicketControlView(self.bot))
        self.bot.add_view(TicketArchivedView(self.bot))

    ticket_group = app_commands.Group(
        name="ticket",
        description="configure and drop customized support ticket panels.",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @ticket_group.command(
        name="setup",
        description="configure the category, log channel, staff role, and optional archive category.",
    )
    async def ticket_setup(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
        log_channel: discord.TextChannel,
        support_role: discord.Role | None = None,
        archive_category: discord.CategoryChannel | None = None,
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
        if archive_category:
            await self.bot.db.update_guild_setting(
                interaction.guild.id, "ticket_archive_category_id", archive_category.id
            )

        embed = kyomi_embed(
            description=(
                f"**tickets configured**\n"
                f"╰ **active category:** `{category.name.lower()}`\n"
                f"╰ **archive category:** `{archive_category.name.lower() if archive_category else 'none'}`\n"
                f"╰ **transcripts:** {log_channel.mention}\n"
                f"╰ **staff role:** {support_role.mention if support_role else '*mods only*'}\n\n"
                "*use `/ticket panel` or `/ticket builder` to deploy your panel.*"
            ),
            color=COLOR_OBSIDIAN,
            tag=None,
            footer=None,
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ticket_group.command(
        name="panel",
        description="open the modal popup window to design your ticket panel with bold text & spacing.",
    )
    async def ticket_panel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CustomPanelModal(self.bot))

    @ticket_group.command(
        name="builder",
        description="open the modal popup window to design your ticket panel with bold text & spacing.",
    )
    async def ticket_builder(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CustomPanelModal(self.bot))

    @ticket_group.command(
        name="archive",
        description="archive the current ticket channel (locks channel & logs transcript).",
    )
    async def ticket_archive(self, interaction: discord.Interaction):
        assert isinstance(interaction.channel, discord.TextChannel)
        ticket = await self.bot.db.get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message(
                "*this channel is not an active ticket room.*", ephemeral=True
            )

        await self.bot.db.archive_ticket_record(interaction.channel.id)

        owner = interaction.guild.get_member(ticket["owner_id"])
        if owner:
            await interaction.channel.set_permissions(
                owner,
                view_channel=True,
                send_messages=False,
                add_reactions=False,
                read_message_history=True,
            )

        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
        archive_cat_id = settings.get("ticket_archive_category_id")
        if archive_cat_id:
            arch_cat = interaction.guild.get_channel(archive_cat_id)
            if isinstance(arch_cat, discord.CategoryChannel):
                try:
                    await interaction.channel.edit(category=arch_cat)
                except discord.HTTPException:
                    pass

        if not interaction.channel.name.startswith("arch-"):
            clean_name = f"arch-{interaction.channel.name}"[:95]
            try:
                await interaction.channel.edit(name=clean_name)
            except discord.HTTPException:
                pass

        await generate_and_log_transcript(self.bot, interaction.channel, interaction.user, action_name="archived")

        arch_embed = create_clean_embed(
            description=(
                f"**ticket archived**\n"
                f"╰ **archived by:** {interaction.user.mention}\n"
                f"╰ **transcript:** saved & logged\n"
                f"╰ **member status:** read-only (new ticket creation locked)\n\n"
                "*staff can restore or permanently remove this room using the actions below.*"
            ),
            color=COLOR_OBSIDIAN,
            tag=None,
            footer=None,
        )
        await interaction.channel.send(embed=arch_embed, view=TicketArchivedView(self.bot))
        await interaction.response.send_message("╰ *ticket archived.*", ephemeral=True)

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
