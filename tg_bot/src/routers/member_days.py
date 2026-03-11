
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from utils.logger import logger
from utils.external_services_client import AsyncHTTPClient
from config import settings

router = Router()


async def _get_config():
    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            resp = await client.get("/site-config/latest")
            return resp.json()
    except Exception:
        logger.exception("Ошибка при получении конфигурации сайта")
        return None

def _format_timeline(tl: dict) -> str:
    if not tl:
        return ""
    title = tl.get("title", "")
    events = tl.get("events", []) or []
    parts = []
    if title:
        parts.append(f"{title}")
    for ev in events:
        time = ev.get("time", "")
        icon = ev.get("icon", "")
        ev_title = ev.get("title", "")
        desc = ev.get("description", "")
        line = f"{time} {icon} {ev_title}"
        if desc:
            line += f"\n{desc}"
        parts.append(line)
    return "\n\n".join(parts)

@router.message(Command("day1"))
async def cmd_member_day1(message: Message):
    config = await _get_config()
    if not config:
        await message.answer("Не удалось получить информацию о днях. Попробуйте позже.")
        return

    event = config.get("event", {})
    timeline_day1 = event.get("timeline_day1") or {}

    if not timeline_day1:
        await message.answer("Информация о первом дне не настроена. Обратитесь к организаторам.")
        return

    response_text = "📅 День 1:\n\n" + _format_timeline(timeline_day1)
    await message.answer(response_text)

@router.message(Command("day2"))
async def cmd_member_day2(message: Message):
    config = await _get_config()
    if not config:
        await message.answer("Не удалось получить информацию о днях. Попробуйте позже.")
        return

    event = config.get("event", {})
    timeline_day2 = event.get("timeline_day2") or {}

    if not timeline_day2:
        await message.answer("Информация о втором дне не настроена. Обратитесь к организаторам.")
        return

    response_text = "📅 День 2:\n\n" + _format_timeline(timeline_day2)
    await message.answer(response_text)