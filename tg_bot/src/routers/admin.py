from aiogram import Router

from .admin_console import console_router

admin_router = Router()

admin_router.include_router(console_router)