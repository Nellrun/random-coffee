import os
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from loguru import logger

from app.database.connection import get_pool
from app.database.repositories import UserRepository, MatchRepository
from app.database.models import UserUpdate, UserCreate

# Create FastAPI app
app = FastAPI(title="Random Coffee Mini App")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/webapp/static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/webapp/templates")

# JWT secret for validating Telegram data
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    logger.warning("BOT_TOKEN not set in environment variables")

# Models for API requests and responses
class TelegramInitData(BaseModel):
    """Model for Telegram Web App init data"""
    auth_date: int
    hash: str
    query_id: Optional[str] = None
    user: Dict[str, Any]

class ProfileData(BaseModel):
    """Model for profile data"""
    full_name: str
    bio: Optional[str] = None
    interests: List[str] = []
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    radius: int = 10
    preferred_language: str = "en"
    photo_url: Optional[str] = None
    preferred_days: List[str] = []
    preferred_time_start: Optional[str] = None
    preferred_time_end: Optional[str] = None
    timezone: str = "UTC"

class FeedbackData(BaseModel):
    """Model for feedback data"""
    match_id: int
    text: str

class WebAppResponse(BaseModel):
    """Model for Web App response"""
    action: str
    profile: Optional[ProfileData] = None
    feedback: Optional[FeedbackData] = None

# Helper functions
def validate_telegram_data(init_data_str: str) -> Dict[str, Any]:
    """Validate Telegram Web App init data"""
    try:
        # Parse the init data
        init_data = {}
        for item in init_data_str.split("&"):
            key, value = item.split("=")
            if key == "user":
                init_data[key] = json.loads(value)
            else:
                init_data[key] = value
        
        # Validate the hash
        data_check_string = "&".join(
            f"{k}={v}" for k, v in sorted(init_data.items()) if k != "hash"
        )
        
        secret_key = hmac.new(
            "WebAppData".encode(),
            BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()
        
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if calculated_hash != init_data.get("hash"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid hash in Telegram data"
            )
        
        return init_data
    
    except Exception as e:
        logger.error(f"Error validating Telegram data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Telegram data: {str(e)}"
        )

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main page"""
    return templates.TemplateResponse(
        "index.html", 
        {"request": request}
    )

@app.get("/profile/edit", response_class=HTMLResponse)
async def profile_edit(request: Request):
    """Serve the profile edit page"""
    return templates.TemplateResponse(
        "profile_edit.html", 
        {"request": request}
    )

@app.get("/profile/{user_id}", response_class=HTMLResponse)
async def profile_view(request: Request, user_id: int):
    """Serve the profile view page"""
    return templates.TemplateResponse(
        "profile_view.html", 
        {"request": request, "user_id": user_id}
    )

@app.get("/api/user/{telegram_id}", response_class=JSONResponse)
async def get_user(telegram_id: int):
    """Get user data by Telegram ID"""
    user = await UserRepository.get_user_by_telegram_id(telegram_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return JSONResponse(content=user)

@app.get("/api/user/profile/{user_id}", response_class=JSONResponse)
async def get_user_profile(user_id: int):
    """Get user profile by user ID"""
    user = await UserRepository.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Return only public profile data
    profile = {
        "id": user["id"],
        "full_name": user["full_name"],
        "username": user["username"],
        "bio": user["bio"],
        "interests": user["interests"],
        "photo_url": user["photo_url"],
        "preferred_language": user["preferred_language"]
    }
    
    return JSONResponse(content=profile)

@app.post("/api/webapp/data")
async def process_webapp_data(data: WebAppResponse):
    """Process data from the Web App"""
    try:
        if data.action == "update_profile" and data.profile:
            # Convert time strings to time objects if provided
            preferred_time_start = None
            preferred_time_end = None
            
            if data.profile.preferred_time_start:
                hour, minute = map(int, data.profile.preferred_time_start.split(":"))
                preferred_time_start = datetime.time(hour, minute)
            
            if data.profile.preferred_time_end:
                hour, minute = map(int, data.profile.preferred_time_end.split(":"))
                preferred_time_end = datetime.time(hour, minute)
            
            # Create UserUpdate object
            user_update = UserUpdate(
                full_name=data.profile.full_name,
                bio=data.profile.bio,
                interests=data.profile.interests,
                location_lat=data.profile.location_lat,
                location_lon=data.profile.location_lon,
                radius=data.profile.radius,
                preferred_language=data.profile.preferred_language,
                photo_url=data.profile.photo_url,
                preferred_days=data.profile.preferred_days,
                preferred_time_start=preferred_time_start,
                preferred_time_end=preferred_time_end,
                timezone=data.profile.timezone
            )
            
            # Get user by Telegram ID from init data
            # In a real app, you would extract the user ID from the validated Telegram data
            # For simplicity, we'll assume the user ID is provided in the request
            user_id = data.profile.user_id if hasattr(data.profile, "user_id") else None
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User ID not provided"
                )
            
            # Update user
            success = await UserRepository.update_user(user_id, user_update)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update user"
                )
            
            return {"status": "success", "message": "Profile updated successfully"}
        
        elif data.action == "feedback" and data.feedback:
            # Process feedback
            # In a real app, you would validate the match ID and user ID
            # For simplicity, we'll assume they are valid
            
            # Update match with feedback
            from app.database.models import MatchUpdate
            
            match_update = MatchUpdate(
                feedback_user1=data.feedback.text
            )
            
            success = await MatchRepository.update_match(data.feedback.match_id, match_update)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save feedback"
                )
            
            return {"status": "success", "message": "Feedback saved successfully"}
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action or missing data"
            )
    
    except Exception as e:
        logger.error(f"Error processing Web App data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing data: {str(e)}"
        )

# Add these imports at the top of the file
import hmac
import hashlib
import datetime