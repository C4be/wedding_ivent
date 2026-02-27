from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from src.database.db import get_db
from src.utils.logger import logger


class RegisterUserMiddleware(BaseMiddleware):
    """Auto-register every new user on first interaction."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            async with await get_db() as db:
                await db.execute(
                    """INSERT OR IGNORE INTO users
                       (telegram_id, username, first_name, last_name)
                       VALUES (?, ?, ?, ?)""",
                    (user.id, user.username, user.first_name, user.last_name),
                )
                await db.commit()
            logger.debug(f"User registered/verified: {user.id} @{user.username}")
        return await handler(event, data)
