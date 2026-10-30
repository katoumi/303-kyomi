import datetime
import discord
from discord import app_commands
from discord.ext import commands
from ui_theme import (
    COLOR_AMBER,
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    ansi_block,
    kyomi_embed,
)


class LoggingCog(commands.Cog, name="Logging"):
    """Dark-aesthetic server audit & mod logs."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    config_group = app_commands.Group(
        name="config",
        description="set up log channels and warning punishments.",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @config_group.command(
        name="modlog",
        description="set the channel for mod actions (/ban, /kick, /warn).",
    )
    async def set_modlog(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        assert interaction.guild is not None
        await self.bot.db.update_guild_setting(
            interaction.guild.id, "mod_log_channel_id", channel.id
        )
        await interaction.response.send_message(
            f"*mod logs will be sent to {channel.mention}.*",
            ephemeral=True,
        )

    @config_group.command(
        name="auditlog",
        description="set the channel for deleted/edited messages and joins/leaves.",
    )
    async def set_auditlog(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        assert interaction.guild is not None
        await self.bot.db.update_guild_setting(
            interaction.guild.id, "audit_log_channel_id", channel.id
        )
        await interaction.response.send_message(
            f"*audit logs will be sent to {channel.mention}.*",
            ephemeral=True,
        )

    @config_group.command(
        name="thresholds",
        description="set how many warnings trigger an auto-mute or auto-ban (0 = off).",
    )
    async def set_thresholds(
        self,
        interaction: discord.Interaction,
        timeout_warnings: app_commands.Range[int, 0, 20],
        ban_warnings: app_commands.Range[int, 0, 30],
    ):
        assert interaction.guild is not None
        await self.bot.db.update_guild_setting(
            interaction.guild.id, "warn_threshold_timeout", timeout_warnings
        )
        await self.bot.db.update_guild_setting(
            interaction.guild.id, "warn_threshold_ban", ban_warnings
        )
        await interaction.response.send_message(
            f"*updated: `{timeout_warnings}` warns = 1h mute  ·  `{ban_warnings}` warns = ban.*",
            ephemeral=True,
        )

    async def _send_audit_embed(
        self, guild: discord.Guild, embed: discord.Embed
    ) -> None:
        settings = await self.bot.db.get_guild_settings(guild.id)
        channel_id = settings.get("audit_log_channel_id")
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                pass

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        content = (message.content or "[media / attachment]")[:800]
        diff_block = ansi_block(f"\u001b[0;31m- {content}\u001b[0m")

        att_info = (
            "\n╰ **files:** " + ", ".join(f"`{a.filename}`" for a in message.attachments)
            if message.attachments
            else ""
        )

        embed = kyomi_embed(
            description=(
                f"**message deleted** in {message.channel.mention}\n"
                f"╰ **by:** {message.author.mention} (`{message.author.id}`){att_info}\n"
                f"{diff_block}"
            ),
            color=COLOR_CRIMSON,
            tag="303  •  deleted",
            guild=message.guild,
        )
        await self._send_audit_embed(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ):
        if not before.guild or before.author.bot:
            return
        if before.content == after.content:
            return

        old_txt = (before.content or "[empty]")[:400]
        new_txt = (after.content or "[empty]")[:400]
        diff_block = ansi_block(
            f"\u001b[0;31m- {old_txt}\u001b[0m",
            f"\u001b[0;32m+ {new_txt}\u001b[0m",
        )

        embed = kyomi_embed(
            description=(
                f"**message edited** in {before.channel.mention}  ·  [jump]({after.jump_url})\n"
                f"╰ **by:** {before.author.mention} (`{before.author.id}`)\n"
                f"{diff_block}"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  edited",
            guild=before.guild,
        )
        await self._send_audit_embed(before.guild, embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        account_age = datetime.datetime.now(datetime.timezone.utc) - member.created_at
        flag = (
            "\n╰ *† new account (<7 days old)*"
            if account_age.days < 7
            else ""
        )
        embed = kyomi_embed(
            description=(
                f"{member.mention} **joined the server**\n"
                f"╰ **id:** `{member.id}`\n"
                f"╰ **created:** {discord.utils.format_dt(member.created_at, 'R')} (`{account_age.days}d`){flag}"
            ),
            color=COLOR_OBSIDIAN if account_age.days >= 7 else COLOR_AMBER,
            tag="303  •  joined",
            guild=member.guild,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await self._send_audit_embed(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        roles = [r.mention for r in member.roles if r != member.guild.default_role]
        embed = kyomi_embed(
            description=(
                f"{member.mention} **left the server**\n"
                f"╰ **id:** `{member.id}`\n"
                f"╰ **roles:** {' '.join(roles[:12]) if roles else '*none*'}"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  left",
            guild=member.guild,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await self._send_audit_embed(member.guild, embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LoggingCog(bot))
