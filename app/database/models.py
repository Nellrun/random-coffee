from datetime import datetime, time
from typing import List, Optional, Union
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Base user model"""
    telegram_id: int
    username: Optional[str] = None
    full_name: str
    bio: Optional[str] = None
    interests: List[str] = []
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    radius: int = 10
    preferred_language: str = "ru"
    photo_url: Optional[str] = None
    preferred_days: List[str] = []
    preferred_time_start: Optional[time] = None
    preferred_time_end: Optional[time] = None
    timezone: str = "Europe/Paris"


class UserCreate(UserBase):
    """Model for creating a new user"""
    pass


class UserUpdate(BaseModel):
    """Model for updating user information"""
    username: Optional[str] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    interests: Optional[List[str]] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    radius: Optional[int] = None
    preferred_language: Optional[str] = None
    photo_url: Optional[str] = None
    preferred_days: Optional[List[str]] = None
    preferred_time_start: Optional[time] = None
    preferred_time_end: Optional[time] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    """Complete user model"""
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool = True


class MatchBase(BaseModel):
    """Base match model"""
    user1_id: int
    user2_id: int
    status: str = "pending"
    meeting_date: Optional[datetime] = None


class MatchCreate(MatchBase):
    """Model for creating a new match"""
    pass


class MatchUpdate(BaseModel):
    """Model for updating match information"""
    status: Optional[str] = None
    meeting_date: Optional[datetime] = None
    feedback_user1: Optional[str] = None
    feedback_user2: Optional[str] = None


class Match(MatchBase):
    """Complete match model"""
    id: int
    created_at: datetime
    feedback_user1: Optional[str] = None
    feedback_user2: Optional[str] = None


class MatchHistoryBase(BaseModel):
    """Base match history model"""
    user1_id: int
    user2_id: int
    status: str = "completed"
    feedback: Optional[str] = None


class MatchHistoryCreate(MatchHistoryBase):
    """Model for creating a new match history entry"""
    pass


class MatchHistory(MatchHistoryBase):
    """Complete match history model"""
    id: int
    match_date: datetime


class UserProfile(BaseModel):
    """User profile model for display"""
    id: int
    username: Optional[str]
    full_name: str
    bio: Optional[str]
    interests: List[str]
    photo_url: Optional[str]
    preferred_language: str