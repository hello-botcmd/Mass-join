import os

# Your API credentials from my.telegram.org
API_ID = 37927665      # <-- REPLACE
API_HASH = "6cc390ad7fdf473b9c5df526acfa18e0"  # <-- REPLACE
BOT_TOKEN = "8886273263:AAHWQ3wWvNskeXoybSuc8X_Fod9IhiUwdrU"  # <-- REPLACE

# Owner Telegram User ID
OWNER_ID = 8580367479   # <-- REPLACE

# Additional sudo users
SUDO_USERS = [8694029886
]

# ── MongoDB ──
MONGO_URI = "mongodb+srv://nexacoders2_db_user:dxYh7QOdHvH6OVdd@cluster0.f4qxcbk.mongodb.net/?appName=Cluster0"   # or your MongoDB Atlas URI
MONGO_DB_NAME = "eryx"

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
