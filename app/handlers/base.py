from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, WebAppInfo
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from loguru import logger
import os

from app.database.repositories import UserRepository
from app.database.models import UserCreate, UserUpdate

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    # Check if user exists
    user = await UserRepository.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        # Create new user with basic info
        new_user = UserCreate(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
        
        user_id = await UserRepository.create_user(new_user)
        logger.info(f"New user created: {user_id}")
        
        # Welcome message for new users
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        webapp_url = os.getenv("WEBAPP_URL")
        
        keyboard = None

        if webapp_url:
            webapp_button = InlineKeyboardButton(
                text="Complete Your Profile",
                web_app=WebAppInfo(url=f"{webapp_url}/profile/edit")
            )
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[webapp_button]]  # one button per row
            )
        
        await message.answer(
            "👋 <b>Welcome to Random Coffee Bot!</b>\n\n"
            "I'll help you connect with interesting people for coffee chats.\n\n"
            "To get started, please fill out your profile by clicking the button below or using the /profile command.",
            reply_markup=keyboard
        )
    else:
        # Welcome back message
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Create keyboard with web app button
        webapp_url = os.getenv("WEBAPP_URL")
        
        keyboard = None
        if webapp_url:
            webapp_button = InlineKeyboardButton(
                text="View Mini App",
                web_app=WebAppInfo(url=f"{webapp_url}")
            )
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[webapp_button]]  # one button per row
            )
        
        await message.answer(
            f"👋 <b>Welcome back, {message.from_user.first_name}!</b>\n\n"
            f"Use /profile to update your profile or /help to see all available commands.",
            reply_markup=keyboard
        )
    
    # Reset any active state
    await state.clear()

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "🤖 <b>Random Coffee Bot Commands</b>\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/profile - View or update your profile\n"
        "/matches - View your current matches\n"
        "/history - View your match history\n"
        "/stats - View your matching statistics\n"
        "/settings - Change your settings\n"
        "/feedback - Leave feedback about the bot\n\n"
        "If you have any questions or issues, please contact the administrator."
    )
    
    await message.answer(help_text)

@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Handle /profile command"""
    # Get user profile
    user = await UserRepository.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        # This shouldn't happen, but just in case
        await message.answer(
            "⚠️ Your profile was not found. Please use /start to register."
        )
        return
    
    # Check if profile is complete
    is_complete = all([
        user['bio'],
        user['interests'],
        user['location_lat'],
        user['location_lon'],
        user['preferred_language']
    ])
    
    # Create profile text
    profile_text = (
        f"👤 <b>Your Profile</b>\n\n"
        f"<b>Name:</b> {user['full_name']}\n"
    )
    
    if user['username']:
        profile_text += f"<b>Username:</b> @{user['username']}\n"
    
    profile_text += f"\n<b>Bio:</b> {user['bio'] or 'Not set'}\n\n"
    
    if user['interests']:
        profile_text += f"<b>Interests:</b> {', '.join(user['interests'])}\n\n"
    else:
        profile_text += "<b>Interests:</b> Not set\n\n"
    
    if user['location_lat'] and user['location_lon']:
        profile_text += f"<b>Location radius:</b> {user['radius']} km\n\n"
    else:
        profile_text += "<b>Location:</b> Not set\n\n"
    
    profile_text += f"<b>Preferred language:</b> {user['preferred_language']}\n\n"
    
    if user['preferred_days']:
        profile_text += f"<b>Preferred days:</b> {', '.join(user['preferred_days'])}\n"
    
    if user['preferred_time_start'] and user['preferred_time_end']:
        profile_text += f"<b>Preferred time:</b> {user['preferred_time_start']} - {user['preferred_time_end']}\n"
    
    profile_text += f"\n<b>Timezone:</b> {user['timezone']}\n\n"
    
    if is_complete:
        profile_text += "✅ Your profile is complete and ready for matching!"
    else:
        profile_text += "⚠️ Your profile is incomplete. Please update it to participate in matching."
    
    # Create inline keyboard for editing profile
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = None
    webapp_url = os.getenv("WEBAPP_URL")
    
    if webapp_url:
        edit_btn = InlineKeyboardButton(
            text="Edit Profile",
            web_app=WebAppInfo(url=f"{webapp_url}/profile/edit")
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[edit_btn]]  # one button per row
        )
    
    await message.answer(profile_text, reply_markup=keyboard)

@router.message(Command("matches"))
async def cmd_matches(message: Message):
    """Handle /matches command"""
    # Get user
    user = await UserRepository.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("⚠️ Your profile was not found. Please use /start to register.")
        return
    
    # Get user's matches
    from app.database.repositories import MatchRepository
    
    matches = await MatchRepository.get_user_matches(user['id'])
    
    if not matches:
        await message.answer(
            "You don't have any matches yet. We'll notify you when you get matched!"
        )
        return
    
    # Create inline keyboard
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    webapp_url = os.getenv("WEBAPP_URL")
    
    # Send message for each match
    for match in matches:
        # Determine the other user
        other_user_id = match['user1_id'] if match['user1_id'] != user['id'] else match['user2_id']
        other_user = await UserRepository.get_user_by_id(other_user_id)
        
        if not other_user:
            continue
        
        # Create message based on status
        if match['status'] == 'pending':
            # Add view profile button
            if webapp_url:
                view_profile = InlineKeyboardButton(
                    text="View Profile",
                    web_app=WebAppInfo(url=f"{webapp_url}/profile/{other_user['id']}?match_id={match['id']}&status=pending")
                )
                keyboard.add(view_profile)
            
            # Add accept/decline buttons
            accept = InlineKeyboardButton(text="Accept ✅", callback_data=f"match_accept_{match['id']}")
            decline = InlineKeyboardButton(text="Decline ❌", callback_data=f"match_decline_{match['id']}")

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[view_profile], [accept, decline]]
            )
            
            message_text = (
                f"🔄 <b>Pending Match</b>\n\n"
                f"You've been matched with <b>{other_user['full_name']}</b> for a coffee chat!\n\n"
                f"<b>About them:</b> {other_user['bio'] or 'No bio provided'}\n\n"
                f"<b>Interests:</b> {', '.join(other_user['interests'])}\n\n"
                f"Please accept or decline this match."
            )
            
            await message.answer(message_text, reply_markup=keyboard)
            
        elif match['status'] == 'accepted':
            keyboard = None
            
            # Add view profile button
            if webapp_url:
                view_profile = InlineKeyboardButton(
                    text="View Profile",
                    web_app=WebAppInfo(url=f"{webapp_url}/profile/{other_user['id']}?match_id={match['id']}&status=accepted")
                )
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[[view_profile]]
                )
            
            # Add contact button
            contact_btn = InlineKeyboardButton(
                text=f"Contact {other_user['full_name']}", 
                url=f"tg://user?id={other_user['telegram_id']}"
            )
            
            # Add complete button
            complete_btn = InlineKeyboardButton(
                text="Mark as Completed", 
                callback_data=f"match_complete_{match['id']}"
            )
            
            keyboard.add(contact_btn, complete_btn)
            
            message_text = (
                f"✅ <b>Accepted Match</b>\n\n"
                f"You've accepted a coffee chat with <b>{other_user['full_name']}</b>!\n\n"
                f"<b>About them:</b> {other_user['bio'] or 'No bio provided'}\n\n"
                f"<b>Interests:</b> {', '.join(other_user['interests'])}\n\n"
                f"Contact them to arrange your meeting, and mark it as completed when done."
            )
            
            await message.answer(message_text, reply_markup=keyboard)
            
        elif match['status'] == 'completed':
            keyboard = None
            
            # Add view profile button
            if webapp_url:
                view_profile = InlineKeyboardButton(
                    text="View Profile",
                    web_app=WebAppInfo(url=f"{webapp_url}/profile/{other_user['id']}?match_id={match['id']}&status=completed")
                )
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[[view_profile]]
                )
            
            # Add feedback button if not already provided
            if (match['user1_id'] == user['id'] and not match['feedback_user1']) or \
               (match['user2_id'] == user['id'] and not match['feedback_user2']):
                feedback_btn = InlineKeyboardButton(
                    text="Leave Feedback", 
                    callback_data=f"feedback_{match['id']}"
                )
                keyboard.add(feedback_btn)
            
            message_text = (
                f"✅ <b>Completed Match</b>\n\n"
                f"You had a coffee chat with <b>{other_user['full_name']}</b>.\n\n"
                f"<b>Date:</b> {match['meeting_date'].strftime('%d %b %Y') if match['meeting_date'] else 'Not specified'}\n\n"
            )
            
            if keyboard.inline_keyboard:
                await message.answer(message_text, reply_markup=keyboard)
            else:
                await message.answer(message_text)

@router.message(Command("history"))
async def cmd_history(message: Message):
    """Handle /history command"""
    # Get user
    user = await UserRepository.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("⚠️ Your profile was not found. Please use /start to register.")
        return
    
    # Get user's match history
    from app.database.repositories import MatchRepository
    
    history = await MatchRepository.get_match_history(user['id'])
    
    if not history:
        await message.answer(
            "You don't have any match history yet. Complete some coffee chats to see them here!"
        )
        return
    
    # Create message
    history_text = "📚 <b>Your Match History</b>\n\n"
    
    for entry in history:
        # Get the other user
        other_user_id = entry['user1_id'] if entry['user1_id'] != user['id'] else entry['user2_id']
        other_user = await UserRepository.get_user_by_id(other_user_id)
        
        if not other_user:
            continue
        
        # Add entry to history text
        history_text += (
            f"☕ <b>{other_user['full_name']}</b>\n"
            f"📅 {entry['match_date'].strftime('%d %b %Y')}\n"
            f"🏷️ Status: {entry['status'].capitalize()}\n\n"
        )
    
    await message.answer(history_text)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Handle /stats command"""
    # Get user
    user = await UserRepository.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("⚠️ Your profile was not found. Please use /start to register.")
        return
    
    # Get user's stats
    from app.database.repositories import MatchRepository
    
    stats = await MatchRepository.get_match_stats(user['id'])
    
    # Create message
    stats_text = (
        f"📊 <b>Your Coffee Chat Statistics</b>\n\n"
        f"Total matches: {stats['total']}\n"
        f"Completed chats: {stats['completed']}\n"
        f"Pending matches: {stats['pending']}\n"
        f"Missed/declined: {stats['missed']}\n\n"
    )
    
    if stats['total'] > 0:
        completion_rate = (stats['completed'] / stats['total']) * 100
        stats_text += f"Completion rate: {completion_rate:.1f}%\n"
    
    await message.answer(stats_text)

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Handle /settings command"""
    # Get user
    user = await UserRepository.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("⚠️ Your profile was not found. Please use /start to register.")
        return
    
    # Create inline keyboard
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Toggle active status
    status_text = "Pause Matching" if user['is_active'] else "Resume Matching"
    status_data = f"settings_status_{'pause' if user['is_active'] else 'resume'}"
    status_btn = InlineKeyboardButton(text=status_text, callback_data=status_data)
    
    # Edit profile button
    webapp_url = os.getenv("WEBAPP_URL")
    if webapp_url:
        edit_btn = InlineKeyboardButton(
            text="Edit Profile",
            web_app=WebAppInfo(url=f"{webapp_url}/profile/edit")
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[edit_btn], [status_btn]]
    )
    
    # Create message
    settings_text = (
        f"⚙️ <b>Your Settings</b>\n\n"
        f"Status: {'Active' if user['is_active'] else 'Paused'}\n"
        f"Language: {user['preferred_language']}\n"
        f"Timezone: {user['timezone']}\n"
        f"Match radius: {user['radius']} km\n\n"
        f"Use the buttons below to change your settings."
    )
    
    await message.answer(settings_text, reply_markup=keyboard)

@router.message(Command("feedback"))
async def cmd_feedback(message: Message, state: FSMContext):
    """Handle /feedback command"""
    from aiogram.fsm.state import State, StatesGroup
    
    class FeedbackStates(StatesGroup):
        waiting_for_feedback = State()
    
    await message.answer(
        "📝 <b>Bot Feedback</b>\n\n"
        "Please send your feedback about the bot. This will be sent to the administrators."
    )
    
    await state.set_state(FeedbackStates.waiting_for_feedback)

@router.message(lambda message: message.text and not message.text.startswith('/'))
async def process_feedback(message: Message, state: FSMContext):
    """Process feedback message"""
    current_state = await state.get_state()
    
    if current_state == "FeedbackStates:waiting_for_feedback":
        # Save feedback
        feedback = message.text
        
        # Here you would typically save this to a database or send to admins
        logger.info(f"Received feedback from user {message.from_user.id}: {feedback}")
        
        await message.answer(
            "✅ Thank you for your feedback! It has been sent to the administrators."
        )
        
        await state.clear()
    else:
        # Handle unknown messages
        await message.answer(
            "I'm not sure what you mean. Use /help to see available commands."
        )