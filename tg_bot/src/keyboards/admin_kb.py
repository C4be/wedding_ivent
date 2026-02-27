from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Участники"), KeyboardButton(text="📊 Все участники")],
            [KeyboardButton(text="📢 Уведомление"), KeyboardButton(text="🖼 Добавить фото")],
            [KeyboardButton(text="➕ Добавить участника"), KeyboardButton(text="🗑 Удалить участника")],
            [KeyboardButton(text="⚙️ Конфиг сайта"), KeyboardButton(text="📝 Шаблоны")],
            [KeyboardButton(text="📥 Экспорт CSV")],
        ],
        resize_keyboard=True,
    )


def templates_kb(templates: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in templates:
        builder.button(text=t["title"], callback_data=f"tpl_{t['id']}")
    builder.button(text="✏️ Новый шаблон", callback_data="tpl_new")
    builder.adjust(1)
    return builder.as_markup()


def confirm_send_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Отправить всем", callback_data="notify_confirm")
    builder.button(text="❌ Отмена", callback_data="notify_cancel")
    builder.adjust(2)
    return builder.as_markup()


def members_kb(members: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in members:
        builder.button(
            text=f"🗑 {m['full_name']} (#{m['id']})",
            callback_data=f"del_member_{m['id']}",
        )
    builder.adjust(1)
    return builder.as_markup()
