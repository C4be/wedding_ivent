import httpx
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

from utils.logger import logger
from utils.external_services_client import AsyncHTTPClient
from config import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id
    username = message.from_user.username
    display_name = message.from_user.full_name or str(user_id)

    logger.info(f"Пользователь {username} (ID: {user_id}) запустил бота.")

    # Если у пользователя нет username — попросим его указать его в настройках Telegram
    if not username:
        await message.answer(
            "Похоже, у вас нет Telegram username. Пожалуйста, задайте его в настройках Telegram (Username) или используйте сайт для привязки аккаунта, затем повторите /start."
        )
        return

    # Приведём username к формату с @
    if not username.startswith("@"):
        username = f"@{username}"

    data: dict | None = None
    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            # обращаемся к сервису по query-параметру tg_username
            resp = await client.get("/members/tg_username", params={"tg_username": username})
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        # если сервис вернул 404 — считаем, что пользователя нет в БД
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
    
    # Обработка результата
    if data and isinstance(data, dict) and data.get("id"):
        first_name = data.get("first_name", "").strip()
        second_name = data.get("second_name", "").strip()
        is_going = bool(data.get("is_going_on_event"))

        # Формируем отображаемое имя как "Фамилия Имя"
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
    else:
        text = (
            f"Привет, {display_name}, не вижу тебя в списках пользователей. "
            "Хочешь зарегистрироваться на мероприятие?"
        )
    logger.info(f'Подготовлен ответ: {text}')
    await message.answer(text)