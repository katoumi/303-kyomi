import datetime
import discord

# 303 KYOMI — Dark Aesthetic Palette (Pitch Black / Ash / Blood / Bone)
COLOR_OBSIDIAN = discord.Color.from_rgb(12, 12, 14)       # #0c0c0e - Pitch black (invisible border in dark mode)
COLOR_CRIMSON = discord.Color.from_rgb(138, 28, 39)       # #8a1c27 - Deep blood red
COLOR_AMBER = discord.Color.from_rgb(166, 130, 92)        # #a6825c - Muted warm ash / bronze
COLOR_MINT = discord.Color.from_rgb(110, 122, 117)        # #6e7a75 - Muted sage / slate
COLOR_SLATE = discord.Color.from_rgb(43, 45, 49)          # #2b2d31 - Discord dark surface


def progress_bar(value: int, maximum: int = 100, length: int = 10) -> str:
    """Minimal monochrome dot/block bar: ━━━━━━┈┈┈┈"""
    ratio = max(0.0, min(1.0, value / maximum)) if maximum else 0.0
    filled = round(ratio * length)
    return "━" * filled + "┈" * (length - filled)


def kyomi_embed(
    title: str | None = None,
    description: str | None = None,
    color: discord.Color = COLOR_OBSIDIAN,
    tag: str = "303  •  kyomi",
    guild: discord.Guild | None = None,
) -> discord.Embed:
    """Creates a minimal, lowercase dark-aesthetic embed."""
    embed = discord.Embed(
        title=title.lower() if title else None,
        description=description,
        color=color,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    icon_url = guild.icon.url if (guild and guild.icon) else None
    embed.set_author(name=tag.lower(), icon_url=icon_url)
    embed.set_footer(text="303 kyomi")
    return embed


def ansi_block(*lines: str) -> str:
    joined = "\n".join(lines)
    return f"```ansi\n{joined}\n```"
