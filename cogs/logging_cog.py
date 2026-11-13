from typing import Literal
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

    @app_commands.command(
        name="setlogs",
        description="set the channel for server logs (mod actions, automod, audit events).",
    )
    @app_commands.describe(
        channel="channel where logs will be sent",
        category="type of logs to route here (default: all logs)",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def setlogs_slash(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        category: Literal["all logs (mod + audit)", "moderation only", "audit only"] = "all logs (mod + audit)",
    ):
        assert interaction.guild is not None
        guild_id = interaction.guild.id

        if category == "all logs (mod + audit)":
            await self.bot.db.update_guild_setting(guild_id, "mod_log_channel_id", channel.id)
            await self.bot.db.update_guild_setting(guild_id, "audit_log_channel_id", channel.id)
            routing_desc = "mod actions (/ban, /kick, /warn, automod) + audit events (edits, deletes, joins)"
        elif category == "moderation only":
            await self.bot.db.update_guild_setting(guild_id, "mod_log_channel_id", channel.id)
            routing_desc = "mod actions (/ban, /kick, /warn, /timeout, automod, antiraid)"
        else:
            await self.bot.db.update_guild_setting(guild_id, "audit_log_channel_id", channel.id)
            routing_desc = "audit events (message edits, deletes, joins, leaves)"

        # Send verification ping to the target channel
        test_embed = kyomi_embed(
            description=(
                f"**logging channel linked**\n"
                f"╰ **configured by:** {interaction.user.mention}\n"
                f"╰ **routing:** `{category}`\n"
                f"╰ *303 kyomi will stream real-time events to this channel.*"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  logs",
            guild=interaction.guild,
        )
        test_status = "verified (test ping delivered)"
        try:
            await channel.send(embed=test_embed)
        except discord.Forbidden:
            test_status = "⚠️ warning: bot lacks 'Send Messages' or 'Embed Links' permissions in that channel"
        except Exception as e:
            test_status = f"⚠️ delivery error: {e}"

        confirm_embed = kyomi_embed(
            description=(
                f"**log channel configured**  ·  {channel.mention}\n"
                f"╰ **events:** `{category}`\n"
                f"╰ **routing:** {routing_desc}\n"
                f"╰ **status:** *{test_status}*"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  config",
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

    @app_commands.command(
        name="logs",
        description="check current moderation and audit logging channels.",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def logs_slash(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
        mod_ch = interaction.guild.get_channel(settings.get("mod_log_channel_id") or 0)
        audit_ch = interaction.guild.get_channel(settings.get("audit_log_channel_id") or 0)
        ticket_ch = interaction.guild.get_channel(settings.get("ticket_log_channel_id") or 0)

        mod_str = mod_ch.mention if isinstance(mod_ch, discord.TextChannel) else "*not set*"
        audit_str = audit_ch.mention if isinstance(audit_ch, discord.TextChannel) else "*not set*"
        ticket_str = (
            ticket_ch.mention
            if isinstance(ticket_ch, discord.TextChannel)
            else ("*falls back to mod log*" if mod_str != "*not set*" else "*not set*")
        )

        embed = kyomi_embed(
            description=(
                "**active log channels**\n"
                f"╰ **mod logs:** {mod_str}\n"
                f"╰ **audit logs:** {audit_str}\n"
                f"╰ **ticket transcripts:** {ticket_str}\n\n"
                "*(use `/setlogs <#channel>` or the dashboard to change)*"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  logs",
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.command(name="setlogs", aliases=["setlog", "modlog", "auditlog"])
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def prefix_setlogs(self, ctx: commands.Context, channel: discord.TextChannel | None = None):
        target = channel or ctx.channel
        if not isinstance(target, discord.TextChannel):
            return await ctx.send("*please specify a text channel.*")

        await self.bot.db.update_guild_setting(ctx.guild.id, "mod_log_channel_id", target.id)
        await self.bot.db.update_guild_setting(ctx.guild.id, "audit_log_channel_id", target.id)

        test_embed = kyomi_embed(
            description=(
                f"**logging channel linked**\n"
                f"╰ **configured by:** {ctx.author.mention}\n"
                f"╰ **routing:** `all logs (mod + audit)`\n"
                f"╰ *303 kyomi will stream real-time events to this channel.*"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  logs",
            guild=ctx.guild,
        )
        try:
            await target.send(embed=test_embed)
        except Exception:
            pass

        confirm = kyomi_embed(
            description=(
                f"**log channel configured**  ·  {target.mention}\n"
                f"╰ **routing:** mod actions + audit events"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  config",
            guild=ctx.guild,
        )
        await ctx.send(embed=confirm)

    @commands.command(name="logs")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def prefix_logs(self, ctx: commands.Context):
        settings = await self.bot.db.get_guild_settings(ctx.guild.id)
        mod_ch = ctx.guild.get_channel(settings.get("mod_log_channel_id") or 0)
        audit_ch = ctx.guild.get_channel(settings.get("audit_log_channel_id") or 0)
        mod_str = mod_ch.mention if isinstance(mod_ch, discord.TextChannel) else "*not set*"
        audit_str = audit_ch.mention if isinstance(audit_ch, discord.TextChannel) else "*not set*"

        embed = kyomi_embed(
            description=(
                "**active log channels**\n"
                f"╰ **mod logs:** {mod_str}\n"
                f"╰ **audit logs:** {audit_str}\n\n"
                "*(use `!setlogs <#channel>` to change)*"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  logs",
            guild=ctx.guild,
        )
        await ctx.send(embed=embed)

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
        channel_id = settings.get("audit_log_channel_id") or settings.get("mod_log_channel_id")
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            try:
                channel = await guild.fetch_channel(channel_id)
            except Exception:
                channel = None
        if isinstance(channel, (discord.TextChannel, discord.Thread)):
            try:
                await channel.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
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
