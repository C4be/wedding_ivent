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

async def _submit_wish(
    message: Message,
    state: FSMContext,
    user,   # User object вместо просто username
    extra_text: str | None,
) -> None:
    data = await state.get_data()

    wish_parts = [data.get("wish_text", "")]
    if extra_text:
        wish_parts.append(f"Ограничения/аллергии: {extra_text}")
    wish_text = "\n".join(p for p in wish_parts if p)

    drinks = data.get("drinks")

    # Тот же fallback что и при регистрации
    if user.username:
        tg_username = f"@{user.username}" if not user.username.startswith("@") else user.username
    else:
        tg_username = f"tg_{user.id}"

    payload = {"wish_text": wish_text}
    if drinks:
        payload["drinks"] = drinks

    await state.clear()

    try:
        url_username = tg_username.lstrip("@")
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            resp = await client.post(f"/wishes/by-tg/{url_username}", json=payload)
        logger.info("Пожелание от %s отправлено успешно, статус %s", tg_username, resp.status_code)
        await message.answer(
            "💌 <b>Ваши пожелания успешно отправлены!</b>\n"
            "Спасибо, мы обязательно постараемся их учесть 🎉"
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        logger.error("HTTP ошибка при отправке пожелания %s: %s", tg_username, status)
        if status == 404:
            await message.answer(
                "Не нашли вас в списке гостей. "
                "Пожалуйста, сначала зарегистрируйтесь с помощью /start."
            )
        else:
            await message.answer(f"Ошибка сервиса ({status}). Попробуйте позже.")
    except Exception:
        logger.exception("Сетевая ошибка при отправке пожелания %s", tg_username)
        await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
