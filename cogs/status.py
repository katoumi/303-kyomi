import asyncio
import datetime
import logging
import discord
from discord import app_commands
from discord.ext import commands, tasks
from ui_theme import (
    COLOR_OBSIDIAN,
    kyomi_embed,
)

logger = logging.getLogger("mod-bot.status")


class StatusCog(commands.Cog, name="Status"):
    """Monochrome bot status voice channel tracker and presence heartbeat."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.status_loop.start()

    def cog_unload(self) -> None:
        self.status_loop.cancel()
        # Attempt synchronous/immediate async shutdown rename if event loop is running
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.mark_all_offline())
        except Exception:
            pass

    async def mark_all_offline(self) -> None:
        """Flips all configured status voice channels to offline on graceful shutdown."""
        for guild in self.bot.guilds:
            try:
                settings = await self.bot.db.get_guild_settings(guild.id)
                vc_id = settings.get("status_vc_id")
                if not vc_id:
                    continue
                channel = guild.get_channel(int(vc_id))
                if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                    continue
                offline_name = "○ 303 kyomi  •  offline"
                if channel.name != offline_name:
                    await channel.edit(name=offline_name, reason="303 kyomi  •  service shutdown")
            except Exception as exc:
                logger.debug("Failed to set offline name for guild %s: %s", guild.id, exc)

    async def render_status_name(self, guild: discord.Guild, settings: dict, is_online: bool = True) -> str:
        fmt = settings.get("status_vc_format") or "● 303 kyomi  •  online"
        ping = round(self.bot.latency * 1000) if self.bot.latency else 0
        dot = "●" if is_online else "○"
        status_text = "online" if is_online else "offline"
        name = fmt.replace("{status}", status_text).replace("{dot}", dot)
        name = name.replace("{ping}", f"{ping}ms").replace("{name}", "303 kyomi")
        return name[:100]

    @tasks.loop(minutes=10)
    async def status_loop(self):
        """Periodically refreshes the status voice channel (10m loop avoids Discord 2-rename/10m rate limits)."""
        if not self.bot.is_ready():
            return

        for guild in self.bot.guilds:
            try:
                settings = await self.bot.db.get_guild_settings(guild.id)
                vc_id = settings.get("status_vc_id")
                if not vc_id:
                    continue

                channel = guild.get_channel(int(vc_id))
                if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                    continue

                target_name = await self.render_status_name(guild, settings, is_online=True)
                if channel.name != target_name:
                    await channel.edit(name=target_name, reason="303 kyomi  •  periodic status sync")
            except discord.RateLimited as rle:
                logger.warning("Status VC rate limit hit on guild %s: retry in %ss", guild.id, rle.retry_after)
                break
            except Exception as exc:
                logger.debug("Error in status_loop for guild %s: %s", guild.id, exc)

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.bot.wait_until_ready()

    status_group = app_commands.Group(
        name="status",
        description="voice channel status indicator and uptime heartbeat.",
        guild_only=True,
    )

    @status_group.command(
        name="setup",
        description="bind a voice channel to display real-time bot online/offline status.",
    )
    @app_commands.describe(
        channel="the voice channel to display bot status",
        lock_channel="whether to lock the voice channel so members cannot join it (default: true)"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def status_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel,
        lock_channel: bool = True,
    ):
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        # Lock channel permissions for @everyone if requested
        if lock_channel:
            try:
                await channel.set_permissions(
                    interaction.guild.default_role,
                    connect=False,
                    view_channel=True,
                    reason="303 kyomi  •  locked status voice channel",
                )
            except discord.Forbidden:
                pass

        await self.bot.db.update_guild_setting(interaction.guild.id, "status_vc_id", channel.id)
        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
        target_name = await self.render_status_name(interaction.guild, settings, is_online=True)

        try:
            await channel.edit(name=target_name, reason="303 kyomi  •  status channel link")
        except discord.Forbidden:
            await interaction.followup.send(
                embed=kyomi_embed(
                    description="⊘ **permission denied**: missing `Manage Channels` permission to rename the voice channel.",
                    color=COLOR_OBSIDIAN,
                    tag="303  •  error",
                    guild=interaction.guild,
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            logger.warning("Could not rename status channel immediately: %s", exc)

        embed = kyomi_embed(
            description=(
                f"status voice channel linked to {channel.mention}.\n\n"
                f"╰ **display name:** `{target_name}`\n"
                f"╰ **sync frequency:** `every 10 minutes` *(rate-limit safe)*\n"
                f"╰ **on shutdown:** automatically flips to `○ offline`"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  status tracker",
            guild=interaction.guild,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @status_group.command(
        name="format",
        description="customize the status voice channel name template.",
    )
    @app_commands.describe(
        template="format template, e.g. '● 303 kyomi  •  online' or '● kyomi [{ping}]'"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def status_format(
        self,
        interaction: discord.Interaction,
        template: str,
    ):
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        clean_fmt = template.strip()[:60]
        await self.bot.db.update_guild_setting(interaction.guild.id, "status_vc_format", clean_fmt)

        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
        target_name = await self.render_status_name(interaction.guild, settings, is_online=True)

        vc_id = settings.get("status_vc_id")
        if vc_id:
            channel = interaction.guild.get_channel(int(vc_id))
            if isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                try:
                    await channel.edit(name=target_name, reason="303 kyomi  •  status format update")
                except Exception:
                    pass

        embed = kyomi_embed(
            description=(
                f"status format template updated.\n\n"
                f"╰ **template:** `{clean_fmt}`\n"
                f"╰ **preview:** `{target_name}`\n"
                f"╰ **tags:** `{{dot}}`, `{{status}}`, `{{ping}}`, `{{name}}`"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  status format",
            guild=interaction.guild,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @status_group.command(
        name="clear",
        description="unlink and disable the status voice channel tracker.",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def status_clear(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        await self.bot.db.update_guild_setting(interaction.guild.id, "status_vc_id", None)
        embed = kyomi_embed(
            description="status voice channel has been unlinked and disabled.",
            color=COLOR_OBSIDIAN,
            tag="303  •  status tracker",
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @status_group.command(
        name="check",
        description="check current bot vitals and status voice channel state.",
    )
    async def status_check(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
        vc_id = settings.get("status_vc_id")
        channel_str = f"<#{vc_id}>" if vc_id else "*none linked*"
        ping = round(self.bot.latency * 1000) if self.bot.latency else 0

        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = getattr(self.bot, "start_time", now)
        diff = now - start_time
        days = diff.days
        hours, rem = divmod(diff.seconds, 3600)
        minutes, _ = divmod(rem, 60)
        uptime = f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m"

        embed = kyomi_embed(
            description=(
                f"**303 kyomi**  •  vitals overview\n\n"
                f"╰ **status:** `● online`\n"
                f"╰ **gateway latency:** `{ping}ms`\n"
                f"╰ **uptime:** `{uptime}`\n"
                f"╰ **status vc:** {channel_str}\n"
                f"╰ **format:** `{settings.get('status_vc_format') or '● 303 kyomi  •  online'}`"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  system status",
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCog(bot))
