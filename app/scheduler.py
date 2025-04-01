import asyncio
import os
from datetime import datetime, time
import pytz
from loguru import logger

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.matching import MatchingService
from app.services.notification import NotificationService


class Scheduler:
    """Scheduler for running periodic tasks"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.notification_service = NotificationService(bot)
    
    def start(self):
        """Start the scheduler"""
        # Schedule matching process
        match_day = os.getenv("MATCH_DAY", "Monday")
        match_hour = int(os.getenv("MATCH_HOUR", "10"))
        
        self.scheduler.add_job(
            self.run_matching_process,
            trigger=CronTrigger(day_of_week=match_day.lower()[:3], hour=match_hour),
            id="matching_process",
            replace_existing=True
        )
        
        # Schedule notification for upcoming matches
        notification_hour = int(os.getenv("NOTIFICATION_HOUR", "9"))
        
        self.scheduler.add_job(
            self.send_match_reminders,
            trigger=CronTrigger(day_of_week=match_day.lower()[:3], hour=notification_hour),
            id="match_reminders",
            replace_existing=True
        )
        
        # Start the scheduler
        self.scheduler.start()
        logger.info(f"Scheduler started. Matching process scheduled for {match_day} at {match_hour}:00")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler shutdown")
    
    async def run_matching_process(self):
        """Run the matching process"""
        logger.info("Running matching process")
        
        try:
            # Create matches
            matches = await MatchingService.create_matches()
            
            if not matches:
                logger.info("No matches created")
                return
            
            # Save matches to database
            match_ids = await MatchingService.save_matches(matches)
            
            # Send notifications
            for match_id in match_ids:
                await self.notification_service.notify_match(match_id)
                # Add a small delay to avoid flooding Telegram API
                await asyncio.sleep(0.5)
            
            logger.info(f"Matching process completed. Created {len(match_ids)} matches.")

            await self.send_match_reminders()
        
        except Exception as e:
            logger.error(f"Error in matching process: {e}")
    
    async def send_match_reminders(self):
        """Send reminders for pending matches"""
        logger.info("Sending match reminders")
        
        try:
            # Get all pending matches
            from app.database.repositories import MatchRepository
            
            # Get all matches with status "pending"
            matches = await MatchRepository.get_matches_by_status("pending")
            
            if not matches:
                logger.info("No pending matches to remind")
                return
            
            # Send reminders
            for match in matches:
                await self.notification_service.send_reminder(match['id'])
                # Add a small delay to avoid flooding Telegram API
                await asyncio.sleep(0.5)
            
            logger.info(f"Sent reminders for {len(matches)} pending matches")
        
        except Exception as e:
            logger.error(f"Error sending match reminders: {e}")


# Add this method to MatchRepository
async def get_matches_by_status(status: str):
    """Get all matches with a specific status"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        matches = await conn.fetch('''
            SELECT * FROM matches WHERE status = $1
        ''', status)
        
        return [dict(match) for match in matches]

# Import these at the top of the file
from app.database.connection import get_pool