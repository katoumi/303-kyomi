import asyncio
import datetime
import io
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
            tag="303  •  claimed",
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
            tag="303  •  priority",
        )
        await interaction.channel.send(embed=alert)

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

        # Disable all buttons on the ticket panel so it can't be clicked twice
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self)

        # Send initial countdown message that will be edited second-by-second
        bar_init = progress_bar(5, 5, length=10)
        countdown_embed = kyomi_embed(
            description=f"╰ *saving transcript & closing in **`5s`**  `{bar_init}`*",
            color=COLOR_CRIMSON,
            tag="303  •  closing",
        )
        status_msg = await interaction.channel.send(embed=countdown_embed)

        # Compile transcript while starting the countdown
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
                cat_str = ticket_data["category"] if ticket_data else "n/a"
                embed = kyomi_embed(
                    description=(
                        f"**closed #{interaction.channel.name}**\n"
                        f"╰ **opened by:** {owner_str}\n"
                        f"╰ **topic:** `{cat_str}`\n"
                        f"╰ **closed by:** {interaction.user.mention}"
                    ),
                    color=COLOR_OBSIDIAN,
                    tag="303  •  transcripts",
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

        # Live edit countdown: 4s -> 3s -> 2s -> 1s -> 0s
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
        assert interaction.guild is not None
        assert isinstance(interaction.user, discord.Member)

        existing = await self.bot.db.get_open_ticket_by_user(
            interaction.guild.id, interaction.user.id
        )
        if existing:
            ch = interaction.guild.get_channel(existing["channel_id"])
            if ch:
                return await interaction.response.send_message(
                    f"*you already have a ticket open: {ch.mention}*",
                    ephemeral=True,
                )
            else:
                await self.bot.db.close_ticket_record(existing["channel_id"])

        category_label = self.values[0]
        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
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
                reason=f"ticket by {interaction.user}",
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "*i need `manage channels` permission to create tickets.*",
                ephemeral=True,
            )

        ticket_id = await self.bot.db.create_ticket(
            interaction.guild.id,
            ticket_channel.id,
            interaction.user.id,
            category_label,
        )

        embed = kyomi_embed(
            description=(
                f"**ticket #{ticket_id:03d}**  ·  `{category_label}`\n\n"
                f"hey {interaction.user.mention} — drop what you need below (screenshots, links, or details) and staff will be right with you."
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  support",
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
            view=TicketControlView(self.bot),
        )

        await interaction.response.send_message(
            f"*opened {ticket_channel.mention}*",
            ephemeral=True,
        )


class TicketPanelView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect(bot))


class TicketsCog(commands.Cog, name="Tickets"):
    """Dark-aesthetic ticket panel & live-countdown transcripts."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(TicketPanelView(self.bot))
        self.bot.add_view(TicketControlView(self.bot))

    ticket_group = app_commands.Group(
        name="ticket",
        description="set up and post the support ticket panel.",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @ticket_group.command(
        name="setup",
        description="set the ticket category, transcript log channel, and staff role.",
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
                "*use `/ticket panel` to drop the dropdown menu in any channel.*"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  setup",
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ticket_group.command(
        name="panel",
        description="drop the dark-aesthetic ticket panel in this channel.",
    )
    async def ticket_panel(
        self,
        interaction: discord.Interaction,
        title: str = "support & reports",
        description: str = (
            "need to talk to staff, report someone, or appeal a mute?\n"
            "pick a topic below to open a private room.\n\n"
            "╰ `✦ general` — questions & server help\n"
            "╰ `◈ report` — privately report a member\n"
            "╰ `✧ appeal` — appeal a warn or mute\n"
            "╰ `◇ other` — partnerships & owners"
        ),
    ):
        assert isinstance(interaction.channel, discord.TextChannel)
        embed = kyomi_embed(
            title=title,
            description=description,
            color=COLOR_OBSIDIAN,
            tag="303  •  desk",
            guild=interaction.guild,
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        await interaction.channel.send(embed=embed, view=TicketPanelView(self.bot))
        await interaction.response.send_message(
            "*posted ticket panel.*", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot))
