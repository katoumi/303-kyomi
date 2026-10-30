import datetime
import discord
from discord import app_commands
from discord.ext import commands
from ui_theme import (
    COLOR_AMBER,
    COLOR_CRIMSON,
    COLOR_MINT,
    COLOR_OBSIDIAN,
    kyomi_embed,
)


class ModerationCog(commands.Cog, name="Moderation"):
    """Dark-aesthetic moderation commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def send_mod_log(
        self,
        guild: discord.Guild,
        action: str,
        target: discord.abc.Snowflake | discord.User | discord.Member,
        moderator: discord.Member | discord.User,
        reason: str,
        color: discord.Color = COLOR_OBSIDIAN,
        extra_fields: dict[str, str] | None = None,
    ) -> int:
        case_id = await self.bot.db.log_mod_case(
            guild.id, action.lower(), target.id, moderator.id, reason
        )
        settings = await self.bot.db.get_guild_settings(guild.id)
        channel_id = settings.get("mod_log_channel_id")
        if not channel_id:
            return case_id

        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return case_id

        target_display = (
            f"{target.mention} (`{target.id}`)"
            if hasattr(target, "mention")
            else f"`{target.id}`"
        )
        lines = [
            f"**case #{case_id:03d}**  ·  `{action.lower()}`",
            f"╰ **user:** {target_display}",
            f"╰ **staff:** {moderator.mention}",
            f"╰ **reason:** {reason}",
        ]
        if extra_fields:
            for k, v in extra_fields.items():
                lines.append(f"╰ **{k.lower()}:** {v}")

        embed = kyomi_embed(
            description="\n".join(lines),
            color=color,
            tag="303  •  modlog",
            guild=guild,
        )
        if hasattr(target, "display_avatar") and target.display_avatar:
            embed.set_thumbnail(url=target.display_avatar.url)

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass
        return case_id

    def _check_hierarchy(
        self, interaction: discord.Interaction, target: discord.Member
    ) -> str | None:
        assert interaction.guild is not None
        assert isinstance(interaction.user, discord.Member)

        if target.id == interaction.user.id:
            return "*you can't do that to yourself.*"
        if target.id == interaction.guild.owner_id:
            return "*you can't moderate the server owner.*"
        if (
            interaction.user.id != interaction.guild.owner_id
            and target.top_role >= interaction.user.top_role
        ):
            return "*their highest role is equal to or above yours.*"
        if target.top_role >= interaction.guild.me.top_role:
            return "*their highest role is equal to or above mine.*"
        return None

    @app_commands.command(name="kick", description="kick a member from the server.")
    @app_commands.describe(member="member to kick", reason="reason")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.guild_only()
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "no reason given",
    ):
        err = self._check_hierarchy(interaction, member)
        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        assert interaction.guild is not None
        try:
            dm = kyomi_embed(
                description=f"you were kicked from **{interaction.guild.name.lower()}**\n╰ **reason:** {reason}",
                color=COLOR_AMBER,
                tag="303  •  kicked",
                guild=interaction.guild,
            )
            await member.send(embed=dm)
        except discord.HTTPException:
            pass

        await member.kick(reason=f"{interaction.user}: {reason}")
        case_id = await self.send_mod_log(
            interaction.guild,
            "kick",
            member,
            interaction.user,
            reason,
            color=COLOR_AMBER,
        )
        embed = kyomi_embed(
            description=f"kicked {member.mention}  ·  `#{case_id:03d}`\n╰ **reason:** {reason}",
            color=COLOR_OBSIDIAN,
            tag="303  •  kick",
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ban", description="ban a member from the server.")
    @app_commands.describe(
        member="member to ban",
        reason="reason",
        delete_days="days of messages to delete (0-7)",
    )
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "no reason given",
        delete_days: app_commands.Range[int, 0, 7] = 0,
    ):
        err = self._check_hierarchy(interaction, member)
        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        assert interaction.guild is not None
        try:
            dm = kyomi_embed(
                description=f"you were banned from **{interaction.guild.name.lower()}**\n╰ **reason:** {reason}",
                color=COLOR_CRIMSON,
                tag="303  •  banned",
                guild=interaction.guild,
            )
            await member.send(embed=dm)
        except discord.HTTPException:
            pass

        await interaction.guild.ban(
            member,
            reason=f"{interaction.user}: {reason}",
            delete_message_days=delete_days,
        )

        case_id = await self.send_mod_log(
            interaction.guild,
            "ban",
            member,
            interaction.user,
            reason,
            color=COLOR_CRIMSON,
        )
        embed = kyomi_embed(
            description=f"banned {member.mention}  ·  `#{case_id:03d}`\n╰ **reason:** {reason}",
            color=COLOR_CRIMSON,
            tag="303  •  ban",
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unban", description="unban a user by their id.")
    @app_commands.describe(user_id="user id", reason="reason")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: str = "no reason given",
    ):
        assert interaction.guild is not None
        try:
            uid = int(user_id.strip())
        except ValueError:
            return await interaction.response.send_message(
                "*enter a valid user id.*", ephemeral=True
            )

        user_obj = discord.Object(id=uid)
        try:
            await interaction.guild.unban(
                user_obj, reason=f"{interaction.user}: {reason}"
            )
        except discord.NotFound:
            return await interaction.response.send_message(
                "*that user isn't banned.*", ephemeral=True
            )

        case_id = await self.send_mod_log(
            interaction.guild,
            "unban",
            user_obj,
            interaction.user,
            reason,
            color=COLOR_MINT,
        )
        embed = kyomi_embed(
            description=f"unbanned `<@{uid}>`  ·  `#{case_id:03d}`\n╰ **reason:** {reason}",
            color=COLOR_OBSIDIAN,
            tag="303  •  unban",
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="timeout", description="mute a member temporarily.")
    @app_commands.describe(
        member="member to mute",
        minutes="minutes (1 - 40320)",
        reason="reason",
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str = "no reason given",
    ):
        err = self._check_hierarchy(interaction, member)
        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        assert interaction.guild is not None
        duration = datetime.timedelta(minutes=minutes)
        await member.timeout(duration, reason=f"{interaction.user}: {reason}")

        case_id = await self.send_mod_log(
            interaction.guild,
            "mute",
            member,
            interaction.user,
            reason,
            color=COLOR_AMBER,
            extra_fields={"duration": f"`{minutes}m`"},
        )
        embed = kyomi_embed(
            description=f"muted {member.mention} for **`{minutes}m`**  ·  `#{case_id:03d}`\n╰ **reason:** {reason}",
            color=COLOR_OBSIDIAN,
            tag="303  •  mute",
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="untimeout", description="unmute a member.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def untimeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "no reason given",
    ):
        err = self._check_hierarchy(interaction, member)
        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        assert interaction.guild is not None
        await member.timeout(None, reason=f"{interaction.user}: {reason}")
        case_id = await self.send_mod_log(
            interaction.guild,
            "unmute",
            member,
            interaction.user,
            reason,
            color=COLOR_MINT,
        )
        embed = kyomi_embed(
            description=f"unmuted {member.mention}  ·  `#{case_id:03d}`",
            color=COLOR_OBSIDIAN,
            tag="303  •  unmute",
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="purge", description="clean up messages in this channel."
    )
    @app_commands.describe(
        amount="number of messages (1-100)",
        member="optional: only from this user",
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
        member: discord.Member | None = None,
    ):
        assert interaction.guild is not None
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message(
                "*use this in a text channel.*", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        check = (lambda m: m.author.id == member.id) if member else (lambda m: True)
        deleted = await interaction.channel.purge(limit=amount, check=check)

        scope = f"from {member.mention}" if member else "in total"
        await self.send_mod_log(
            interaction.guild,
            "purge",
            member or interaction.user,
            interaction.user,
            f"deleted {len(deleted)} messages {scope} in {interaction.channel.mention}",
            color=COLOR_OBSIDIAN,
        )
        await interaction.followup.send(
            f"*cleaned up **`{len(deleted)}`** messages {scope}.*",
            ephemeral=True,
        )

    @app_commands.command(
        name="warn",
        description="warn a member.",
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ):
        err = self._check_hierarchy(interaction, member)
        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        assert interaction.guild is not None
        warn_id = await self.bot.db.add_warning(
            interaction.guild.id, member.id, interaction.user.id, reason
        )
        all_warnings = await self.bot.db.get_warnings(interaction.guild.id, member.id)
        warn_count = len(all_warnings)

        try:
            dm = kyomi_embed(
                description=(
                    f"you got a warning in **{interaction.guild.name.lower()}**\n"
                    f"╰ **reason:** {reason}\n"
                    f"╰ **total warns:** `{warn_count}`"
                ),
                color=COLOR_AMBER,
                tag="303  •  warned",
                guild=interaction.guild,
            )
            await member.send(embed=dm)
        except discord.HTTPException:
            pass

        case_id = await self.send_mod_log(
            interaction.guild,
            f"warn #{warn_id}",
            member,
            interaction.user,
            reason,
            color=COLOR_AMBER,
            extra_fields={"warns": f"`{warn_count}`"},
        )

        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
        ban_threshold = settings.get("warn_threshold_ban") or 0
        timeout_threshold = settings.get("warn_threshold_timeout") or 0
        escalation_note = ""

        if ban_threshold > 0 and warn_count >= ban_threshold:
            try:
                await interaction.guild.ban(
                    member, reason=f"reached {warn_count} warnings"
                )
                escalation_note = f"\n╰ *hit `{warn_count}` warns -> **auto-banned***"
            except discord.Forbidden:
                pass
        elif timeout_threshold > 0 and warn_count >= timeout_threshold:
            try:
                await member.timeout(
                    datetime.timedelta(hours=1),
                    reason=f"reached {warn_count} warnings",
                )
                escalation_note = f"\n╰ *hit `{warn_count}` warns -> **muted 1h***"
            except discord.Forbidden:
                pass

        embed = kyomi_embed(
            description=(
                f"warned {member.mention}  ·  `#{warn_id}` *(total: `{warn_count}`)*\n"
                f"╰ **reason:** {reason}{escalation_note}"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  warn",
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="warnings", description="check a member's warnings.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def warnings(
        self, interaction: discord.Interaction, member: discord.Member
    ):
        assert interaction.guild is not None
        records = await self.bot.db.get_warnings(interaction.guild.id, member.id)
        if not records:
            return await interaction.response.send_message(
                f"*{member.mention} is clean (0 warnings).*", ephemeral=True
            )

        lines = [
            f"╰ `#{r['id']}` {r['reason']}  — *<@{r['moderator_id']}>*"
            for r in records[:15]
        ]
        embed = kyomi_embed(
            description=f"**warnings for {member.name.lower()} ({len(records)})**\n" + "\n".join(lines),
            color=COLOR_OBSIDIAN,
            tag="303  •  warns",
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="delwarn", description="delete a warning by its id.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def delwarn(self, interaction: discord.Interaction, warning_id: int):
        assert interaction.guild is not None
        removed = await self.bot.db.remove_warning(interaction.guild.id, warning_id)
        if not removed:
            return await interaction.response.send_message(
                f"*couldn't find warn `#{warning_id}`.*", ephemeral=True
            )
        await interaction.response.send_message(
            f"*deleted warn `#{warning_id}`.*", ephemeral=True
        )

    @app_commands.command(name="clearwarns", description="clear all warnings for a member.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def clearwarns(
        self, interaction: discord.Interaction, member: discord.Member
    ):
        assert interaction.guild is not None
        count = await self.bot.db.clear_warnings(interaction.guild.id, member.id)
        await interaction.response.send_message(
            f"*cleared `{count}` warning(s) for {member.mention}.*"
        )

    @app_commands.command(name="slowmode", description="set channel slowmode.")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: app_commands.Range[int, 0, 21600],
    ):
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message(
                "*use this in a text channel.*", ephemeral=True
            )
        await interaction.channel.edit(slowmode_delay=seconds)
        msg = (
            "*turned off slowmode.*"
            if seconds == 0
            else f"*slowmode set to **`{seconds}s`**.*"
        )
        await interaction.response.send_message(msg)

    @app_commands.command(name="lock", description="lock the current channel.")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def lock(
        self,
        interaction: discord.Interaction,
        reason: str = "locked by staff",
    ):
        assert interaction.guild is not None
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message(
                "*use this in a text channel.*", ephemeral=True
            )
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite,
            reason=f"locked by {interaction.user}: {reason}",
        )
        embed = kyomi_embed(
            description=f"**channel locked**\n╰ {reason}",
            color=COLOR_CRIMSON,
            tag="303  •  locked",
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unlock", description="unlock the current channel.")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def unlock(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message(
                "*use this in a text channel.*", ephemeral=True
            )
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite,
            reason=f"unlocked by {interaction.user}",
        )
        embed = kyomi_embed(
            description="**channel unlocked**",
            color=COLOR_OBSIDIAN,
            tag="303  •  unlocked",
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
