# Random Coffee Bot

A Telegram bot for connecting people for coffee chats, built with Python, aiogram, asyncpg, and FastAPI.

## Features

- **User Registration**: Users can register and fill out their profile through a Mini App
- **Smart Matching**: Algorithm matches users based on interests, location, and language preferences
- **Notifications**: Users receive notifications about new matches and reminders
- **Match Management**: Users can accept, decline, or mark matches as completed
- **Feedback System**: Users can leave feedback after meetings
- **Statistics**: Users can view their matching statistics
- **Modern Mini App**: Web application inside Telegram with a modern and intuitive interface

## Requirements

- Python 3.8+
- PostgreSQL 12+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Mini App configured in Telegram

## Installation

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/random-coffee-bot.git
   cd random-coffee-bot
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

4. Edit the `.env` file with your configuration:
   ```
   BOT_TOKEN=your_telegram_bot_token_here
   WEBAPP_URL=your_mini_app_url_here
   WEBAPP_PORT=8000
   
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=coffee_bot
   DB_USER=postgres
   DB_PASSWORD=your_password_here
   
   TIMEZONE=UTC
   MATCH_DAY=Monday
   MATCH_HOUR=10
   NOTIFICATION_HOUR=9
   MAX_MISSED_MATCHES=3
   ```

5. Create the PostgreSQL database:
   ```bash
   createdb coffee_bot
   ```

6. Run the bot and webapp separately:
   ```bash
   # Terminal 1: Run the bot
   python bot.py
   
   # Terminal 2: Run the webapp
   python run_webapp.py
   ```

### Docker Deployment

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/random-coffee-bot.git
   cd random-coffee-bot
   ```

2. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file with your configuration (see above).

4. Build and run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

## Project Structure

```
random-coffee-bot/
├── app/                      # Main application package
│   ├── database/             # Database related modules
│   │   ├── repositories/     # Database repositories
│   │   ├── connection.py     # Database connection management
│   │   └── models.py         # Pydantic models
│   ├── handlers/             # Telegram bot handlers
│   ├── middlewares/          # Telegram bot middlewares
│   ├── services/             # Business logic services
│   ├── webapp/               # Mini App (Telegram Web App)
│   │   ├── static/           # Static files (CSS, JS, images)
│   │   ├── templates/        # HTML templates
│   │   └── main.py           # FastAPI application
│   ├── commands.py           # Bot commands setup
│   └── scheduler.py          # Scheduler for periodic tasks
├── tests/                    # Test package
├── .env.example              # Example environment variables
├── .env.test                 # Test environment variables
├── bot.py                    # Main bot entry point
├── run_webapp.py             # Script to run the FastAPI webapp
├── docker-compose.yml        # Docker Compose configuration
├── Dockerfile                # Docker configuration
├── pytest.ini                # Pytest configuration
├── README.md                 # This file
└── requirements.txt          # Python dependencies
```

## Mini App Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and get your bot token.
2. Use the `/newapp` command in BotFather to create a new Mini App.
3. Set the Mini App URL to your deployed webapp URL (e.g., `https://your-domain.com` or `http://localhost:8000` for local development).
4. Update your `.env` file with the bot token and Mini App URL.

## Mini App Features

The Mini App provides a user-friendly interface for:

1. **Profile Management**: Users can create and edit their profiles with:
   - Name/nickname
   - Bio
   - Interests
   - Location
   - Preferred language
   - Profile photo (via URL)
   - Preferred days/times for meetings
   - Timezone

2. **Match Interaction**: Users can:
   - View match profiles
   - Accept or decline matches
   - Contact matched users
   - Mark meetings as completed
   - Leave feedback after meetings

## Testing

1. Create a test database:
   ```bash
   createdb coffee_bot_test
   ```

2. Run the tests:
   ```bash
   pytest
   ```

3. Run tests with coverage:
   ```bash
   pytest --cov=app
   ```

## Matching Algorithm

The matching algorithm works as follows:

1. Collects all active users who haven't missed too many matches
2. For each user, finds available candidates based on:
   - Location proximity
   - Language preferences
   - Common interests
   - Previous match history (to avoid repeats)
3. Sorts users by the number of available candidates (ascending)
4. Creates matches, prioritizing users with fewer options
5. Handles remaining users (for odd numbers) by creating groups of 3

## Bot Commands

- `/start` - Start the bot
- `/help` - Show help information
- `/profile` - View or update your profile
- `/matches` - View your current matches
- `/history` - View your match history
- `/stats` - View your matching statistics
- `/settings` - Change your settings
- `/feedback` - Leave feedback about the bot

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.