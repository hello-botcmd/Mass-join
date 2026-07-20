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
        "📌 **Quick Start**\n"
        "1. Click **➕ Add Account** to add your first account\n"
        "2. Edit `data/name.txt` with names\n"
        "3. Use **📋 Start Join** to join a channel\n"
        "4. Use **👁️ View Booster** or **❤️ Reactions** on posts\n",
        buttons=get_main_keyboard()
    )


async def handle_help(event):
    """Send detailed help message."""
    if not is_authorized(event.sender_id):
        await event.reply("⛔ You are not authorised.")
        return

    help_text = (
        "❓ **Help — Bot Features**\n\n"
        "**➕ Add Account**\n"
        "Add accounts via Phone+OTP+2FA or session string/file.\n\n"
        "**📋 Start Join**\n"
        "Join a private channel/group with multiple accounts.\n"
        "Set a timer gap between joins and randomly distribute online/offline status.\n\n"
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
        "• `/remove(chatid)` — Remove all accounts from a specific chat\n"
        "• `/start` — Show main menu\n\n"
        "**Adding Accounts**\n"
        "1. Click **➕ Add Account** button\n"
        "2. Choose **Phone + OTP + 2FA** or **Session String / File**\n"
        "3. Follow the prompts\n"
        "4. The bot auto-assigns a name from `name.txt`\n\n"
        "**name.txt**\n"
        "Edit `data/name.txt` with one name per line.\n"
        "The bot automatically assigns the next unused name when adding accounts."
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
    match = re.search(r"/remove[\(\s]*(.+?)[\)\s]*$", text)
    if not match:
        await event.reply(
            "❌ Usage: `/remove(chatid)` or `/remove @channelusername`\n"
            "Example: `/remove(-1001234567890)`"
        )
        return

    chat_identifier = match.group(1).strip()
    await event.reply(f"🔄 Removing all accounts from `{chat_identifier}`...")

    from utils.database import get_all_accounts
    from utils.telegram_client import create_client, leave_channel
    from utils.stats_tracker import remove_chat_from_all_accounts
    from config import API_ID, API_HASH

    accounts = get_all_accounts()
    removed_count = 0
    fail_count = 0
    total = len(accounts)

    progress_msg = await event.reply(f"🔄 Starting removal from `{chat_identifier}`... **0/{total}**")

    for i, (acc_id, acc_data) in enumerate(accounts.items()):
        session_string = acc_data.get("session_string", "")
        session_name = acc_data.get("session", acc_id)
        account_name = acc_data.get("name", acc_id)

        client = await create_client(
            session_string if session_string else session_name,
            API_ID, API_HASH
        )

        try:
            await client.connect()
            if await client.is_user_authorized():
                result = await leave_channel(client, chat_identifier)
                if result:
                    removed_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1
        except Exception:
            fail_count += 1
        finally:
            await client.disconnect()

        if (i + 1) % 5 == 0 or i == total - 1:
            try:
                await progress_msg.edit(
                    f"🔄 Removing... **{i+1}/{total}**\n"
                    f"✅ Left: {removed_count} | ❌ Failed: {fail_count}"
                )
            except Exception:
                pass

    # Clean up stats
    remove_chat_from_all_accounts(chat_identifier)

    await progress_msg.edit(
        f"✅ **Removal complete!**\n"
        f"Accounts removed: **{removed_count}**\n"
        f"Failed: **{fail_count}**\n"
        f"Chat: `{chat_identifier}`\n"
        f"Stats cleaned up."
    )
