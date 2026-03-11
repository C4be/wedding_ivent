from __future__ import annotations

import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.logger import logger
from utils.external_services_client import AsyncHTTPClient
from config import settings

router = Router()


def kb_confirm_leave():
    b = InlineKeyboardBuilder()
    b.button(text="😔 Да, не придём", callback_data="leave_confirm")
    b.button(text="❌ Отмена", callback_data="leave_cancel")
    b.adjust(1)
    return b.as_markup()


@router.message(Command("leave"))
async def cmd_leave(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id

    # Сначала ищем текущего пользователя по telegram_id, чтобы получить имя/фамилию
    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            resp = await client.get(f"/members/by-telegram-id/{user_id}")
            member = resp.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            await message.answer("Не нашли вас в списке гостей. Сначала зарегистрируйтесь — /start")
        else:
            logger.error("HTTP ошибка при поиске участника %s: %s", user_id, exc.response.status_code)
            await message.answer(f"Ошибка сервиса ({exc.response.status_code}). Попробуйте позже.")
        return
    except Exception:
        logger.exception("Сетевая ошибка при поиске участника %s", user_id)
        await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
        return

    if not member or not member.get("id"):
        await message.answer("Не нашли вас в списке гостей. Сначала зарегистрируйтесь — /start")
        return

    first_name = member.get("first_name", "")
    second_name = member.get("second_name", "")

    # Получаем всю семью
    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            resp = await client.get(
                "/members/family/search",
                params={"first_name": first_name, "second_name": second_name},
            )
            family: list = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP ошибка при получении семьи %s %s: %s", first_name, second_name, exc.response.status_code)
        await message.answer(f"Ошибка сервиса ({exc.response.status_code}). Попробуйте позже.")
        return
    except Exception:
        logger.exception("Сетевая ошибка при получении семьи %s %s", first_name, second_name)
        await message.answer("Не удалось связаться с сервисом. Попробуйте позже.")
        return

    if not isinstance(family, list) or not family:
        await message.answer("Не удалось найти данные о вашей семье.")
        return

    # Сохраняем список id членов семьи в state
    member_ids = [m["id"] for m in family if m.get("id")]
    going_members = [m for m in family if m.get("is_going_on_event")]

    if not going_members:
        await message.answer("Все члены вашей семьи уже отмечены как не приходящие. 👍")
        return

    await state.update_data(leave_member_ids=member_ids)

    # Формируем список имён для подтверждения
    names = "\n".join(
        f"• {m.get('first_name', '')} {m.get('second_name', '')}"
        for m in family
    )
    await message.answer(
        f"Вы хотите отметить, что <b>вся семья не придёт</b> на мероприятие?\n\n"
        f"Это затронет следующих участников:\n{names}",
        reply_markup=kb_confirm_leave(),
    )


@router.callback_query(F.data == "leave_confirm")
async def cb_leave_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    member_ids: list[int] = data.get("leave_member_ids", [])
    await state.clear()

    if not member_ids:
        await callback.message.edit_text("Что-то пошло не так. Попробуйте снова — /leave")
        await callback.answer()
        return

    success = 0
    failed_ids = []

    try:
        async with AsyncHTTPClient(base_url=settings.DB_SERVICE_URL) as client:
            for member_id in member_ids:
                try:
                    await client.patch(
                        f"/members/{member_id}/going",
                        params={"is_going": False},
                    )
                    success += 1
                    logger.info("Участник %s отмечен как не приходящий", member_id)
                except httpx.HTTPStatusError as exc:
                    logger.error(
                        "HTTP ошибка при обновлении статуса участника %s: %s",
                        member_id, exc.response.status_code,
                    )
                    failed_ids.append(member_id)
                except Exception:
                    logger.exception("Ошибка при обновлении статуса участника %s", member_id)
                    failed_ids.append(member_id)
    except Exception:
        logger.exception("Сетевая ошибка при отписке семьи")
        await callback.message.edit_text("Не удалось связаться с сервисом. Попробуйте позже.")
        await callback.answer()
        return

    if not failed_ids:
        await callback.message.edit_text(
            "😔 Очень жаль, что вы не сможете прийти.\n"
            "Статус всех членов семьи обновлён. Если передумаете — напишите /start!"
        )
    else:
        await callback.message.edit_text(
            f"Обновлено: {success} участников.\n"
            f"Не удалось обновить: {len(failed_ids)} участников (id: {failed_ids}).\n"
            "Попробуйте позже."
        )

    await callback.answer()


@router.callback_query(F.data == "leave_cancel")
async def cb_leave_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Отмена. Ждём вас на свадьбе! 🎉")
    await callback.answer()
