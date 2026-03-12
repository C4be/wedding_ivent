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
# FSM — добавление нового участника семьи
# ---------------------------------------------------------------------------

class AddFamilyMemberFSM(StatesGroup):
    role = State()
    first_name = State()
    second_name = State()
    phone = State()          # только для FAMALY_TAIL


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def _kb_family_list(family: list[dict]) -> object:
    """Список участников семьи — каждый на отдельной кнопке."""
    b = InlineKeyboardBuilder()
    for m in family:
        name = f"{m.get('first_name', '')} {m.get('second_name', '')}".strip()
        role_icon = {"FAMALY_HEAD": "👑", "FAMALY_TAIL": "💑", "CHILD": "👶"}.get(m.get("role", ""), "👤")
        going_icon = "✅" if m.get("is_going_on_event") else "❌"
        b.button(
            text=f"{role_icon} {name} {going_icon}",
            callback_data=f"fam_member:{m['id']}",
        )
    b.button(text="➕ Добавить участника", callback_data="fam_add_member")
    b.adjust(1)
    return b.as_markup()


def _kb_member_actions(member_id: int, is_going: bool) -> object:
    b = InlineKeyboardBuilder()
    if is_going:
        b.button(text="❌ Отметить как не придёт", callback_data=f"fam_going:{member_id}:0")
    else:
        b.button(text="✅ Отметить как придёт", callback_data=f"fam_going:{member_id}:1")
    b.button(text="🗑 Удалить участника", callback_data=f"fam_delete:{member_id}")
    b.button(text="🔙 Назад к списку", callback_data="fam_back")
    b.adjust(1)
    return b.as_markup()


def _kb_member_role():
    b = InlineKeyboardBuilder()
    b.button(text="💑 Вторая половинка", callback_data="fam_role_FAMALY_TAIL")
    b.button(text="👶 Ребёнок", callback_data="fam_role_CHILD")
    b.adjust(1)
    return b.as_markup()


def _kb_confirm_delete(member_id: int):
    b = InlineKeyboardBuilder()
    b.button(text="✅ Да, удалить", callback_data=f"fam_delete_confirm:{member_id}")
    b.button(text="❌ Отмена", callback_data=f"fam_member:{member_id}")
    b.adjust(2)
    return b.as_markup()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _role_label(role: str) -> str:
    return {"FAMALY_HEAD": "Глава семьи", "FAMALY_TAIL": "Вторая половинка", "CHILD": "Ребёнок"}.get(role, role)


async def _get_member_by_tg_id(telegram_id: int) -> dict | None:
    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            resp = await client.get(f"/members/by-telegram-id/{telegram_id}")
            return resp.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return None
        raise
    except Exception:
        raise


async def _get_family(first_name: str, second_name: str) -> list[dict]:
    async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
        resp = await client.get(
            "/members/family/search",
            params={"first_name": first_name, "second_name": second_name},
        )
        return resp.json()


def _family_text(family: list[dict]) -> str:
    lines = ["<b>👨‍👩‍👧 Ваша семья:</b>\n"]
    for m in family:
        name = f"{m.get('first_name', '')} {m.get('second_name', '')}".strip()
        role = _role_label(m.get("role", ""))
        going = "✅ придёт" if m.get("is_going_on_event") else "❌ не придёт"
        lines.append(f"• <b>{name}</b> — {role} {going}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# /family entry point
# ---------------------------------------------------------------------------

@router.message(Command("family"))
async def cmd_family(message: Message, state: FSMContext) -> None:
    await state.clear()
    telegram_id = message.from_user.id

    try:
        member = await _get_member_by_tg_id(telegram_id)
    except Exception:
        logger.exception("Ошибка при поиске участника по telegram_id=%s", telegram_id)
        await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
        return

    if not member or not member.get("id"):
        await message.answer(
            "Не нашёл тебя в списке гостей. Сначала зарегистрируйся — /start"
        )
        return

    # Проверяем, является ли пользователь главным участником семьи
    if not member.get("is_main_account", False):
        await message.answer(
            "⚠️ Управление семьёй доступно только тому, кто регистрировал вашу семью.\n"
            "Обратитесь к тому, кто вас зарегистрировал."
        )
        return

    first_name = member.get("first_name", "")
    second_name = member.get("second_name", "")

    try:
        family = await _get_family(first_name, second_name)
    except Exception:
        logger.exception("Ошибка при получении семьи для %s %s", first_name, second_name)
        await message.answer("Не удалось загрузить данные семьи. Попробуйте позже.")
        return

    if not family:
        await message.answer("Не удалось найти данные о вашей семье.")
        return

    # Сохраняем данные главного участника, включая его id
    await state.update_data(
        _head_first_name=first_name,
        _head_second_name=second_name,
        _head_id=member.get("id"),
    )

    await message.answer(
        _family_text(family),
        reply_markup=_kb_family_list(family),
    )


# ---------------------------------------------------------------------------
# Просмотр конкретного участника
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("fam_member:"))
async def cb_show_member(callback: CallbackQuery, state: FSMContext) -> None:
    member_id = int(callback.data.split(":")[1])

    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            resp = await client.get(f"/members/by-telegram-id/{callback.from_user.id}")
            me = resp.json()
            first_name = me.get("first_name", "")
            second_name = me.get("second_name", "")
            family = await _get_family(first_name, second_name)
    except Exception:
        logger.exception("Ошибка при получении данных семьи")
        await callback.answer("Ошибка загрузки данных.", show_alert=True)
        return

    member = next((m for m in family if m["id"] == member_id), None)
    if not member:
        await callback.answer("Участник не найден.", show_alert=True)
        return

    name = f"{member.get('first_name', '')} {member.get('second_name', '')}".strip()
    role = _role_label(member.get("role", ""))
    going = "✅ придёт" if member.get("is_going_on_event") else "❌ не придёт"
    phone = member.get("phone_number") or "не указан"
    tg = member.get("tg_username") or "не указан"

    text = (
        f"<b>{name}</b>\n"
        f"Роль: {role}\n"
        f"Статус: {going}\n"
        f"Телефон: <code>{phone}</code>\n"
        f"Telegram: {tg}"
    )

    is_going = bool(member.get("is_going_on_event"))
    await callback.message.edit_text(text, reply_markup=_kb_member_actions(member_id, is_going))
    await callback.answer()


# ---------------------------------------------------------------------------
# Назад к списку семьи
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "fam_back")
async def cb_back_to_family(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    first_name = data.get("_head_first_name", "")
    second_name = data.get("_head_second_name", "")

    if not first_name:
        # Перезагрузить из БД
        try:
            me = await _get_member_by_tg_id(callback.from_user.id)
            first_name = me.get("first_name", "") if me else ""
            second_name = me.get("second_name", "") if me else ""
        except Exception:
            await callback.answer("Ошибка загрузки данных.", show_alert=True)
            return

    try:
        family = await _get_family(first_name, second_name)
    except Exception:
        await callback.answer("Ошибка загрузки данных.", show_alert=True)
        return

    await callback.message.edit_text(
        _family_text(family),
        reply_markup=_kb_family_list(family),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Изменить статус присутствия
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("fam_going:"))
async def cb_toggle_going(callback: CallbackQuery, state: FSMContext) -> None:
    _, member_id_str, val_str = callback.data.split(":")
    member_id = int(member_id_str)
    is_going = val_str == "1"

    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            resp = await client.patch(
                f"/members/{member_id}/going",
                params={"is_going": is_going},
            )
            updated = resp.json()
        logger.info("Статус участника %s изменён: is_going=%s", member_id, is_going)
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP ошибка при изменении статуса %s: %s", member_id, exc.response.status_code)
        await callback.answer(f"Ошибка сервиса ({exc.response.status_code}).", show_alert=True)
        return
    except Exception:
        logger.exception("Сетевая ошибка при изменении статуса %s", member_id)
        await callback.answer("Не удалось связаться с сервисом.", show_alert=True)
        return

    name = f"{updated.get('first_name', '')} {updated.get('second_name', '')}".strip()
    status_text = "✅ будет присутствовать" if is_going else "❌ не придёт"
    await callback.answer(f"{name} теперь {status_text}", show_alert=True)

    # Перерисовываем карточку участника
    role = _role_label(updated.get("role", ""))
    going_text = "✅ придёт" if updated.get("is_going_on_event") else "❌ не придёт"
    phone = updated.get("phone_number") or "не указан"
    tg = updated.get("tg_username") or "не указан"
    text = (
        f"<b>{name}</b>\n"
        f"Роль: {role}\n"
        f"Статус: {going_text}\n"
        f"Телефон: <code>{phone}</code>\n"
        f"Telegram: {tg}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=_kb_member_actions(member_id, is_going),
    )


# ---------------------------------------------------------------------------
# Удаление участника
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("fam_delete:"))
async def cb_delete_member(callback: CallbackQuery, state: FSMContext) -> None:
    member_id = int(callback.data.split(":")[1])

    # Запрашиваем подтверждение
    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите <b>удалить</b> этого участника?\n"
        "Это действие нельзя отменить.",
        reply_markup=_kb_confirm_delete(member_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fam_delete_confirm:"))
async def cb_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    member_id = int(callback.data.split(":")[1])

    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            await client.request("DELETE", f"/members/{member_id}")
        logger.info("Участник %s удалён", member_id)
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP ошибка при удалении %s: %s", member_id, exc.response.status_code)
        await callback.answer(f"Ошибка сервиса ({exc.response.status_code}).", show_alert=True)
        return
    except Exception:
        logger.exception("Сетевая ошибка при удалении %s", member_id)
        await callback.answer("Не удалось связаться с сервисом.", show_alert=True)
        return

    await callback.answer("🗑 Участник удалён.", show_alert=True)

    # Возвращаемся к обновлённому списку семьи
    data = await state.get_data()
    first_name = data.get("_head_first_name", "")
    second_name = data.get("_head_second_name", "")

    try:
        family = await _get_family(first_name, second_name)
    except Exception:
        await callback.message.edit_text("Участник удалён. Обновите список — /family")
        return

    if not family:
        await callback.message.edit_text(
            "Участник удалён. Семья пуста. Вы можете зарегистрировать новых участников через /family"
        )
        return

    await callback.message.edit_text(
        _family_text(family),
        reply_markup=_kb_family_list(family),
    )


# ---------------------------------------------------------------------------
# Добавление нового участника — FSM
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "fam_add_member")
async def cb_add_member_start(callback: CallbackQuery, state: FSMContext) -> None:
    # Дополнительная проверка на случай, если state был создан в обход /family
    data = await state.get_data()
    if not data.get("_head_id"):
        # Перепроверяем из БД
        try:
            me = await _get_member_by_tg_id(callback.from_user.id)
        except Exception:
            await callback.answer("Ошибка загрузки данных.", show_alert=True)
            return
        if not me or not me.get("is_main_account", False):
            await callback.answer(
                "Управление семьёй доступно только тому, кто регистрировал вашу семью.",
                show_alert=True,
            )
            return
        await state.update_data(
            _head_first_name=me.get("first_name", ""),
            _head_second_name=me.get("second_name", ""),
            _head_id=me.get("id"),
        )

    await state.set_state(AddFamilyMemberFSM.role)
    await callback.message.edit_text(
        "Выбери <b>роль</b> нового участника:",
        reply_markup=_kb_member_role(),
    )
    await callback.answer()


@router.callback_query(AddFamilyMemberFSM.role, F.data.startswith("fam_role_"))
async def cb_add_member_role(callback: CallbackQuery, state: FSMContext) -> None:
    role = callback.data.removeprefix("fam_role_")
    await state.update_data(_new_role=role)
    await state.set_state(AddFamilyMemberFSM.first_name)
    role_label = "второй половинки" if role == "FAMALY_TAIL" else "ребёнка"
    await callback.message.edit_text(f"Введи <b>имя</b> {role_label}:")
    await callback.answer()


@router.message(AddFamilyMemberFSM.first_name)
async def add_member_first_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Имя не может быть пустым. Введи <b>имя</b>:")
        return
    await state.update_data(_new_first_name=name)
    await state.set_state(AddFamilyMemberFSM.second_name)
    await message.answer("Введи <b>фамилию</b>:")


@router.message(AddFamilyMemberFSM.second_name)
async def add_member_second_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Фамилия не может быть пустой. Введи <b>фамилию</b>:")
        return
    await state.update_data(_new_second_name=name)

    data = await state.get_data()
    role = data.get("_new_role")

    if role == "CHILD":
        await _save_new_family_member(message, state, phone=None)
    else:
        await state.set_state(AddFamilyMemberFSM.phone)
        await message.answer("Введи <b>номер телефона</b> второй половинки:")


@router.message(AddFamilyMemberFSM.phone)
async def add_member_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip().replace(" ", "").replace("-", "").replace("+", "")
    if not phone.isdigit() or len(phone) < 10:
        await message.answer("Некорректный номер. Введи <b>номер телефона</b> цифрами:")
        return
    await _save_new_family_member(message, state, phone=phone)


async def _save_new_family_member(message: Message, state: FSMContext, phone: str | None) -> None:
    data = await state.get_data()
    role = data["_new_role"]
    first_name = data["_new_first_name"]
    second_name = data["_new_second_name"]
    head_first = data.get("_head_first_name", "")
    head_second = data.get("_head_second_name", "")

    # Берём id главного участника из state (сохранили при входе в /family)
    main_account_id: int | None = data.get("_head_id")

    # Если по какой-то причине нет — ищем через API
    if not main_account_id:
        try:
            family = await _get_family(head_first, head_second)
            head = next((m for m in family if m.get("role") == "FAMALY_HEAD"), None)
            if head:
                main_account_id = head["id"]
        except Exception:
            logger.exception("Не удалось получить семью для определения main_account")

    payload: dict = {
        "first_name": first_name,
        "second_name": second_name,
        "role": role,
        "main_account": main_account_id,
        "is_main_account": False,
        "is_going_on_event": True,
    }
    if phone:
        payload["phone_number"] = phone

    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            resp = await client.post("/members", json=payload)
            new_member = resp.json()
        logger.info("Добавлен новый участник семьи: %s %s (id=%s)", first_name, second_name, new_member.get("id"))
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP ошибка при добавлении участника: %s", exc.response.status_code)
        await message.answer(f"Ошибка сервиса ({exc.response.status_code}). Попробуйте позже.")
        await state.clear()
        return
    except Exception:
        logger.exception("Сетевая ошибка при добавлении участника")
        await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
        await state.clear()
        return

    # Показываем обновлённый список
    try:
        family = await _get_family(head_first, head_second)
    except Exception:
        await message.answer(
            f"✅ {first_name} {second_name} добавлен(а)!\n\nОбновите список — /family"
        )
        await state.clear()
        return

    await state.update_data(
        _new_role=None, _new_first_name=None, _new_second_name=None
    )
    await message.answer(
        f"✅ {first_name} {second_name} добавлен(а)!\n\n" + _family_text(family),
        reply_markup=_kb_family_list(family),
    )
    await state.set_state(None)
