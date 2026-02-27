from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📸 Галерея"), KeyboardButton(text="📤 Загрузить фото")],
            [KeyboardButton(text="📅 Программа"), KeyboardButton(text="💌 Пожелания")],
            [KeyboardButton(text="🥂 Напитки"), KeyboardButton(text="📝 RSVP")],
            [KeyboardButton(text="❓ Задать вопрос")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
    )


def plan_days_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 День 1", callback_data="plan_day_1")
    builder.button(text="📅 День 2", callback_data="plan_day_2")
    builder.adjust(2)
    return builder.as_markup()


def drinks_kb(drinks: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for drink in drinks:
        builder.button(
            text=f"{drink['emoji']} {drink['name']}",
            callback_data=f"drink_{drink['name']}",
        )
    builder.button(text="✅ Готово", callback_data="drink_done")
    builder.adjust(2)
    return builder.as_markup()


def attendance_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data="attend_yes")
    builder.button(text="❌ Нет", callback_data="attend_no")
    builder.adjust(2)
    return builder.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_yes")
    builder.button(text="✏️ Изменить", callback_data="confirm_no")
    builder.adjust(2)
    return builder.as_markup()


def skip_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data="skip")
    return builder.as_markup()
