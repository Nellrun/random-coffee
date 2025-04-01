import os
from typing import Optional
import asyncpg
from loguru import logger

# Global connection pool
_pool: Optional[asyncpg.Pool] = None

async def create_pool() -> asyncpg.Pool:
    """Create and return database connection pool"""
    global _pool
    
    if _pool is not None:
        return _pool
    
    try:
        _pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "coffee_bot"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            min_size=5,
            max_size=20
        )
        
        # Initialize database if needed
        await init_db()
        
        logger.info("Database connection established successfully")
        return _pool
    except Exception as e:
        logger.error(f"Failed to create database connection pool: {e}")
        raise

async def get_pool() -> asyncpg.Pool:
    """Get existing connection pool or create a new one"""
    global _pool
    if _pool is None:
        return await create_pool()
    return _pool

async def close_pool():
    """Close the database connection pool"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")

async def init_db():
    """Initialize database tables if they don't exist"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Create users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                full_name VARCHAR(255) NOT NULL,
                bio TEXT,
                interests TEXT[],
                location_lat FLOAT,
                location_lon FLOAT,
                radius INTEGER DEFAULT 10,
                preferred_language VARCHAR(50) DEFAULT 'en',
                photo_url TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE,
                preferred_days TEXT[],
                preferred_time_start TIME,
                preferred_time_end TIME,
                timezone VARCHAR(50) DEFAULT 'UTC'
            )
        ''')
        
        # Create matches table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id SERIAL PRIMARY KEY,
                user1_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                user2_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                status VARCHAR(50) DEFAULT 'pending',
                meeting_date TIMESTAMP WITH TIME ZONE,
                feedback_user1 TEXT,
                feedback_user2 TEXT,
                UNIQUE(user1_id, user2_id, created_at)
            )
        ''')
        
        # Create match history table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS match_history (
                id SERIAL PRIMARY KEY,
                user1_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                user2_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                match_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                status VARCHAR(50) DEFAULT 'completed',
                feedback TEXT
            )
        ''')
        
        logger.info("Database tables initialized")