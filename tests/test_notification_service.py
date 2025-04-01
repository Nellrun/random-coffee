import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import os
from dotenv import load_dotenv

# Load environment variables for testing
load_dotenv(".env.test", override=True)

from app.database.connection import create_pool, close_pool
from app.database.repositories import UserRepository, MatchRepository
from app.database.models import UserCreate, MatchCreate
from app.services.notification import NotificationService

# Test data
TEST_USERS = [
    UserCreate(
        telegram_id=123456789,
        username="user1",
        full_name="User One",
        bio="User 1 bio",
        interests=["coffee", "python", "testing"],
        location_lat=40.7128,
        location_lon=-74.0060,
        radius=10,
        preferred_language="en",
        timezone="UTC"
    ),
    UserCreate(
        telegram_id=987654321,
        username="user2",
        full_name="User Two",
        bio="User 2 bio",
        interests=["coffee", "python", "asyncio"],
        location_lat=40.7128,
        location_lon=-74.0060,
        radius=10,
        preferred_language="en",
        timezone="UTC"
    )
]

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
        for user in TEST_USERS:
            await conn.execute("DELETE FROM users WHERE telegram_id = $1", user.telegram_id)
        
        # Also clean up matches
        await conn.execute("DELETE FROM matches")
        await conn.execute("DELETE FROM match_history")
    
    yield
    
    async with db_pool.acquire() as conn:
        # Clean up after test
        for user in TEST_USERS:
            await conn.execute("DELETE FROM users WHERE telegram_id = $1", user.telegram_id)
        
        # Also clean up matches
        await conn.execute("DELETE FROM matches")
        await conn.execute("DELETE FROM match_history")

@pytest.fixture
async def create_test_users(clean_db):
    """Create test users"""
    user_ids = []
    for user in TEST_USERS:
        user_id = await UserRepository.create_user(user)
        user_ids.append(user_id)
    
    return user_ids

@pytest.fixture
async def create_test_match(create_test_users):
    """Create a test match"""
    # Get user IDs
    users = await UserRepository.get_active_users()
    test_users = [user for user in users if user['telegram_id'] in [u.telegram_id for u in TEST_USERS]]
    
    # Create match
    match = MatchCreate(
        user1_id=test_users[0]['id'],
        user2_id=test_users[1]['id'],
        status="pending"
    )
    
    match_id = await MatchRepository.create_match(match)
    return match_id

@pytest.mark.asyncio
async def test_notify_match(create_test_match):
    """Test notifying users about a match"""
    match_id = create_test_match
    
    # Create mock bot
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()
    
    # Create notification service
    notification_service = NotificationService(mock_bot)
    
    # Notify match
    result = await notification_service.notify_match(match_id)
    
    # Verify result
    assert result is True
    
    # Verify bot.send_message was called twice (once for each user)
    assert mock_bot.send_message.call_count == 2

@pytest.mark.asyncio
async def test_notify_match_status_accepted(create_test_match):
    """Test notifying users about match acceptance"""
    match_id = create_test_match
    
    # Get match
    match = await MatchRepository.get_match_by_id(match_id)
    
    # Create mock bot
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()
    
    # Create notification service
    notification_service = NotificationService(mock_bot)
    
    # Notify match status
    result = await notification_service.notify_match_status(match_id, "accepted", match['user1_id'])
    
    # Verify result
    assert result is True
    
    # Verify bot.send_message was called once (for the other user)
    assert mock_bot.send_message.call_count == 1

@pytest.mark.asyncio
async def test_notify_match_status_declined(create_test_match):
    """Test notifying users about match decline"""
    match_id = create_test_match
    
    # Get match
    match = await MatchRepository.get_match_by_id(match_id)
    
    # Create mock bot
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()
    
    # Create notification service
    notification_service = NotificationService(mock_bot)
    
    # Notify match status
    result = await notification_service.notify_match_status(match_id, "declined", match['user1_id'])
    
    # Verify result
    assert result is True
    
    # Verify bot.send_message was called once (for the other user)
    assert mock_bot.send_message.call_count == 1

@pytest.mark.asyncio
async def test_notify_match_status_completed(create_test_match):
    """Test notifying users about match completion"""
    match_id = create_test_match
    
    # Create mock bot
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()
    
    # Create notification service
    notification_service = NotificationService(mock_bot)
    
    # Notify match status
    result = await notification_service.notify_match_status(match_id, "completed")
    
    # Verify result
    assert result is True
    
    # Verify bot.send_message was called twice (once for each user)
    assert mock_bot.send_message.call_count == 2

@pytest.mark.asyncio
async def test_send_reminder(create_test_match):
    """Test sending reminders"""
    match_id = create_test_match
    
    # Create mock bot
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()
    
    # Create notification service
    notification_service = NotificationService(mock_bot)
    
    # Send reminder
    result = await notification_service.send_reminder(match_id)
    
    # Verify result
    assert result is True
    
    # Verify bot.send_message was called twice (once for each user)
    assert mock_bot.send_message.call_count == 2