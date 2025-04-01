from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from app.database.repositories import UserRepository, MatchRepository
from app.database.models import MatchUpdate, MatchHistoryCreate
from app.services.notification import NotificationService

router = Router()

class FeedbackStates(StatesGroup):
    waiting_for_match_feedback = State()

@router.callback_query(F.data.startswith("match_accept_"))
async def on_match_accept(callback: CallbackQuery, bot: Bot):
    """Handle match acceptance"""
    # Extract match ID from callback data
    match_id = int(callback.data.split("_")[-1])
    
    # Get match details
    match = await MatchRepository.get_match_by_id(match_id)
    if not match:
        await callback.answer("Match not found", show_alert=True)
        return
    
    # Get user
    user = await UserRepository.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("User not found", show_alert=True)
        return
    
    # Update match status
    match_update = MatchUpdate(status="accepted")
    success = await MatchRepository.update_match(match_id, match_update)
    
    if success:
        # Send notification to the other user
        notification_service = NotificationService(bot)
        await notification_service.notify_match_status(match_id, "accepted", user['id'])
        
        await callback.answer("Match accepted! You can now contact the other person.", show_alert=True)
        
        # Update the message
        other_user_id = match['user1_id'] if match['user1_id'] != user['id'] else match['user2_id']
        other_user = await UserRepository.get_user_by_id(other_user_id)
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        
        # Add contact button
        contact_btn = InlineKeyboardButton(
            text=f"Contact {other_user['full_name']}", 
            url=f"tg://user?id={other_user['telegram_id']}"
        )
        
        # Add complete button
        complete_btn = InlineKeyboardButton(
            text="Mark as Completed", 
            callback_data=f"match_complete_{match_id}"
        )
        
        keyboard.add(contact_btn, complete_btn)
        
        message_text = (
            f"✅ <b>Match Accepted!</b>\n\n"
            f"You've accepted a coffee chat with <b>{other_user['full_name']}</b>!\n\n"
            f"<b>About them:</b> {other_user['bio'] or 'No bio provided'}\n\n"
            f"<b>Interests:</b> {', '.join(other_user['interests'])}\n\n"
            f"Contact them to arrange your meeting, and mark it as completed when done."
        )
        
        await callback.message.edit_text(message_text, reply_markup=keyboard)
    else:
        await callback.answer("Failed to accept match. Please try again.", show_alert=True)

@router.callback_query(F.data.startswith("match_decline_"))
async def on_match_decline(callback: CallbackQuery, bot: Bot):
    """Handle match decline"""
    # Extract match ID from callback data
    match_id = int(callback.data.split("_")[-1])
    
    # Get match details
    match = await MatchRepository.get_match_by_id(match_id)
    if not match:
        await callback.answer("Match not found", show_alert=True)
        return
    
    # Get user
    user = await UserRepository.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("User not found", show_alert=True)
        return
    
    # Update match status
    match_update = MatchUpdate(status="declined")
    success = await MatchRepository.update_match(match_id, match_update)
    
    if success:
        # Send notification to the other user
        notification_service = NotificationService(bot)
        await notification_service.notify_match_status(match_id, "declined", user['id'])
        
        await callback.answer("Match declined.", show_alert=True)
        
        # Update the message
        message_text = (
            f"❌ <b>Match Declined</b>\n\n"
            f"You've declined this match. We'll find you a new match soon!"
        )
        
        await callback.message.edit_text(message_text)
    else:
        await callback.answer("Failed to decline match. Please try again.", show_alert=True)

@router.callback_query(F.data.startswith("match_complete_"))
async def on_match_complete(callback: CallbackQuery, bot: Bot):
    """Handle match completion"""
    # Extract match ID from callback data
    match_id = int(callback.data.split("_")[-1])
    
    # Get match details
    match = await MatchRepository.get_match_by_id(match_id)
    if not match:
        await callback.answer("Match not found", show_alert=True)
        return
    
    # Get user
    user = await UserRepository.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("User not found", show_alert=True)
        return
    
    # Update match status
    match_update = MatchUpdate(status="completed")
    success = await MatchRepository.update_match(match_id, match_update)
    
    if success:
        # Add to match history
        history_entry = MatchHistoryCreate(
            user1_id=match['user1_id'],
            user2_id=match['user2_id'],
            status="completed"
        )
        
        await MatchRepository.add_to_history(history_entry)
        
        # Send notification to both users
        notification_service = NotificationService(bot)
        await notification_service.notify_match_status(match_id, "completed")
        
        await callback.answer("Match marked as completed!", show_alert=True)
        
        # Update the message
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        feedback_btn = InlineKeyboardButton(
            text="Leave Feedback", 
            callback_data=f"feedback_{match_id}"
        )
        keyboard.add(feedback_btn)
        
        message_text = (
            f"✅ <b>Match Completed!</b>\n\n"
            f"You've marked this match as completed. Thank you for participating!\n\n"
            f"Would you like to leave feedback about your experience?"
        )
        
        await callback.message.edit_text(message_text, reply_markup=keyboard)
    else:
        await callback.answer("Failed to complete match. Please try again.", show_alert=True)

@router.callback_query(F.data.startswith("feedback_"))
async def on_feedback_request(callback: CallbackQuery, state: FSMContext):
    """Handle feedback request"""
    # Extract match ID from callback data
    match_id = int(callback.data.split("_")[-1])
    
    # Store match ID in state
    await state.update_data(match_id=match_id)
    
    # Set state to waiting for feedback
    await state.set_state(FeedbackStates.waiting_for_match_feedback)
    
    await callback.answer()
    
    await callback.message.answer(
        "📝 <b>Match Feedback</b>\n\n"
        "Please share your feedback about this coffee chat. What went well? What could be improved?\n\n"
        "Your feedback will help us improve the matching process."
    )

@router.message(FeedbackStates.waiting_for_match_feedback)
async def process_match_feedback(message, state: FSMContext):
    """Process match feedback"""
    # Get data from state
    data = await state.get_data()
    match_id = data.get("match_id")
    
    if not match_id:
        await message.answer("Something went wrong. Please try again.")
        await state.clear()
        return
    
    # Get match details
    match = await MatchRepository.get_match_by_id(match_id)
    if not match:
        await message.answer("Match not found. Please try again.")
        await state.clear()
        return
    
    # Get user
    user = await UserRepository.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("User not found. Please try again.")
        await state.clear()
        return
    
    # Update match with feedback
    if match['user1_id'] == user['id']:
        match_update = MatchUpdate(feedback_user1=message.text)
    else:
        match_update = MatchUpdate(feedback_user2=message.text)
    
    success = await MatchRepository.update_match(match_id, match_update)
    
    if success:
        await message.answer(
            "✅ Thank you for your feedback! It will help us improve the matching process."
        )
    else:
        await message.answer(
            "Failed to save feedback. Please try again."
        )
    
    await state.clear()

@router.callback_query(F.data.startswith("settings_status_"))
async def on_status_toggle(callback: CallbackQuery):
    """Handle status toggle"""
    # Extract action from callback data
    action = callback.data.split("_")[-1]
    
    # Get user
    user = await UserRepository.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("User not found", show_alert=True)
        return
    
    # Update user status
    if action == "pause":
        success = await UserRepository.deactivate_user(user['id'])
        status_text = "paused"
    else:  # resume
        success = await UserRepository.activate_user(user['id'])
        status_text = "resumed"
    
    if success:
        await callback.answer(f"Matching {status_text} successfully!", show_alert=True)
        
        # Update the message
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        
        # Toggle active status
        new_status_text = "Resume Matching" if action == "pause" else "Pause Matching"
        new_status_data = f"settings_status_{'resume' if action == 'pause' else 'pause'}"
        status_btn = InlineKeyboardButton(text=new_status_text, callback_data=new_status_data)
        
        # Edit profile button
        edit_btn = InlineKeyboardButton(text="Edit Profile", web_app={"url": f"{os.getenv('WEBAPP_URL')}/profile/edit"})
        
        keyboard.add(status_btn, edit_btn)
        
        # Create message
        settings_text = (
            f"⚙️ <b>Your Settings</b>\n\n"
            f"Status: {'Paused' if action == 'pause' else 'Active'}\n"
            f"Language: {user['preferred_language']}\n"
            f"Timezone: {user['timezone']}\n"
            f"Match radius: {user['radius']} km\n\n"
            f"Use the buttons below to change your settings."
        )
        
        await callback.message.edit_text(settings_text, reply_markup=keyboard)
    else:
        await callback.answer(f"Failed to {action} matching. Please try again.", show_alert=True)


import os  # Add this import at the top of the file