import asyncio
import re
from telethon import events, Button
from utils.name_assigner import load_accounts, save_accounts
from utils.telegram_client import create_client, set_online, set_offline
from utils.stats_tracker import load_stats
from config import API_ID, API_HASH, OWNER_ID, SUDO_USERS
from keyboards.main_keyboard import get_main_keyboard
from keyboards.reaction_keyboard import get_reaction_type_keyboard

# Temporary state
_reaction_flows = {}
_view_flows = {}


def is_authorized(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in SUDO_USERS


async def handle_callback_query(event):
    """Route all button presses."""
    user_id = event.sender_id
    if not is_authorized(user_id):
        await event.answer("⛔ You are not authorised.", alert=True)
        return

    data = event.data.decode()
    print(f"[Callback] User {user_id}: {data}")

    # ── Main Menu ──
    if data == "back_main":
        from keyboards.main_keyboard import get_main_keyboard
        await event.edit(
            "🏠 **Main Menu**\n\nSelect an option below:",
            buttons=get_main_keyboard()
        )
        return

    # ── Help ──
    if data == "help":
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
            "**Adding Accounts**\n"
            "1. Send `/add_account`\n"
            "2. Provide phone number or upload `.session` file\n"
            "3. Enter OTP code + 2FA password if needed\n"
            "4. The bot auto-assigns a name from `name.txt`\n\n"
            "**name.txt**\n"
            "Edit `data/name.txt` with one name per line.\n"
            "The bot automatically assigns the next unused name when adding accounts."
        )
        await event.edit(help_text, buttons=[[Button.inline("🔙 Back", b"back_main")]])
        return

    # ── Stats ──
    if data == "stats":
        accounts = load_accounts()
        stats_data = load_stats()
        total = len(accounts)

        # Count active accounts (those with sessions that authorize)
        active_count = 0
        for acc_id, acc_data in accounts.items():
            session_name = acc_data.get("session", acc_id)
            client = await create_client(session_name, API_ID, API_HASH)
            try:
                await client.connect()
                if await client.is_user_authorized():
                    active_count += 1
            except Exception:
                pass
            finally:
                await client.disconnect()

        # Build per-account channel list
        lines = [f"📊 **Stats**\n", f"Total accounts: **{total}**\nActive: **{active_count}**\n"]
        for acc_id, acc_data in accounts.items():
            name = acc_data.get("name", acc_id)
            joined_chats = stats_data.get(acc_id, [])
            if joined_chats:
                chat_list = "\n".join([f"  • `{c}`" for c in joined_chats[:5]])
                if len(joined_chats) > 5:
                    chat_list += f"\n  • ... and {len(joined_chats)-5} more"
                lines.append(f"\n**{name}** (ID: `{acc_id}`):\n{chat_list}")
            else:
                lines.append(f"\n**{name}** (ID: `{acc_id}`): No joins yet")

        text = "\n".join(lines)
        # Split if too long
        if len(text) > 3500:
            text = text[:3500] + "\n\n... (truncated)"

        await event.edit(text, buttons=[[Button.inline("🔙 Back", b"back_main")]])
        return

    # ── View Booster ──
    if data == "view_booster":
        _view_flows[user_id] = {"step": "awaiting_link"}
        await event.edit(
            "👁️ **View Booster**\n\n"
            "Please send the **post link** you want to boost views on.\n\n"
            "Format: `https://t.me/c/1234567890/123` or `https://t.me/channelname/123`",
            buttons=[[Button.inline("🔙 Cancel", b"cancel_view")]]
        )
        return

    # ── Reactions ──
    if data == "reactions":
        _reaction_flows[user_id] = {"step": "awaiting_link"}
        await event.edit(
            "❤️ **Reactions**\n\n"
            "Please send the **post link** you want to add reactions to.\n\n"
            "Format: `https://t.me/c/1234567890/123` or `https://t.me/channelname/123`",
            buttons=[[Button.inline("🔙 Cancel", b"cancel_reaction")]]
        )
        return

    # ── Health ──
    if data == "health":
        accounts = load_accounts()
        if not accounts:
            await event.edit("❌ No accounts found.", buttons=[[Button.inline("🔙 Back", b"back_main")]])
            return

        await event.edit("🔄 Checking account health...")

        results = []
        for acc_id, acc_data in accounts.items():
            session_name = acc_data.get("session", acc_id)
            name = acc_data.get("name", acc_id)
            client = await create_client(session_name, API_ID, API_HASH)
            status_icon = "❌"
            status_text = "disconnected"
            try:
                await client.connect()
                if await client.is_user_authorized():
                    me = await client.get_me()
                    status_icon = "✅"
                    status_text = f"online (ID: {me.id})"
                else:
                    status_icon = "⚠️"
                    status_text = "not authorized"
            except Exception as e:
                status_icon = "❌"
                status_text = f"error: {str(e)[:30]}"
            finally:
                await client.disconnect()
            results.append(f"{status_icon} **{name}** — {status_text}")

        text = "💚 **Health Report**\n\n" + "\n".join(results)
        await event.edit(text, buttons=[[Button.inline("🔙 Back", b"back_main")]])
        return

    # ── Status Overrides ──
    if data == "all_online":
        accounts = load_accounts()
        if not accounts:
            await event.answer("❌ No accounts.", alert=True)
            return
        await event.edit("🟢 Setting all accounts to **Online**...")
        success = 0
        fail = 0
        for acc_id, acc_data in accounts.items():
            session_name = acc_data.get("session", acc_id)
            client = await create_client(session_name, API_ID, API_HASH)
            try:
                await client.connect()
                if await client.is_user_authorized():
                    await set_online(client)
                    success += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
            finally:
                await client.disconnect()
        await event.edit(
            f"🟢 **All → Online** complete!\n"
            f"Online: {success} | Failed/skipped: {fail}",
            buttons=[[Button.inline("🔙 Back", b"back_main")]]
        )
        return

    if data == "all_last_seen":
        accounts = load_accounts()
        if not accounts:
            await event.answer("❌ No accounts.", alert=True)
            return
        await event.edit("🕒 Setting all accounts to **Last Seen Recently**...")
        success = 0
        fail = 0
        for acc_id, acc_data in accounts.items():
            session_name = acc_data.get("session", acc_id)
            client = await create_client(session_name, API_ID, API_HASH)
            try:
                await client.connect()
                if await client.is_user_authorized():
                    await set_offline(client)  # offline triggers "last seen recently"
                    success += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
            finally:
                await client.disconnect()
        await event.edit(
            f"🕒 **All → Last Seen Recently** complete!\n"
            f"Updated: {success} | Failed/skipped: {fail}",
            buttons=[[Button.inline("🔙 Back", b"back_main")]]
        )
        return

    # ── Reaction Type Selection ──
    if data == "react_mix" or data == "react_single":
        mode = "mix" if data == "react_mix" else "single"
        flow = _reaction_flows.get(user_id)
        if not flow or "link" not in flow:
            await event.answer("Session expired. Start again.", alert=True)
            return

        link = flow["link"]
        await event.edit(f"🔄 Adding **{mode}** reactions to the post...")

        from utils.reaction_engine import run_reactions
        result = await run_reactions(
            API_ID, API_HASH, link, mode,
            single_emoji="👍",
            progress_callback=lambda i, t, s: None  # simplified
        )

        await event.edit(
            f"✅ **Reactions complete!**\n"
            f"Mode: {mode}\n"
            f"Success: {result['success']} | Failed: {result['failed']}",
            buttons=[[Button.inline("🔙 Back", b"back_main")]]
        )
        if user_id in _reaction_flows:
            del _reaction_flows[user_id]
        return

    # ── Timer Selection (from join flow) ──
    if data.startswith("timer_"):
        # Import here to avoid circular imports
        from handlers.join_handlers import handle_timer_selection
        await handle_timer_selection(event)
        return

    # ── Cancel flows ──
    if data == "cancel_join":
        if user_id in _reaction_flows:
            del _reaction_flows[user_id]
        from keyboards.main_keyboard import get_main_keyboard
        await event.edit("❌ Join cancelled.", buttons=get_main_keyboard())
        return

    if data == "cancel_view":
        if user_id in _view_flows:
            del _view_flows[user_id]
        from keyboards.main_keyboard import get_main_keyboard
        await event.edit("❌ View booster cancelled.", buttons=get_main_keyboard())
        return

    if data == "cancel_reaction":
        if user_id in _reaction_flows:
            del _reaction_flows[user_id]
        from keyboards.main_keyboard import get_main_keyboard
        await event.edit("❌ Reactions cancelled.", buttons=get_main_keyboard())
        return

    if data == "cancel_login":
        if user_id in _login_flows_global:
            del _login_flows_global[user_id]
        await event.edit("❌ Login cancelled.", buttons=get_main_keyboard())
        return

    # ── Start Join (from main menu) ──
    if data == "start_join":
        from handlers.join_handlers import handle_start_join
        await handle_start_join(event)
        return

    # ── Upload session ──
    if data == "upload_session":
        await event.edit(
            "📤 **Upload .session file**\n\n"
            "Send me your `.session` file directly.\n"
            "The bot will save it and register the account.",
            buttons=[[Button.inline("🔙 Cancel", b"cancel_login")]]
        )
        return


# Store reference to login flows for cancel
_login_flows_global = {}