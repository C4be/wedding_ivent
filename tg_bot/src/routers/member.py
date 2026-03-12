from aiogram import Router

from .member_start import router as cmd_start_router
from .member_registration import router as registration_router
from .member_leave import router as leave_router
from .wish import router as wish_router
from .member_days import router as member_days_router
from .member_join import router as member_join_router
from .member_family import router as member_family_router

member_router = Router()

member_router.include_router(cmd_start_router)
member_router.include_router(registration_router)
member_router.include_router(leave_router)
member_router.include_router(wish_router)
member_router.include_router(member_days_router)
member_router.include_router(member_join_router)
member_router.include_router(member_family_router)
