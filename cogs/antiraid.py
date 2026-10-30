import collections
import datetime
import time
import discord
from discord import app_commands
from discord.ext import commands
from ui_theme import (
    COLOR_AMBER,
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    kyomi_embed,
)


class RaidThresholdSelect(discord.ui.Select):
    """Dropdown 1: Join-velocity trigger sensitivity."""

    def __init__(self, cog: "AntiRaidCog", settings: dict):
        self.cog = cog
        cur_joins = settings.get("antiraid_joins", 6)
        cur_sec = settings.get("antiraid_interval_sec", 10)

        options = [
            discord.SelectOption(
                label="◈ strict trigger (4 joins / 10s)",
                value="4:10",
                description="triggers lockdown if 4 users join within 10 seconds",
                default=(cur_joins == 4 and cur_sec == 10),
            ),
            discord.SelectOption(
                label="◈ balanced trigger (6 joins / 10s)",
                value="6:10",
                description="recommended — triggers on 6 joins within 10 seconds",
                default=(cur_joins == 6 and cur_sec == 10),
            ),
            discord.SelectOption(
                label="◈ relaxed trigger (10 joins / 12s)",
                value="10:12",
                description="for large servers — triggers on 10 joins within 12 seconds",
                default=(cur_joins == 10 and cur_sec == 12),
            ),
        ]
        super().__init__(
            placeholder=f"✦ join velocity  ·  {cur_joins} joins / {cur_sec}s",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        joins_s, sec_s = self.values[0].split(":")
        await self.cog.bot.db.update_guild_setting(
            interaction.guild.id, "antiraid_joins", int(joins_s)
        )
        await self.cog.bot.db.update_guild_setting(
            interaction.guild.id, "antiraid_interval_sec", int(sec_s)
        )
        view = await self.cog.build_hud_view(interaction.guild)
        await interaction.response.edit_message(content="`303  •  anti-raid`", embed=None, view=view)


class AccountAgeGateSelect(discord.ui.Select):
    """Dropdown 2: Minimum Discord account age filter."""

    def __init__(self, cog: "AntiRaidCog", settings: dict):
        self.cog = cog
        cur_days = settings.get("antiraid_min_account_days", 2)

        options = [
            discord.SelectOption(
                label="◇ age gate: off (allow all account ages)",
                value="0",
                description="do not block brand-new discord accounts",
                default=(cur_days == 0),
            ),
            discord.SelectOption(
                label="◇ age gate: 1 day old minimum",
                value="1",
                description="blocks throwaway alt accounts created today",
                default=(cur_days == 1),
            ),
            discord.SelectOption(
                label="◇ age gate: 2 days old minimum",
                value="2",
                description="recommended — blocks fresh raid accounts (<48h)",
                default=(cur_days == 2),
            ),
            discord.SelectOption(
                label="◇ age gate: 7 days old minimum",
                value="7",
                description="strict — requires accounts to be at least 1 week old",
                default=(cur_days == 7),
            ),
            discord.SelectOption(
                label="◇ age gate: 14 days old minimum",
                value="14",
                description="high security — requires 2-week-old accounts",
                default=(cur_days == 14),
            ),
        ]
        gate_txt = f"min {cur_days}d old" if cur_days > 0 else "off"
        super().__init__(
            placeholder=f"✧ account age gate  ·  {gate_txt}",
            min_values=1,
            max_values=1,
            options=options,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        days = int(self.values[0])
        await self.cog.bot.db.update_guild_setting(
            interaction.guild.id, "antiraid_min_account_days", days
        )
        view = await self.cog.build_hud_view(interaction.guild)
        await interaction.response.edit_message(content="`303  •  anti-raid`", embed=None, view=view)


class RaidActionSelect(discord.ui.Select):
    """Dropdown 3: Automated defense response when a raid or underage alt is detected."""

    def __init__(self, cog: "AntiRaidCog", settings: dict):
        self.cog = cog
        cur_act = settings.get("antiraid_action") or "kick"

        options = [
            discord.SelectOption(
                label="▸ action: kick raiders + pause invites (2h)",
                value="kick",
                description="recommended — kicks raid accounts & pauses server invites",
                default=(cur_act == "kick"),
            ),
            discord.SelectOption(
                label="▸ action: ban raiders + pause invites (2h)",
                value="ban",
                description="lethal — permanently bans raid wave & pauses invites",
                default=(cur_act == "ban"),
            ),
            discord.SelectOption(
                label="▸ action: mute raiders (6h) + pause invites",
                value="timeout",
                description="quarantines raiders with a 6-hour timeout",
                default=(cur_act == "timeout"),
            ),
        ]
        super().__init__(
            placeholder=f"⊘ raid response  ·  {cur_act} + pause invites",
            min_values=1,
            max_values=1,
            options=options,
            row=3,
        )

    async def callback(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        act = self.values[0]
        await self.cog.bot.db.update_guild_setting(
            interaction.guild.id, "antiraid_action", act
        )
        view = await self.cog.build_hud_view(interaction.guild)
        await interaction.response.edit_message(content="`303  •  anti-raid`", embed=None, view=view)


class AntiRaidFloatingHUD(discord.ui.View):
    """Borderless B&W Buttons + Dropdowns HUD for Anti-Raid & Emergency Lockdown."""

    def __init__(
        self, cog: "AntiRaidCog", guild: discord.Guild, settings: dict
    ):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.settings = settings

        enabled = bool(settings.get("antiraid_enabled", 1))
        locked = guild.id in cog.locked_channels and bool(
            cog.locked_channels[guild.id]
        )

        self.btn_toggle.label = f"{'●' if enabled else '○'} anti-raid: {'on' if enabled else 'off'}"
        self.btn_toggle.style = (
            discord.ButtonStyle.primary
            if enabled
            else discord.ButtonStyle.secondary
        )

        self.btn_lockdown.label = (
            "● panic lockdown: active (click to lift)"
            if locked
            else "○ panic lockdown: off"
        )
        self.btn_lockdown.style = (
            discord.ButtonStyle.danger
            if locked
            else discord.ButtonStyle.secondary
        )

        self.add_item(RaidThresholdSelect(cog, settings))
        self.add_item(AccountAgeGateSelect(cog, settings))
        self.add_item(RaidActionSelect(cog, settings))

    @discord.ui.button(label="anti-raid", row=0)
    async def btn_toggle(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        cur = int(bool(self.settings.get("antiraid_enabled", 1)))
        await self.cog.bot.db.update_guild_setting(
            interaction.guild.id, "antiraid_enabled", 0 if cur else 1
        )
        view = await self.cog.build_hud_view(interaction.guild)
        await interaction.response.edit_message(content="`303  •  anti-raid`", embed=None, view=view)

    @discord.ui.button(label="panic lockdown", row=0)
    async def btn_lockdown(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)
        gid = interaction.guild.id
        is_locked = gid in self.cog.locked_channels and bool(
            self.cog.locked_channels[gid]
        )
        if is_locked:
            count = await self.cog.lift_server_lockdown(
                interaction.guild, f"lifted by {interaction.user}"
            )
            note = f"*lifted lockdown across `{count}` channels & restored invites.*"
        else:
            count = await self.cog.trigger_server_lockdown(
                interaction.guild, f"manual panic lockdown by {interaction.user}"
            )
            note = f"*locked `{count}` public channels & paused server invites.*"

        view = await self.cog.build_hud_view(interaction.guild)
        await interaction.edit_original_response(content="`303  •  anti-raid`", embed=None, view=view)
        await interaction.followup.send(note, ephemeral=True)


class RaidAlertControlView(discord.ui.View):
    """Buttons attached to the mod-log alert when a raid is automatically intercepted."""

    def __init__(self, cog: "AntiRaidCog", raider_ids: list[int]):
        super().__init__(timeout=3600)
        self.cog = cog
        self.raider_ids = raider_ids

    @discord.ui.button(
        label="✦ lift lockdown & resume invites",
        style=discord.ButtonStyle.secondary,
    )
    async def btn_lift(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        await interaction.response.defer()
        count = await self.cog.lift_server_lockdown(
            interaction.guild, f"raid cleared by {interaction.user}"
        )
        button.disabled = True
        button.label = f"● lockdown lifted ({count} ch)"
        await interaction.edit_original_response(view=self)

    @discord.ui.button(
        label="× ban all flagged raiders",
        style=discord.ButtonStyle.danger,
    )
    async def btn_ban_wave(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        await interaction.response.defer()
        banned = 0
        for uid in self.raider_ids:
            try:
                await interaction.guild.ban(
                    discord.Object(id=uid),
                    reason=f"303 anti-raid wave ban by {interaction.user}",
                    delete_message_days=1,
                )
                banned += 1
            except discord.HTTPException:
                pass
        button.disabled = True
        button.label = f"● banned {banned} raiders"
        await interaction.edit_original_response(view=self)


class AntiRaidCog(commands.Cog, name="AntiRaid"):
    """Automated Anti-Raid Shield, Account Age Gate & Panic Lockdown HUD."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # guild_id -> deque of (timestamp, member_id)
        self.join_tracker: dict[int, collections.deque[tuple[float, int]]] = (
            collections.defaultdict(lambda: collections.deque(maxlen=30))
        )
        # guild_id -> list of channel IDs locked during panic mode
        self.locked_channels: dict[int, list[int]] = {}
        self.last_raid_trigger: dict[int, float] = {}

    async def build_hud_view(
        self, guild: discord.Guild
    ) -> AntiRaidFloatingHUD:
        settings = await self.bot.db.get_guild_settings(guild.id)
        return AntiRaidFloatingHUD(self, guild, settings)

    async def trigger_server_lockdown(
        self, guild: discord.Guild, reason: str
    ) -> int:
        """Pauses server invites/DMs for 2 hours and locks public text channels."""
        # 1. Pause guild invites & DMs via Discord's native Incident Actions API if available
        try:
            until = datetime.datetime.now(
                datetime.timezone.utc
            ) + datetime.timedelta(hours=2)
            await guild.edit(
                invites_disabled_until=until,
                dms_disabled_until=until,
                reason=reason,
            )
        except Exception:
            pass

        # 2. Lock public text channels where @everyone can currently send messages
        locked: list[int] = self.locked_channels.setdefault(guild.id, [])
        for channel in guild.text_channels:
            perms_for_default = channel.permissions_for(guild.default_role)
            if perms_for_default. view_channel and perms_for_default.send_messages:
                overwrite = channel.overwrites_for(guild.default_role)
                if overwrite.send_messages is not False:
                    overwrite.send_messages = False
                    try:
                        await channel.set_permissions(
                            guild.default_role,
                            overwrite=overwrite,
                            reason=f"303 anti-raid: {reason}",
                        )
                        if channel.id not in locked:
                            locked.append(channel.id)
                    except discord.HTTPException:
                        pass
        return len(locked)

    async def lift_server_lockdown(
        self, guild: discord.Guild, reason: str
    ) -> int:
        """Restores public channel send permissions and re-enables invites."""
        try:
            await guild.edit(
                invites_disabled_until=None,
                dms_disabled_until=None,
                reason=reason,
            )
        except Exception:
            pass

        locked = self.locked_channels.pop(guild.id, [])
        restored = 0
        for cid in locked:
            channel = guild.get_channel(cid)
            if isinstance(channel, discord.TextChannel):
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.send_messages = None
                try:
                    await channel.set_permissions(
                        guild.default_role,
                        overwrite=overwrite,
                        reason=f"303 lift lockdown: {reason}",
                    )
                    restored += 1
                except discord.HTTPException:
                    pass
        return restored

    async def _punish_raider(
        self, guild: discord.Guild, member: discord.Member, action: str, reason: str
    ) -> None:
        try:
            if action == "ban":
                await guild.ban(member, reason=reason, delete_message_days=1)
            elif action == "timeout":
                await member.timeout(
                    datetime.timedelta(hours=6), reason=reason
                )
            else:
                await member.kick(reason=reason)
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        if member.bot:
            return

        settings = await self.bot.db.get_guild_settings(guild.id)
        if not settings.get("antiraid_enabled", 1):
            return

        action = settings.get("antiraid_action") or "kick"
        min_days = settings.get("antiraid_min_account_days", 2)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        account_age_days = (now_utc - member.created_at).days

        # 1. Account Age Gate check
        if min_days > 0 and account_age_days < min_days:
            try:
                dm = kyomi_embed(
                    description=(
                        f"entry blocked in **{guild.name.lower()}**\n"
                        f"╰ **reason:** your discord account must be at least `{min_days}` day(s) old."
                    ),
                    color=COLOR_AMBER,
                    tag="303  •  anti-raid",
                    guild=guild,
                )
                await member.send(embed=dm)
            except discord.HTTPException:
                pass

            await self._punish_raider(
                guild,
                member,
                "kick",
                f"303 anti-raid: account younger than {min_days}d ({account_age_days}d old)",
            )
            mod_cog = self.bot.get_cog("Moderation")
            if mod_cog and hasattr(mod_cog, "send_mod_log"):
                await mod_cog.send_mod_log(
                    guild,
                    "anti-raid · age gate",
                    member,
                    guild.me,
                    f"blocked new account (`{account_age_days}d` old, min `{min_days}d`)",
                    color=COLOR_AMBER,
                )
            return

        # 2. Join Velocity Tracker (Mass Join Raid Detection)
        now = time.monotonic()
        threshold = settings.get("antiraid_joins", 6)
        interval = settings.get("antiraid_interval_sec", 10)

        history = self.join_tracker[guild.id]
        history.append((now, member.id))

        while history and now - history[0][0] > interval:
            history.popleft()

        if len(history) >= threshold:
            raider_ids = [uid for _, uid in history]
            history.clear()

            # Punish everyone in the raid burst
            for uid in raider_ids:
                target = guild.get_member(uid)
                if target:
                    await self._punish_raider(
                        guild,
                        target,
                        action,
                        f"303 anti-raid: mass join burst ({len(raider_ids)} joins / {interval}s)",
                    )

            # Activate server lockdown (if not already triggered in the last 60s)
            last_trig = self.last_raid_trigger.get(guild.id, 0.0)
            if now - last_trig > 60:
                self.last_raid_trigger[guild.id] = now
                locked_count = await self.trigger_server_lockdown(
                    guild, f"mass join burst ({len(raider_ids)} joins in {interval}s)"
                )

                log_ch_id = settings.get("mod_log_channel_id") or settings.get(
                    "audit_log_channel_id"
                )
                if log_ch_id:
                    log_ch = guild.get_channel(log_ch_id)
                    if isinstance(log_ch, discord.TextChannel):
                        raider_mentions = ", ".join(
                            f"<@{uid}>" for uid in raider_ids[:15]
                        )
                        alert = kyomi_embed(
                            description=(
                                f"**† raid intercepted**\n"
                                f"╰ **burst:** `{len(raider_ids)}` joins within `{interval}s`\n"
                                f"╰ **action:** `{action}` applied  ·  locked `{locked_count}` channels  ·  paused invites\n"
                                f"╰ **accounts:** {raider_mentions}"
                            ),
                            color=COLOR_CRIMSON,
                            tag="303  •  anti-raid",
                            guild=guild,
                        )
                        try:
                            await log_ch.send(
                                embed=alert,
                                view=RaidAlertControlView(self, raider_ids),
                            )
                        except discord.HTTPException:
                            pass

    antiraid_group = app_commands.Group(
        name="antiraid",
        description="open the borderless anti-raid & panic lockdown controls.",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @antiraid_group.command(
        name="panel",
        description="open the borderless anti-raid buttons & dropdowns menu.",
    )
    async def antiraid_panel(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)
        view = await self.build_hud_view(interaction.guild)
        await interaction.followup.send("`303  •  anti-raid`", view=view, ephemeral=True)

    @antiraid_group.command(
        name="lockdown",
        description="immediately toggle emergency server lockdown (locks public channels & pauses invites).",
    )
    async def antiraid_lockdown(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)
        gid = interaction.guild.id
        is_locked = gid in self.locked_channels and bool(
            self.locked_channels[gid]
        )
        if is_locked:
            count = await self.lift_server_lockdown(
                interaction.guild, f"lifted by {interaction.user}"
            )
            await interaction.followup.send(
                f"*lifted lockdown across `{count}` channels & resumed invites.*",
                ephemeral=True,
            )
        else:
            count = await self.trigger_server_lockdown(
                interaction.guild, f"triggered by {interaction.user}"
            )
            await interaction.followup.send(
                f"*panic lockdown active — locked `{count}` channels & paused invites.*",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiRaidCog(bot))
