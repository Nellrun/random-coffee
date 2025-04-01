from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import asyncpg

from app.database.connection import get_pool
from app.database.models import MatchCreate, MatchUpdate, MatchHistoryCreate


class MatchRepository:
    """Repository for match-related database operations"""

    @staticmethod
    async def create_match(match: MatchCreate) -> int:
        """Create a new match and return the match ID"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            match_id = await conn.fetchval('''
                INSERT INTO matches (user1_id, user2_id, status, meeting_date)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            ''', match.user1_id, match.user2_id, match.status, match.meeting_date)
            
            return match_id

    @staticmethod
    async def get_match_by_id(match_id: int) -> Optional[Dict[str, Any]]:
        """Get a match by ID"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            match = await conn.fetchrow('''
                SELECT * FROM matches WHERE id = $1
            ''', match_id)
            
            return dict(match) if match else None

    @staticmethod
    async def update_match(match_id: int, match_data: MatchUpdate) -> bool:
        """Update match information"""
        pool = await get_pool()
        
        # Filter out None values
        update_data = {k: v for k, v in match_data.dict().items() if v is not None}
        if not update_data:
            return False
        
        # Build the SET clause dynamically
        set_clause = ", ".join([f"{key} = ${i+1}" for i, key in enumerate(update_data.keys())])
        
        # Build the query
        query = f"UPDATE matches SET {set_clause} WHERE id = ${len(update_data) + 1} RETURNING id"
        
        # Build the parameters
        params = list(update_data.values()) + [match_id]
        
        async with pool.acquire() as conn:
            result = await conn.fetchval(query, *params)
            return result is not None

    @staticmethod
    async def get_user_matches(user_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all matches for a user"""
        pool = await get_pool()
        
        conditions = ["(user1_id = $1 OR user2_id = $1)"]
        params = [user_id]
        
        if status:
            conditions.append("status = $2")
            params.append(status)
        
        where_clause = " AND ".join(conditions)
        query = f"SELECT * FROM matches WHERE {where_clause} ORDER BY created_at DESC"
        
        async with pool.acquire() as conn:
            matches = await conn.fetch(query, *params)
            return [dict(match) for match in matches]

    @staticmethod
    async def get_match_history(user_id: int) -> List[Dict[str, Any]]:
        """Get match history for a user"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            history = await conn.fetch('''
                SELECT * FROM match_history 
                WHERE user1_id = $1 OR user2_id = $1
                ORDER BY match_date DESC
            ''', user_id)
            
            return [dict(entry) for entry in history]

    @staticmethod
    async def add_to_history(history_entry: MatchHistoryCreate) -> int:
        """Add a match to history"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            history_id = await conn.fetchval('''
                INSERT INTO match_history (user1_id, user2_id, status, feedback)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            ''', history_entry.user1_id, history_entry.user2_id, 
                history_entry.status, history_entry.feedback)
            
            return history_id

    @staticmethod
    async def get_previous_matches(user_id: int) -> List[int]:
        """Get IDs of users that the given user has been matched with before"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            # Get from matches table
            current_matches = await conn.fetch('''
                SELECT user1_id, user2_id FROM matches
                WHERE user1_id = $1 OR user2_id = $1
            ''', user_id)
            
            # Get from history table
            history_matches = await conn.fetch('''
                SELECT user1_id, user2_id FROM match_history
                WHERE user1_id = $1 OR user2_id = $1
            ''', user_id)
            
            # Combine and extract the other user's ID
            matched_users = set()
            for match in current_matches + history_matches:
                if match['user1_id'] == user_id:
                    matched_users.add(match['user2_id'])
                else:
                    matched_users.add(match['user1_id'])
            
            return list(matched_users)

    @staticmethod
    async def count_missed_matches(user_id: int) -> int:
        """Count how many consecutive matches a user has missed"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            # Get the most recent matches in reverse chronological order
            recent_matches = await conn.fetch('''
                SELECT id, status FROM matches
                WHERE (user1_id = $1 OR user2_id = $1)
                ORDER BY created_at DESC
                LIMIT 10
            ''', user_id)
            
            # Count consecutive missed matches
            missed_count = 0
            for match in recent_matches:
                if match['status'] in ['missed', 'cancelled']:
                    missed_count += 1
                else:
                    # If we find a non-missed match, break the streak
                    break
            
            return missed_count

    @staticmethod
    async def get_match_stats(user_id: int) -> Dict[str, int]:
        """Get match statistics for a user"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            # Count total matches
            total = await conn.fetchval('''
                SELECT COUNT(*) FROM matches
                WHERE user1_id = $1 OR user2_id = $1
            ''', user_id)
            
            # Count completed matches
            completed = await conn.fetchval('''
                SELECT COUNT(*) FROM matches
                WHERE (user1_id = $1 OR user2_id = $1) AND status = 'completed'
            ''', user_id)
            
            # Count missed matches
            missed = await conn.fetchval('''
                SELECT COUNT(*) FROM matches
                WHERE (user1_id = $1 OR user2_id = $1) AND status IN ('missed', 'cancelled')
            ''', user_id)
            
            # Count pending matches
            pending = await conn.fetchval('''
                SELECT COUNT(*) FROM matches
                WHERE (user1_id = $1 OR user2_id = $1) AND status = 'pending'
            ''', user_id)
            
            return {
                "total": total,
                "completed": completed,
                "missed": missed,
                "pending": pending
            }
            
    @staticmethod
    async def get_matches_by_status(status: str) -> List[Dict[str, Any]]:
        """Get all matches with a specific status"""
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            matches = await conn.fetch('''
                SELECT * FROM matches WHERE status = $1
            ''', status)
            
            return [dict(match) for match in matches]