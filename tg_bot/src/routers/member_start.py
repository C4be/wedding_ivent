import httpx
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from utils.logger import logger
from utils.external_services_client import AsyncHTTPClient
from config import settings
from .member_registration import start_registration

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    username = message.from_user.username
    display_name = message.from_user.full_name or str(user_id)

    logger.info(f"Пользователь {username} (ID: {user_id}) запустил бота.")

    data: dict | None = None
    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            resp = await client.get(f"/members/by-telegram-id/{user_id}")
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            data = None
        else:
            logger.exception("Ошибка при обращении к DB_SERVICE_URL")
            await message.answer("Произошла ошибка при проверке аккаунта. Попробуйте позже.")
            return
    except Exception:
        logger.exception("Ошибка сетевого взаимодействия с сервисом пользователей")
        await message.answer("Не удалось связаться с сервисом пользователей. Попробуйте позже.")
        return

    if data and isinstance(data, dict) and data.get("id"):
        first_name = data.get("first_name", "").strip()
        second_name = data.get("second_name", "").strip()
        is_going = bool(data.get("is_going_on_event"))

        display_user_name = " ".join(p for p in (second_name, first_name) if p).strip()
        if not display_user_name:
            display_user_name = display_name

        if is_going:
            text = f"Привет, {display_user_name}, вижу тебя в списках участников."
        else:
            text = (
                f"Привет, {display_user_name}, вижу твою анкету. "
                "Хотите передумать и прийти на мероприятие?"
            )
        logger.info(f'Подготовлен ответ: {text}')
        await message.answer(text)
    else:
        await message.answer(
            f"Привет, {display_name}! 👋\n"
            "Не вижу тебя в списках участников. Давай зарегистрируемся!"
        )
        await start_registration(message, state)