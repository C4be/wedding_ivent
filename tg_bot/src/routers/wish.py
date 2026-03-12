from __future__ import annotations

import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.logger import logger
from utils.external_services_client import AsyncHTTPClient
from config import settings

router = Router()


# ---------------------------------------------------------------------------
# FSM States
# ---------------------------------------------------------------------------

class WishFSM(StatesGroup):
    wish_text      = State()   # Общие пожелания / что хочет увидеть
    drinks         = State()   # Напитки
    restrictions   = State()   # Ограничения и аллергии


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def kb_skip():
    b = InlineKeyboardBuilder()
    b.button(text="⏭ Пропустить", callback_data="wish_skip")
    return b.as_markup()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

@router.message(Command("add_wish"))
async def cmd_add_wish(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(WishFSM.wish_text)
    await message.answer(
        "🎊 <b>Поделитесь вашими пожеланиями для свадьбы!</b>\n\n"
        "✍️ <b>Шаг 1/3 — Общие пожелания</b>\n"
        "Напишите, что вы хотите увидеть на свадьбе, какие конкурсы, "
        "музыку, атмосферу вы бы пожелали молодожёнам?\n\n"
        "<i>Например: хочу живую музыку, медленный танец, фотозону с цветами...</i>"
    )


# ---------------------------------------------------------------------------
# Шаг 1: Общие пожелания
# ---------------------------------------------------------------------------

@router.message(WishFSM.wish_text)
async def step_wish_text(message: Message, state: FSMContext) -> None:
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("Пожалуйста, напишите ваши пожелания текстом:")
        return
    await state.update_data(wish_text=text)
    await state.set_state(WishFSM.drinks)
    await message.answer(
        "🍾 <b>Шаг 2/3 — Напитки</b>\n"
        "Что вы хотите пить на свадьбе? Перечислите через запятую.\n\n"
        "<i>Например: шампанское, красное вино, апельсиновый сок, минеральная вода</i>",
        reply_markup=kb_skip(),
    )


# ---------------------------------------------------------------------------
# Шаг 2: Напитки
# ---------------------------------------------------------------------------

@router.callback_query(WishFSM.drinks, F.data == "wish_skip")
async def step_drinks_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(drinks=None)
    await state.set_state(WishFSM.restrictions)
    await callback.message.edit_text(
        "🚫 <b>Шаг 3/3 — Ограничения и аллергии</b>\n"
        "Есть ли у вас пищевые ограничения, аллергии или другие пожелания "
        "по меню, которые нам стоит учесть?\n\n"
        "<i>Например: аллергия на орехи, не ем мясо, непереносимость лактозы</i>",
        reply_markup=kb_skip(),
    )
    await callback.answer()


@router.message(WishFSM.drinks)
async def step_drinks(message: Message, state: FSMContext) -> None:
    raw = message.text.strip() if message.text else ""
    if not raw:
        await message.answer(
            "Введите напитки через запятую или нажмите «Пропустить»:",
            reply_markup=kb_skip(),
        )
        return
    drinks = [d.strip() for d in raw.split(",") if d.strip()]
    await state.update_data(drinks=drinks if drinks else None)
    await state.set_state(WishFSM.restrictions)
    await message.answer(
        "🚫 <b>Шаг 3/3 — Ограничения и аллергии</b>\n"
        "Есть ли у вас пищевые ограничения, аллергии или другие пожелания "
        "по меню, которые нам стоит учесть?\n\n"
        "<i>Например: аллергия на орехи, не ем мясо, непереносимость лактозы</i>",
        reply_markup=kb_skip(),
    )


# ---------------------------------------------------------------------------
# Шаг 3: Ограничения и аллергии
# ---------------------------------------------------------------------------

@router.callback_query(WishFSM.restrictions, F.data == "wish_skip")
async def step_restrictions_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await _submit_wish(callback.message, state, callback.from_user, extra_text=None)
    await callback.answer()


@router.message(WishFSM.restrictions)
async def step_restrictions(message: Message, state: FSMContext) -> None:
    restrictions = message.text.strip() if message.text else ""
    await _submit_wish(message, state, message.from_user, extra_text=restrictions or None)


# ---------------------------------------------------------------------------
# Отправка на сервер
# ---------------------------------------------------------------------------

async def _update_member_info(member_id: int, user, chat_id: int) -> None:
    """Обновляет telegram_id, chat_id и tg_username участника если они отсутствуют или некорректны."""
    tg_username = f"@{user.username}" if user.username else f"@tg_{user.id}"
    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            await client.patch(f"/members/{member_id}/telegram-id", params={"telegram_id": user.id})
            await client.patch(f"/members/{member_id}/chat-id", params={"chat_id": chat_id})
            if user.username:
                # Обновляем tg_username только если у пользователя есть реальный username
                await client.patch(f"/members/{member_id}/tg-username", params={"tg_username": tg_username})
        logger.info("Обновлена информация участника %s: telegram_id=%s, chat_id=%s", member_id, user.id, chat_id)
    except Exception:
        logger.exception("Не удалось обновить информацию участника %s", member_id)


async def _submit_wish(
    message: Message,
    state: FSMContext,
    user,
    extra_text: str | None,
) -> None:
    data = await state.get_data()

    wish_parts = [data.get("wish_text", "")]
    if extra_text:
        wish_parts.append(f"Ограничения/аллергии: {extra_text}")
    wish_text = "\n".join(p for p in wish_parts if p)

    drinks = data.get("drinks")

    if user.username:
        tg_username = f"@{user.username}" if not user.username.startswith("@") else user.username
    else:
        tg_username = f"@tg_{user.id}"

    logger.info("Пользователь %s отправляет пожелание: %s", tg_username, wish_text)

    payload = {"wish_text": wish_text}
    if drinks:
        payload["drinks"] = drinks

    await state.clear()

    async def _post_wish(username: str) -> None:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            resp = await client.post(f"/wishes/by-tg/{username}", json=payload)
        logger.info("Пожелание от %s отправлено успешно, статус %s", username, resp.status_code)

    _not_registered_text = (
        "Не нашли вас в списке гостей. "
        "Пожалуйста, сначала зарегистрируйтесь с помощью /start."
    )

    # 1. Пробуем по tg_username из Telegram-профиля
    try:
        await _post_wish(tg_username)
        await message.answer(
            "💌 <b>Ваши пожелания успешно отправлены!</b>\n"
            "Спасибо, мы обязательно постараемся их учесть 🎉"
        )
        return
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 404:
            logger.error("HTTP ошибка при отправке пожелания %s: %s", tg_username, exc.response.status_code)
            await message.answer(f"Ошибка сервиса ({exc.response.status_code}). Попробуйте позже.")
            return
        logger.warning("Не найден по tg_username=%s, пробуем telegram_id=%s", tg_username, user.id)
    except Exception:
        logger.exception("Сетевая ошибка при отправке пожелания %s", tg_username)
        await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
        return

    # 2. Ищем участника по telegram_id → берём его tg_username из БД
    db_username: str | None = None
    member_id: int | None = None
    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            resp = await client.get(f"/members/by-telegram-id/{user.id}")
            member = resp.json()
        db_username = member.get("tg_username") or None
        member_id = member.get("id")
        logger.info("Найден по telegram_id=%s, db tg_username=%s", user.id, db_username)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 404:
            logger.error("HTTP ошибка при поиске по telegram_id=%s: %s", user.id, exc.response.status_code)
            await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
            return
        logger.warning("Не найден по telegram_id=%s, пробуем по имени/фамилии", user.id)
    except Exception:
        logger.exception("Сетевая ошибка при поиске по telegram_id=%s", user.id)
        await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
        return

    # 3. Если не нашли по telegram_id — ищем по имени и фамилии из Telegram-профиля
    found_by_name = False
    if not db_username:
        tg_first = (user.first_name or "").strip()
        tg_last = (user.last_name or "").strip()
        if tg_first or tg_last:
            try:
                async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
                    resp = await client.get(
                        "/members/by-name",
                        params={"first_name": tg_first, "second_name": tg_last},
                    )
                    member = resp.json()
                db_username = member.get("tg_username") or None
                member_id = member.get("id")
                found_by_name = True
                logger.info("Найден по имени '%s %s', db tg_username=%s, id=%s", tg_first, tg_last, db_username, member_id)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404:
                    logger.error(
                        "HTTP ошибка при поиске по имени '%s %s': %s",
                        tg_first, tg_last, exc.response.status_code,
                    )
                    await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
                    return
                logger.warning("Не найден по имени '%s %s'", tg_first, tg_last)
            except Exception:
                logger.exception("Сетевая ошибка при поиске по имени '%s %s'", tg_first, tg_last)
                await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
                return

    if not db_username or not member_id:
        await message.answer(_not_registered_text)
        return

    # Если нашли через fallback — обновляем информацию участника
    if found_by_name:
        await _update_member_info(member_id, user, message.chat.id)
        # После обновления используем актуальный tg_username
        db_username = tg_username

    # 4. Повторяем запрос с username из БД
    try:
        await _post_wish(db_username)
        await message.answer(
            "💌 <b>Ваши пожелания успешно отправлены!</b>\n"
            "Спасибо, мы обязательно постараемся их учесть 🎉"
        )
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP ошибка при повторной отправке пожелания %s: %s", db_username, exc.response.status_code)
        await message.answer(_not_registered_text)
    except Exception:
        logger.exception("Сетевая ошибка при повторной отправке пожелания %s", db_username)
        await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
