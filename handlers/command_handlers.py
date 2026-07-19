import re
from telethon import events, Button
from keyboards.main_keyboard import get_main_keyboard
from utils.name_assigner import load_accounts, save_accounts
from utils.stats_tracker import load_stats, save_stats
from config import OWNER_ID, SUDO_USERS


def is_authorized(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in SUDO_USERS


async def handle_start(event):
    """Welcome message with main menu."""
    if not is_authorized(event.sender_id):
        await event.reply("⛔ You are not authorised to use this bot.")
        return

    await event.reply(
        "🤖 **Telegram Account Manager Bot**\n\n"
        "Welcome! I manage multiple Telegram accounts.\n"
        "Use the buttons below or type commands.\n\n"
        "📌 **First time?**\n"
        "1. Run `/add_account` to add your first account\n"
        "2. Edit `data/name.txt` with names\n"
        "3. Use **📋 Start Join** to join a channel\n",
        buttons=get_main_keyboard()
    )


async def handle_help(event):
    """Send help message."""
    if not is_authorized(event.sender_id):
        await event.reply("⛔ You are not authorised.")
        return

    help_text = (
        "❓ **Help — Bot Features**\n\n"
        "**📋 Start Join**\n"
        "Join a private channel/group with multiple accounts.\n"
        "You can set a timer gap between joins and randomly distribute online/offline status.\n\n"
        "**📊 Stats**\n"
        "View which accounts joined which channels, total accounts, and active count.\n\n"
        "**👁️ View Booster**\n"
        "Increase view count on a post using all accounts (3s fixed gap).\n\n"
        "**❤️ Reactions**\n"
        "Add reactions to a post — Mix (random emojis) or Single (specific emoji).\n\n"
        "**💚 Health**\n"
        "Check which accounts are working and their current status.\n\n"
        "**Status Overrides**\n"
        "• 🟢 All IDs → Online: Force all accounts online\n"
        "• 🕒 All IDs → Last Seen Recently: Force all accounts to show 'last seen recently'\n\n"
        "**Commands**\n"
        "• `/add_account` — Add a new Telegram account\n"
        "• `/remove(chatid)` — Remove all accounts from a specific chat\n"
        "• `/start` — Show main menu\n\n"
        "**name.txt**\n"
        "Edit `data/name.txt` with one name per line.\n"
        "The bot auto-assigns the next unused name when adding accounts."
    )
    await event.reply(help_text, buttons=get_main_keyboard())


async def handle_remove(event):
    """
    /remove(chatid) — Remove all accounts from a specific chat.
    Usage: /remove(-1001234567890)  or  /remove @channelusername
    """
    if not is_authorized(event.sender_id):
        await event.reply("⛔ You are not authorised.")
        return

    text = event.message.text.strip()
    # Extract chat ID from parentheses or after /remove
    match = re.search(r"/remove[\(\s]*(.+?)[\)\s]*$", text)
    if not match:
        await event.reply(
            "❌ Usage: `/remove(chatid)` or `/remove @channelusername`\n"
            "Example: `/remove(-1001234567890)`"
        )
        return

    chat_identifier = match.group(1).strip()
    await event.reply(f"🔄 Removing accounts from `{chat_identifier}`...")

    accounts = load_accounts()
    stats = load_stats()
    removed_count = 0

    # We use the stats to find which accounts joined this chat
    # For each account that joined this chat, we try to leave
    from utils.telegram_client import create_client
    from telethon.tl.functions.channels import LeaveChannelRequest
    from config import API_ID, API_HASH

    for acc_id, acc_data in accounts.items():
        joined_chats = stats.get(acc_id, [])
        if chat_identifier not in joined_chats:
            continue

        session_name = acc_data.get("session", acc_id)
        client = await create_client(session_name, API_ID, API_HASH)
        try:
            await client.connect()
            if await client.is_user_authorized():
                # Resolve the chat
                try:
                    entity = await client.get_entity(chat_identifier)
                    await client(LeaveChannelRequest(entity))
                    removed_count += 1
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            await client.disconnect()

    # Update stats: remove that chat from all accounts
    for acc_id in stats:
        if chat_identifier in stats[acc_id]:
            stats[acc_id].remove(chat_identifier)
    save_stats(stats)

    await event.reply(
        f"✅ Removed **{removed_count}** accounts from `{chat_identifier}`.\n"
        f"Stats updated.",
        buttons=get_main_keyboard()
    )