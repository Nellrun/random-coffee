# handlers package
from aiogram import Dispatcher
from app.handlers.base import router as base_router
from app.handlers.callbacks import router as callback_router
from app.handlers.webapp import router as webapp_router

def register_all_handlers(dp: Dispatcher):
    """Register all handlers"""
    # Register routers
    dp.include_router(base_router)
    dp.include_router(callback_router)
    dp.include_router(webapp_router)