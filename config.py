import os

# Your API credentials from my.telegram.org
API_ID = 37927665          # <-- REPLACE WITH YOUR API_ID
API_HASH = "6cc390ad7fdf473b9c5df526acfa18e0"  # <-- REPLACE WITH YOUR API_HASH
BOT_TOKEN = "8886273263:AAHWQ3wWvNskeXoybSuc8X_Fod9IhiUwdrU"  # <-- REPLACE WITH YOUR BOT_TOKEN

# Owner Telegram User ID (numerical) — the bot's master
OWNER_ID = 8694029886       # <-- REPLACE WITH YOUR OWNER ID

# Additional sudo users who can operate the bot
SUDO_USERS = [
    8694029886,              # <-- REPLACE with actual sudo user IDs
    8580367479,
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
