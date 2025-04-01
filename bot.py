import asyncio
import logging
import os
from dotenv import load_dotenv

from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from app.database.connection import create_pool, close_pool
from app.handlers import register_all_handlers
from app.middlewares import setup_middlewares
from app.commands import set_bot_commands
from app.scheduler import Scheduler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger.add("logs/bot_{time}.log", rotation="1 day", retention="7 days", level="INFO")

async def main():
    """Main function to start the bot"""
    logger.info("Starting bot...")
    
    # Initialize bot and dispatcher
    bot = Bot(token=os.getenv("BOT_TOKEN"), parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    
    # Setup middlewares
    setup_middlewares(dp)
    
    # Register all handlers
    register_all_handlers(dp)
    
    # Set bot commands
    await set_bot_commands(bot)
    
    # Initialize database connection
    pool = await create_pool()
    
    # Initialize scheduler
    scheduler = Scheduler(bot)
    scheduler.start()
    
    # Start polling
    try:
        logger.info("Bot started successfully!")
        await dp.start_polling(bot, skip_updates=True)
    finally:
        logger.info("Shutting down...")
        scheduler.shutdown()
        await close_pool()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")