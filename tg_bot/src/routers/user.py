from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.database.db import get_db
from src.keyboards.user_kb import (
    main_menu_kb, plan_days_kb, drinks_kb,
    attendance_kb, confirm_kb, skip_kb,
)
from src.states.user_states import (
    RSVPState, SendImageState, SendWishState, AskQuestionState,
)
from src.utils.logger import logger

router = Router(name="user")

# ───────────────────────── HELPERS ──────────────────────────

async def _get_drinks(db) -> list:
    async with db.execute("SELECT name, emoji FROM drinks") as cur:
        return [dict(r) for r in await cur.fetchall()]


# ───────────────────────── START / MENU ─────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    name = message.from_user.first_name or "Гость"
    await message.answer(
        f"💍 Привет, <b>{name}</b>!\n\n"
        "Добро пожаловать на бот нашей свадьбы 🎉\n"
        "Здесь ты можешь:\n"
        "• Посмотреть <b>программу</b> торжества\n"
        "• Подтвердить <b>участие (RSVP)</b>\n"
        "• Выбрать <b>напитки</b>\n"
        "• Поделиться <b>фото</b> и оставить <b>пожелания</b>\n\n"
        "Используй меню ниже 👇",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    logger.info(f"User {message.from_user.id} started the bot")


@router.message(Command("menu"))
@router.message(F.text == "🏠 Главное меню")
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu_kb())


# ───────────────────────── GALLERY ──────────────────────────

@router.message(Command("gallery"))
@router.message(F.text == "📸 Галерея")
async def cmd_gallery(message: Message):
    async with await get_db() as db:
        async with db.execute("SELECT url, caption FROM gallery_links ORDER BY id DESC") as cur:
            links = await cur.fetchall()

    if not links:
        await message.answer("📭 Ссылки на фотографии ещё не добавлены. Загляни позже!")
        return

    text = "📸 <b>Свадебные фотографии</b>\n\n"
    for i, row in enumerate(links, 1):
        caption = row["caption"] or "Фото"
        text += f"{i}. <a href='{row['url']}'>{caption}</a>\n"

    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
    logger.info(f"User {message.from_user.id} requested gallery ({len(links)} links)")


# ───────────────────────── SEND IMAGE ───────────────────────

@router.message(Command("send_image"))
@router.message(F.text == "📤 Загрузить фото")
async def cmd_send_image(message: Message, state: FSMContext):
    await state.set_state(SendImageState.waiting_for_image)
    await message.answer(
        "📷 Пришли мне фото или несколько фотографий для общего альбома!\n"
        "Отправь фото, и я добавлю его в галерею.",
        reply_markup=None,
    )


@router.message(SendImageState.waiting_for_image, F.photo)
async def process_image(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await state.set_state(SendImageState.waiting_for_caption)
    await message.answer("✍️ Добавь подпись к фото (или нажми «Пропустить»):", reply_markup=skip_kb())


@router.message(SendImageState.waiting_for_caption)
@router.callback_query(SendImageState.waiting_for_caption, F.data == "skip")
async def process_image_caption(event, state: FSMContext):
    if isinstance(event, CallbackQuery):
        caption = None
        message = event.message
        await event.answer()
    else:
        caption = event.text
        message = event

    data = await state.get_data()
    photo_id = data.get("photo_id")

    async with await get_db() as db:
        await db.execute(
            "INSERT INTO gallery_links (url, caption, added_by) VALUES (?, ?, ?)",
            (f"tg://photo/{photo_id}", caption, message.chat.id),
        )
        await db.commit()

    await state.clear()
    await message.answer("✅ Фото добавлено в общий альбом! Спасибо 💕", reply_markup=main_menu_kb())
    logger.info(f"User {message.chat.id} uploaded photo")


# ───────────────────────── PLAN ─────────────────────────────

@router.message(Command("plan"))
@router.message(F.text == "📅 Программа")
async def cmd_plan(message: Message):
    await message.answer(
        "📅 <b>Программа торжества</b>\n\nВыбери день:",
        parse_mode="HTML",
        reply_markup=plan_days_kb(),
    )


@router.callback_query(F.data == "plan_day_1")
async def plan_day_1(callback: CallbackQuery):
    text = (
        "📅 <b>Программа 1-го дня</b>\n\n"
        "🕑 14:00 — Сбор гостей\n"
        "🕒 15:00 — Выездная регистрация\n"
        "🥂 16:00 — Фуршет и поздравления\n"
        "🍽 18:00 — Торжественный ужин\n"
        "💃 20:00 — Танцы и развлечения\n"
        "🎂 22:00 — Торт\n"
        "🌙 00:00 — Завершение вечера\n"
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "plan_day_2")
async def plan_day_2(callback: CallbackQuery):
    text = (
        "📅 <b>Программа 2-го дня</b>\n\n"
        "☀️ 13:00 — Сбор гостей\n"
        "🥗 14:00 — Лёгкий обед на природе\n"
        "🎮 15:00 — Игры и конкурсы\n"
        "🔥 17:00 — Барбекю\n"
        "🌅 20:00 — Завершение праздника\n"
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


# ───────────────────────── WISHES ───────────────────────────

@router.message(Command("ask"))
@router.message(F.text == "💌 Пожелания")
async def cmd_wishes(message: Message, state: FSMContext):
    await state.set_state(SendWishState.waiting_for_wish)
    await message.answer(
        "💌 Напиши своё пожелание или предложение по организации свадьбы.\n"
        "Мы обязательно примем его во внимание! ✨"
    )


@router.message(SendWishState.waiting_for_wish)
async def process_wish(message: Message, state: FSMContext):
    wish_text = message.text
    async with await get_db() as db:
        await db.execute(
            "UPDATE members SET wishes = ? WHERE telegram_id = ?",
            (wish_text, message.from_user.id),
        )
        await db.commit()

    await state.clear()
    await message.answer(
        "💕 Спасибо за твоё пожелание! Мы очень ценим это.",
        reply_markup=main_menu_kb(),
    )
    logger.info(f"User {message.from_user.id} sent a wish")


# ───────────────────────── DRINKS ───────────────────────────

@router.message(F.text == "🥂 Напитки")
async def cmd_drinks(message: Message, state: FSMContext):
    async with await get_db() as db:
        drinks = await _get_drinks(db)
    await state.update_data(selected_drinks=[])
    await message.answer(
        "🥂 Выбери предпочтительные напитки (можно несколько):",
        reply_markup=drinks_kb(drinks),
    )


@router.callback_query(F.data.startswith("drink_") & ~F.data.endswith("done"))
async def process_drink_choice(callback: CallbackQuery, state: FSMContext):
    drink_name = callback.data.replace("drink_", "")
    data = await state.get_data()
    selected: list = data.get("selected_drinks", [])

    if drink_name in selected:
        selected.remove(drink_name)
        await callback.answer(f"Убрано: {drink_name}")
    else:
        selected.append(drink_name)
        await callback.answer(f"Добавлено: {drink_name} ✅")

    await state.update_data(selected_drinks=selected)


@router.callback_query(F.data == "drink_done")
async def process_drink_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected: list = data.get("selected_drinks", [])

    if not selected:
        await callback.answer("Выбери хотя бы один напиток!", show_alert=True)
        return

    drinks_str = ", ".join(selected)
    async with await get_db() as db:
        await db.execute(
            "UPDATE members SET drink_pref = ? WHERE telegram_id = ?",
            (drinks_str, callback.from_user.id),
        )
        await db.commit()

    await state.clear()
    await callback.message.edit_text(
        f"✅ Отлично! Записали твои предпочтения:\n<b>{drinks_str}</b>",
        parse_mode="HTML",
    )
    await callback.message.answer("Возвращаемся в меню 👇", reply_markup=main_menu_kb())
    await callback.answer()
    logger.info(f"User {callback.from_user.id} selected drinks: {drinks_str}")


# ───────────────────────── RSVP ─────────────────────────────

@router.message(Command("rsvp"))
@router.message(F.text == "📝 RSVP")
async def cmd_rsvp(message: Message, state: FSMContext):
    await state.set_state(RSVPState.full_name)
    await message.answer(
        "📝 <b>Подтверждение участия</b>\n\n"
        "Я задам несколько вопросов, чтобы мы могли лучше подготовиться.\n\n"
        "Как тебя зовут? (Имя и Фамилия)",
        parse_mode="HTML",
    )


@router.message(RSVPState.full_name)
async def rsvp_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(RSVPState.partner_name)
    await message.answer(
        "Придёшь с партнёром/партнёршей? Напиши имя или нажми «Пропустить»:",
        reply_markup=skip_kb(),
    )


@router.message(RSVPState.partner_name)
async def rsvp_partner(message: Message, state: FSMContext):
    await state.update_data(partner_name=message.text)
    await state.set_state(RSVPState.phone)
    await message.answer("📱 Твой номер телефона:")


@router.callback_query(RSVPState.partner_name, F.data == "skip")
async def rsvp_partner_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(partner_name=None)
    await state.set_state(RSVPState.phone)
    await callback.message.answer("📱 Твой номер телефона:")
    await callback.answer()


@router.message(RSVPState.phone)
async def rsvp_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(RSVPState.email)
    await message.answer("📧 Email (или нажми «Пропустить»):", reply_markup=skip_kb())


@router.message(RSVPState.email)
async def rsvp_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text)
    await state.set_state(RSVPState.attendance_day1)
    await message.answer("📅 Придёшь на <b>1-й день</b> торжества?", parse_mode="HTML", reply_markup=attendance_kb())


@router.callback_query(RSVPState.email, F.data == "skip")
async def rsvp_email_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(email=None)
    await state.set_state(RSVPState.attendance_day1)
    await callback.message.answer("📅 Придёшь на <b>1-й день</b> торжества?", parse_mode="HTML", reply_markup=attendance_kb())
    await callback.answer()


@router.callback_query(RSVPState.attendance_day1, F.data.in_({"attend_yes", "attend_no"}))
async def rsvp_day1(callback: CallbackQuery, state: FSMContext):
    await state.update_data(attendance_day1=1 if callback.data == "attend_yes" else 0)
    await state.set_state(RSVPState.attendance_day2)
    await callback.message.answer("📅 Придёшь на <b>2-й день</b>?", parse_mode="HTML", reply_markup=attendance_kb())
    await callback.answer()


@router.callback_query(RSVPState.attendance_day2, F.data.in_({"attend_yes", "attend_no"}))
async def rsvp_day2(callback: CallbackQuery, state: FSMContext):
    await state.update_data(attendance_day2=1 if callback.data == "attend_yes" else 0)
    data = await state.get_data()
    await state.set_state(RSVPState.confirm)

    day1 = "✅ Да" if data.get("attendance_day1") else "❌ Нет"
    day2 = "✅ Да" if data.get("attendance_day2") else "❌ Нет"
    partner = data.get("partner_name") or "—"
    summary = (
        f"📋 <b>Проверь данные:</b>\n\n"
        f"👤 Имя: {data.get('full_name')}\n"
        f"💑 Партнёр: {partner}\n"
        f"📱 Телефон: {data.get('phone')}\n"
        f"📧 Email: {data.get('email') or '—'}\n"
        f"📅 День 1: {day1}\n"
        f"📅 День 2: {day2}\n"
    )
    await callback.message.answer(summary, parse_mode="HTML", reply_markup=confirm_kb())
    await callback.answer()


@router.callback_query(RSVPState.confirm, F.data == "confirm_yes")
async def rsvp_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id

    async with await get_db() as db:
        await db.execute(
            """INSERT INTO members
               (telegram_id, full_name, partner_name, phone, email, attendance_day1, attendance_day2)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(telegram_id) DO UPDATE SET
                 full_name=excluded.full_name,
                 partner_name=excluded.partner_name,
                 phone=excluded.phone,
                 email=excluded.email,
                 attendance_day1=excluded.attendance_day1,
                 attendance_day2=excluded.attendance_day2""",
            (
                user_id, data["full_name"], data.get("partner_name"),
                data.get("phone"), data.get("email"),
                data.get("attendance_day1", 0), data.get("attendance_day2", 0),
            ),
        )
        await db.commit()

    await state.clear()
    await callback.message.answer(
        "🎉 <b>Отлично! Ждём тебя на нашей свадьбе!</b>\n\nЕсли что-то изменится — можешь пройти анкету снова.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
    logger.info(f"User {user_id} completed RSVP")


@router.callback_query(RSVPState.confirm, F.data == "confirm_no")
async def rsvp_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RSVPState.full_name)
    await callback.message.answer("Хорошо, начнём заново. Как тебя зовут?")
    await callback.answer()


# ───────────────────────── ASK QUESTION ─────────────────────

@router.message(Command("ask"))
@router.message(F.text == "❓ Задать вопрос")
async def cmd_ask(message: Message, state: FSMContext):
    await state.set_state(AskQuestionState.waiting_for_question)
    await message.answer("❓ Напиши свой вопрос, и организаторы ответят тебе в ближайшее время!")


@router.message(AskQuestionState.waiting_for_question)
async def process_question(message: Message, state: FSMContext):
    from src.config import ADMIN_IDS
    from aiogram import Bot

    bot: Bot = message.bot
    question = message.text
    user = message.from_user
    notify_text = (
        f"❓ <b>Вопрос от гостя</b>\n\n"
        f"👤 {user.full_name} (@{user.username or 'нет'})\n"
        f"🆔 {user.id}\n\n"
        f"💬 {question}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, notify_text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")

    await state.clear()
    await message.answer(
        "✅ Вопрос отправлен организаторам! Ответим совсем скоро 💕",
        reply_markup=main_menu_kb(),
    )
    logger.info(f"User {message.from_user.id} asked a question")
