import os
import json
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession
from utils.name_assigner import load_accounts, save_accounts, get_next_name
from config import SESSION_DIR, API_ID, API_HASH

# Temporary storage for login flows
_login_flows = {}


async def handle_add_account_command(event):
    """Handle /add_account command — delegates to the button menu."""
    from keyboards.main_keyboard import get_add_account_keyboard
    await event.reply(
        "➕ **Add Account**\n\n"
        "Choose how you want to add an account:",
        buttons=get_add_account_keyboard()
    )


async def handle_add_account_menu(event):
    """Show the add-account sub-menu with two options."""
    from keyboards.main_keyboard import get_add_account_keyboard
    await event.edit(
        "➕ **Add Account**\n\n"
        "Choose how you want to add an account:",
        buttons=get_add_account_keyboard()
    )


async def handle_add_by_phone(event):
    """Start the phone-based login flow."""
    user_id = event.sender_id
    _login_flows[user_id] = {"step": "awaiting_phone"}
    await event.edit(
        "📱 **Add by Phone**\n\n"
        "Send me the phone number in international format.\n"
        "Example: `+1234567890`\n\n"
        "I'll send an OTP code and ask for your 2FA password if needed.",
        buttons=[[Button.inline("🔙 Cancel", b"cancel_login")]]
    )


async def handle_add_by_session(event):
    """Show the session string/file sub-menu."""
    user_id = event.sender_id
    _login_flows[user_id] = {"step": "awaiting_session"}
    await event.edit(
        "🔑 **Add by Session**\n\n"
        "You can either:\n\n"
        "1. **Upload a `.session` file** — send the file directly\n"
        "2. **Paste a session string** — copy & paste the base64 string\n\n"
        "Send the file or paste the string now.",
        buttons=[[Button.inline("🔙 Cancel", b"cancel_login")]]
    )


async def handle_phone_input(event):
    """Receive phone number and send OTP code request."""
    user_id = event.sender_id
    phone = event.message.text.strip()

    session_name = f"temp_{user_id}_{phone.replace('+', '')}"
    client = TelegramClient(os.path.join(SESSION_DIR, session_name), API_ID, API_HASH)
    await client.connect()

    try:
        if await client.is_user_authorized():
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
            if user_id in _login_flows:
                del _login_flows[user_id]
            return

        await client.send_code_request(phone)
        _login_flows[user_id].update({
            "phone": phone,
            "session_name": session_name,
            "client": client,
            "step": "awaiting_code"
        })

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
        await event.reply("❌ Session expired. Please start again.")
        return

    try:
        await client.sign_in(phone, code)
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
        _login_flows[user_id]["step"] = "awaiting_2fa"
        await event.reply("🔐 **2FA Required**\n\nPlease send your 2FA password.")
        return
    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")
        if "code" in str(e).lower() or "invalid" in str(e).lower():
            await event.reply("Try again with the correct code, or restart with the button.")
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
    """Handle .session file upload."""
    user_id = event.sender_id

    if not event.message.file or not event.message.file.name:
        await event.reply("❌ Please upload a `.session` file.")
        return

    if not event.message.file.name.endswith(".session"):
        await event.reply("❌ File must have `.session` extension.")
        return

    file_name = event.message.file.name
    destination = os.path.join(SESSION_DIR, file_name)
    await event.message.download_media(destination)

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
        if user_id in _login_flows:
            del _login_flows[user_id]


async def handle_session_string_input(event):
    """
    Handle a base64 session string pasted by the user.
    Saves it as a .session file and registers the account.
    """
    user_id = event.sender_id
    session_string = event.message.text.strip()

    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            await event.reply("❌ The session string is not authorized (invalid or expired).")
            await client.disconnect()
            return

        me = await client.get_me()
        account_id = str(me.id)
        name = get_next_name()

        # Save the string session to a file for persistence
        session_file_name = f"string_{account_id}"
        saved_session_string = client.session.save()
        session_file_path = os.path.join(SESSION_DIR, session_file_name + ".session")

        accounts = load_accounts()
        accounts[account_id] = {
            "name": name,
            "phone": getattr(me, "phone", "unknown"),
            "session": session_file_name,
            "session_string": saved_session_string,
            "status": "active"
        }
        save_accounts(accounts)

        with open(session_file_path, "w") as f:
            f.write(saved_session_string)

        await event.reply(f"✅ Account **{name}** (ID: `{account_id}`) added from session string!")

    except Exception as e:
        await event.reply(f"❌ Invalid session string: {str(e)}")
    finally:
        await client.disconnect()
        if user_id in _login_flows:
            del _login_flows[user_id]
