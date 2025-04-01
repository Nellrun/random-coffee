import pytest
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables for testing
load_dotenv(".env.test", override=True)

from app.database.connection import create_pool, close_pool
from app.database.repositories import UserRepository
from app.database.models import UserCreate, UserUpdate

# Test data
TEST_USER = UserCreate(
    telegram_id=123456789,
    username="test_user",
    full_name="Test User",
    bio="This is a test user",
    interests=["coffee", "testing", "python"],
    location_lat=40.7128,
    location_lon=-74.0060,
    radius=10,
    preferred_language="en",
    preferred_days=["Monday", "Wednesday", "Friday"],
    timezone="UTC"
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_pool():
    """Create a database pool for testing"""
    pool = await create_pool()
    yield pool
    await close_pool()

@pytest.fixture(async_generator)
async def clean_db(db_pool):
    """Clean the database before and after tests"""
    async with db_pool.acquire() as conn:
        # Clean up before test
        await conn.execute("DELETE FROM users WHERE telegram_id = $1", TEST_USER.telegram_id)
    
    yield
    
    async with db_pool.acquire() as conn:
        # Clean up after test
        await conn.execute("DELETE FROM users WHERE telegram_id = $1", TEST_USER.telegram_id)

@pytest.mark.asyncio
async def test_create_user(clean_db):
    """Test creating a user"""
    # Create user
    user_id = await UserRepository.create_user(TEST_USER)
    
    # Verify user was created
    assert user_id is not None
    assert isinstance(user_id, int)
    
    # Get user by telegram_id
    user = await UserRepository.get_user_by_telegram_id(TEST_USER.telegram_id)
    
    # Verify user data
    assert user is not None
    assert user['telegram_id'] == TEST_USER.telegram_id
    assert user['username'] == TEST_USER.username
    assert user['full_name'] == TEST_USER.full_name
    assert user['bio'] == TEST_USER.bio
    assert user['interests'] == TEST_USER.interests
    assert user['location_lat'] == TEST_USER.location_lat
    assert user['location_lon'] == TEST_USER.location_lon
    assert user['radius'] == TEST_USER.radius
    assert user['preferred_language'] == TEST_USER.preferred_language
    assert user['preferred_days'] == TEST_USER.preferred_days
    assert user['timezone'] == TEST_USER.timezone
    assert user['is_active'] is True

@pytest.mark.asyncio
async def test_update_user(clean_db):
    """Test updating a user"""
    # Create user
    user_id = await UserRepository.create_user(TEST_USER)
    
    # Update user
    update_data = UserUpdate(
        bio="Updated bio",
        interests=["coffee", "testing", "python", "asyncio"],
        radius=15
    )
    
    success = await UserRepository.update_user(user_id, update_data)
    assert success is True
    
    # Get updated user
    user = await UserRepository.get_user_by_id(user_id)
    
    # Verify updated data
    assert user['bio'] == update_data.bio
    assert user['interests'] == update_data.interests
    assert user['radius'] == update_data.radius
    
    # Verify other fields remain unchanged
    assert user['telegram_id'] == TEST_USER.telegram_id
    assert user['username'] == TEST_USER.username
    assert user['full_name'] == TEST_USER.full_name

@pytest.mark.asyncio
async def test_deactivate_user(clean_db):
    """Test deactivating a user"""
    # Create user
    user_id = await UserRepository.create_user(TEST_USER)
    
    # Deactivate user
    success = await UserRepository.deactivate_user(user_id)
    assert success is True
    
    # Get user
    user = await UserRepository.get_user_by_id(user_id)
    
    # Verify user is deactivated
    assert user['is_active'] is False

@pytest.mark.asyncio
async def test_activate_user(clean_db):
    """Test activating a user"""
    # Create user
    user_id = await UserRepository.create_user(TEST_USER)
    
    # Deactivate user
    await UserRepository.deactivate_user(user_id)
    
    # Activate user
    success = await UserRepository.activate_user(user_id)
    assert success is True
    
    # Get user
    user = await UserRepository.get_user_by_id(user_id)
    
    # Verify user is activated
    assert user['is_active'] is True

@pytest.mark.asyncio
async def test_get_active_users(clean_db):
    """Test getting active users"""
    # Create user
    user_id = await UserRepository.create_user(TEST_USER)
    
    # Get active users
    users = await UserRepository.get_active_users()
    
    # Verify our test user is in the active users
    test_user_found = False
    for user in users:
        if user['telegram_id'] == TEST_USER.telegram_id:
            test_user_found = True
            break
    
    assert test_user_found is True
    
    # Deactivate user
    await UserRepository.deactivate_user(user_id)
    
    # Get active users again
    users = await UserRepository.get_active_users()
    
    # Verify our test user is not in the active users
    test_user_found = False
    for user in users:
        if user['telegram_id'] == TEST_USER.telegram_id:
            test_user_found = True
            break
    
    assert test_user_found is False