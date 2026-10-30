import discord
from discord import app_commands
from discord.ext import commands


class HelpPopupModal(discord.ui.Modal, title="303  •  kyomi manual"):
    """Floating Popup Modal for /help — displays B&W symbol manual outside of chat."""

    def __init__(self, section: str = "all"):
        super().__init__(timeout=300)

        mod_guide = discord.ui.TextInput(
            label="✦ moderation & channel control",
            style=discord.TextStyle.paragraph,
            default=(
                "╰ /warn <user> <reason>  ·  /warnings <user>\n"
                "╰ /delwarn <id>  ·  /clearwarns <user>\n"
                "╰ /timeout <user> <mins>  ·  /untimeout <user>\n"
                "╰ /kick <user>  ·  /ban <user>  ·  /unban <id>\n"
                "╰ /purge <1-100> [user]  ·  /slowmode <sec>\n"
                "╰ /lock [reason]  ·  /unlock"
            ),
            required=False,
        )

        automod_guide = discord.ui.TextInput(
            label="◈ automod, anti-raid & dossier",
            style=discord.TextStyle.paragraph,
            default=(
                "╰ /automod panel — floating filter buttons & dropdowns\n"
                "╰ /antiraid panel — join velocity, age gate & lockdown\n"
                "╰ /antiraid lockdown — 1-click panic server lockdown\n"
                "╰ /dossier <user> — trust bar, history & staff notes\n"
                "╰ right-click user -> apps -> inspect user\n"
                "╰ right-click msg  -> apps -> delete & warn"
            ),
            required=False,
        )

        tickets_guide = discord.ui.TextInput(
            label="✧ tickets & transcripts",
            style=discord.TextStyle.paragraph,
            default=(
                "╰ /ticket setup <category> <log_channel> [role]\n"
                "╰ /ticket panel — drop the support dropdown menu\n"
                "╰ inside tickets: [claim], [pin / urgent], [close]"
            ),
            required=False,
        )

        bumps_logs_guide = discord.ui.TextInput(
            label="⊘ bumping & server logs",
            style=discord.TextStyle.paragraph,
            default=(
                "╰ /bump setup <channel> [role] — 2h disboard ping\n"
                "╰ /bump leaderboard  ·  /bump simulate (60s test)\n"
                "╰ /bump autopromo <channel> <mins> <msg>\n"
                "╰ /config modlog <ch>  ·  /config auditlog <ch>\n"
                "╰ /config thresholds <mute_warns> <ban_warns>"
            ),
            required=False,
        )

        self.add_item(mod_guide)
        self.add_item(automod_guide)
        self.add_item(tickets_guide)
        self.add_item(bumps_logs_guide)

    async def on_submit(self, interaction: discord.Interaction):
        # Closing/submitting the modal leaves zero messages in chat
        await interaction.response.defer()


class HelpModuleSelect(discord.ui.Select):
    """Borderless dropdown that pops open a Modal when any category is selected."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        options = [
            discord.SelectOption(
                label="✦ open full manual (popup modal)",
                value="modal:all",
                description="opens the floating 303 kyomi command window",
            ),
            discord.SelectOption(
                label="◈ open automod switches (floating hud)",
                value="hud:automod",
                description="opens the borderless automod buttons & dropdowns",
            ),
        ]
        super().__init__(
            placeholder="✦ 303 kyomi  ·  select a window to open...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        if choice == "modal:all":
            await interaction.response.send_modal(HelpPopupModal())
        elif choice == "hud:automod":
            assert interaction.guild is not None
            automod_cog = self.bot.get_cog("AutoMod")
            if automod_cog and hasattr(automod_cog, "build_hud_view"):
                hud = await automod_cog.build_hud_view(interaction.guild)
                await interaction.response.edit_message(content=None, embed=None, view=hud)


class HelpFloatingHUD(discord.ui.View):
    """Borderless B&W buttons + dropdown for /help that launch floating Modals."""

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.add_item(HelpModuleSelect(bot))

    @discord.ui.button(
        label="✦ command manual (modal)",
        style=discord.ButtonStyle.primary,
        row=1,
    )
    async def btn_open_manual(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(HelpPopupModal())

    @discord.ui.button(
        label="◈ automod hud",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def btn_open_automod(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild is not None
        automod_cog = self.bot.get_cog("AutoMod")
        if automod_cog and hasattr(automod_cog, "build_hud_view"):
            hud = await automod_cog.build_hud_view(interaction.guild)
            await interaction.response.edit_message(content=None, embed=None, view=hud)


class HelpCog(commands.Cog, name="Help"):
    """Floating Modal & borderless B&W symbol help guide."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="open the floating 303 kyomi manual modal.",
    )
    async def help_command(self, interaction: discord.Interaction):
        # Immediately pops open the floating Modal window in the center of Discord
        await interaction.response.send_modal(HelpPopupModal())


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
