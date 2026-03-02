from __future__ import annotations

import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
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

class RegistrationFSM(StatesGroup):
    # Главный участник
    first_name = State()
    second_name = State()
    phone_number = State()
    is_going = State()
    solo_or_family = State()

    # Член семьи (цикл)
    member_role = State()
    member_first_name = State()
    member_second_name = State()
    member_phone = State()      # только для FAMALY_TAIL
    member_tg = State()         # только для FAMALY_TAIL
    member_add_more = State()


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def kb_yes_no(yes_cb: str, no_cb: str):
    b = InlineKeyboardBuilder()
    b.button(text="✅ Да", callback_data=yes_cb)
    b.button(text="❌ Нет", callback_data=no_cb)
    b.adjust(2)
    return b.as_markup()


def kb_solo_family():
    b = InlineKeyboardBuilder()
    b.button(text="👤 Только я", callback_data="reg_solo")
    b.button(text="👨‍👩‍👧 С семьёй", callback_data="reg_family")
    b.adjust(2)
    return b.as_markup()


def kb_member_role():
    b = InlineKeyboardBuilder()
    b.button(text="💑 Вторая половинка", callback_data="role_FAMALY_TAIL")
    b.button(text="👶 Ребёнок", callback_data="role_CHILD")
    b.adjust(1)
    return b.as_markup()


def kb_add_more():
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить ещё", callback_data="member_add_more")
    b.button(text="✅ Завершить регистрацию", callback_data="member_done")
    b.adjust(1)
    return b.as_markup()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _send_registration(
    state: FSMContext,
    tg_username: str,
) -> tuple[bool, str]:
    """Отправляет данные в сервис. Возвращает (успех, сообщение)."""
    data = await state.get_data()

    head = {
        "first_name": data["first_name"],
        "second_name": data["second_name"],
        "phone_number": data["phone_number"],
        "tg_username": tg_username,
        "role": "FAMALY_HEAD",
        "main_account": None,
        "is_main_account": True,
        "is_going_on_event": data["is_going"],
    }

    members: list[dict] = data.get("family_members", [])

    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            if not members:
                resp = await client.post("/members", json=head)
            else:
                payload = [head] + members
                resp = await client.post("/members/family", json=payload)

        logger.info(f"Регистрация {tg_username} прошла успешно, статус {resp.status_code}")
        return True, "Регистрация прошла успешно! 🎉"
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP ошибка при регистрации {tg_username}: {exc.response.status_code}")
        return False, f"Ошибка сервиса ({exc.response.status_code}). Попробуйте позже."
    except Exception:
        logger.exception(f"Сетевая ошибка при регистрации {tg_username}")
        return False, "Не удалось связаться с сервисом. Попробуйте позже."


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def start_registration(message: Message, state: FSMContext) -> None:
    """Запускает FSM регистрации."""
    await state.clear()
    await state.set_state(RegistrationFSM.first_name)
    await message.answer("📝 Начнём регистрацию!\n\nВведите ваше <b>имя</b>:")


# ---------------------------------------------------------------------------
# Шаг 1: Имя
# ---------------------------------------------------------------------------

@router.message(RegistrationFSM.first_name)
async def step_first_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Имя не может быть пустым. Введите ваше <b>имя</b>:")
        return
    await state.update_data(first_name=name)
    await state.set_state(RegistrationFSM.second_name)
    await message.answer("Введите вашу <b>фамилию</b>:")


# ---------------------------------------------------------------------------
# Шаг 2: Фамилия
# ---------------------------------------------------------------------------

@router.message(RegistrationFSM.second_name)
async def step_second_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Фамилия не может быть пустой. Введите вашу <b>фамилию</b>:")
        return
    await state.update_data(second_name=name)
    await state.set_state(RegistrationFSM.phone_number)
    await message.answer("Введите ваш <b>номер телефона</b> (например: 8xxxxxxxxxx):")


# ---------------------------------------------------------------------------
# Шаг 3: Телефон
# ---------------------------------------------------------------------------

@router.message(RegistrationFSM.phone_number)
async def step_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip().replace(" ", "").replace("-", "").replace("+", "")
    if not phone.isdigit() or len(phone) < 10:
        await message.answer("Некорректный номер. Введите <b>номер телефона</b> цифрами (например: 8xxxxxxxxxx):")
        return
    await state.update_data(phone_number=phone)

    # tg_username подтягиваем автоматически — шаг пропускается
    tg = message.from_user.username or ""
    if tg and not tg.startswith("@"):
        tg = f"@{tg}"
    await state.update_data(tg_username=tg)

    await state.set_state(RegistrationFSM.is_going)
    await message.answer(
        "Вы планируете <b>присутствовать</b> на мероприятии?",
        reply_markup=kb_yes_no("going_yes", "going_no"),
    )


# ---------------------------------------------------------------------------
# Шаг 4: Едет ли на мероприятие
# ---------------------------------------------------------------------------

@router.callback_query(RegistrationFSM.is_going, F.data.in_({"going_yes", "going_no"}))
async def step_is_going(callback: CallbackQuery, state: FSMContext) -> None:
    is_going = callback.data == "going_yes"
    await state.update_data(is_going=is_going, family_members=[])

    if not is_going:
        # Сохраняем анкету с is_going=False и завершаем регистрацию
        await callback.message.edit_text("Очень жаль 😔 Будем ждать тебя, если надумаешь — просто напиши!")
        await callback.answer()

        data = await state.get_data()
        tg_username = data.get("tg_username") or f"@{callback.from_user.username or ''}"
        ok, msg = await _send_registration(state, tg_username)
        if not ok:
            await callback.message.answer(msg)
        await state.clear()
        return

    await callback.message.edit_text(
        "Отлично! 🎉 Вы придёте <b>один/одна</b> или <b>с семьёй</b>?",
        reply_markup=kb_solo_family(),
    )
    await state.set_state(RegistrationFSM.solo_or_family)
    await callback.answer()


# ---------------------------------------------------------------------------
# Шаг 5: Один или с семьёй
# ---------------------------------------------------------------------------

@router.callback_query(RegistrationFSM.solo_or_family, F.data == "reg_solo")
async def step_solo(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    tg_username = data.get("tg_username") or f"@{callback.from_user.username or ''}"
    await callback.message.edit_text("Отлично! Завершаем регистрацию...")
    await callback.answer()

    ok, msg = await _send_registration(state, tg_username)
    await callback.message.answer(msg)
    await state.clear()


@router.callback_query(RegistrationFSM.solo_or_family, F.data == "reg_family")
async def step_family_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(RegistrationFSM.member_role)
    await callback.message.edit_text(
        "Добавьте первого члена семьи.\nВыберите <b>роль</b>:",
        reply_markup=kb_member_role(),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Цикл добавления членов семьи
# ---------------------------------------------------------------------------

@router.callback_query(RegistrationFSM.member_role, F.data.startswith("role_"))
async def step_member_role(callback: CallbackQuery, state: FSMContext) -> None:
    role = callback.data.removeprefix("role_")  # FAMALY_TAIL | CHILD
    await state.update_data(_current_role=role)
    await state.set_state(RegistrationFSM.member_first_name)
    role_label = "второй половинки" if role == "FAMALY_TAIL" else "ребёнка"
    await callback.message.edit_text(f"Введите <b>имя</b> {role_label}:")
    await callback.answer()


@router.message(RegistrationFSM.member_first_name)
async def step_member_first_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Имя не может быть пустым. Введите <b>имя</b>:")
        return
    await state.update_data(_m_first_name=name)
    await state.set_state(RegistrationFSM.member_second_name)
    await message.answer("Введите <b>фамилию</b>:")


@router.message(RegistrationFSM.member_second_name)
async def step_member_second_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Фамилия не может быть пустой. Введите <b>фамилию</b>:")
        return
    await state.update_data(_m_second_name=name)

    data = await state.get_data()
    role = data.get("_current_role")

    if role == "CHILD":
        # Для детей — сразу сохраняем без телефона и tg
        await _save_member_and_ask(message, state, phone="", tg="", skip_contacts=True)
    else:
        # Для второй половинки — спрашиваем телефон
        await state.set_state(RegistrationFSM.member_phone)
        await message.answer("Введите <b>номер телефона</b>:")


@router.message(RegistrationFSM.member_phone)
async def step_member_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip().replace(" ", "").replace("-", "").replace("+", "")
    if not phone.isdigit() or len(phone) < 10:
        await message.answer("Некорректный номер. Введите <b>номер телефона</b> цифрами:")
        return
    await state.update_data(_m_phone=phone)
    await state.set_state(RegistrationFSM.member_tg)
    await message.answer(
        "Введите <b>Telegram username</b> второй половинки (например: @username):\n"
        "<i>Поле обязательно для заполнения.</i>",
    )


@router.message(RegistrationFSM.member_tg)
async def step_member_tg(message: Message, state: FSMContext) -> None:
    tg = message.text.strip()
    if tg and not tg.startswith("@"):
        tg = f"@{tg}"

    # Валидация: username не должен быть пустым (только "@" не считается)
    if not tg or tg == "@":
        await message.answer(
            "Username не может быть пустым. Введите <b>Telegram username</b> (например: @username):"
        )
        return

    data = await state.get_data()
    await _save_member_and_ask(message, state, phone=data.get("_m_phone", ""), tg=tg)


# ---------------------------------------------------------------------------
# Сохранение члена семьи
# ---------------------------------------------------------------------------

async def _save_member_and_ask(
    message: Message,
    state: FSMContext,
    phone: str,
    tg: str,
    skip_contacts: bool = False,
) -> None:
    """Сохраняет текущего члена семьи и спрашивает, добавить ли ещё."""
    data = await state.get_data()
    role = data["_current_role"]

    member: dict = {
        "first_name": data["_m_first_name"],
        "second_name": data["_m_second_name"],
        "role": role,
        "is_main_account": False,
        "is_going_on_event": True,
    }

    if not skip_contacts:
        member["phone_number"] = phone
        member["tg_username"] = tg

    family_members: list = data.get("family_members", [])
    family_members.append(member)
    await state.update_data(family_members=family_members)

    await state.set_state(RegistrationFSM.member_add_more)
    await message.answer(
        f"✅ {data['_m_first_name']} {data['_m_second_name']} добавлен(а).\n\n"
        "Хотите добавить ещё одного члена семьи?",
        reply_markup=kb_add_more(),
    )


# ---------------------------------------------------------------------------
# Добавить ещё / завершить
# ---------------------------------------------------------------------------

@router.callback_query(RegistrationFSM.member_add_more, F.data == "member_add_more")
async def step_add_more(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(RegistrationFSM.member_role)
    await callback.message.edit_text(
        "Выберите <b>роль</b> следующего члена семьи:",
        reply_markup=kb_member_role(),
    )
    await callback.answer()


@router.callback_query(RegistrationFSM.member_add_more, F.data == "member_done")
async def step_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    tg_username = data.get("tg_username") or f"@{callback.from_user.username or ''}"

    await callback.message.edit_text("Завершаем регистрацию...")
    await callback.answer()

    ok, msg = await _send_registration(state, tg_username)
    await callback.message.answer(msg)
    await state.clear()
