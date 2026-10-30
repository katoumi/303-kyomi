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
    progress_bar,
)


def calculate_trust_score(
    member: discord.Member, warn_count: int, case_count: int
) -> tuple[int, str]:
    now = datetime.datetime.now(datetime.timezone.utc)
    account_days = (now - member.created_at).days
    server_days = (now - member.joined_at).days if member.joined_at else 0

    score = 50
    score += min(account_days // 15, 25)
    score += min(server_days // 7, 20)
    if len(member.roles) > 1:
        score += 5

    score -= warn_count * 18
    score -= case_count * 5
    score = max(0, min(100, score))

    if score >= 80:
        return score, "trusted"
    elif score >= 50:
        return score, "clean"
    elif score >= 25:
        return score, "watched"
    else:
        return score, "flagged"


class AddNoteModal(discord.ui.Modal, title="leave a note"):
    note_input = discord.ui.TextInput(
        label="note (staff only)",
        style=discord.TextStyle.paragraph,
        placeholder="write something about this user...",
        required=True,
        max_length=500,
    )

    def __init__(self, cog: "DossierCog", target: discord.Member):
        super().__init__()
        self.cog = cog
        self.target = target

    async def on_submit(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        note_id = await self.cog.bot.db.add_staff_note(
            interaction.guild.id,
            self.target.id,
            interaction.user.id,
            self.note_input.value.strip(),
        )
        embed = await self.cog.build_dossier_embed(
            interaction.guild, self.target, tab="notes"
        )
        view = DossierDashboardView(self.cog, self.target, active_tab="notes")
        await interaction.response.edit_message(
            content=f"*saved note `#{note_id}`*",
            embed=embed,
            view=view,
        )


class QuickWarnModal(discord.ui.Modal, title="warn user"):
    reason_input = discord.ui.TextInput(
        label="reason",
        style=discord.TextStyle.short,
        placeholder="why are you warning them?",
        required=True,
        max_length=300,
    )

    def __init__(self, cog: "DossierCog", target: discord.Member):
        super().__init__()
        self.cog = cog
        self.target = target

    async def on_submit(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        reason = self.reason_input.value.strip()
        warn_id = await self.cog.bot.db.add_warning(
            interaction.guild.id, self.target.id, interaction.user.id, reason
        )
        warnings = await self.cog.bot.db.get_warnings(
            interaction.guild.id, self.target.id
        )
        try:
            dm_embed = kyomi_embed(
                description=(
                    f"you were warned in **{interaction.guild.name.lower()}**\n\n"
                    f"╰ **reason:** {reason}\n"
                    f"╰ **strikes:** `{len(warnings)}`"
                ),
                color=COLOR_CRIMSON,
                tag="303  •  notice",
                guild=interaction.guild,
            )
            await self.target.send(embed=dm_embed)
        except discord.HTTPException:
            pass

        mod_cog = self.cog.bot.get_cog("Moderation")
        if mod_cog and hasattr(mod_cog, "send_mod_log"):
            await mod_cog.send_mod_log(
                interaction.guild,
                f"warn #{warn_id}",
                self.target,
                interaction.user,
                reason,
                color=COLOR_AMBER,
            )

        embed = await self.cog.build_dossier_embed(
            interaction.guild, self.target, tab="history"
        )
        view = DossierDashboardView(self.cog, self.target, active_tab="history")
        await interaction.response.edit_message(
            content=f"*warned **{self.target.name}** (`#{warn_id}`)*",
            embed=embed,
            view=view,
        )


class DossierDashboardView(discord.ui.View):
    def __init__(
        self, cog: "DossierCog", target: discord.Member, active_tab: str = "profile"
    ):
        super().__init__(timeout=240)
        self.cog = cog
        self.target = target
        self.active_tab = active_tab
        self._sync_tab_styles()

    def _sync_tab_styles(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id:
                if item.custom_id == f"tab:{self.active_tab}":
                    item.style = discord.ButtonStyle.primary
                    item.disabled = True
                elif item.custom_id.startswith("tab:"):
                    item.style = discord.ButtonStyle.secondary
                    item.disabled = False

    # --- ROW 0: Minimal lowercase tabs ---
    @discord.ui.button(label="profile", custom_id="tab:profile", row=0)
    async def tab_profile(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        self.active_tab = "profile"
        self._sync_tab_styles()
        embed = await self.cog.build_dossier_embed(
            interaction.guild, self.target, tab="profile"
        )
        await interaction.response.edit_message(content=None, embed=embed, view=self)

    @discord.ui.button(label="history", custom_id="tab:history", row=0)
    async def tab_history(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        self.active_tab = "history"
        self._sync_tab_styles()
        embed = await self.cog.build_dossier_embed(
            interaction.guild, self.target, tab="history"
        )
        await interaction.response.edit_message(content=None, embed=embed, view=self)

    @discord.ui.button(label="notes", custom_id="tab:notes", row=0)
    async def tab_notes(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        self.active_tab = "notes"
        self._sync_tab_styles()
        embed = await self.cog.build_dossier_embed(
            interaction.guild, self.target, tab="notes"
        )
        await interaction.response.edit_message(content=None, embed=embed, view=self)

    # --- ROW 1: Quick actions ---
    @discord.ui.button(label="warn", style=discord.ButtonStyle.secondary, row=1)
    async def warn_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(QuickWarnModal(self.cog, self.target))

    @discord.ui.button(label="mute 15m", style=discord.ButtonStyle.secondary, row=1)
    async def mute_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        if self.target.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                "*can't mute them — their role is higher than mine.*", ephemeral=True
            )
        await self.target.timeout(
            datetime.timedelta(minutes=15),
            reason=f"muted by {interaction.user}",
        )
        mod_cog = self.cog.bot.get_cog("Moderation")
        if mod_cog and hasattr(mod_cog, "send_mod_log"):
            await mod_cog.send_mod_log(
                interaction.guild,
                "mute (15m)",
                self.target,
                interaction.user,
                "quick mute via profile",
                color=COLOR_AMBER,
            )
        embed = await self.cog.build_dossier_embed(
            interaction.guild, self.target, tab=self.active_tab
        )
        await interaction.response.edit_message(
            content=f"*muted {self.target.mention} for 15m*",
            embed=embed,
            view=self,
        )

    @discord.ui.button(label="+ note", style=discord.ButtonStyle.secondary, row=1)
    async def add_note_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(AddNoteModal(self.cog, self.target))

    @discord.ui.button(label="clear warns", style=discord.ButtonStyle.danger, row=1)
    async def wipe_warns_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        cleared = await self.cog.bot.db.clear_warnings(
            interaction.guild.id, self.target.id
        )
        embed = await self.cog.build_dossier_embed(
            interaction.guild, self.target, tab="history"
        )
        self.active_tab = "history"
        self._sync_tab_styles()
        await interaction.response.edit_message(
            content=f"*cleared `{cleared}` warn(s) for {self.target.mention}*",
            embed=embed,
            view=self,
        )


class DossierCog(commands.Cog, name="Dossier"):
    """Dark-aesthetic user profile inspector, trust bar, and staff notes."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx_menu_user = app_commands.ContextMenu(
            name="inspect user",
            callback=self.inspect_member_context,
        )
        self.ctx_menu_msg = app_commands.ContextMenu(
            name="delete & warn",
            callback=self.flag_message_context,
        )
        self.bot.tree.add_command(self.ctx_menu_user)
        self.bot.tree.add_command(self.ctx_menu_msg)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(
            self.ctx_menu_user.name, type=self.ctx_menu_user.type
        )
        self.bot.tree.remove_command(
            self.ctx_menu_msg.name, type=self.ctx_menu_msg.type
        )

    async def build_dossier_embed(
        self, guild: discord.Guild, member: discord.Member, tab: str = "profile"
    ) -> discord.Embed:
        warnings = await self.bot.db.get_warnings(guild.id, member.id)
        notes = await self.bot.db.get_staff_notes(guild.id, member.id)
        cases = await self.bot.db.get_user_mod_cases(guild.id, member.id)

        score, status_tag = calculate_trust_score(member, len(warnings), len(cases))
        bar = progress_bar(score, 100, length=10)

        embed = kyomi_embed(
            color=COLOR_OBSIDIAN,
            tag=f"303  •  {member.name.lower()}",
            guild=guild,
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        if tab == "profile":
            joined_str = (
                discord.utils.format_dt(member.joined_at, "R")
                if member.joined_at
                else "n/a"
            )
            roles = [
                r.mention
                for r in reversed(member.roles)
                if r != guild.default_role
            ]
            role_display = " ".join(roles[:7]) if roles else "*none*"
            muted_line = "\n╰ **status:** `muted`" if member.is_timed_out() else ""

            embed.description = (
                f"{member.mention}  ·  `{member.id}`\n"
                f"╰ **trust:** `{bar}` `{score}%` *({status_tag})*\n"
                f"╰ **record:** `{len(warnings)}` warns  ·  `{len(notes)}` notes  ·  `{len(cases)}` logs\n\n"
                f"**dates**\n"
                f"╰ **created:** {discord.utils.format_dt(member.created_at, 'R')}\n"
                f"╰ **joined:** {joined_str}{muted_line}\n\n"
                f"**roles ({len(roles)})**\n"
                f"╰ {role_display}"
            )

        elif tab == "history":
            lines = ["**active warnings**"]
            if warnings:
                for w in warnings[:6]:
                    lines.append(
                        f"╰ `#{w['id']}` {w['reason'][:75]}  — *<@{w['moderator_id']}>*"
                    )
            else:
                lines.append("╰ *clean — no active warnings*")

            lines.append("\n**past actions**")
            if cases:
                for c in cases[:6]:
                    lines.append(
                        f"╰ `#{c['id']}` **{c['action'].lower()}** — {c['reason'][:65]}"
                    )
            else:
                lines.append("╰ *no mod history*")

            embed.description = "\n".join(lines)

        elif tab == "notes":
            if not notes:
                embed.description = (
                    "**staff notes**\n"
                    "╰ *no notes yet. click `+ note` below to leave one.*"
                )
            else:
                lines = ["**staff notes**"]
                for n in notes[:8]:
                    lines.append(
                        f"╰ `#{n['id']}` {n['note']}  — *<@{n['author_id']}>*"
                    )
                embed.description = "\n".join(lines)

        return embed

    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def inspect_member_context(
        self, interaction: discord.Interaction, member: discord.Member
    ):
        assert interaction.guild is not None
        embed = await self.build_dossier_embed(
            interaction.guild, member, tab="profile"
        )
        view = DossierDashboardView(self, member, active_tab="profile")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def flag_message_context(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        assert interaction.guild is not None
        if message.author.bot or not isinstance(message.author, discord.Member):
            return await interaction.response.send_message(
                "*can't warn a bot.*", ephemeral=True
            )

        content_preview = message.content[:200] or "[attachment]"
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        reason = f"flagged in #{message.channel}: \"{content_preview}\""
        warn_id = await self.bot.db.add_warning(
            interaction.guild.id, message.author.id, interaction.user.id, reason
        )

        mod_cog = self.bot.get_cog("Moderation")
        if mod_cog and hasattr(mod_cog, "send_mod_log"):
            await mod_cog.send_mod_log(
                interaction.guild,
                "delete & warn",
                message.author,
                interaction.user,
                reason,
                color=COLOR_CRIMSON,
            )

        await interaction.response.send_message(
            f"*deleted message & warned {message.author.mention} (`#{warn_id}`)*",
            ephemeral=True,
        )

    @app_commands.command(
        name="dossier",
        description="view a member's profile, trust score, warnings, and staff notes.",
    )
    @app_commands.describe(member="member to inspect")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def dossier_slash(
        self, interaction: discord.Interaction, member: discord.Member
    ):
        assert interaction.guild is not None
        embed = await self.build_dossier_embed(
            interaction.guild, member, tab="profile"
        )
        view = DossierDashboardView(self, member, active_tab="profile")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DossierCog(bot))
