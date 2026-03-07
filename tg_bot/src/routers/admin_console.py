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

# ==================================
# Рассылка
# ==================================

def _is_admin(user_id) -> bool:
    return int(user_id) in (settings.ADMIN_IDS or [])

class BroadcastFSM(StatesGroup):
    text = State()

@console_router.message(Command("broadcast"))
async def cmd_broadcast_start(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    # support inline args: /broadcast Текст...
    raw = (message.text or "").strip()
    args = ""
    if raw:
        # raw может быть "/broadcast", "/broadcast@YourBot", или "/broadcast Текст..."
        parts = raw.split(None, 1)
        if len(parts) > 1:
            args = parts[1].strip()

    if args:
        await _do_broadcast(message, args)
        return

    await state.set_state(BroadcastFSM.text)
    await message.answer("Отправь текст рассылки (отменить — /cancel).")



@console_router.message(BroadcastFSM.text)
async def cmd_broadcast_text(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        await state.clear()
        return

    text = message.text or ""
    await _do_broadcast(message, text)
    await state.clear()


async def _do_broadcast(message: Message, text: str) -> None:
    """Собирает пользователей из сервиса и пытается отправить сообщение каждому.
    Сначала — по chat_id (если есть в данных), иначе — по tg_username (через get_chat).
    Отчёт отправляется администратору по завершении.
    """
    sent = 0
    failed = 0
    skipped = 0

    # ограничитель параллельных отправок, чтобы избежать rate-limit
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

    async def _send_to_user(u: dict) -> None:
        nonlocal sent, failed, skipped
        async with sem:
            # возможные поля: 'tg_chat_id', 'chat_id', 'tg_username'
            chat_id = u.get("tg_chat_id") or u.get("chat_id")
            tg_username = u.get("tg_username")  # e.g. "@nick" or "nick"
            try:
                if chat_id:
                    await message.bot.send_message(chat_id=chat_id, text=text)
                    sent += 1
                    return

                if tg_username:
                    # ensure starts with @ for get_chat
                    if not tg_username.startswith("@"):
                        username = f"@{tg_username}"
                    else:
                        username = tg_username
                    # get_chat может вернуть объект, если бот имеет доступ
                    chat = await message.bot.get_chat(username)
                    await message.bot.send_message(chat_id=chat.id, text=text)
                    sent += 1
                    return

                # нет контактной информации
                skipped += 1
            except (TelegramAPIError, TelegramBadRequest) as exc:
                # Forbidden -> пользователь не дал доступ / не начинал диалог
                logger.warning("Не удалось отправить пользователю %s: %s", u.get("tg_username") or u.get("id"), exc)
                failed += 1
            except TelegramRetryAfter as exc:
                # Telegram rate limit — задержаем и повторим
                wait = int(getattr(exc, "retry_after", 1))
                logger.warning("Rate limit, ждём %s сек", wait)
                await asyncio.sleep(wait)
                try:
                    # повторная попытка (простая)
                    if chat_id:
                        await message.bot.send_message(chat_id=chat_id, text=text)
                    elif tg_username:
                        if not tg_username.startswith("@"):
                            username = f"@{tg_username}"
                        else:
                            username = tg_username
                        chat = await message.bot.get_chat(username)
                        await message.bot.send_message(chat_id=chat.id, text=text)
                    sent += 1
                except Exception:
                    logger.exception("Повторная попытка не удалась")
                    failed += 1
            except Exception:
                logger.exception("Ошибка при отправке сообщения")
                failed += 1

    tasks = [asyncio.create_task(_send_to_user(u)) for u in users]
    # await all with simple gather to surface exceptions inside tasks (they are caught inside)
    await asyncio.gather(*tasks)

    summary = (
        f"Рассылка завершена.\n"
        f"Отправлено: {sent}\n"
        f"Не доставлено (ошибки): {failed}\n"
        f"Пропущено (нет контактов): {skipped}"
    )
    await message.answer(summary)



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
                data = response.text
                await message.answer(f'Общее количество человек на свадьбу: {data}')

        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP ошибка (GET /members/stats/count) = {exc.response.status_code}")
            await message.answer(f"Ошибка сервиса ({exc.response.status_code}). Попробуйте позже.")
            return
        except Exception:
            logger.exception(f"Сетевая ошибка (GET /members/stats/count)")
            await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
            return
    else:
        await message.answer("Вы не являетесь администратором! Мне жаль (")


@console_router.message(Command('cnt_families'))
async def cmd_cnt_families(message: Message):
    user_id = message.from_user.id
    if _is_admin(user_id):
        try:
            async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
                response = await client.get("/members/stats/families-count")
                data = response.text
                await message.answer(f'Общее количество семей на свадьбу: {data}')

        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP ошибка (GET /members/stats/families-count) = {exc.response.status_code}")
            await message.answer(f"Ошибка сервиса ({exc.response.status_code}). Попробуйте позже.")
            return
        except Exception:
            logger.exception(f"Сетевая ошибка (GET /members/stats/families-count)")
            await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
            return
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

                # formating text
                final_text = ""
                for i in range(len(data)):
                    memeber_dict = data[i]
                    uname = memeber_dict.get("first_name", "") + " " + memeber_dict.get("second_name", "")
                    tg_id = memeber_dict.get("tg_username", "")

                    people = f'{uname}' + (f' (@{tg_id})' if tg_id else '')

                    is_main_acc = memeber_dict.get("is_main_account", False)
                    is_going = memeber_dict.get("is_going_on_event", False)
                    member = (f'<b>{people}</b>' if is_main_acc else people) + ('✅' if is_going else '❌') + '\n'

                    final_text += f'{i + 1}) {member}'

                await message.answer(f'Список участников:\n{final_text}')

        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP ошибка (GET /members) = {exc.response.status_code}")
            await message.answer(f"Ошибка сервиса ({exc.response.status_code}). Попробуйте позже.")
            return
        except Exception:
            logger.exception(f"Сетевая ошибка (GET /members)")
            await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
            return
    else:
        await message.answer("Вы не являетесь администратором! Мне жаль (")


