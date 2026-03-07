from aiohttp import web

from config import settings

import logging

# --- Веб-эндпоинт для приёма POST от формы ---
async def form_handler(bot, request: web.Request) -> web.Response:
    try:
        # Пытаемся получить JSON (если форма отправляет JSON)
        data = await request.json()
    except:
        # Если не JSON, пробуем получить данные как форму (application/x-www-form-urlencoded)
        post_data = await request.post()
        data = dict(post_data)

    text = data.get("text")
    parse_mode = data.get("parse_mode", "HTML")

    # Отправляем сообщение администратору
    try:
        await bot.send_message(chat_id=settings.ADMIN_IDS[0], text=text, parse_mode=parse_mode)
        return web.json_response({"status": "ok", "message": "Сообщение отправлено администратору"})
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения админу: {e}")
        return web.json_response({"status": "error", "message": "Не удалось отправить сообщение"}, status=500)

    except Exception as e:
        logging.exception(e)
        return web.json_response({"status": "error", "message": "Внутренняя ошибка сервера"}, status=500)