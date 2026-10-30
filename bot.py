import asyncio
import logging
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import Database
from dashboard import WebDashboard

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
)
logger = logging.getLogger("mod-bot")

COGS = [
    "cogs.moderation",
    "cogs.automod",
    "cogs.antiraid",
    "cogs.logging_cog",
    "cogs.dossier",
    "cogs.tickets",
    "cogs.bumping",
    "cogs.help_cog",
]


class ModBot(commands.Bot):
    def __init__(self, db_path: str):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.moderation = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
        )
        self.db = Database(db_path)

    async def setup_hook(self) -> None:
        for cog in COGS:
            await self.load_extension(cog)
            logger.info("Loaded extension: %s", cog)

        synced = await self.tree.sync()
        logger.info("Synchronized %d global slash command(s).", len(synced))

    async def on_ready(self) -> None:
        assert self.user is not None
        logger.info("Logged in as %s (ID: %d)", self.user, self.user.id)
        await self.change_presence(
            status=discord.Status.dnd,
            activity=discord.CustomActivity(name="303  •  watching"),
        )


async def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    db_path = os.getenv("DATABASE_PATH", "data/moderation.db")

    if not token or token == "your_discord_bot_token_here":
        logger.error(
            "Missing DISCORD_TOKEN! Copy .env.example to .env and add your bot token."
        )
        return

    bot = ModBot(db_path=db_path)
    await bot.db.connect()
    logger.info("Connected to SQLite database at %s", bot.db.db_path)

    # Start the Web Dashboard & healthcheck server BEFORE Discord login
    # so cloud hosts (Render/Koyeb) mark the deployment as LIVE immediately
    dashboard = WebDashboard(bot, bot.db)
    await dashboard.start()
    logger.info("Web Dashboard listening on port %d", dashboard.port)

    # Connect to Discord with automatic backoff if shared cloud IP is rate-limited (429)
    retry_delay = 15
    while True:
        try:
            await bot.start(token)
            break
        except discord.HTTPException as exc:
            if exc.status == 429:
                logger.warning(
                    "Discord shared-IP rate limit (429) encountered. Retrying in %ds while keeping Web Dashboard online...",
                    retry_delay,
                )
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 180)
            else:
                logger.error("Discord HTTP error: %s", exc)
                await asyncio.sleep(30)
        except Exception as exc:
            logger.error("Unexpected connection error: %s — retrying in 20s", exc)
            await asyncio.sleep(20)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
