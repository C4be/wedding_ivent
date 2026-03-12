from __future__ import annotations

import httpx
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Tuple, Optional

from utils.logger import logger
from utils.external_services_client import AsyncHTTPClient
from config import settings

router = Router()


# ---------------------------------------------------------------------------
# FSM States
# ---------------------------------------------------------------------------

class JoinRegistrationFSM(StatesGroup):
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
    member_phone = State()       # только для FAMALY_TAIL
    member_add_more = State()


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def _kb_yes_no(yes_cb: str, no_cb: str):
    b = InlineKeyboardBuilder()
    b.button(text="✅ Да", callback_data=yes_cb)
    b.button(text="❌ Нет", callback_data=no_cb)
    b.adjust(2)
    return b.as_markup()


def _kb_solo_family():
    b = InlineKeyboardBuilder()
    b.button(text="👤 Только я", callback_data="join_solo")
    b.button(text="👨‍👩‍👧 С семьёй", callback_data="join_family")
    b.adjust(2)
    return b.as_markup()


def _kb_member_role():
    b = InlineKeyboardBuilder()
    b.button(text="💑 Вторая половинка", callback_data="jrole_FAMALY_TAIL")
    b.button(text="👶 Ребёнок", callback_data="jrole_CHILD")
    b.adjust(1)
    return b.as_markup()


def _kb_add_more():
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить ещё", callback_data="jmember_add_more")
    b.button(text="✅ Завершить регистрацию", callback_data="jmember_done")
    b.adjust(1)
    return b.as_markup()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def __get_user_info(user):
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def _build_tg_username(user) -> str:
    if user.username:
        uname = user.username
        return f"@{uname}" if not uname.startswith("@") else uname
    return f"@id_{user.id}"


async def __check_member_in_db_by_username(
    username: str, full_name: str, msg: Message
) -> Tuple[Optional[dict], bool]:
    if not username.startswith("@"):
        username = f"@{username}"

    async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
        try:
            response = await client.get("/members/tg_username", params={"tg_username": username})
            if response.status_code == 200:
                member_data: dict = response.json()
                logger.info(f"Пользователь {full_name} найден в БД по username. ID: {member_data.get('id')}")
                await msg.reply("Обнаружил Вас в Базе данных по username! Проверю информацию и продолжим дальше...")
                return member_data, True
            elif response.status_code == 404:
                logger.info(f"Пользователь {full_name} не найден в БД по username.")
                return None, False
            else:
                logger.error(f"Ошибка БД для {full_name}: {response.status_code} - {response.text}")
                return None, False
        except Exception as e:
            logger.error(f"Исключение при запросе к БД для {full_name}: {e}")
            await msg.reply(f"Произошла ошибка при проверке по username.")
            return None, False


async def __check_member_in_db_by_full_name(
    first_name: str, second_name: str, msg: Message
) -> Tuple[Optional[dict], bool]:
    full_name = f"{first_name} {second_name}".strip().title()
    async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
        try:
            response = await client.get(
                "/members/by-name",
                params={"first_name": first_name, "second_name": second_name},
            )
            if response.status_code == 200:
                member_data: dict = response.json()
                logger.info(f"Пользователь {full_name} найден в БД по полному имени. ID: {member_data.get('id')}")
                await msg.reply("Обнаружил Вас в Базе данных по полному имени! Проверю информацию и продолжим дальше...")
                return member_data, True
            elif response.status_code == 404:
                logger.info(f"Пользователь {full_name} не найден в БД по полному имени.")
                return None, False
            else:
                logger.error(f"Ошибка БД для {full_name} по имени: {response.status_code} - {response.text}")
                return None, False
        except Exception as e:
            logger.error(f"Исключение при запросе к БД для {full_name} по имени: {e}")
            await msg.reply("Произошла ошибка при проверке по имени и фамилии.")
            return None, False


async def _send_registration(
    state: FSMContext,
    tg_username: str,
    telegram_id: int,
    chat_id: int,
) -> tuple[bool, str]:
    """Отправляет данные регистрации в сервис."""
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

            member_data = resp.json()

            if isinstance(member_data, list):
                member_id = member_data[0].get("id")
            else:
                member_id = member_data.get("id")

            if member_id:
                try:
                    await client.patch(
                        f"/members/{member_id}/telegram-id",
                        params={"telegram_id": telegram_id},
                    )
                    await client.patch(
                        f"/members/{member_id}/chat-id",
                        params={"chat_id": chat_id},
                    )
                    logger.info(f"Обновлены telegram_id и chat_id для участника {member_id}")
                except Exception:
                    logger.exception(f"Не удалось обновить telegram_id/chat_id для участника {member_id}")

        logger.info(f"Регистрация {tg_username} прошла успешно, статус {resp.status_code}")
        return True, "Регистрация прошла успешно! 🎉"
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP ошибка при регистрации {tg_username}: {exc.response.status_code}")
        return False, f"Ошибка сервиса ({exc.response.status_code}). Попробуйте позже."
    except Exception:
        logger.exception(f"Сетевая ошибка при регистрации {tg_username}")
        return False, "Не удалось связаться с сервисом. Попробуйте позже."


async def _update_member_info(member_id: int, user, chat_id: int) -> None:
    """Обновляет telegram_id, chat_id и tg_username участника если они отсутствуют или некорректны."""
    tg_username = f"@{user.username}" if user.username else f"@tg_{user.id}"
    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            await client.patch(f"/members/{member_id}/telegram-id", params={"telegram_id": user.id})
            await client.patch(f"/members/{member_id}/chat-id", params={"chat_id": chat_id})
            if user.username:
                await client.patch(f"/members/{member_id}/tg-username", params={"tg_username": tg_username})
        logger.info("Обновлена информация участника %s: telegram_id=%s, chat_id=%s", member_id, user.id, chat_id)
    except Exception:
        logger.exception("Не удалось обновить информацию участника %s", member_id)


# ---------------------------------------------------------------------------
# Entry point — /join
# ---------------------------------------------------------------------------

@router.message(Command("join"))
async def cmd_join(message: Message, state: FSMContext):
    user = message.from_user
    if not user:
        await message.reply("Не удалось получить информацию о Вас.")
        return

    user_info = __get_user_info(user)
    first_name = user_info.get("first_name", "")
    last_name = user_info.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip().title()
    username = user_info.get("username", "")
    user_id = user_info.get("id", "")

    logger.info(f"Пользователь {full_name} (@{username}, ID: {user_id}) пытается присоединиться к свадебному ивенту.")
    hello_message = await message.reply(f"Приветствую, {full_name}. Сейчас я проверю тебя в базе данных...")

    # 1. Поиск по username
    member_data, is_ok = await __check_member_in_db_by_username(username, full_name, hello_message)

    if not is_ok:
        # 2. Поиск по имени и фамилии
        member_data, is_ok = await __check_member_in_db_by_full_name(first_name, last_name, hello_message)

        if not is_ok:
            # 3. Не найден — запускаем регистрацию
            logger.info(f"Пользователь {full_name} (@{username}, ID: {user_id}) не найден. Запускаем регистрацию.")
            await hello_message.reply(
                "Не нашёл тебя в базе данных. Давай зарегистрируемся! 📝\n\n"
                "Введи своё <b>имя</b> (как тебя зовут):"
            )
            await state.clear()
            await state.update_data(_tg_username=_build_tg_username(user), _telegram_id=user_id)
            await state.set_state(JoinRegistrationFSM.first_name)
            return

        # Найден по имени/фамилии — обновляем информацию
        if member_data and member_data.get("id"):
            await _update_member_info(member_data["id"], user, message.chat.id)

    # Найден по username — на всякий случай обновляем telegram_id и chat_id
    elif member_data and member_data.get("id"):
        await _update_member_info(member_data["id"], user, message.chat.id)

    await hello_message.reply(
        f"Отлично, {full_name}! Ты уже есть в нашей базе данных. Добро пожаловать! 🎉"
    )


# ---------------------------------------------------------------------------
# Шаг 1: Имя
# ---------------------------------------------------------------------------

@router.message(JoinRegistrationFSM.first_name)
async def join_step_first_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Имя не может быть пустым. Введи своё <b>имя</b>:")
        return
    await state.update_data(first_name=name)
    await state.set_state(JoinRegistrationFSM.second_name)
    await message.answer("Введи свою <b>фамилию</b>:")


# ---------------------------------------------------------------------------
# Шаг 2: Фамилия
# ---------------------------------------------------------------------------

@router.message(JoinRegistrationFSM.second_name)
async def join_step_second_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Фамилия не может быть пустой. Введи свою <b>фамилию</b>:")
        return
    await state.update_data(second_name=name)
    await state.set_state(JoinRegistrationFSM.phone_number)
    await message.answer("Введи свой <b>номер телефона</b> (например: 8xxxxxxxxxx):")


# ---------------------------------------------------------------------------
# Шаг 3: Телефон
# ---------------------------------------------------------------------------

@router.message(JoinRegistrationFSM.phone_number)
async def join_step_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip().replace(" ", "").replace("-", "").replace("+", "")
    if not phone.isdigit() or len(phone) < 10:
        await message.answer("Некорректный номер. Введи <b>номер телефона</b> цифрами (например: 8xxxxxxxxxx):")
        return
    await state.update_data(phone_number=phone, family_members=[])
    await state.set_state(JoinRegistrationFSM.is_going)
    await message.answer(
        "Ты планируешь <b>присутствовать</b> на мероприятии?",
        reply_markup=_kb_yes_no("jgoing_yes", "jgoing_no"),
    )


# ---------------------------------------------------------------------------
# Шаг 4: Планирует ли прийти
# ---------------------------------------------------------------------------

@router.callback_query(JoinRegistrationFSM.is_going, F.data.in_({"jgoing_yes", "jgoing_no"}))
async def join_step_is_going(callback: CallbackQuery, state: FSMContext) -> None:
    is_going = callback.data == "jgoing_yes"
    await state.update_data(is_going=is_going)
    await callback.answer()

    if not is_going:
        await callback.message.edit_text("Очень жаль 😔 Будем ждать тебя, если надумаешь — просто напиши!")
        data = await state.get_data()
        ok, msg = await _send_registration(
            state,
            tg_username=data["_tg_username"],
            telegram_id=data["_telegram_id"],
            chat_id=callback.message.chat.id,
        )
        if not ok:
            await callback.message.answer(msg)
        await state.clear()
        return

    await callback.message.edit_text(
        "Отлично! 🎉 Придёшь <b>один/одна</b> или <b>с семьёй</b>?",
        reply_markup=_kb_solo_family(),
    )
    await state.set_state(JoinRegistrationFSM.solo_or_family)


# ---------------------------------------------------------------------------
# Шаг 5: Один или с семьёй
# ---------------------------------------------------------------------------

@router.callback_query(JoinRegistrationFSM.solo_or_family, F.data == "join_solo")
async def join_step_solo(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Отлично! Завершаем регистрацию...")
    await callback.answer()
    data = await state.get_data()
    ok, msg = await _send_registration(
        state,
        tg_username=data["_tg_username"],
        telegram_id=data["_telegram_id"],
        chat_id=callback.message.chat.id,
    )
    await callback.message.answer(msg)
    await state.clear()


@router.callback_query(JoinRegistrationFSM.solo_or_family, F.data == "join_family")
async def join_step_family_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(JoinRegistrationFSM.member_role)
    await callback.message.edit_text(
        "Добавь первого члена семьи.\nВыбери <b>роль</b>:",
        reply_markup=_kb_member_role(),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Цикл добавления членов семьи
# ---------------------------------------------------------------------------

@router.callback_query(JoinRegistrationFSM.member_role, F.data.startswith("jrole_"))
async def join_step_member_role(callback: CallbackQuery, state: FSMContext) -> None:
    role = callback.data.removeprefix("jrole_")  # FAMALY_TAIL | CHILD
    await state.update_data(_current_role=role)
    await state.set_state(JoinRegistrationFSM.member_first_name)
    role_label = "второй половинки" if role == "FAMALY_TAIL" else "ребёнка"
    await callback.message.edit_text(f"Введи <b>имя</b> {role_label}:")
    await callback.answer()


@router.message(JoinRegistrationFSM.member_first_name)
async def join_step_member_first_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Имя не может быть пустым. Введи <b>имя</b>:")
        return
    await state.update_data(_m_first_name=name)
    await state.set_state(JoinRegistrationFSM.member_second_name)
    await message.answer("Введи <b>фамилию</b>:")


@router.message(JoinRegistrationFSM.member_second_name)
async def join_step_member_second_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Фамилия не может быть пустой. Введи <b>фамилию</b>:")
        return
    await state.update_data(_m_second_name=name)

    data = await state.get_data()
    role = data.get("_current_role")

    if role == "CHILD":
        # Для детей — сохраняем без телефона
        await _join_save_member_and_ask(message, state, phone="")
    else:
        # Для второй половинки — спрашиваем телефон
        await state.set_state(JoinRegistrationFSM.member_phone)
        await message.answer("Введи <b>номер телефона</b> второй половинки:")


@router.message(JoinRegistrationFSM.member_phone)
async def join_step_member_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip().replace(" ", "").replace("-", "").replace("+", "")
    if not phone.isdigit() or len(phone) < 10:
        await message.answer("Некорректный номер. Введи <b>номер телефона</b> цифрами:")
        return
    await _join_save_member_and_ask(message, state, phone=phone)


# ---------------------------------------------------------------------------
# Сохранение члена семьи
# ---------------------------------------------------------------------------

async def _join_save_member_and_ask(
    message: Message,
    state: FSMContext,
    phone: str,
) -> None:
    data = await state.get_data()
    role = data["_current_role"]

    member: dict = {
        "first_name": data["_m_first_name"],
        "second_name": data["_m_second_name"],
        "role": role,
        "is_main_account": False,
        "is_going_on_event": True,
    }

    if role == "FAMALY_TAIL" and phone:
        member["phone_number"] = phone

    family_members: list = data.get("family_members", [])
    family_members.append(member)
    await state.update_data(family_members=family_members)

    await state.set_state(JoinRegistrationFSM.member_add_more)
    await message.answer(
        f"✅ {data['_m_first_name']} {data['_m_second_name']} добавлен(а).\n\n"
        "Хотите добавить ещё одного члена семьи?",
        reply_markup=_kb_add_more(),
    )


# ---------------------------------------------------------------------------
# Добавить ещё / завершить
# ---------------------------------------------------------------------------

@router.callback_query(JoinRegistrationFSM.member_add_more, F.data == "jmember_add_more")
async def join_step_add_more(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(JoinRegistrationFSM.member_role)
    await callback.message.edit_text(
        "Выбери <b>роль</b> следующего члена семьи:",
        reply_markup=_kb_member_role(),
    )
    await callback.answer()


@router.callback_query(JoinRegistrationFSM.member_add_more, F.data == "jmember_done")
async def join_step_done(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Завершаем регистрацию...")
    await callback.answer()
    data = await state.get_data()
    ok, msg = await _send_registration(
        state,
        tg_username=data["_tg_username"],
        telegram_id=data["_telegram_id"],
        chat_id=callback.message.chat.id,
    )
    await callback.message.answer(msg)
    await state.clear()