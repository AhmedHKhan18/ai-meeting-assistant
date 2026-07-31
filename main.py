"""Entry point: starts the Discord bot connection and the APScheduler event loop."""

import asyncio

from agents.ceo_agent import CEOAgent
from models.db import init_db
from tools.config_loader import load_settings
from tools.logging_setup import get_logger

logger = get_logger("main")


async def main() -> None:
    init_db()
    settings = load_settings()
    agent = CEOAgent(settings=settings)
    await agent.start()


if __name__ == "__main__":
    asyncio.run(main())
