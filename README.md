# Telegram Account Manager Bot

Manage multiple Telegram accounts: join channels, boost views, add reactions, and control online status — all from one bot.

## Features

- **Add Accounts** via phone + OTP + 2FA, or by uploading `.session` files
- **Auto-naming** from `name.txt` — assign names to accounts automatically
- **Join Private Channels/Groups** with configurable timer gaps (1s, 2s, 5s, 10s)
- **Random Status Distribution** — randomly assign "online", "offline after 2min", or "last seen recently"
- **View Booster** — increment post views with all accounts (3s fixed gap)
- **Reactions** — add Mix (random emojis) or Single (fixed emoji) reactions
- **Status Overrides** — force all accounts online or to "last seen recently"
- **Stats & Health** — view account activity and check session validity
- **Access Control** — owner + sudo users only
- **Remove from Chat** — remove all added accounts from a specific chat

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt