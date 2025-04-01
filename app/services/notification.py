from typing import List, Dict, Any, Optional
import os
from datetime import datetime
import pytz
from loguru import logger

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database.repositories import UserRepository, MatchRepository


class NotificationService:
    """Service for sending notifications to users"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.webapp_url = os.getenv("WEBAPP_URL", "")
    
    async def notify_match(self, match_id: int) -> bool:
        """Notify users about a new match"""
        try:
            # Get match details
            match = await MatchRepository.get_match_by_id(match_id)
            if not match:
                logger.error(f"Match {match_id} not found")
                return False
            
            # Get user details
            user1 = await UserRepository.get_user_by_id(match['user1_id'])
            user2 = await UserRepository.get_user_by_id(match['user2_id'])
            
            if not user1 or not user2:
                logger.error(f"Users for match {match_id} not found")
                return False
            
            # Send notifications
            await self._send_match_notification(user1, user2, match_id)
            await self._send_match_notification(user2, user1, match_id)
            
            logger.info(f"Match notifications sent for match {match_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error sending match notification: {e}")
            return False
    
    async def _send_match_notification(self, user: Dict[str, Any], match_partner: Dict[str, Any], match_id: int):
        """Send match notification to a user"""        
        # Add view profile button
        profile_url = f"{self.webapp_url}/profile/{match_partner['id']}"
        view_profile = InlineKeyboardButton(text="View Profile", web_app={"url": profile_url})
        
        # Add accept/decline buttons
        accept = InlineKeyboardButton(text="Accept ✅", callback_data=f"match_accept_{match_id}")
        decline = InlineKeyboardButton(text="Decline ❌", callback_data=f"match_decline_{match_id}")

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[view_profile], [accept, decline]]  # one button per row
        )
        
        # Create message text
        message = (
            f"🎉 <b>New Coffee Match!</b>\n\n"
            f"You've been matched with <b>{match_partner['full_name']}</b> for a coffee chat!\n\n"
            f"<b>About them:</b> {match_partner['bio'] or 'No bio provided'}\n\n"
            f"<b>Interests:</b> {', '.join(match_partner['interests'])}\n\n"
            f"Click the button below to view their full profile and accept or decline the match."
        )
        
        # Send message
        await self.bot.send_message(
            chat_id=user['telegram_id'],
            text=message,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    async def notify_match_status(self, match_id: int, status: str, user_id: Optional[int] = None) -> bool:
        """Notify users about match status change"""
        try:
            # Get match details
            match = await MatchRepository.get_match_by_id(match_id)
            if not match:
                logger.error(f"Match {match_id} not found")
                return False
            
            # Get user details
            user1 = await UserRepository.get_user_by_id(match['user1_id'])
            user2 = await UserRepository.get_user_by_id(match['user2_id'])
            
            if not user1 or not user2:
                logger.error(f"Users for match {match_id} not found")
                return False
            
            # Determine which user initiated the status change
            initiator = None
            recipient = None
            
            if user_id:
                if user_id == user1['id']:
                    initiator = user1
                    recipient = user2
                else:
                    initiator = user2
                    recipient = user1
            
            # Send notification based on status
            if status == "accepted":
                if initiator and recipient:
                    await self._send_acceptance_notification(recipient, initiator, match_id)
                
            elif status == "declined":
                if initiator and recipient:
                    await self._send_decline_notification(recipient, initiator, match_id)
                
            elif status == "completed":
                # Send completion notification to both users
                feedback_btn = InlineKeyboardButton(
                    text="Leave Feedback", 
                    callback_data=f"feedback_{match_id}"
                )
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[[feedback_btn]]  # one button per row
                )
                
                message = (
                    f"✅ <b>Coffee Match Completed!</b>\n\n"
                    f"Your coffee chat with <b>{user2['full_name']}</b> has been marked as completed.\n\n"
                    f"Would you like to leave feedback?"
                )
                
                await self.bot.send_message(
                    chat_id=user1['telegram_id'],
                    text=message,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                
                message = (
                    f"✅ <b>Coffee Match Completed!</b>\n\n"
                    f"Your coffee chat with <b>{user1['full_name']}</b> has been marked as completed.\n\n"
                    f"Would you like to leave feedback?"
                )
                
                await self.bot.send_message(
                    chat_id=user2['telegram_id'],
                    text=message,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            
            logger.info(f"Match status notification sent for match {match_id}, status: {status}")
            return True
        
        except Exception as e:
            logger.error(f"Error sending match status notification: {e}")
            return False
    
    async def _send_acceptance_notification(self, user: Dict[str, Any], acceptor: Dict[str, Any], match_id: int):
        """Send notification that match was accepted"""
        # Add contact button
        contact_btn = InlineKeyboardButton(
            text=f"Contact {acceptor['full_name']}", 
            url=f"tg://user?id={acceptor['telegram_id']}"
        )
        
        # Add complete button
        complete_btn = InlineKeyboardButton(
            text="Mark as Completed", 
            callback_data=f"match_complete_{match_id}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[contact_btn, complete_btn]]  # one button per row
        )
        
        message = (
            f"🎉 <b>Match Accepted!</b>\n\n"
            f"<b>{acceptor['full_name']}</b> has accepted your coffee match request!\n\n"
            f"You can now contact them directly to arrange a time and place for your coffee chat."
        )
        
        await self.bot.send_message(
            chat_id=user['telegram_id'],
            text=message,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    async def _send_decline_notification(self, user: Dict[str, Any], decliner: Dict[str, Any], match_id: int):
        """Send notification that match was declined"""
        message = (
            f"❌ <b>Match Declined</b>\n\n"
            f"Unfortunately, <b>{decliner['full_name']}</b> has declined your coffee match request.\n\n"
            f"Don't worry, we'll find you a new match soon!"
        )
        
        await self.bot.send_message(
            chat_id=user['telegram_id'],
            text=message,
            parse_mode="HTML"
        )
    
    async def send_reminder(self, match_id: int) -> bool:
        """Send reminder about pending match"""
        try:
            # Get match details
            match = await MatchRepository.get_match_by_id(match_id)
            if not match or match['status'] != "pending":
                return False
            
            # Get user details
            user1 = await UserRepository.get_user_by_id(match['user1_id'])
            user2 = await UserRepository.get_user_by_id(match['user2_id'])
            
            if not user1 or not user2:
                return False
            
            # Add view profile button
            profile_url = f"{self.webapp_url}/profile/{user2['id']}"
            view_profile = InlineKeyboardButton(text="View Profile", web_app={"url": profile_url})
            
            # Add accept/decline buttons
            accept = InlineKeyboardButton(text="Accept ✅", callback_data=f"match_accept_{match_id}")
            decline = InlineKeyboardButton(text="Decline ❌", callback_data=f"match_decline_{match_id}")
            
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[view_profile], [accept, decline]]  # one button per row
            )
            
            # Send reminder to user1
            message = (
                f"⏰ <b>Reminder: Pending Coffee Match</b>\n\n"
                f"You still have a pending coffee match with <b>{user2['full_name']}</b>.\n\n"
                f"Please accept or decline the match."
            )
            
            await self.bot.send_message(
                chat_id=user1['telegram_id'],
                text=message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
            # Send reminder to user2
            profile_url = f"{self.webapp_url}/profile/{user1['id']}"
            view_profile = InlineKeyboardButton(text="View Profile", web_app={"url": profile_url})

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[view_profile], [accept, decline]]  # one button per row
            )
            
            message = (
                f"⏰ <b>Reminder: Pending Coffee Match</b>\n\n"
                f"You still have a pending coffee match with <b>{user1['full_name']}</b>.\n\n"
                f"Please accept or decline the match."
            )
            
            await self.bot.send_message(
                chat_id=user2['telegram_id'],
                text=message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
            logger.info(f"Reminder sent for match {match_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
            return False