from aiogram import Router, F, Bot
from aiogram.types import Message, WebAppInfo, WebAppData
from loguru import logger
import json

from app.database.repositories import UserRepository, MatchRepository
from app.database.models import UserUpdate, MatchUpdate

router = Router()

@router.message(F.web_app_data)
async def process_webapp_data(message: Message, bot: Bot):
    """Process data received from the web app"""
    try:
        # Get the data from the web app
        web_app_data = message.web_app_data
        data = json.loads(web_app_data.data)
        
        # Get user
        user = await UserRepository.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("⚠️ Your profile was not found. Please use /start to register.")
            return
        
        # Process data based on the action
        action = data.get('action')
        
        if action == 'update_profile':
            # Update user profile
            profile_data = data.get('profile', {})
            
            # Convert data to UserUpdate model
            user_update = UserUpdate(
                full_name=profile_data.get('full_name'),
                bio=profile_data.get('bio'),
                interests=profile_data.get('interests'),
                location_lat=profile_data.get('location_lat'),
                location_lon=profile_data.get('location_lon'),
                radius=profile_data.get('radius'),
                preferred_language=profile_data.get('preferred_language'),
                photo_url=profile_data.get('photo_url'),
                preferred_days=profile_data.get('preferred_days'),
                preferred_time_start=profile_data.get('preferred_time_start'),
                preferred_time_end=profile_data.get('preferred_time_end'),
                timezone=profile_data.get('timezone')
            )
            
            # Update user in database
            success = await UserRepository.update_user(user['id'], user_update)
            
            if success:
                await message.answer(
                    "✅ Your profile has been updated successfully!\n\n"
                    "Use /profile to view your updated profile."
                )
            else:
                await message.answer(
                    "❌ Failed to update your profile. Please try again."
                )
        
        elif action == 'feedback':
            # Process feedback
            feedback_data = data.get('feedback', {})
            match_id = feedback_data.get('match_id')
            feedback_text = feedback_data.get('text')
            
            if match_id and feedback_text:
                # Get match
                match = await MatchRepository.get_match_by_id(match_id)
                if not match:
                    await message.answer("Match not found.")
                    return
                
                # Update match with feedback
                if match['user1_id'] == user['id']:
                    match_update = MatchUpdate(feedback_user1=feedback_text)
                else:
                    match_update = MatchUpdate(feedback_user2=feedback_text)
                
                success = await MatchRepository.update_match(match_id, match_update)
                
                if success:
                    await message.answer(
                        "✅ Thank you for your feedback! It will help us improve the matching process."
                    )
                else:
                    await message.answer(
                        "❌ Failed to save feedback. Please try again."
                    )
            else:
                await message.answer(
                    "❌ Invalid feedback data. Please try again."
                )
        
        elif action == 'match_action':
            # Process match action (accept, decline, complete)
            match_id = data.get('match_id')
            action_type = data.get('action_type')
            
            if match_id and action_type:
                # Get match
                match = await MatchRepository.get_match_by_id(match_id)
                if not match:
                    await message.answer("Match not found.")
                    return
                
                # Process action
                if action_type == 'accept':
                    # Update match status to accepted
                    match_update = MatchUpdate(status="accepted")
                    success = await MatchRepository.update_match(match_id, match_update)
                    
                    if success:
                        # Send notification to the other user
                        from app.services.notification import NotificationService
                        notification_service = NotificationService(bot)
                        await notification_service.notify_match_status(match_id, "accepted", user['id'])
                        
                        await message.answer(
                            "✅ You've accepted the match! You can now contact the other person."
                        )
                    else:
                        await message.answer(
                            "❌ Failed to accept match. Please try again."
                        )
                
                elif action_type == 'decline':
                    # Update match status to declined
                    match_update = MatchUpdate(status="declined")
                    success = await MatchRepository.update_match(match_id, match_update)
                    
                    if success:
                        # Send notification to the other user
                        from app.services.notification import NotificationService
                        notification_service = NotificationService(bot)
                        await notification_service.notify_match_status(match_id, "declined", user['id'])
                        
                        await message.answer(
                            "✅ You've declined the match. We'll find you a new match soon!"
                        )
                    else:
                        await message.answer(
                            "❌ Failed to decline match. Please try again."
                        )
                
                elif action_type == 'complete':
                    # Update match status to completed
                    match_update = MatchUpdate(status="completed")
                    success = await MatchRepository.update_match(match_id, match_update)
                    
                    if success:
                        # Add to match history
                        from app.database.models import MatchHistoryCreate
                        
                        history_entry = MatchHistoryCreate(
                            user1_id=match['user1_id'],
                            user2_id=match['user2_id'],
                            status="completed"
                        )
                        
                        await MatchRepository.add_to_history(history_entry)
                        
                        # Send notification to both users
                        from app.services.notification import NotificationService
                        notification_service = NotificationService(bot)
                        await notification_service.notify_match_status(match_id, "completed")
                        
                        await message.answer(
                            "✅ You've marked this match as completed. Thank you for participating!"
                        )
                    else:
                        await message.answer(
                            "❌ Failed to complete match. Please try again."
                        )
                else:
                    await message.answer(
                        "❌ Invalid action type. Please try again."
                    )
            else:
                await message.answer(
                    "❌ Invalid match action data. Please try again."
                )
        
        else:
            await message.answer(
                "❌ Unknown action. Please try again."
            )
    
    except Exception as e:
        logger.error(f"Error processing web app data: {e}")
        await message.answer(
            "❌ An error occurred while processing your data. Please try again."
        )