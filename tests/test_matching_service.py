import pytest
import asyncio
from unittest.mock import patch, MagicMock
import os
from dotenv import load_dotenv

# Load environment variables for testing
load_dotenv(".env.test", override=True)

from app.database.connection import create_pool, close_pool
from app.database.repositories import UserRepository, MatchRepository
from app.database.models import UserCreate
from app.services.matching import MatchingService

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
    ),
    UserCreate(
        telegram_id=123123123,
        username="user3",
        full_name="User Three",
        bio="User 3 bio",
        interests=["coffee", "testing", "asyncio"],
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

@pytest.mark.asyncio
async def test_get_active_users_for_matching(create_test_users):
    """Test getting active users for matching"""
    # Mock the count_missed_matches method to always return 0
    with patch.object(MatchRepository, 'count_missed_matches', return_value=0):
        users = await MatchingService.get_active_users_for_matching()
        
        # Verify all test users are included
        assert len(users) >= len(TEST_USERS)
        
        # Verify our test users are in the active users
        test_telegram_ids = [user.telegram_id for user in TEST_USERS]
        found_count = 0
        
        for user in users:
            if user['telegram_id'] in test_telegram_ids:
                found_count += 1
        
        assert found_count == len(TEST_USERS)

@pytest.mark.asyncio
async def test_get_available_candidates(create_test_users):
    """Test getting available candidates for a user"""
    # Get all users
    users = await UserRepository.get_active_users()
    
    # Get user IDs
    user_ids = [user['id'] for user in users if user['telegram_id'] in [u.telegram_id for u in TEST_USERS]]
    
    # Get candidates for first user
    candidates = await MatchingService.get_available_candidates(user_ids[0], users)
    
    # Verify candidates include other test users but not self
    assert len(candidates) >= len(TEST_USERS) - 1
    
    # Verify first user is not in candidates
    for candidate in candidates:
        assert candidate['id'] != user_ids[0]
    
    # Verify other test users are in candidates
    other_user_ids = user_ids[1:]
    found_count = 0
    
    for candidate in candidates:
        if candidate['id'] in other_user_ids:
            found_count += 1
    
    assert found_count == len(other_user_ids)

@pytest.mark.asyncio
async def test_create_matches(create_test_users):
    """Test creating matches between users"""
    # Mock the necessary methods
    with patch.object(MatchingService, 'get_active_users_for_matching') as mock_get_users, \
         patch.object(MatchingService, 'get_available_candidates') as mock_get_candidates, \
         patch.object(MatchRepository, 'get_previous_matches', return_value=[]):
        
        # Get all users
        users = await UserRepository.get_active_users()
        test_users = [user for user in users if user['telegram_id'] in [u.telegram_id for u in TEST_USERS]]
        
        # Setup mocks
        mock_get_users.return_value = test_users
        
        # Mock get_available_candidates to return all other users
        def mock_get_candidates_impl(user_id, all_users):
            return [u for u in all_users if u['id'] != user_id]
        
        mock_get_candidates.side_effect = mock_get_candidates_impl
        
        # Create matches
        matches = await MatchingService.create_matches()
        
        # Verify matches were created
        assert len(matches) > 0
        
        # Verify each user is only matched once
        matched_users = set()
        for user1_id, user2_id in matches:
            assert user1_id not in matched_users
            assert user2_id not in matched_users
            matched_users.add(user1_id)
            matched_users.add(user2_id)

@pytest.mark.asyncio
async def test_save_matches(create_test_users):
    """Test saving matches to database"""
    # Get all users
    users = await UserRepository.get_active_users()
    test_users = [user for user in users if user['telegram_id'] in [u.telegram_id for u in TEST_USERS]]
    
    # Create a test match
    test_match = [(test_users[0]['id'], test_users[1]['id'])]
    
    # Save match
    match_ids = await MatchingService.save_matches(test_match)
    
    # Verify match was saved
    assert len(match_ids) == 1
    
    # Get match from database
    match = await MatchRepository.get_match_by_id(match_ids[0])
    
    # Verify match data
    assert match is not None
    assert match['user1_id'] == test_users[0]['id']
    assert match['user2_id'] == test_users[1]['id']
    assert match['status'] == 'pending'