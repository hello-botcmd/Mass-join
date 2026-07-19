import os
import json
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from utils.name_assigner import load_accounts, save_accounts, get_next_name
from config import SESSION_DIR, API_ID, API_HASH

# Temporary storage for login flows
_login_flows = {}


async def handle_add_account_command(event):
    """Handler for /add_account command."""
    user_id = event.sender_id
    if user_id not in _login_flows:
        _login_flows[user_id] = {}

    await event.reply(
        "📱 **Add Account**\n\n"
        "Send me the phone number (international format, e.g., +1234567890)\n"
        "Or upload a `.session` file if you already have one.",
        buttons=[
            [Button.inline("📤 Upload .session file", b"upload_session")]
        ]
    )
    _login_flows[user_id]["step"] = "awaiting_phone"


async def handle_phone_input(event):
    """Receive phone number and send OTP code request."""
    user_id = event.sender_id
    phone = event.message.text.strip()

    # Create a temporary client for this login
    session_name = f"temp_{user_id}_{phone.replace('+', '')}"
    client = TelegramClient(os.path.join(SESSION_DIR, session_name), API_ID, API_HASH)
    await client.connect()

    try:
        if await client.is_user_authorized():
            # Already authorized — save as a new account
            me = await client.get_me()
            account_id = str(me.id)
            name = get_next_name()
            accounts = load_accounts()
            accounts[account_id] = {
                "name": name,
                "phone": phone,
                "session": session_name,
                "status": "active"
            }
            save_accounts(accounts)
            await event.reply(f"✅ Account **{name}** (ID: `{account_id}`) already had an active session and has been added!")
            await client.disconnect()
            return

        # Send code request
        await client.send_code_request(phone)
        _login_flows[user_id]["phone"] = phone
        _login_flows[user_id]["session_name"] = session_name
        _login_flows[user_id]["client"] = client
        _login_flows[user_id]["step"] = "awaiting_code"

        await event.reply(
            f"📱 Code sent to `{phone}`\n\n"
            "Please reply with the OTP code you received.\n"
            "If you have 2FA enabled, just send the code first, then I'll ask for your 2FA password.",
            buttons=[[Button.inline("🔙 Cancel", b"cancel_login")]]
        )

    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")
        await client.disconnect()
        if user_id in _login_flows:
            del _login_flows[user_id]


async def handle_code_input(event):
    """Receive OTP code and attempt sign in."""
    user_id = event.sender_id
    code = event.message.text.strip()

    flow = _login_flows.get(user_id, {})
    if not flow or flow.get("step") != "awaiting_code":
        return

    client = flow.get("client")
    phone = flow.get("phone")
    session_name = flow.get("session_name")

    if not client:
        await event.reply("❌ Session expired. Please start over with /add_account.")
        return

    try:
        await client.sign_in(phone, code)
        # Success — no 2FA needed
        me = await client.get_me()
        account_id = str(me.id)
        name = get_next_name()
        accounts = load_accounts()
        accounts[account_id] = {
            "name": name,
            "phone": phone,
            "session": session_name,
            "status": "active"
        }
        save_accounts(accounts)
        await event.reply(f"✅ Account **{name}** (ID: `{account_id}`) added successfully!")
        del _login_flows[user_id]

    except SessionPasswordNeededError:
        # 2FA required
        _login_flows[user_id]["step"] = "awaiting_2fa"
        await event.reply("🔐 **2FA Required**\n\nPlease send your 2FA password.")
        return
    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")
        if "code" in str(e).lower() or "invalid" in str(e).lower():
            await event.reply("Try again with the correct code, or use /add_account to restart.")
        else:
            del _login_flows[user_id]
            await client.disconnect()


async def handle_2fa_input(event):
    """Receive 2FA password and complete login."""
    user_id = event.sender_id
    password = event.message.text.strip()

    flow = _login_flows.get(user_id, {})
    if not flow or flow.get("step") != "awaiting_2fa":
        return

    client = flow.get("client")
    phone = flow.get("phone")
    session_name = flow.get("session_name")

    try:
        await client.sign_in(password=password)
        me = await client.get_me()
        account_id = str(me.id)
        name = get_next_name()
        accounts = load_accounts()
        accounts[account_id] = {
            "name": name,
            "phone": phone,
            "session": session_name,
            "status": "active"
        }
        save_accounts(accounts)
        await event.reply(f"✅ Account **{name}** (ID: `{account_id}`) added successfully with 2FA!")
    except Exception as e:
        await event.reply(f"❌ 2FA Error: {str(e)}")
        return
    finally:
        del _login_flows[user_id]
        await client.disconnect()


async def handle_session_file_upload(event):
    """
    Handle .session file upload.
    The bot receives the file, saves it to SESSION_DIR,
    then tries to connect and register the account.
    """
    user_id = event.sender_id
    if not event.message.file or not event.message.file.name:
        await event.reply("❌ Please upload a `.session` file.")
        return

    if not event.message.file.name.endswith(".session"):
        await event.reply("❌ File must have `.session` extension.")
        return

    # Download the file
    file_name = event.message.file.name
    destination = os.path.join(SESSION_DIR, file_name)
    await event.message.download_media(destination)

    # Try to connect with the session
    client = TelegramClient(destination, API_ID, API_HASH)
    try:
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            account_id = str(me.id)
            name = get_next_name()
            accounts = load_accounts()
            accounts[account_id] = {
                "name": name,
                "phone": getattr(me, "phone", "unknown"),
                "session": file_name.replace(".session", ""),
                "status": "active"
            }
            save_accounts(accounts)
            await event.reply(f"✅ Account **{name}** (ID: `{account_id}`) added from session file!")
        else:
            await event.reply("❌ The session file is not authorized. Please upload a valid .session file.")
            os.remove(destination)
    except Exception as e:
        await event.reply(f"❌ Error loading session: {str(e)}")
        if os.path.exists(destination):
            os.remove(destination)
    finally:
        await client.disconnect()