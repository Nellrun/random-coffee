import random
from typing import List, Dict, Any, Tuple, Set
from datetime import datetime
import pytz
from loguru import logger

from app.database.repositories import UserRepository, MatchRepository
from app.database.models import MatchCreate


class MatchingService:
    """Service for matching users for coffee meetings"""
    
    @staticmethod
    async def get_active_users_for_matching() -> List[Dict[str, Any]]:
        """Get all active users eligible for matching"""
        # Get all active users
        users = await UserRepository.get_active_users()
        
        # Filter out users who have missed too many matches in a row
        max_missed = int(os.getenv("MAX_MISSED_MATCHES", "3"))
        eligible_users = []
        
        for user in users:
            missed_count = await MatchRepository.count_missed_matches(user['id'])
            if missed_count < max_missed:
                eligible_users.append(user)
            else:
                logger.info(f"User {user['id']} excluded from matching due to {missed_count} missed matches")
        
        return eligible_users
    
    @staticmethod
    async def get_available_candidates(user_id: int, all_users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all available candidates for a user"""
        # Get the user
        user = next((u for u in all_users if u['id'] == user_id), None)
        if not user:
            return []
        
        # Get previously matched users
        previous_matches = await MatchRepository.get_previous_matches(user_id)
        
        # Filter candidates
        candidates = []
        for candidate in all_users:
            # Skip self
            if candidate['id'] == user_id:
                continue
            
            # Skip previously matched users
            if candidate['id'] in previous_matches:
                continue
            
            # Check location if available
            if all([user['location_lat'], user['location_lon'], 
                    candidate['location_lat'], candidate['location_lon']]):
                # Calculate distance (simplified)
                distance = MatchingService._calculate_distance(
                    user['location_lat'], user['location_lon'],
                    candidate['location_lat'], candidate['location_lon']
                )
                
                # Check if within radius
                if distance > user['radius']:
                    continue
            
            # Check language preference
            if user['preferred_language'] != candidate['preferred_language']:
                continue
            
            # Check for common interests
            user_interests = set(user['interests'])
            candidate_interests = set(candidate['interests'])
            
            if not user_interests.intersection(candidate_interests):
                continue
            
            candidates.append(candidate)
        
        return candidates
    
    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers using Haversine formula"""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of earth in kilometers
        
        return c * r
    
    @staticmethod
    async def create_matches() -> List[Tuple[int, int]]:
        """Create matches between users"""
        logger.info("Starting matching process")
        
        # Get all eligible users
        users = await MatchingService.get_active_users_for_matching()
        logger.info(f"Found {len(users)} eligible users for matching")
        
        if len(users) < 2:
            logger.warning("Not enough users for matching")
            return []
        
        # Sort users by number of available candidates (ascending)
        users_with_candidates = []
        for user in users:
            candidates = await MatchingService.get_available_candidates(user['id'], users)
            users_with_candidates.append((user, candidates))
        
        users_with_candidates.sort(key=lambda x: len(x[1]))
        
        # Create matches
        matches = []
        matched_users: Set[int] = set()
        
        for user, candidates in users_with_candidates:
            # Skip if user already matched
            if user['id'] in matched_users:
                continue
            
            # Filter out already matched candidates
            available_candidates = [c for c in candidates if c['id'] not in matched_users]
            
            if not available_candidates:
                logger.info(f"No available candidates for user {user['id']}")
                continue
            
            # Select candidate with minimum previous matches
            candidate = min(available_candidates, 
                           key=lambda c: len(MatchRepository.get_previous_matches(c['id'])))
            
            # Create match
            matches.append((user['id'], candidate['id']))
            matched_users.add(user['id'])
            matched_users.add(candidate['id'])
            
            logger.info(f"Created match between users {user['id']} and {candidate['id']}")
        
        # Handle remaining users (for odd number of users)
        remaining_users = [u[0] for u in users_with_candidates if u[0]['id'] not in matched_users]
        
        if len(remaining_users) >= 3:
            # Create a group of 3
            group = remaining_users[:3]
            matches.append((group[0]['id'], group[1]['id']))
            matches.append((group[1]['id'], group[2]['id']))
            matches.append((group[0]['id'], group[2]['id']))
            
            logger.info(f"Created group match between users {group[0]['id']}, {group[1]['id']}, and {group[2]['id']}")
        
        return matches
    
    @staticmethod
    async def save_matches(matches: List[Tuple[int, int]]) -> List[int]:
        """Save matches to database"""
        match_ids = []
        
        for user1_id, user2_id in matches:
            match = MatchCreate(
                user1_id=user1_id,
                user2_id=user2_id,
                status="pending"
            )
            
            match_id = await MatchRepository.create_match(match)
            match_ids.append(match_id)
        
        logger.info(f"Saved {len(match_ids)} matches to database")
        return match_ids


import os  # Add this import at the top of the file