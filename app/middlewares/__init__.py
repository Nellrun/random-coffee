# middlewares package
from aiogram import Dispatcher
from app.middlewares.logging import LoggingMiddleware

def setup_middlewares(dp: Dispatcher):
    """Setup middlewares for the dispatcher"""
    dp.update.middleware(LoggingMiddleware())