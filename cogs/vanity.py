import logging
import discord
from discord import app_commands
from discord.ext import commands
from ui_theme import COLOR_OBSIDIAN, COLOR_CRIMSON, COLOR_MINT, kyomi_embed

logger = logging.getLogger("mod-bot")


def get_member_custom_status(member: discord.Member) -> str:
    """Extracts custom status text from member activities if present."""
    if not member or not member.activities:
        return ""
    for act in member.activities:
        if isinstance(act, discord.CustomActivity):
            parts = []
            if act.name:
                parts.append(str(act.name))
            if act.state and act.state != act.name:
                parts.append(str(act.state))
            return " ".join(parts).strip()
    return ""


class VanityTrackerCog(commands.Cog, name="Vanity"):
    """Tracks custom vanity status (e.g. .gg/303) and auto-assigns supporter roles."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    vanity_group = app_commands.Group(
        name="vanity",
        description="track and reward members with server vanity url in custom status.",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    async def _process_member_vanity(
        self,
        guild: discord.Guild,
        member: discord.Member,
        settings: dict | None = None,
    ) -> bool | None:
        """Evaluates a member's custom status against the server vanity phrase.
        Returns True if awarded, False if revoked, None if unchanged/disabled.
        """
        if member.bot:
            return None

        if not settings:
            settings = await self.bot.db.get_guild_settings(guild.id)

        if not settings.get("vanity_enabled"):
            return None

        phrase = (settings.get("vanity_phrase") or "").strip().lower()
        role_id = settings.get("vanity_role_id")
        if not phrase or not role_id:
            return None

        role = guild.get_role(role_id)
        if not role:
            return None

        # Check bot hierarchy permissions
        if guild.me.top_role <= role:
            logger.warning(
                "Vanity role '%s' is higher than or equal to bot's top role in %s",
                role.name,
                guild.name,
            )
            return None

        status_text = get_member_custom_status(member)
        has_phrase = phrase in status_text.lower() if status_text else False
        has_role = role in member.roles

        log_channel_id = settings.get("vanity_channel_id")
        log_channel = guild.get_channel(log_channel_id) if log_channel_id else None

        if has_phrase and not has_role:
            try:
                await member.add_roles(
                    role, reason=f"303 kyomi: vanity detected in status ({phrase})"
                )
                await self.bot.db.add_vanity_supporter(guild.id, member.id, status_text)
                if isinstance(log_channel, discord.TextChannel):
                    embed = kyomi_embed(
                        title="✧ vanity rep awarded",
                        description=(
                            f"**member:** {member.mention} (`{member.id}`)\n"
                            f"╰ **status:** `{status_text}`\n"
                            f"╰ **role granted:** {role.mention}"
                        ),
                        color=COLOR_MINT,
                        guild=guild,
                    )
                    await log_channel.send(embed=embed)
                return True
            except discord.Forbidden:
                logger.error("Missing permissions to add vanity role to %s", member.name)
            except discord.HTTPException as e:
                logger.error("HTTP error adding vanity role: %s", e)

        elif not has_phrase and has_role:
            try:
                await member.remove_roles(
                    role, reason="303 kyomi: vanity status removed"
                )
                await self.bot.db.remove_vanity_supporter(guild.id, member.id)
                if isinstance(log_channel, discord.TextChannel):
                    embed = kyomi_embed(
                        title="○ vanity rep revoked",
                        description=(
                            f"**member:** {member.mention} (`{member.id}`)\n"
                            f"╰ **status:** `{status_text or 'none'}`\n"
                            f"╰ **role removed:** {role.name}"
                        ),
                        color=COLOR_OBSIDIAN,
                        guild=guild,
                    )
                    await log_channel.send(embed=embed)
                return False
            except discord.Forbidden:
                logger.error("Missing permissions to remove vanity role from %s", member.name)
            except discord.HTTPException as e:
                logger.error("HTTP error removing vanity role: %s", e)

        elif has_phrase and has_role:
            # Refresh recorded status text in db
            await self.bot.db.add_vanity_supporter(guild.id, member.id, status_text)

        return None

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        """Listens for custom status change in real time."""
        if not after.guild:
            return

        old_status = get_member_custom_status(before)
        new_status = get_member_custom_status(after)

        # Only trigger if status text has meaningfully changed
        if old_status != new_status:
            await self._process_member_vanity(after.guild, after)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Inspects custom status when a user joins the server."""
        await self._process_member_vanity(member.guild, member)

    @vanity_group.command(
        name="setup",
        description="configure the vanity status tracker and supporter role.",
    )
    @app_commands.describe(
        phrase="the string to search for in user custom status (e.g. .gg/303 or /303)",
        role="the reward role given to active vanity supporters",
        log_channel="optional channel to log role awards and revocations",
        enabled="whether the vanity tracker is active",
    )
    async def vanity_setup(
        self,
        interaction: discord.Interaction,
        phrase: str,
        role: discord.Role,
        log_channel: discord.TextChannel | None = None,
        enabled: bool = True,
    ) -> None:
        assert interaction.guild is not None

        if interaction.guild.me.top_role <= role:
            return await interaction.response.send_message(
                f"× *error: the role {role.mention} is higher than or equal to my highest role.*",
                ephemeral=True,
            )

        clean_phrase = phrase.strip().lower()
        await self.bot.db.update_guild_setting(
            interaction.guild.id, "vanity_enabled", 1 if enabled else 0
        )
        await self.bot.db.update_guild_setting(
            interaction.guild.id, "vanity_phrase", clean_phrase
        )
        await self.bot.db.update_guild_setting(
            interaction.guild.id, "vanity_role_id", role.id
        )
        if log_channel:
            await self.bot.db.update_guild_setting(
                interaction.guild.id, "vanity_channel_id", log_channel.id
            )

        embed = kyomi_embed(
            title="✦ vanity status tracker armed",
            description=(
                f"╰ **status phrase:** `{clean_phrase}`\n"
                f"╰ **supporter role:** {role.mention}\n"
                f"╰ **feed logs:** {log_channel.mention if log_channel else '*disabled*'}\n"
                f"╰ **system state:** `{'active' if enabled else 'disabled'}`\n\n"
                "*members who place this phrase in their custom discord status will receive the role automatically.*"
            ),
            color=COLOR_OBSIDIAN,
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed)

    @vanity_group.command(
        name="check",
        description="inspect a member's current custom status and vanity eligibility.",
    )
    @app_commands.describe(member="target member to inspect")
    async def vanity_check(
        self, interaction: discord.Interaction, member: discord.Member
    ) -> None:
        assert interaction.guild is not None

        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
        phrase = (settings.get("vanity_phrase") or ".gg/303").strip().lower()
        role_id = settings.get("vanity_role_id")
        role = interaction.guild.get_role(role_id) if role_id else None

        status_text = get_member_custom_status(member)
        has_phrase = phrase in status_text.lower() if status_text else False
        has_role = (role in member.roles) if role else False

        embed = kyomi_embed(
            title=f"◈ vanity audit: {member.name}",
            description=(
                f"╰ **target user:** {member.mention} (`{member.id}`)\n"
                f"╰ **detected status:** `{status_text if status_text else 'no custom status'}`\n"
                f"╰ **target phrase:** `{phrase}`\n"
                f"╰ **phrase match:** `{'yes ✦' if has_phrase else 'no ○'}`\n"
                f"╰ **supporter role:** {role.mention if role else '*not configured*'} (`{'held' if has_role else 'missing'}`)"
            ),
            color=COLOR_MINT if has_phrase else COLOR_OBSIDIAN,
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @vanity_group.command(
        name="scan",
        description="perform a full server scan across all cached members to sync vanity roles.",
    )
    async def vanity_scan(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
        if not settings.get("vanity_enabled"):
            return await interaction.followup.send(
                "*vanity tracker is currently disabled. run `/vanity setup` to configure.*"
            )

        awarded = 0
        revoked = 0
        total_scanned = 0

        for member in interaction.guild.members:
            if member.bot:
                continue
            total_scanned += 1
            res = await self._process_member_vanity(
                interaction.guild, member, settings=settings
            )
            if res is True:
                awarded += 1
            elif res is False:
                revoked += 1

        embed = kyomi_embed(
            title="✦ vanity scan complete",
            description=(
                f"╰ **members scanned:** `{total_scanned}`\n"
                f"╰ **roles awarded:** `{awarded}`\n"
                f"╰ **roles revoked:** `{revoked}`"
            ),
            color=COLOR_OBSIDIAN,
            guild=interaction.guild,
        )
        await interaction.followup.send(embed=embed)

    @vanity_group.command(
        name="list",
        description="list current active vanity status supporters.",
    )
    async def vanity_list(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None

        supporters = await self.bot.db.get_vanity_supporters(interaction.guild.id)
        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
        phrase = settings.get("vanity_phrase") or ".gg/303"

        if not supporters:
            return await interaction.response.send_message(
                f"*no active vanity supporters detected matching `{phrase}`.*",
                ephemeral=True,
            )

        lines = []
        for i, row in enumerate(supporters[:25], start=1):
            member = interaction.guild.get_member(row["user_id"])
            tag = member.name if member else f"user_{row['user_id']}"
            st = (row.get("status_text") or phrase)[:32]
            lines.append(f"`{i:02d}` **{tag}** — `{st}`")

        embed = kyomi_embed(
            title=f"✦ vanity supporters ({len(supporters)})",
            description="\n".join(lines),
            color=COLOR_OBSIDIAN,
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VanityTrackerCog(bot))
