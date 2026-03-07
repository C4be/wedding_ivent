import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web 

from config import settings
from routers import member_router, admin_router
from utils.logger import logger
from routers import form_handler


from aiohttp import web

from config import settings

import logging

bot = None

def init_bot(bot_instance):
    global bot
    bot = bot_instance

# --- Веб-эндпоинт для приёма POST от формы ---
async def form_handler(request: web.Request) -> web.Response:
    global bot
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



async def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/form", form_handler)  # эндпоинт, который будет принимать POST
    return app

async def run_web_server(app: web.Application):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=5555)  # порт можно вынести в настройки
    await site.start()
    logger.info("Веб-сервер запущен на порту 5555")
    return runner

async def main() -> None:
    logger.info("Запуск свадебного бота...")

    
    init_bot(Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    ))
    global bot
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем роутеры
    dp.include_router(member_router)
    dp.include_router(admin_router)

    # Создаём и запускаем веб-сервер
    web_app = await create_web_app()
    web_runner = await run_web_server(web_app)

    logger.info("Бот запущен. Нажмите Ctrl+C, чтобы остановить.")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await web_runner.cleanup()
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
