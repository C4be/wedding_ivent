import asyncio
import sys
import os

# Ensure src/ is in path when running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS
from database.db import init_db
from middlewares.auth import RegisterUserMiddleware
from routers import user_router, admin_router
from utils.logger import logger


async def main() -> None:
    logger.info("Starting Wedding Bot...")

    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register middleware
    dp.message.middleware(RegisterUserMiddleware())
    dp.callback_query.middleware(RegisterUserMiddleware())

    # Register routers (admin first — higher priority)
    dp.include_router(admin_router)
    dp.include_router(user_router)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
