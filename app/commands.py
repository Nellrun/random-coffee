from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault


async def set_bot_commands(bot: Bot):
    """Set bot commands for easier access"""
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help information"),
        BotCommand(command="profile", description="View or update your profile"),
        BotCommand(command="matches", description="View your current matches"),
        BotCommand(command="history", description="View your match history"),
        BotCommand(command="stats", description="View your matching statistics"),
        BotCommand(command="settings", description="Change your settings"),
        BotCommand(command="feedback", description="Leave feedback about the bot"),
    ]
    
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())