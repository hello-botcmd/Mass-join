import os

# Your API credentials from my.telegram.org
API_ID = 123456789          # <-- REPLACE WITH YOUR API_ID
API_HASH = "your_api_hash_here"  # <-- REPLACE WITH YOUR API_HASH
BOT_TOKEN = "your_bot_token_here"  # <-- REPLACE WITH YOUR BOT_TOKEN

# Owner Telegram User ID (numerical) — the bot's master
OWNER_ID = 1234567890       # <-- REPLACE WITH YOUR OWNER ID

# Additional sudo users who can operate the bot
SUDO_USERS = [
    1234567891,              # <-- REPLACE with actual sudo user IDs
    1234567892,
]

# System
SESSION_DIR = "data/sessions"
ACCOUNTS_FILE = "data/accounts.json"
STATS_FILE = "data/stats.json"
NAME_FILE = "data/name.txt"

# Ensure data directories exist
os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

# Default timer gap (seconds) between joins
DEFAULT_JOIN_GAP = 2

# View booster fixed gap
VIEW_GAP = 3

# Reaction emoji lists
MIX_EMOJIS = ["👍", "❤️", "🔥", "🎉", "😁", "🤩", "👏", "💯", "🎊", "✨"]
SINGLE_EMOJI = "👍"
