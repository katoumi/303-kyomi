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
        self.dashboard = WebDashboard(self, self.db)

    async def setup_hook(self) -> None:
        await self.db.connect()
        logger.info("Connected to SQLite database at %s", self.db.db_path)

        for cog in COGS:
            await self.load_extension(cog)
            logger.info("Loaded extension: %s", cog)

        await self.dashboard.start()
        logger.info(
            "Web Dashboard online at http://localhost:%d", self.dashboard.port
        )

        synced = await self.tree.sync()
        logger.info("Synchronized %d global slash command(s).", len(synced))

    async def on_ready(self) -> None:
        assert self.user is not None
        logger.info("Logged in as %s (ID: %d)", self.user, self.user.id)
        await self.change_presence(
            status=discord.Status.dnd,
            activity=discord.CustomActivity(name="303  •  watching"),
        )

    async def close(self) -> None:
        await self.dashboard.stop()
        await self.db.close()
        await super().close()


async def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    db_path = os.getenv("DATABASE_PATH", "data/moderation.db")

    if not token or token == "your_discord_bot_token_here":
        logger.error(
            "Missing DISCORD_TOKEN! Copy .env.example to .env and add your bot token."
        )
        return

    bot = ModBot(db_path=db_path)
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
