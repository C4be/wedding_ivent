# import json
# from aiogram import Router, F, Bot
# from aiogram.filters import Command
# from aiogram.types import Message, CallbackQuery, BufferedInputFile
# from aiogram.fsm.context import FSMContext


# from database.db import get_db
# from keyboards.admin_kb import (
#     admin_menu_kb, templates_kb, confirm_send_kb, members_kb,
# )
# from keyboards.user_kb import skip_kb
# from services.csv_export import export_members_to_csv, export_drinks_stats_to_csv
# from services.site_api import (
#     get_site_config, update_site_config,
#     add_image_to_site, add_member_to_site, delete_member_from_site,
# )
# from states.admin_states import (
#     SendNotificationState, AddImageState, AddMemberState,
#     DeleteMemberState, CreateTemplateState, UpdateConfigState,
# )
# from utils.logger import logger


# router = Router(name="admin")

# # ==============================================================================
# # Обычные команды Commands
# # ==============================================================================

# @router.message(Command("admin"))
# async def cmd_admin(message: Message, is_admin: bool):
#     """Показать панель администратора c кнопками"""
#     if not is_admin:
#         return
#     await message.answer(
#         "🔐 **Панель администратора**", 
#         parse_mode="MarkdownV2",
#         reply_markup=admin_menu_kb()
#     )
#     logger.info(f"Админ {message.from_user.username}({message.from_user.id}) открыл панель администратора")


# @router.message(F.text == "👥 Участники")
# async def cmd_get_members(message: Message, is_admin: bool):
#     """Показать список участников с их данными и статусом посещения"""
#     if not is_admin:
#         return
#     async with await get_db() as db:
#         async with db.execute(
#             "SELECT id, full_name, phone, attendance_day1, attendance_day2, drink_pref FROM members ORDER BY id"
#         ) as cur:
#             members = await cur.fetchall()

#     if not members:
#         await message.answer("📭 Анкет пока нет.")
#         return

#     text = f"👥 <b>Участники ({len(members)}):</b>\n\n"
#     for m in members:
#         d1 = "✅" if m["attendance_day1"] else "❌"
#         d2 = "✅" if m["attendance_day2"] else "❌"
#         text += f"#{m['id']} <b>{m['full_name']}</b> | 📱{m['phone'] or '—'} | Д1{d1} Д2{d2}\n"

#     await message.answer(text, parse_mode="HTML")
#     logger.info(f"Админ {message.from_user.username}({message.from_user.id}) запросил список участников")


# @router.message(F.text == "📊 Все участники")
# async def cmd_get_all_members(message: Message, is_admin: bool):
#     if not is_admin:
#         return
#     async with await get_db() as db:
#         async with db.execute(
#             """SELECT m.id, m.full_name, m.partner_name, m.attendance_day1, m.attendance_day2
#                FROM members m ORDER BY m.id"""
#         ) as cur:
#             members = await cur.fetchall()

#     total_people = 0
#     text = f"📊 <b>Все люди (с парами):</b>\n\n"
#     for m in members:
#         d1 = "✅" if m["attendance_day1"] else "❌"
#         d2 = "✅" if m["attendance_day2"] else "❌"
#         partner = f" + {m['partner_name']}" if m["partner_name"] else ""
#         text += f"#{m['id']} <b>{m['full_name']}{partner}</b> | Д1{d1} Д2{d2}\n"
#         total_people += 1
#         if m["partner_name"]:
#             total_people += 1

#     text += f"\n👥 Всего людей: <b>{total_people}</b>"
#     await message.answer(text, parse_mode="HTML")


# # ───────────────────────── SEND NOTIFICATION ────────────────

# @router.message(F.text == "📢 Уведомление")
# async def cmd_send_notification(message: Message, state: FSMContext, is_admin: bool):
#     if not is_admin:
#         return
#     async with await get_db() as db:
#         async with db.execute("SELECT id, title FROM message_templates ORDER BY id") as cur:
#             templates = [dict(t) for t in await cur.fetchall()]

#     await state.set_state(SendNotificationState.choose_template)
#     if templates:
#         await message.answer(
#             "📝 Выбери шаблон или напиши своё сообщение:",
#             reply_markup=templates_kb(templates),
#         )
#     else:
#         await state.set_state(SendNotificationState.input_text)
#         await message.answer("✍️ Напиши текст уведомления:")


# @router.callback_query(SendNotificationState.choose_template, F.data.startswith("tpl_") & ~F.data.endswith("new"))
# async def notification_template_chosen(callback: CallbackQuery, state: FSMContext, is_admin: bool):
#     if not is_admin:
#         return
#     tpl_id = int(callback.data.replace("tpl_", ""))
#     async with await get_db() as db:
#         async with db.execute("SELECT body FROM message_templates WHERE id = ?", (tpl_id,)) as cur:
#             row = await cur.fetchone()

#     if not row:
#         await callback.answer("Шаблон не найден", show_alert=True)
#         return

#     await state.update_data(notify_text=row["body"])
#     await state.set_state(SendNotificationState.confirm)
#     await callback.message.answer(
#         f"📢 <b>Превью сообщения:</b>\n\n{row['body']}",
#         parse_mode="HTML",
#         reply_markup=confirm_send_kb(),
#     )
#     await callback.answer()


# @router.callback_query(SendNotificationState.choose_template, F.data == "tpl_new")
# async def notification_new_text(callback: CallbackQuery, state: FSMContext,  is_admin: bool):
#     if not is_admin:
#         return
#     await state.set_state(SendNotificationState.input_text)
#     await callback.message.answer("✍️ Напиши текст уведомления:")
#     await callback.answer()


# @router.message(SendNotificationState.input_text)
# async def notification_input(message: Message, state: FSMContext):
#     await state.update_data(notify_text=message.text)
#     await state.set_state(SendNotificationState.confirm)
#     await message.answer(
#         f"📢 <b>Превью:</b>\n\n{message.text}",
#         parse_mode="HTML",
#         reply_markup=confirm_send_kb(),
#     )


# @router.callback_query(SendNotificationState.confirm, F.data == "notify_confirm")
# async def notification_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     if not await check_admin_cb(callback):
#         return
#     data = await state.get_data()
#     notify_text = data.get("notify_text", "")

#     async with await get_db() as db:
#         async with db.execute("SELECT telegram_id FROM users") as cur:
#             users = await cur.fetchall()

#     sent, failed = 0, 0
#     for user in users:
#         try:
#             await bot.send_message(user["telegram_id"], notify_text, parse_mode="HTML")
#             sent += 1
#         except Exception as e:
#             failed += 1
#             logger.warning(f"Failed to notify user {user['telegram_id']}: {e}")

#     await state.clear()
#     await callback.message.answer(
#         f"✅ Рассылка завершена!\n📤 Отправлено: {sent}\n❌ Ошибок: {failed}",
#         reply_markup=admin_menu_kb(),
#     )
#     await callback.answer()
#     logger.info(f"Admin {callback.from_user.id} sent notification to {sent} users")


# @router.callback_query(SendNotificationState.confirm, F.data == "notify_cancel")
# async def notification_cancel(callback: CallbackQuery, state: FSMContext):
#     await state.clear()
#     await callback.message.answer("❌ Рассылка отменена.", reply_markup=admin_menu_kb())
#     await callback.answer()


# # ───────────────────────── ADD IMAGE ────────────────────────

# @router.message(F.text == "🖼 Добавить фото")
# async def cmd_add_image(message: Message, state: FSMContext):
#     if not await check_admin(message):
#         return
#     await state.set_state(AddImageState.waiting_for_url)
#     await message.answer("🔗 Вставь ссылку на Яндекс Диск или другой источник:")


# @router.message(AddImageState.waiting_for_url)
# async def add_image_url(message: Message, state: FSMContext):
#     await state.update_data(image_url=message.text)
#     await state.set_state(AddImageState.waiting_for_caption)
#     await message.answer("✍️ Подпись к фото (или пропусти):", reply_markup=skip_kb())


# @router.message(AddImageState.waiting_for_caption)
# @router.callback_query(AddImageState.waiting_for_caption, F.data == "skip")
# async def add_image_caption(event, state: FSMContext):
#     if isinstance(event, CallbackQuery):
#         caption = None
#         message = event.message
#         await event.answer()
#     else:
#         caption = event.text
#         message = event

#     data = await state.get_data()
#     url = data.get("image_url")

#     async with await get_db() as db:
#         await db.execute(
#             "INSERT INTO gallery_links (url, caption, added_by) VALUES (?, ?, ?)",
#             (url, caption, message.chat.id),
#         )
#         await db.commit()

#     # Sync with site
#     await add_image_to_site({"url": url, "caption": caption})

#     await state.clear()
#     await message.answer("✅ Ссылка добавлена в галерею!", reply_markup=admin_menu_kb())
#     logger.info(f"Admin added gallery link: {url}")


# # ───────────────────────── ADD MEMBER ───────────────────────

# @router.message(F.text == "➕ Добавить участника")
# async def cmd_add_member(message: Message, state: FSMContext):
#     if not await check_admin(message):
#         return
#     await state.set_state(AddMemberState.full_name)
#     await message.answer("👤 Введи имя участника:")


# @router.message(AddMemberState.full_name)
# async def add_member_name(message: Message, state: FSMContext):
#     await state.update_data(full_name=message.text)
#     await state.set_state(AddMemberState.partner_name)
#     await message.answer("💑 Имя партнёра (или пропустить):", reply_markup=skip_kb())


# @router.message(AddMemberState.partner_name)
# async def add_member_partner(message: Message, state: FSMContext):
#     await state.update_data(partner_name=message.text)
#     await state.set_state(AddMemberState.phone)
#     await message.answer("📱 Телефон:")


# @router.callback_query(AddMemberState.partner_name, F.data == "skip")
# async def add_member_partner_skip(callback: CallbackQuery, state: FSMContext):
#     await state.update_data(partner_name=None)
#     await state.set_state(AddMemberState.phone)
#     await callback.message.answer("📱 Телефон:")
#     await callback.answer()


# @router.message(AddMemberState.phone)
# async def add_member_phone(message: Message, state: FSMContext):
#     await state.update_data(phone=message.text)
#     await state.set_state(AddMemberState.email)
#     await message.answer("📧 Email (или пропустить):", reply_markup=skip_kb())


# @router.message(AddMemberState.email)
# @router.callback_query(AddMemberState.email, F.data == "skip")
# async def add_member_email(event, state: FSMContext):
#     if isinstance(event, CallbackQuery):
#         email = None
#         message = event.message
#         await event.answer()
#     else:
#         email = event.text
#         message = event

#     data = await state.get_data()
#     async with await get_db() as db:
#         await db.execute(
#             "INSERT INTO members (full_name, partner_name, phone, email) VALUES (?, ?, ?, ?)",
#             (data["full_name"], data.get("partner_name"), data.get("phone"), email),
#         )
#         await db.commit()

#     await add_member_to_site({
#         "full_name": data["full_name"],
#         "partner_name": data.get("partner_name"),
#         "phone": data.get("phone"),
#         "email": email,
#     })

#     await state.clear()
#     await message.answer(f"✅ Участник <b>{data['full_name']}</b> добавлен!", parse_mode="HTML", reply_markup=admin_menu_kb())
#     logger.info(f"Admin added member: {data['full_name']}")


# # ───────────────────────── DELETE MEMBER ────────────────────

# @router.message(F.text == "🗑 Удалить участника")
# async def cmd_delete_member(message: Message, state: FSMContext):
#     if not await check_admin(message):
#         return
#     async with await get_db() as db:
#         async with db.execute("SELECT id, full_name FROM members ORDER BY id") as cur:
#             members = [dict(m) for m in await cur.fetchall()]

#     if not members:
#         await message.answer("📭 Нет участников.")
#         return

#     await state.set_state(DeleteMemberState.waiting_for_id)
#     await message.answer("🗑 Выбери участника для удаления:", reply_markup=members_kb(members))


# @router.callback_query(DeleteMemberState.waiting_for_id, F.data.startswith("del_member_"))
# async def delete_member_confirm(callback: CallbackQuery, state: FSMContext):
#     if not await check_admin_cb(callback):
#         return
#     member_id = int(callback.data.replace("del_member_", ""))

#     async with await get_db() as db:
#         async with db.execute("SELECT full_name FROM members WHERE id = ?", (member_id,)) as cur:
#             row = await cur.fetchone()
#         if row:
#             await db.execute("DELETE FROM members WHERE id = ?", (member_id,))
#             await db.commit()

#     await delete_member_from_site(member_id)
#     await state.clear()
#     name = row["full_name"] if row else f"#{member_id}"
#     await callback.message.answer(f"✅ Участник <b>{name}</b> удалён.", parse_mode="HTML", reply_markup=admin_menu_kb())
#     await callback.answer()
#     logger.info(f"Admin deleted member #{member_id}: {name}")


# # ───────────────────────── CONFIG ───────────────────────────

# @router.message(F.text == "⚙️ Конфиг сайта")
# async def cmd_get_config(message: Message, state: FSMContext):
#     if not await check_admin(message):
#         return
#     config = await get_site_config()
#     if config:
#         config_text = json.dumps(config, ensure_ascii=False, indent=2)
#         await message.answer(
#             f"⚙️ <b>Текущий конфиг сайта:</b>\n\n<pre>{config_text}</pre>",
#             parse_mode="HTML",
#         )
#         await state.set_state(UpdateConfigState.waiting_for_config)
#         await message.answer("✏️ Пришли обновлённый JSON-конфиг или нажми /cancel для отмены:")
#     else:
#         await message.answer("❌ Не удалось получить конфиг сайта. Проверь подключение.")


# @router.message(UpdateConfigState.waiting_for_config)
# async def update_config(message: Message, state: FSMContext):
#     if not await check_admin(message):
#         return
#     try:
#         new_config = json.loads(message.text)
#         result = await update_site_config(new_config)
#         if result:
#             await message.answer("✅ Конфиг обновлён!", reply_markup=admin_menu_kb())
#         else:
#             await message.answer("❌ Ошибка при обновлении конфига.")
#     except json.JSONDecodeError:
#         await message.answer("❌ Некорректный JSON. Попробуй снова.")
#         return
#     await state.clear()
#     logger.info(f"Admin {message.from_user.id} updated site config")


# # ───────────────────────── TEMPLATES ────────────────────────

# @router.message(F.text == "📝 Шаблоны")
# async def cmd_templates(message: Message, state: FSMContext):
#     if not await check_admin(message):
#         return
#     async with await get_db() as db:
#         async with db.execute("SELECT id, title, body FROM message_templates ORDER BY id") as cur:
#             templates = [dict(t) for t in await cur.fetchall()]

#     if templates:
#         text = "📝 <b>Шаблоны сообщений:</b>\n\n"
#         for t in templates:
#             text += f"#{t['id']} <b>{t['title']}</b>\n{t['body'][:80]}...\n\n"
#         await message.answer(text, parse_mode="HTML", reply_markup=templates_kb(templates))
#     else:
#         await message.answer("📭 Шаблонов нет. Создать новый?", reply_markup=templates_kb([]))

#     await state.set_state(CreateTemplateState.waiting_for_title)


# @router.callback_query(F.data == "tpl_new")
# async def create_template_start(callback: CallbackQuery, state: FSMContext):
#     if not await check_admin_cb(callback):
#         return
#     await state.set_state(CreateTemplateState.waiting_for_title)
#     await callback.message.answer("✍️ Введи название шаблона:")
#     await callback.answer()


# @router.message(CreateTemplateState.waiting_for_title)
# async def create_template_title(message: Message, state: FSMContext):
#     await state.update_data(tpl_title=message.text)
#     await state.set_state(CreateTemplateState.waiting_for_body)
#     await message.answer("✍️ Введи текст шаблона (можно использовать HTML-теги):")


# @router.message(CreateTemplateState.waiting_for_body)
# async def create_template_body(message: Message, state: FSMContext):
#     data = await state.get_data()
#     async with await get_db() as db:
#         await db.execute(
#             "INSERT INTO message_templates (title, body) VALUES (?, ?)",
#             (data["tpl_title"], message.text),
#         )
#         await db.commit()
#     await state.clear()
#     await message.answer(
#         f"✅ Шаблон <b>{data['tpl_title']}</b> сохранён!",
#         parse_mode="HTML",
#         reply_markup=admin_menu_kb(),
#     )
#     logger.info(f"Admin created template: {data['tpl_title']}")


# # ───────────────────────── CSV EXPORT ───────────────────────

# @router.message(F.text == "📥 Экспорт CSV")
# async def cmd_export_csv(message: Message):
#     if not await check_admin(message):
#         return
#     async with await get_db() as db:
#         async with db.execute("SELECT * FROM members ORDER BY id") as cur:
#             members = [dict(m) for m in await cur.fetchall()]
#         async with db.execute(
#             "SELECT drink_pref, COUNT(*) as count FROM members WHERE drink_pref IS NOT NULL GROUP BY drink_pref ORDER BY count DESC"
#         ) as cur:
#             drinks_stats = [dict(r) for r in await cur.fetchall()]

#     members_csv = export_members_to_csv(members)
#     drinks_csv = export_drinks_stats_to_csv(drinks_stats)

#     await message.answer_document(
#         BufferedInputFile(members_csv.read(), filename="members.csv"),
#         caption=f"👥 Участники: {len(members)} чел.",
#     )
#     await message.answer_document(
#         BufferedInputFile(drinks_csv.read(), filename="drinks_stats.csv"),
#         caption="🥂 Статистика напитков",
#     )
#     logger.info(f"Admin {message.from_user.id} exported CSV ({len(members)} members)")


# # ───────────────────────── CANCEL ───────────────────────────

# @router.message(Command("cancel"))
# async def cmd_cancel(message: Message, state: FSMContext):
#     if not await check_admin(message):
#         return
#     await state.clear()
#     await message.answer("❌ Действие отменено.", reply_markup=admin_menu_kb())
