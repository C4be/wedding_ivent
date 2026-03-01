from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

from database.db import get_db
from utils.logger import logger
from config import ADMIN_IDS


class RegisterUserMiddleware(BaseMiddleware):
    """
    Middleware для регистрации новых пользователей в БД и назначению админки
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        is_admin = False

        # 1. Регистрация и проверка пользователя
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
            is_admin = user.id in ADMIN_IDS

        # 2. Добавляем флаг is_admin в data для дальнейшего использования в хендлерах
        data['is_admin'] = is_admin

        return await handler(event, data)
