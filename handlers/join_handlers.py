import asyncio
import random
from telethon import events, Button
from utils.telegram_client import create_client, join_private_channel, set_online, set_offline, change_account_name, get_session_string
from utils.database import get_all_accounts, save_account, get_session_string as get_db_session
from utils.stats_tracker import record_join
from utils.status_manager import random_distribution, apply_status
from config import API_ID, API_HASH

_join_flows = {}


async def handle_start_join(event):
    """Start the join flow — ask for invite link."""
    user_id = event.sender_id
    accounts = get_all_accounts()
    if not accounts:
        await event.answer("❌ No accounts added yet. Add accounts first!", alert=True)
        return

    _join_flows[user_id] = {
        "step": "awaiting_link",
        "accounts": accounts,
        "account_ids": list(accounts.keys())
    }

    await event.reply(
        "📋 **Start Join**\n\n"
        f"Total accounts available: **{len(accounts)}**\n\n"
        "Please send the **invite link** for the private channel/group.\n"
        "Example: `https://t.me/joinchat/AAAAAFFszQPyPEZ7wgxLtd`\n"
        "Or: `https://t.me/+abc123xyz`",
        buttons=[[Button.inline("🔙 Cancel", b"cancel_join")]]
    )


async def handle_join_link(event):
    """Receive the invite link, ask for timer gap."""
    user_id = event.sender_id
    link = event.message.text.strip()

    if user_id not in _join_flows:
        return

    _join_flows[user_id]["link"] = link
    _join_flows[user_id]["step"] = "awaiting_timer"

    from keyboards.timer_keyboard import get_timer_keyboard
    await event.reply(
        "⏱ **Select Timer Gap**\n\n"
        "Choose the delay between joining each account:",
        buttons=get_timer_keyboard()
    )


async def handle_timer_selection(event):
    """Receive timer gap selection, ask for status distribution counts."""
    user_id = event.sender_id
    data = event.data.decode()

    gap_map = {
        "timer_1": 1,
        "timer_2": 2,
        "timer_5": 5,
        "timer_10": 10,
    }
    gap = gap_map.get(data, 2)

    if user_id not in _join_flows:
        await event.answer("Session expired.", alert=True)
        return

    _join_flows[user_id]["gap"] = gap
    _join_flows[user_id]["step"] = "awaiting_online_count"

    total = len(_join_flows[user_id]["account_ids"])
    await event.reply(
        f"⏱ Gap set to **{gap}s**\n\n"
        "Now let's configure the **status distribution**.\n\n"
        f"Total accounts: **{total}**\n\n"
        "**How many accounts should remain fully online?**\n"
        "Send a number (e.g., `20`)",
        buttons=[[Button.inline("🔙 Cancel", b"cancel_join")]]
    )


async def handle_online_count(event):
    """Receive online count, ask for offline_2min count."""
    user_id = event.sender_id
    text = event.message.text.strip()

    if user_id not in _join_flows or _join_flows[user_id].get("step") != "awaiting_online_count":
        return

    try:
        count = int(text)
    except ValueError:
        await event.reply("❌ Please send a valid number.")
        return

    total = len(_join_flows[user_id]["account_ids"])
    if count < 0 or count > total:
        await event.reply(f"❌ Number must be between 0 and {total}.")
        return

    _join_flows[user_id]["online_count"] = count
    _join_flows[user_id]["step"] = "awaiting_offline_2min_count"

    remaining = total - count
    await event.reply(
        f"✅ **{count}** accounts will stay online.\n\n"
        f"**How many should go offline 2 minutes after joining?**\n"
        f"Send a number (remaining: {remaining})",
        buttons=[[Button.inline("🔙 Cancel", b"cancel_join")]]
    )


async def handle_offline_2min_count(event):
    """Receive offline_2min count, ask for last_seen count."""
    user_id = event.sender_id
    text = event.message.text.strip()

    if user_id not in _join_flows or _join_flows[user_id].get("step") != "awaiting_offline_2min_count":
        return

    try:
        count = int(text)
    except ValueError:
        await event.reply("❌ Please send a valid number.")
        return

    total = len(_join_flows[user_id]["account_ids"])
    used = _join_flows[user_id].get("online_count", 0)
    remaining = total - used

    if count < 0 or count > remaining:
        await event.reply(f"❌ Number must be between 0 and {remaining}.")
        return

    _join_flows[user_id]["offline_2min_count"] = count
    _join_flows[user_id]["step"] = "awaiting_last_seen_count"

    remaining2 = remaining - count
    await event.reply(
        f"✅ **{count}** accounts will go offline after 2 minutes.\n\n"
        f"**How many should show 'last seen recently'?**\n"
        f"Send a number (remaining: {remaining2})",
        buttons=[[Button.inline("🔙 Cancel", b"cancel_join")]]
    )


async def handle_last_seen_count(event):
    """Receive last_seen count, then begin the join process."""
    user_id = event.sender_id
    text = event.message.text.strip()

    if user_id not in _join_flows or _join_flows[user_id].get("step") != "awaiting_last_seen_count":
        return

    try:
        count = int(text)
    except ValueError:
        await event.reply("❌ Please send a valid number.")
        return

    total = len(_join_flows[user_id]["account_ids"])
    used = _join_flows[user_id].get("online_count", 0) + _join_flows[user_id].get("offline_2min_count", 0)
    remaining = total - used

    if count < 0 or count > remaining:
        count = remaining

    flow = _join_flows[user_id]
    flow["last_seen_count"] = count

    status_map = random_distribution(
        flow["account_ids"],
        flow["online_count"],
        flow["offline_2min_count"],
        flow["last_seen_count"]
    )

    link = flow["link"]
    gap = flow["gap"]

    progress_msg = await event.reply(
        f"🚀 **Starting join process...**\n"
        f"Channel: `{link}`\n"
        f"Accounts: {total}\n"
        f"Gap: {gap}s\n"
        f"Online: {flow['online_count']} | Offline 2min: {flow['offline_2min_count']} | Last seen: {flow['last_seen_count']}\n\n"
        f"🔄 Starting..."
    )

    account_ids = flow["account_ids"].copy()
    random.shuffle(account_ids)

    success_count = 0
    fail_count = 0

    for i, account_id in enumerate(account_ids):
        account_data = flow["accounts"].get(account_id, {})
        account_name = account_data.get("name", account_id)

        # Get session string from DB (accounts may have been updated)
        session_string = get_db_session(account_id)
        session_name = account_data.get("session", account_id)

        client = await create_client(
            session_string if session_string else session_name,
            API_ID, API_HASH
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                fail_count += 1
                await progress_msg.edit(
                    f"🚀 Joining... **{i+1}/{total}**\n"
                    f"✅ Success: {success_count} | ❌ Failed: {fail_count}\n"
                    f"➡️ {account_name} — not authorized, skipped."
                )
                await client.disconnect()
                continue

            # ── STEP 1: Change the account's display name on Telegram ──
            name_changed = await change_account_name(client, account_name)
            if name_changed:
                name_status = "name set ✓"
            else:
                name_status = "name failed"

            # ── STEP 2: Join the channel ──
            joined = await join_private_channel(client, link)

            if joined:
                success_count += 1
                record_join(account_id, link)

                # Save the session string after a successful join for future use
                try:
                    ss = await get_session_string(client)
                    save_account(account_id, {**account_data, "session_string": ss})
                except Exception:
                    pass

                # Apply status
                status = status_map.get(account_id, "last_seen_recently")
                await apply_status(client, status)
            else:
                fail_count += 1

            await progress_msg.edit(
                f"🚀 Joining... **{i+1}/{total}**\n"
                f"✅ Success: {success_count} | ❌ Failed: {fail_count}\n"
                f"➡️ {account_name} — {'✓ joined, ' + name_status if joined else '✗ failed'}"
            )

            # Handle offline_2min: schedule going offline after 2 minutes
            if joined and status_map.get(account_id) == "offline_2min":
                asyncio.create_task(
                    _delayed_set_offline(
                        account_id, account_data, account_name, 120
                    )
                )

        except Exception as e:
            fail_count += 1
            await progress_msg.edit(
                f"🚀 Joining... **{i+1}/{total}**\n"
                f"✅ Success: {success_count} | ❌ Failed: {fail_count}\n"
                f"➡️ {account_name} — ✗ error: {str(e)[:40]}"
            )
        finally:
            await client.disconnect()

        if i < total - 1:
            await asyncio.sleep(gap)

    await progress_msg.edit(
        f"✅ **Join complete!**\n"
        f"Successfully joined: **{success_count}**\n"
        f"Failed: **{fail_count}**\n"
        f"Total: **{total}**"
    )

    del _join_flows[user_id]


async def _delayed_set_offline(account_id: str, account_data: dict, account_name: str, delay: int):
    """Set an account offline after a delay."""
    await asyncio.sleep(delay)
    session_string = get_db_session(account_id)
    session_name = account_data.get("session", account_id)

    client = await create_client(
        session_string if session_string else session_name,
        API_ID, API_HASH
    )
    try:
        await client.connect()
        if await client.is_user_authorized():
            await set_offline(client)
    except Exception:
        pass
    finally:
        await client.disconnect()
