import os

# Your API credentials from my.telegram.org
API_ID = 123456789          # <-- REPLACE
API_HASH = "your_api_hash_here"  # <-- REPLACE
BOT_TOKEN = "your_bot_token_here"  # <-- REPLACE

# Owner Telegram User ID
OWNER_ID = 1234567890       # <-- REPLACE

# Additional sudo users
SUDO_USERS = [
    1234567891,
    1234567892,
]

# ── MongoDB ──
MONGO_URI = "mongodb://localhost:27017"   # or your MongoDB Atlas URI
MONGO_DB_NAME = "telegram_account_bot"

# System
SESSION_DIR = "data/sessions"

# Ensure session directory exists
os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

# Default timer gap (seconds) between joins
DEFAULT_JOIN_GAP = 2

# View booster fixed gap
VIEW_GAP = 3

# Reaction emoji lists
MIX_EMOJIS = ["👍", "❤️", "🔥", "🎉", "😁", "🤩", "👏", "💯", "🎊", "✨"]
SINGLE_EMOJI = "👍"
