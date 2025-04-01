from typing import List, Optional, Dict, Any
import asyncpg
from datetime import datetime

from app.database.connection import get_pool
from app.database.models import User, UserCreate, UserUpdate


class UserRepository:
    """Repository for user-related database operations"""

    @staticmethod
    async def create_user(user: UserCreate) -> int:
        """Create a new user and return the user ID"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            user_id = await conn.fetchval('''
                INSERT INTO users (
                    telegram_id, username, full_name, bio, interests,
                    location_lat, location_lon, radius, preferred_language,
                    photo_url, preferred_days, preferred_time_start,
                    preferred_time_end, timezone
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING id
            ''', user.telegram_id, user.username, user.full_name, user.bio,
                user.interests, user.location_lat, user.location_lon,
                user.radius, user.preferred_language, user.photo_url,
                user.preferred_days, user.preferred_time_start,
                user.preferred_time_end, user.timezone)
            
            return user_id

    @staticmethod
    async def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get a user by Telegram ID"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            user = await conn.fetchrow('''
                SELECT * FROM users WHERE telegram_id = $1
            ''', telegram_id)
            
            return dict(user) if user else None

    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """Get a user by ID"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            user = await conn.fetchrow('''
                SELECT * FROM users WHERE id = $1
            ''', user_id)
            
            return dict(user) if user else None

    @staticmethod
    async def update_user(user_id: int, user_data: UserUpdate) -> bool:
        """Update user information"""
        pool = await get_pool()
        
        # Filter out None values
        update_data = {k: v for k, v in user_data.dict().items() if v is not None}
        if not update_data:
            return False
        
        # Build the SET clause dynamically
        set_clause = ", ".join([f"{key} = ${i+2}" for i, key in enumerate(update_data.keys())])
        set_clause += ", updated_at = $1"
        
        # Build the query
        query = f"UPDATE users SET {set_clause} WHERE telegram_id = ${len(update_data) + 2} RETURNING id"
        
        # Build the parameters
        params = [datetime.now()] + list(update_data.values()) + [user_id]
        
        async with pool.acquire() as conn:
            result = await conn.fetchval(query, *params)
            return result is not None

    @staticmethod
    async def get_active_users() -> List[Dict[str, Any]]:
        """Get all active users"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            users = await conn.fetch('''
                SELECT * FROM users WHERE is_active = TRUE
            ''')
            
            return [dict(user) for user in users]

    @staticmethod
    async def get_users_by_criteria(
        interests: Optional[List[str]] = None,
        language: Optional[str] = None,
        radius_km: Optional[int] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get users by various criteria"""
        pool = await get_pool()
        
        conditions = ["is_active = TRUE"]
        params = []
        param_idx = 1
        
        if interests:
            conditions.append(f"interests && ${param_idx}::text[]")
            params.append(interests)
            param_idx += 1
        
        if language:
            conditions.append(f"preferred_language = ${param_idx}")
            params.append(language)
            param_idx += 1
        
        # If location parameters are provided, filter by distance
        if all([lat, lon, radius_km]):
            # Using PostgreSQL's earthdistance extension would be better,
            # but for simplicity, we'll use a basic calculation
            conditions.append(f'''
                (
                    6371 * acos(
                        cos(radians(${param_idx})) * 
                        cos(radians(location_lat)) * 
                        cos(radians(location_lon) - radians(${param_idx+1})) + 
                        sin(radians(${param_idx})) * 
                        sin(radians(location_lat))
                    ) <= ${param_idx+2}
                )
            ''')
            params.extend([lat, lon, radius_km])
            param_idx += 3
        
        where_clause = " AND ".join(conditions)
        query = f"SELECT * FROM users WHERE {where_clause}"
        
        async with pool.acquire() as conn:
            users = await conn.fetch(query, *params)
            return [dict(user) for user in users]

    @staticmethod
    async def deactivate_user(user_id: int) -> bool:
        """Deactivate a user"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            result = await conn.fetchval('''
                UPDATE users 
                SET is_active = FALSE, updated_at = $1
                WHERE id = $2
                RETURNING id
            ''', datetime.now(), user_id)
            
            return result is not None

    @staticmethod
    async def activate_user(user_id: int) -> bool:
        """Activate a user"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            result = await conn.fetchval('''
                UPDATE users 
                SET is_active = TRUE, updated_at = $1
                WHERE id = $2
                RETURNING id
            ''', datetime.now(), user_id)
            
            return result is not None