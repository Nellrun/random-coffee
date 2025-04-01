from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from loguru import logger


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging all updates"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Log incoming updates"""
        # Get user from data if available
        user = data.get('event_from_user')
        
        if user and isinstance(user, User):
            # Log user information
            logger.info(
                f"Update from user {user.id} (@{user.username or 'no username'}, {user.full_name})"
            )
        
        # Log update type
        update_type = event.__class__.__name__
        logger.info(f"Processing {update_type}")
        
        # Pass to next handler
        return await handler(event, data)