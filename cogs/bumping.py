import datetime
import time
import discord
from discord import app_commands
from discord.ext import commands, tasks
from ui_theme import (
    COLOR_AMBER,
    COLOR_OBSIDIAN,
    kyomi_embed,
    progress_bar,
)

DISBOARD_BOT_ID = 302050872383242240
BUMP_COOLDOWN_SECONDS = 7200  # 2 hours


class BumpingCog(commands.Cog, name="Bumping"):
    """Dark-aesthetic bump tracker, 2h reminder & auto-promo."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_autopromo_sent: dict[int, float] = {}
        self.bump_reminder_loop.start()
        self.autopromo_loop.start()

    def cog_unload(self) -> None:
        self.bump_reminder_loop.cancel()
        self.autopromo_loop.cancel()

    bump_group = app_commands.Group(
        name="bump",
        description="bump reminders, top bumpers, and auto-promo.",
        guild_only=True,
    )

    @bump_group.command(
        name="setup",
        description="set the bump channel and optional ping role.",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def bump_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        ping_role: discord.Role | None = None,
    ):
        assert interaction.guild is not None
        await self.bot.db.update_guild_setting(
            interaction.guild.id, "bump_channel_id", channel.id
        )
        await self.bot.db.update_guild_setting(
            interaction.guild.id,
            "bump_role_id",
            ping_role.id if ping_role else None,
        )
        embed = kyomi_embed(
            description=(
                f"**bump tracker set**\n"
                f"╰ **channel:** {channel.mention}\n"
                f"╰ **ping role:** {ping_role.mention if ping_role else '*none*'}\n\n"
                "*i'll track `/bump` automatically and ping when the 2h cooldown is up.*"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  bumps",
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bump_group.command(
        name="leaderboard",
        description="see the top server bumpers and next bump timer.",
    )
    async def bump_leaderboard(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        leaders = await self.bot.db.get_bump_leaderboard(interaction.guild.id, limit=10)
        settings = await self.bot.db.get_guild_settings(interaction.guild.id)
        next_ts = settings.get("next_bump_timestamp") or 0
        now = int(time.time())

        if next_ts > now:
            remaining = max(0, next_ts - now)
            elapsed = max(0, BUMP_COOLDOWN_SECONDS - remaining)
            bar = progress_bar(elapsed, BUMP_COOLDOWN_SECONDS, length=10)
            status_line = f"╰ **next bump:** <t:{next_ts}:R>  `{bar}`"
        else:
            bar = progress_bar(100, 100, length=10)
            status_line = f"╰ **● ready now:** click </bump:947088344167366698>  `{bar}`"

        if not leaders:
            board_block = "╰ *no bumps recorded yet*"
        else:
            top_count = max(1, leaders[0]["bump_count"])
            lines = []
            for idx, row in enumerate(leaders, start=1):
                mini_bar = progress_bar(row["bump_count"], top_count, length=6)
                lines.append(
                    f"`0{idx}` `{mini_bar}` <@{row['user_id']}> — **{row['bump_count']}**"
                )
            board_block = "\n".join(lines)

        embed = kyomi_embed(
            description=(
                f"**bump status**\n"
                f"{status_line}\n\n"
                f"**top bumpers**\n"
                f"{board_block}"
            ),
            color=COLOR_OBSIDIAN,
            tag=f"303  •  {interaction.guild.name.lower()}",
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed)

    @bump_group.command(
        name="autopromo",
        description="auto-post a custom promo or reminder message on a timer.",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def bump_autopromo(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
        interval_minutes: app_commands.Range[int, 30, 1440] = 120,
        message: str | None = None,
    ):
        assert interaction.guild is not None
        if not channel or not message:
            await self.bot.db.update_guild_setting(
                interaction.guild.id, "autopromo_channel_id", None
            )
            return await interaction.response.send_message(
                "*turned off auto-promo.*", ephemeral=True
            )

        await self.bot.db.update_guild_setting(
            interaction.guild.id, "autopromo_channel_id", channel.id
        )
        await self.bot.db.update_guild_setting(
            interaction.guild.id, "autopromo_interval_min", interval_minutes
        )
        await self.bot.db.update_guild_setting(
            interaction.guild.id, "autopromo_message", message
        )
        self._last_autopromo_sent[interaction.guild.id] = time.time()

        embed = kyomi_embed(
            description=(
                f"**auto-promo active**\n"
                f"╰ **channel:** {channel.mention}\n"
                f"╰ **every:** `{interval_minutes}m`\n"
                f"╰ **message:** {message}"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  autopromo",
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bump_group.command(
        name="simulate",
        description="test the bump tracker with a 60s countdown.",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def bump_simulate(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        assert isinstance(interaction.channel, discord.TextChannel)

        next_ts = int(time.time()) + 60
        total_bumps = await self.bot.db.record_bump(
            interaction.guild.id, interaction.user.id, next_ts
        )
        await self.bot.db.update_guild_setting(
            interaction.guild.id, "bump_channel_id", interaction.channel.id
        )

        embed = kyomi_embed(
            description=(
                f"recorded a bump for {interaction.user.mention} *(test mode)*\n"
                f"╰ **your bumps:** `{total_bumps}`\n"
                f"╰ **next ping:** <t:{next_ts}:R>"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  bump",
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.id != DISBOARD_BOT_ID:
            return

        embed_text = ""
        if message.embeds:
            e = message.embeds[0]
            embed_text = f"{e.title or ''} {e.description or ''}".lower()

        if "bump done" not in embed_text and "bumped" not in embed_text:
            return

        bumper: discord.User | discord.Member | None = None
        if message.interaction_metadata:
            bumper = message.interaction_metadata.user
        elif message.interaction and message.interaction.user:
            bumper = message.interaction.user

        next_ts = int(time.time()) + BUMP_COOLDOWN_SECONDS
        user_id = bumper.id if bumper else self.bot.user.id
        total_bumps = await self.bot.db.record_bump(
            message.guild.id, user_id, next_ts
        )

        settings = await self.bot.db.get_guild_settings(message.guild.id)
        if not settings.get("bump_channel_id"):
            await self.bot.db.update_guild_setting(
                message.guild.id, "bump_channel_id", message.channel.id
            )

        embed = kyomi_embed(
            description=(
                f"thanks for bumping, {bumper.mention if bumper else 'fam'}.\n"
                f"╰ **total bumps:** `{total_bumps}`\n"
                f"╰ **next bump:** <t:{next_ts}:R> *(<t:{next_ts}:t>)*"
            ),
            color=COLOR_OBSIDIAN,
            tag="303  •  bumped",
            guild=message.guild,
        )
        try:
            await message.channel.send(embed=embed)
        except discord.HTTPException:
            pass

    @tasks.loop(seconds=30)
    async def bump_reminder_loop(self):
        if not self.bot.db.conn:
            return

        now = int(time.time())
        due_guilds = await self.bot.db.get_due_bumps(now)
        for row in due_guilds:
            guild_id = row["guild_id"]
            await self.bot.db.update_guild_setting(
                guild_id, "next_bump_timestamp", 0
            )

            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue

            channel_id = row.get("bump_channel_id")
            channel = guild.get_channel(channel_id) if channel_id else None
            if not isinstance(channel, discord.TextChannel):
                continue

            role_id = row.get("bump_role_id")
            role_ping = f"<@&{role_id}>" if role_id else None

            embed = kyomi_embed(
                description=(
                    "**time to bump**\n"
                    "╰ click </bump:947088344167366698> to boost the server\n"
                    "╰ check `/bump leaderboard` for ranks"
                ),
                color=COLOR_AMBER,
                tag="303  •  reminder",
                guild=guild,
            )
            try:
                await channel.send(content=role_ping, embed=embed)
            except discord.HTTPException:
                pass

    @bump_reminder_loop.before_loop
    async def before_bump_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=60)
    async def autopromo_loop(self):
        if not self.bot.db.conn:
            return

        now = time.time()
        for guild in self.bot.guilds:
            settings = await self.bot.db.get_guild_settings(guild.id)
            ch_id = settings.get("autopromo_channel_id")
            msg_text = settings.get("autopromo_message")
            interval_min = settings.get("autopromo_interval_min") or 120

            if not ch_id or not msg_text:
                continue

            last_sent = self._last_autopromo_sent.get(guild.id, 0.0)
            if now - last_sent >= interval_min * 60:
                self._last_autopromo_sent[guild.id] = now
                channel = guild.get_channel(ch_id)
                if isinstance(channel, discord.TextChannel):
                    embed = kyomi_embed(
                        description=msg_text,
                        color=COLOR_OBSIDIAN,
                        tag=f"303  •  {guild.name.lower()}",
                        guild=guild,
                    )
                    if guild.icon:
                        embed.set_thumbnail(url=guild.icon.url)
                    try:
                        await channel.send(embed=embed)
                    except discord.HTTPException:
                        pass

    @autopromo_loop.before_loop
    async def before_autopromo_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(BumpingCog(bot))
