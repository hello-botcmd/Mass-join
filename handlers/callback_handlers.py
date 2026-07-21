import asyncio
import re
from telethon import events, Button
from utils.database import get_all_accounts
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

    # ── Main Menu Back ──
    if data == "back_main":
        await event.edit(
            "🏠 **Main Menu**\n\nSelect an option below:",
            buttons=get_main_keyboard()
        )
        return

    # ── Add Account Menu ──
    if data == "add_account_menu":
        from handlers.account_handlers import handle_add_account_menu
        await handle_add_account_menu(event)
        return

    if data == "add_by_phone":
        from handlers.account_handlers import handle_add_by_phone
        await handle_add_by_phone(event)
        return

    if data == "add_by_session":
        from handlers.account_handlers import handle_add_by_session
        await handle_add_by_session(event)
        return

    # ── Help ──
    if data == "help":
        help_text = (
            "❓ **Help — Bot Features**\n\n"
            "**➕ Add Account**\n"
            "Add accounts via Phone+OTP+2FA or session string/file.\n\n"
            "**📋 Start Join**\n"
            "Join a private channel/group with multiple accounts.\n"
            "Set timer gap between joins and randomly distribute online/offline status.\n"
            "Accounts get their assigned name set on Telegram automatically.\n\n"
            "**📊 Stats**\n"
            "View which accounts joined which channels, total accounts, and active count.\n\n"
            "**👁️ View Booster**\n"
            "Increase view count on a post using all accounts (3s fixed gap).\n\n"
            "**❤️ Reactions**\n"
            "Add reactions to a post — Mix (random emojis) or Single (specific emoji).\n\n"
            "**💚 Health**\n"
            "Check which accounts are working vs dead.\n\n"
            "**Status Overrides**\n"
            "• 🟢 All IDs → Online: Force all accounts online (green circle)\n"
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
        await event.edit(help_text, buttons=[[Button.inline("🔙 Back", b"back_main")]])
        return

    # ── Stats ──
    if data == "stats":
        accounts = get_all_accounts()
        stats_data = load_stats()
        total = len(accounts)

        active_count = 0
        for acc_id, acc_data in accounts.items():
            session_string = acc_data.get("session_string", "")
            session_name = acc_data.get("session", acc_id)
            client = await create_client(
                session_string if session_string else session_name,
                API_ID, API_HASH
            )
            try:
                await client.connect()
                if await client.is_user_authorized():
                    active_count += 1
            except Exception:
                pass
            finally:
                await client.disconnect()

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
        if len(text) > 3500:
            text = text[:3500] + "\n\n... (truncated)"

        await event.edit(text, buttons=[[Button.inline("🔙 Back", b"back_main")]])
        return

    # ── View Booster ──
    # ── View Booster ──
    if data == "view_booster":
        _view_flows[user_id] = {"step": "awaiting_link"}
        await event.edit(
            "👁️ **View Booster**\n\n"
            "**IMPORTANT:** All accounts must have already joined the channel "
            "before boosting views.\n\n"
            "Please send the **post link** you want to boost views on.\n\n"
            "Format: `https://t.me/c/1234567890/123` or `https://t.me/channelname/123`\n\n"
            "⚠️ **Note:** Telegram only allows view increment **once per account per day** "
            "per message. Running this multiple times on the same post won't increase views further.",
            buttons=[[Button.inline("🔙 Cancel", b"cancel_view")]]
        )
        return

    # ── Reactions ──
    # ── Reactions ──
    if data == "reactions":
        _reaction_flows[user_id] = {"step": "awaiting_link"}
        await event.edit(
            "❤️ **Reactions**\n\n"
            "**IMPORTANT:** All accounts must have already joined the channel "
            "before adding reactions.\n\n"
            "Please send the **post link** you want to add reactions to.\n\n"
            "Format: `https://t.me/c/1234567890/123` or `https://t.me/channelname/123`",
            buttons=[[Button.inline("🔙 Cancel", b"cancel_reaction")]]
        )
        return

    # ── Health ──
    if data == "health":
        accounts = get_all_accounts()
        if not accounts:
            await event.edit("❌ No accounts found.", buttons=[[Button.inline("🔙 Back", b"back_main")]])
            return

        await event.edit("🔄 Checking account health...\n\nTesting each account session...")

        working = 0
        dead = 0
        results = []

        for acc_id, acc_data in accounts.items():
            session_string = acc_data.get("session_string", "")
            session_name = acc_data.get("session", acc_id)
            name = acc_data.get("name", acc_id)

            client = await create_client(
                session_string if session_string else session_name,
                API_ID, API_HASH
            )

            try:
                await client.connect()
                if await client.is_user_authorized():
                    me = await client.get_me()
                    working += 1
                    results.append(f"✅ **{name}** — Working (ID: {me.id})")
                else:
                    dead += 1
                    results.append(f"❌ **{name}** — Dead (not authorized)")
            except Exception as e:
                dead += 1
                results.append(f"❌ **{name}** — Dead ({str(e)[:30]})")
            finally:
                await client.disconnect()

        text = (
            f"💚 **Health Report**\n\n"
            f"**Working:** {working}\n"
            f"**Dead:** {dead}\n"
            f"**Total:** {len(accounts)}\n\n" +
            "\n".join(results)
        )

        if len(text) > 4000:
            text = text[:4000] + "\n\n... (truncated)"

        await event.edit(text, buttons=[[Button.inline("🔙 Back", b"back_main")]])
        return

    # ── Status Overrides ──
    if data == "all_online":
        accounts = get_all_accounts()
        if not accounts:
            await event.answer("❌ No accounts.", alert=True)
            return

        await event.edit("🟢 Setting all accounts to **Online**...\n\nThis may take a moment...")

        success = 0
        fail = 0
        for acc_id, acc_data in accounts.items():
            session_string = acc_data.get("session_string", "")
            session_name = acc_data.get("session", acc_id)
            name = acc_data.get("name", acc_id)

            client = await create_client(
                session_string if session_string else session_name,
                API_ID, API_HASH
            )
            try:
                await client.connect()
                if await client.is_user_authorized():
                    result = await set_online(client)
                    if result:
                        success += 1
                    else:
                        fail += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
            finally:
                await client.disconnect()

        await event.edit(
            f"🟢 **All → Online** complete!\n"
            f"✅ Online: {success}\n"
            f"❌ Failed: {fail}\n"
            f"Total: {success + fail}",
            buttons=[[Button.inline("🔙 Back", b"back_main")]]
        )
        return

    if data == "all_last_seen":
        accounts = get_all_accounts()
        if not accounts:
            await event.answer("❌ No accounts.", alert=True)
            return

        await event.edit("🕒 Setting all accounts to **Last Seen Recently**...\n\nThis may take a moment...")

        success = 0
        fail = 0
        for acc_id, acc_data in accounts.items():
            session_string = acc_data.get("session_string", "")
            session_name = acc_data.get("session", acc_id)
            name = acc_data.get("name", acc_id)

            client = await create_client(
                session_string if session_string else session_name,
                API_ID, API_HASH
            )
            try:
                await client.connect()
                if await client.is_user_authorized():
                    result = await set_offline(client)
                    if result:
                        success += 1
                    else:
                        fail += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
            finally:
                await client.disconnect()

        await event.edit(
            f"🕒 **All → Last Seen Recently** complete!\n"
            f"✅ Updated: {success}\n"
            f"❌ Failed: {fail}\n"
            f"Total: {success + fail}",
            buttons=[[Button.inline("🔙 Back", b"back_main")]]
        )
        return

    # ── Reaction Type Selection ──
    # ── Reaction Type Selection ──
    if data in ("react_mix", "react_single"):
        mode = "mix" if data == "react_mix" else "single"
        flow = _reaction_flows.get(user_id)
        if not flow or "link" not in flow:
            await event.answer("Session expired. Start again.", alert=True)
            return

        link = flow["link"]
        progress_msg = await event.edit(f"🔄 Adding **{mode}** reactions to the post...\n\nStarting...")

        from utils.reaction_engine import run_reactions

        async def progress_callback(idx, total, status):
            try:
                await progress_msg.edit(
                    f"🔄 Adding reactions... **{idx}/{total}**\n"
                    f"Last: {status}"
                )
            except Exception:
                pass

        result = await run_reactions(
            API_ID, API_HASH, link, mode,
            single_emoji="👍",
            progress_callback=progress_callback
        )

        summary_parts = [
            f"✅ **Reactions complete!**\n",
            f"✅ Success: {result['success']}",
            f"❌ Failed: {result['failed']}",
        ]
        if result.get('not_member'):
            summary_parts.append(f"👤 Not channel member: {result['not_member']}")
        if result.get('flood_wait'):
            summary_parts.append(f"⏳ Flood wait: {result['flood_wait']}")

        await progress_msg.edit(
            "\n".join(summary_parts),
            buttons=[[Button.inline("🔙 Back", b"back_main")]]
        )
        if user_id in _reaction_flows:
            del _reaction_flows[user_id]
        return

    # ── Timer Selection (from join flow) ──
    if data.startswith("timer_"):
        from handlers.join_handlers import handle_timer_selection
        await handle_timer_selection(event)
        return

    # ── Start Join (from main menu) ──
    if data == "start_join":
        from handlers.join_handlers import handle_start_join
        await handle_start_join(event)
        return

    # ── Cancel flows ──
    if data == "cancel_join":
        if user_id in _reaction_flows:
            del _reaction_flows[user_id]
        await event.edit("❌ Join cancelled.", buttons=get_main_keyboard())
        return

    if data == "cancel_view":
        if user_id in _view_flows:
            del _view_flows[user_id]
        await event.edit("❌ View booster cancelled.", buttons=get_main_keyboard())
        return

    if data == "cancel_reaction":
        if user_id in _reaction_flows:
            del _reaction_flows[user_id]
        await event.edit("❌ Reactions cancelled.", buttons=get_main_keyboard())
        return

    if data == "cancel_login":
        from handlers.account_handlers import _login_flows
        if user_id in _login_flows:
            del _login_flows[user_id]
        await event.edit("❌ Login cancelled.", buttons=get_main_keyboard())
        return
