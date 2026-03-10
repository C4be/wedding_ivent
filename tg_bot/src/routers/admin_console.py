import httpx
import asyncio
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError, TelegramRetryAfter

from config import settings
from utils.logger import logger
from utils.external_services_client import AsyncHTTPClient

console_router = Router()

_CONTENT_TEXT       = "text"
_CONTENT_PHOTO      = "photo"
_CONTENT_VIDEO      = "video"
_CONTENT_VOICE      = "voice"
_CONTENT_VIDEO_NOTE = "video_note"


def _is_admin(user_id) -> bool:
    return int(user_id) in (settings.ADMIN_IDS or [])


# ==================================
# Рассылка
# ==================================

class BroadcastFSM(StatesGroup):
    waiting_content = State()


@console_router.message(Command("broadcast"))
async def cmd_broadcast_start(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    # Inline-аргумент: /broadcast Текст...
    raw = (message.text or "").strip()
    parts = raw.split(None, 1)
    if len(parts) > 1 and parts[1].strip():
        await _do_broadcast(message, content_type=_CONTENT_TEXT, text=parts[1].strip())
        return

    await state.set_state(BroadcastFSM.waiting_content)
    await message.answer(
        "Отправь сообщение для рассылки.\n"
        "Поддерживаются: <b>текст</b>, <b>фото</b>, <b>видео</b>, "
        "<b>голосовое</b>, <b>кружок</b> (с подписью или без).\n\n"
        "Отменить — /cancel"
    )


@console_router.message(Command("cancel"), BroadcastFSM.waiting_content)
async def cmd_cancel_broadcast(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Рассылка отменена.")


@console_router.message(BroadcastFSM.waiting_content)
async def cmd_broadcast_content(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        await state.clear()
        return

    await state.clear()

    if message.photo:
        # берём наибольшее разрешение
        file_id = message.photo[-1].file_id
        caption = message.caption or ""
        await _do_broadcast(message, content_type=_CONTENT_PHOTO, file_id=file_id, text=caption)
    elif message.video:
        file_id = message.video.file_id
        caption = message.caption or ""
        await _do_broadcast(message, content_type=_CONTENT_VIDEO, file_id=file_id, text=caption)
    elif message.voice:
        await _do_broadcast(message, content_type=_CONTENT_VOICE, file_id=message.voice.file_id)
    elif message.video_note:
        await _do_broadcast(message, content_type=_CONTENT_VIDEO_NOTE, file_id=message.video_note.file_id)
    elif message.text:
        await _do_broadcast(message, content_type=_CONTENT_TEXT, text=message.text)
    else:
        await message.answer(
            "Поддерживаются только текст, фото, видео, голосовые и кружки. Попробуйте снова — /broadcast"
        )


async def _do_broadcast(
    message: Message,
    content_type: str,
    text: str = "",
    file_id: str = "",
) -> None:
    """Рассылает сообщение всем участникам у которых есть chat_id."""
    sent = 0
    failed = 0
    skipped = 0
    sem = asyncio.Semaphore(10)

    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL, timeout=10.0) as client:
            resp = await client.get("/members")
            users = resp.json()
    except Exception:
        logger.exception("Не удалось получить список пользователей для рассылки")
        await message.answer("Не удалось получить список пользователей. Попробуйте позже.")
        return

    if not isinstance(users, list):
        await message.answer("Сервис вернул некорректные данные.")
        return

    async def _send_wrapper(u: dict) -> None:
        nonlocal sent, failed, skipped

        chat_id = u.get("chat_id")
        if not chat_id:
            logger.warning(
                "Нет chat_id у участника id=%s (%s %s), пропускаем",
                u.get("id"), u.get("first_name"), u.get("second_name"),
            )
            skipped += 1
            return

        async def _try_send():
            if content_type == _CONTENT_PHOTO:
                await message.bot.send_photo(chat_id=chat_id, photo=file_id, caption=text or None)
            elif content_type == _CONTENT_VIDEO:
                await message.bot.send_video(chat_id=chat_id, video=file_id, caption=text or None)
            elif content_type == _CONTENT_VOICE:
                await message.bot.send_voice(chat_id=chat_id, voice=file_id)
            elif content_type == _CONTENT_VIDEO_NOTE:
                await message.bot.send_video_note(chat_id=chat_id, video_note=file_id)
            else:
                await message.bot.send_message(chat_id=chat_id, text=text)

        async with sem:
            try:
                await _try_send()
                sent += 1
            except TelegramRetryAfter as exc:
                wait = int(getattr(exc, "retry_after", 1))
                logger.warning("Rate limit, ждём %s сек", wait)
                await asyncio.sleep(wait)
                try:
                    await _try_send()
                    sent += 1
                except Exception:
                    logger.exception("Повторная попытка не удалась для chat_id=%s", chat_id)
                    failed += 1
            except (TelegramAPIError, TelegramBadRequest) as exc:
                logger.warning("Не удалось отправить chat_id=%s: %s", chat_id, exc)
                failed += 1
            except Exception:
                logger.exception("Ошибка при отправке сообщения chat_id=%s", chat_id)
                failed += 1

    await asyncio.gather(*[asyncio.create_task(_send_wrapper(u)) for u in users])

    summary = (
        f"Рассылка завершена.\n"
        f"Отправлено: {sent}\n"
        f"Не доставлено (ошибки): {failed}\n"
        f"Пропущено (нет chat_id): {skipped}"
    )
    await message.answer(summary)


# ==================================
# Прочие команды
# ==================================

@console_router.message(Command('console'))
async def cmd_console(message: Message):
    user_id = message.from_user.id
    if _is_admin(user_id):
        await message.answer("Вы Админ. Список комманд:\n<i>will be later</i>")
        return
    await message.answer("Вы не являетесь администратором! Мне жаль (")


@console_router.message(Command('cnt_peoples'))
async def cmd_cnt_peoples(message: Message):
    user_id = message.from_user.id
    if _is_admin(user_id):
        try:
            async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
                response = await client.get("/members/stats/count")
                await message.answer(f'Общее количество человек на свадьбу: {response.text}')
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP ошибка (GET /members/stats/count) = {exc.response.status_code}")
            await message.answer(f"Ошибка сервиса ({exc.response.status_code}). Попробуйте позже.")
        except Exception:
            logger.exception("Сетевая ошибка (GET /members/stats/count)")
            await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
    else:
        await message.answer("Вы не являетесь администратором! Мне жаль (")


@console_router.message(Command('cnt_families'))
async def cmd_cnt_families(message: Message):
    user_id = message.from_user.id
    if _is_admin(user_id):
        try:
            async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
                response = await client.get("/members/stats/families-count")
                await message.answer(f'Общее количество семей на свадьбу: {response.text}')
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP ошибка (GET /members/stats/families-count) = {exc.response.status_code}")
            await message.answer(f"Ошибка сервиса ({exc.response.status_code}). Попробуйте позже.")
        except Exception:
            logger.exception("Сетевая ошибка (GET /members/stats/families-count)")
            await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
    else:
        await message.answer("Вы не являетесь администратором! Мне жаль (")


@console_router.message(Command('all_members'))
async def cmd_all_members(message: Message):
    user_id = message.from_user.id
    if _is_admin(user_id):
        try:
            async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
                response = await client.get("/members")
                data = response.json()

                final_text = ""
                for i, member_dict in enumerate(data):
                    uname = member_dict.get("first_name", "") + " " + member_dict.get("second_name", "")
                    tg_id = member_dict.get("tg_username", "")
                    people = f'{uname}' + (f' ({tg_id})' if tg_id else '')
                    is_main_acc = member_dict.get("is_main_account", False)
                    is_going = member_dict.get("is_going_on_event", False)
                    member = (f'<b>{people}</b>' if is_main_acc else people) + ('✅' if is_going else '❌') + '\n'
                    final_text += f'{i + 1}) {member}'

                await message.answer(f'Список участников:\n{final_text}')
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP ошибка (GET /members) = {exc.response.status_code}")
            await message.answer(f"Ошибка сервиса ({exc.response.status_code}). Попробуйте позже.")
        except Exception:
            logger.exception("Сетевая ошибка (GET /members)")
            await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
    else:
        await message.answer("Вы не являетесь администратором! Мне жаль (")


