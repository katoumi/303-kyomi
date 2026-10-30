import collections
import datetime
import hashlib
import re
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

INVITE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discordapp\.com/invite|discord\.com/invite)/[a-zA-Z0-9\-]+",
    re.IGNORECASE,
)
URL_REGEX = re.compile(r"https?://[^\s/$.?#].[^\s]*", re.IGNORECASE)


class AddWordModal(discord.ui.Modal, title="303  •  block word"):
    word_input = discord.ui.TextInput(
        label="word or phrase to block",
        style=discord.TextStyle.short,
        placeholder="type word...",
        required=True,
        max_length=100,
    )

    def __init__(self, cog: "AutoModCog"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        word = self.word_input.value.strip().lower()
        await self.cog.bot.db.add_bad_word(interaction.guild.id, word)
        view = await self.cog.build_hud_view(interaction.guild)
        await interaction.response.edit_message(content="`303  •  automod`", embed=None, view=view)


class SpamPresetSelect(discord.ui.Select):
    """Dropdown 1: Anti-Spam sensitivity & Max Mentions presets (pure B&W symbols)."""

    def __init__(self, cog: "AutoModCog", settings: dict):
        self.cog = cog
        cur_spam = settings.get("spam_threshold", 5)
        cur_sec = settings.get("spam_interval_sec", 5)
        cur_ment = settings.get("max_mentions", 5)

        options = [
            discord.SelectOption(
                label="◈ spam: strict (3 msgs / 5s)",
                value="spam:3:5",
                description="fast trigger — mutes after 3 rapid messages",
                default=(cur_spam == 3 and cur_sec == 5),
            ),
            discord.SelectOption(
                label="◈ spam: balanced (5 msgs / 5s)",
                value="spam:5:5",
                description="default — mutes after 5 messages in 5 seconds",
                default=(cur_spam == 5 and cur_sec == 5),
            ),
            discord.SelectOption(
                label="◈ spam: relaxed (8 msgs / 6s)",
                value="spam:8:6",
                description="chill — only catches heavy flood spam",
                default=(cur_spam == 8 and cur_sec == 6),
            ),
            discord.SelectOption(
                label="◇ mention cap: strict (max 3 pings)",
                value="mentions:3",
                description=f"current cap: {cur_ment} mentions per message",
            ),
            discord.SelectOption(
                label="◇ mention cap: standard (max 5 pings)",
                value="mentions:5",
                description=f"current cap: {cur_ment} mentions per message",
            ),
            discord.SelectOption(
                label="◇ mention cap: relaxed (max 10 pings)",
                value="mentions:10",
                description=f"current cap: {cur_ment} mentions per message",
            ),
        ]
        super().__init__(
            placeholder=f"✦ sensitivity  ·  {cur_spam} msgs/{cur_sec}s  ·  max {cur_ment} pings",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        val = self.values[0]
        if val.startswith("spam:"):
            _, msgs, secs = val.split(":")
            await self.cog.bot.db.update_guild_setting(
                interaction.guild.id, "spam_threshold", int(msgs)
            )
            await self.cog.bot.db.update_guild_setting(
                interaction.guild.id, "spam_interval_sec", int(secs)
            )
        elif val.startswith("mentions:"):
            _, count = val.split(":")
            await self.cog.bot.db.update_guild_setting(
                interaction.guild.id, "max_mentions", int(count)
            )

        view = await self.cog.build_hud_view(interaction.guild)
        await interaction.response.edit_message(content="`303  •  automod`", embed=None, view=view)


class EscalationPresetSelect(discord.ui.Select):
    """Dropdown 2: Automatic punishment thresholds for warnings (pure B&W symbols)."""

    def __init__(self, cog: "AutoModCog", settings: dict):
        self.cog = cog
        cur_mute = settings.get("warn_threshold_timeout", 3)
        cur_ban = settings.get("warn_threshold_ban", 5)

        options = [
            discord.SelectOption(
                label="▸ strict punish (2 warns = mute  ·  4 warns = ban)",
                value="2:4",
                description="tight enforcement for public servers",
                default=(cur_mute == 2 and cur_ban == 4),
            ),
            discord.SelectOption(
                label="▸ standard punish (3 warns = mute  ·  5 warns = ban)",
                value="3:5",
                description="recommended balance for communities",
                default=(cur_mute == 3 and cur_ban == 5),
            ),
            discord.SelectOption(
                label="▸ lenient punish (4 warns = mute  ·  7 warns = ban)",
                value="4:7",
                description="more chances before automatic action",
                default=(cur_mute == 4 and cur_ban == 7),
            ),
            discord.SelectOption(
                label="▸ mute only (3 warns = mute  ·  auto-ban off)",
                value="3:0",
                description="never auto-ban, only auto-mute for 1h",
                default=(cur_mute == 3 and cur_ban == 0),
            ),
            discord.SelectOption(
                label="▸ manual only (auto-punishments disabled)",
                value="0:0",
                description="warnings are logged without automatic mutes/bans",
                default=(cur_mute == 0 and cur_ban == 0),
            ),
        ]
        ban_label = f"{cur_ban}w=ban" if cur_ban else "ban off"
        mute_label = f"{cur_mute}w=mute" if cur_mute else "mute off"
        super().__init__(
            placeholder=f"✧ auto-punish  ·  {mute_label}  ·  {ban_label}",
            min_values=1,
            max_values=1,
            options=options,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        mute_w, ban_w = self.values[0].split(":")
        await self.cog.bot.db.update_guild_setting(
            interaction.guild.id, "warn_threshold_timeout", int(mute_w)
        )
        await self.cog.bot.db.update_guild_setting(
            interaction.guild.id, "warn_threshold_ban", int(ban_w)
        )
        view = await self.cog.build_hud_view(interaction.guild)
        await interaction.response.edit_message(content="`303  •  automod`", embed=None, view=view)


class WordRemoveSelect(discord.ui.Select):
    """Dropdown 3: Click any blocked word from the dropdown to unblock it immediately."""

    def __init__(self, cog: "AutoModCog", words: list[str]):
        self.cog = cog
        if words:
            options = [
                discord.SelectOption(
                    label=f"× {w}",
                    value=w,
                    description="select to unblock this word",
                )
                for w in words[:25]
            ]
            placeholder = f"⊘ blocked words ({len(words)})  ·  select to remove..."
            disabled = False
        else:
            options = [
                discord.SelectOption(
                    label="no words blocked",
                    value="__none__",
                )
            ]
            placeholder = "⊘ blocked words (0)  ·  click '+ word' below to add"
            disabled = True

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            disabled=disabled,
            row=3,
        )

    async def callback(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        word = self.values[0]
        if word != "__none__":
            await self.cog.bot.db.remove_bad_word(interaction.guild.id, word)
        view = await self.cog.build_hud_view(interaction.guild)
        await interaction.response.edit_message(content="`303  •  automod`", embed=None, view=view)


class AutoModFloatingHUD(discord.ui.View):
    """
    Pure borderless component HUD (zero embed box, zero colored emojis, pure B&W symbols).
    Includes Ghost-Ping & Cross-Channel Scam Guard toggles.
    """

    def __init__(self, cog: "AutoModCog", settings: dict, words: list[str]):
        super().__init__(timeout=300)
        self.cog = cog
        self.settings = settings
        self.words = words

        self._sync_toggle_buttons()
        self.add_item(SpamPresetSelect(cog, settings))
        self.add_item(EscalationPresetSelect(cog, settings))
        self.add_item(WordRemoveSelect(cog, words))

    def _sync_toggle_buttons(self) -> None:
        master = bool(self.settings.get("automod_enabled", 1))
        spam = bool(self.settings.get("anti_spam_enabled", 1))
        invites = bool(self.settings.get("block_invites", 1))
        links = bool(self.settings.get("block_links", 0))
        ghost = bool(self.settings.get("ghostping_enabled", 1))
        scam = bool(self.settings.get("scam_guard_enabled", 1))

        self.btn_master.label = f"{'●' if master else '○'} automod: {'on' if master else 'off'}"
        self.btn_master.style = (
            discord.ButtonStyle.primary if master else discord.ButtonStyle.secondary
        )

        self.btn_spam.label = f"{'●' if spam else '○'} anti-spam: {'on' if spam else 'off'}"
        self.btn_spam.style = (
            discord.ButtonStyle.primary if spam else discord.ButtonStyle.secondary
        )

        self.btn_invites.label = f"{'●' if invites else '○'} invites: {'blocked' if invites else 'allowed'}"
        self.btn_invites.style = (
            discord.ButtonStyle.primary if invites else discord.ButtonStyle.secondary
        )

        self.btn_links.label = f"{'●' if links else '○'} links: {'blocked' if links else 'allowed'}"
        self.btn_links.style = (
            discord.ButtonStyle.primary if links else discord.ButtonStyle.secondary
        )

        self.btn_ghost.label = f"{'●' if ghost else '○'} ghost-ping: {'on' if ghost else 'off'}"
        self.btn_ghost.style = (
            discord.ButtonStyle.primary if ghost else discord.ButtonStyle.secondary
        )

        self.btn_scam.label = f"{'●' if scam else '○'} scam-guard: {'on' if scam else 'off'}"
        self.btn_scam.style = (
            discord.ButtonStyle.primary if scam else discord.ButtonStyle.secondary
        )

    async def _flip(self, interaction: discord.Interaction, column: str):
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)
        current = int(bool(self.settings.get(column, 0)))
        new_val = 0 if current else 1
        await self.cog.bot.db.update_guild_setting(
            interaction.guild.id, column, new_val
        )
        view = await self.cog.build_hud_view(interaction.guild)
        await interaction.edit_original_response(content="`303  •  automod`", embed=None, view=view)

    # --- ROW 0: Core Filter Switches ---
    @discord.ui.button(label="automod", row=0)
    async def btn_master(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._flip(interaction, "automod_enabled")

    @discord.ui.button(label="anti-spam", row=0)
    async def btn_spam(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._flip(interaction, "anti_spam_enabled")

    @discord.ui.button(label="invites", row=0)
    async def btn_invites(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._flip(interaction, "block_invites")

    @discord.ui.button(label="links", row=0)
    async def btn_links(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._flip(interaction, "block_links")

    @discord.ui.button(label="ghost-ping", row=0)
    async def btn_ghost(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._flip(interaction, "ghostping_enabled")

    # --- ROW 4: Scam Guard & Word Actions ---
    @discord.ui.button(label="scam-guard", row=4)
    async def btn_scam(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._flip(interaction, "scam_guard_enabled")

    @discord.ui.button(
        label="＋ add word", style=discord.ButtonStyle.secondary, row=4
    )
    async def btn_add_word(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(AddWordModal(self.cog))

    @discord.ui.button(
        label="× clear words", style=discord.ButtonStyle.danger, row=4
    )
    async def btn_clear_words(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        for w in list(self.words):
            await self.cog.bot.db.remove_bad_word(interaction.guild.id, w)
        view = await self.cog.build_hud_view(interaction.guild)
        await interaction.response.edit_message(content="`303  •  automod`", embed=None, view=view)


class AutoModCog(commands.Cog, name="AutoMod"):
    """Borderless AutoMod HUD + Ghost-Ping Detector + Cross-Channel Scam Guard."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.spam_tracker: dict[tuple[int, int], collections.deque[float]] = (
            collections.defaultdict(lambda: collections.deque(maxlen=15))
        )
        # (guild_id, user_id) -> deque of (timestamp, channel_id, message_id, content_hash)
        self.cross_channel_tracker: dict[
            tuple[int, int], collections.deque[tuple[float, int, int, str]]
        ] = collections.defaultdict(lambda: collections.deque(maxlen=10))
        # Track message IDs deleted by AutoMod itself so we don't flag them as ghost-pings
        self.automod_deleted_ids: collections.deque[int] = collections.deque(
            maxlen=200
        )

    async def build_hud_view(self, guild: discord.Guild) -> AutoModFloatingHUD:
        settings = await self.bot.db.get_guild_settings(guild.id)
        words = await self.bot.db.get_bad_words(guild.id)
        return AutoModFloatingHUD(self, settings, words)

    automod_group = app_commands.Group(
        name="automod",
        description="open the borderless automod button & dropdown controls.",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @automod_group.command(
        name="panel",
        description="open the borderless automod buttons & dropdown menu.",
    )
    async def automod_panel(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)
        view = await self.build_hud_view(interaction.guild)
        await interaction.followup.send("`303  •  automod`", view=view, ephemeral=True)

    @automod_group.command(
        name="status",
        description="open the borderless automod buttons & dropdown menu.",
    )
    async def automod_status(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)
        view = await self.build_hud_view(interaction.guild)
        await interaction.followup.send("`303  •  automod`", view=view, ephemeral=True)

    @automod_group.command(
        name="addword", description="add a word to the chat filter."
    )
    async def add_word(self, interaction: discord.Interaction, word: str):
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.add_bad_word(interaction.guild.id, word)
        view = await self.build_hud_view(interaction.guild)
        await interaction.followup.send("`303  •  automod`", view=view, ephemeral=True)

    @automod_group.command(
        name="removeword", description="remove a word from the chat filter."
    )
    async def remove_word(self, interaction: discord.Interaction, word: str):
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.remove_bad_word(interaction.guild.id, word)
        view = await self.build_hud_view(interaction.guild)
        await interaction.followup.send("`303  •  automod`", view=view, ephemeral=True)

    async def _handle_violation(
        self,
        message: discord.Message,
        label: str,
        reason: str,
        timeout_minutes: int = 0,
    ) -> None:
        assert message.guild is not None
        assert isinstance(message.author, discord.Member)

        self.automod_deleted_ids.append(message.id)
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        try:
            notice = kyomi_embed(
                description=f"{message.author.mention} — *{reason}*",
                color=COLOR_CRIMSON,
                tag=f"303  •  {label}",
            )
            await message.channel.send(embed=notice, delete_after=5)
        except discord.HTTPException:
            pass

        if timeout_minutes > 0:
            try:
                await message.author.timeout(
                    datetime.timedelta(minutes=timeout_minutes),
                    reason=f"automod ({label}): {reason}",
                )
            except discord.HTTPException:
                pass

        mod_cog = self.bot.get_cog("Moderation")
        if mod_cog and hasattr(mod_cog, "send_mod_log"):
            await mod_cog.send_mod_log(
                guild=message.guild,
                action=f"automod · {label}",
                target=message.author,
                moderator=message.guild.me,
                reason=f"{reason} in {message.channel.mention}\n╰ `{message.content[:200]}`",
                color=COLOR_AMBER,
            )

    # --- Ghost-Ping Detection (Delete & Edit) ---
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if message.id in self.automod_deleted_ids:
            return

        # Ignore old messages (> 20 seconds old) — only catch actual rapid ghost-pings
        age_sec = (
            datetime.datetime.now(datetime.timezone.utc) - message.created_at
        ).total_seconds()
        if age_sec > 20:
            return

        user_pings = [
            u for u in message.mentions if not u.bot and u.id != message.author.id
        ]
        role_pings = list(message.role_mentions)
        has_everyone = message.mention_everyone

        if not user_pings and not role_pings and not has_everyone:
            return

        settings = await self.bot.db.get_guild_settings(message.guild.id)
        if not settings.get("ghostping_enabled", 1):
            return

        targets = [u.mention for u in user_pings] + [r.mention for r in role_pings]
        if has_everyone:
            targets.append("`@everyone`")
        target_str = ", ".join(targets[:8])

        embed = kyomi_embed(
            description=(
                f"**⊘ ghost-ping detected**\n"
                f"╰ **by:** {message.author.mention}\n"
                f"╰ **pinged:** {target_str}\n"
                f"╰ **message:** `{message.content[:220]}`"
            ),
            color=COLOR_CRIMSON,
            tag="303  •  ghost-ping",
            guild=message.guild,
        )
        try:
            await message.channel.send(embed=embed)
        except discord.HTTPException:
            pass

        mod_cog = self.bot.get_cog("Moderation")
        if mod_cog and hasattr(mod_cog, "send_mod_log"):
            await mod_cog.send_mod_log(
                guild=message.guild,
                action="ghost-ping",
                target=message.author,
                moderator=message.guild.me,
                reason=f"deleted ping to {target_str} in {message.channel.mention} after `{int(age_sec)}s`\n╰ `{message.content[:200]}`",
                color=COLOR_AMBER,
            )

    @commands.Cog.listener()
    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ):
        if not before.guild or before.author.bot:
            return

        age_sec = (
            datetime.datetime.now(datetime.timezone.utc) - before.created_at
        ).total_seconds()
        if age_sec > 30:
            return

        before_users = {
            u for u in before.mentions if not u.bot and u.id != before.author.id
        }
        after_users = {
            u for u in after.mentions if not u.bot and u.id != after.author.id
        }
        removed_users = before_users - after_users
        removed_roles = set(before.role_mentions) - set(after.role_mentions)

        if not removed_users and not removed_roles:
            return

        settings = await self.bot.db.get_guild_settings(before.guild.id)
        if not settings.get("ghostping_enabled", 1):
            return

        targets = [u.mention for u in removed_users] + [
            r.mention for r in removed_roles
        ]
        target_str = ", ".join(targets[:8])

        embed = kyomi_embed(
            description=(
                f"**⊘ ghost-ping (edited out)**\n"
                f"╰ **by:** {before.author.mention}\n"
                f"╰ **removed ping:** {target_str}\n"
                f"╰ **original:** `{before.content[:200]}`"
            ),
            color=COLOR_CRIMSON,
            tag="303  •  ghost-ping",
            guild=before.guild,
        )
        try:
            await before.channel.send(embed=embed)
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if not isinstance(message.author, discord.Member):
            return

        if (
            message.author.guild_permissions.administrator
            or message.author.guild_permissions.manage_messages
        ):
            return

        settings = await self.bot.db.get_guild_settings(message.guild.id)
        if not settings.get("automod_enabled", 1):
            return

        content_lower = message.content.lower().strip()

        # 1. Blocked words check
        bad_words = await self.bot.db.get_bad_words(message.guild.id)
        for word in bad_words:
            pattern = rf"\b{re.escape(word)}\b"
            if re.search(pattern, content_lower) or word in content_lower:
                await self._handle_violation(
                    message, "filter", f"watch your language (`{word}`)"
                )
                return

        # 2. Invite links check
        if settings.get("block_invites", 1) and INVITE_REGEX.search(message.content):
            await self._handle_violation(
                message, "invites", "no server invites allowed here"
            )
            return

        # 3. External links check
        if settings.get("block_links", 0) and URL_REGEX.search(message.content):
            await self._handle_violation(
                message, "links", "links are disabled in this channel"
            )
            return

        # 4. Mass mention cap
        max_mentions = settings.get("max_mentions", 5)
        total_mentions = len(message.mentions) + len(message.role_mentions)
        if max_mentions > 0 and total_mentions > max_mentions:
            await self._handle_violation(
                message,
                "mass ping",
                f"too many mentions ({total_mentions}/{max_mentions}) — muted 10m",
                timeout_minutes=10,
            )
            return

        # 5. Cross-Channel Copy-Paste & Scam Detector
        if settings.get("scam_guard_enabled", 1) and len(content_lower) >= 6:
            now_mono = time.monotonic()
            msg_hash = hashlib.md5(content_lower.encode("utf-8")).hexdigest()
            scam_key = (message.guild.id, message.author.id)
            c_hist = self.cross_channel_tracker[scam_key]
            c_hist.append((now_mono, message.channel.id, message.id, msg_hash))

            while c_hist and now_mono - c_hist[0][0] > 15:
                c_hist.popleft()

            matching = [entry for entry in c_hist if entry[3] == msg_hash]
            unique_channels = {entry[1] for entry in matching}

            if len(unique_channels) >= 3:
                # Purge all matching messages across the channels & mute for 1h
                for _, ch_id, m_id, _ in matching:
                    self.automod_deleted_ids.append(m_id)
                    ch = message.guild.get_channel(ch_id)
                    if isinstance(ch, discord.TextChannel):
                        try:
                            await ch.get_partial_message(m_id).delete()
                        except discord.HTTPException:
                            pass
                c_hist.clear()
                await self._handle_violation(
                    message,
                    "scam-guard",
                    "cross-channel copy-paste spam detected — muted for 60m",
                    timeout_minutes=60,
                )
                return

        # 6. Anti-spam flood guard
        if settings.get("anti_spam_enabled", 1):
            now = time.monotonic()
            threshold = settings.get("spam_threshold", 5)
            interval = settings.get("spam_interval_sec", 5)
            key = (message.guild.id, message.author.id)
            history = self.spam_tracker[key]
            history.append(now)

            while history and now - history[0] > interval:
                history.popleft()

            if len(history) >= threshold:
                history.clear()
                await self._handle_violation(
                    message,
                    "spam",
                    "slow down — muted for 5m",
                    timeout_minutes=5,
                )


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoModCog(bot))
