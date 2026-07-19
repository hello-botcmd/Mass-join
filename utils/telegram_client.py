import os
import asyncio
from telethon import TelegramClient, functions, types
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, GetMessagesViewsRequest, SendReactionRequest

SESSION_DIR = "data/sessions"


async def create_client(session_name: str, api_id: int, api_hash: str) -> TelegramClient:
    session_path = os.path.join(SESSION_DIR, session_name)
    client = TelegramClient(session_path, api_id, api_hash)
    return client


async def login_with_password(client: TelegramClient, phone: str, password: str) -> bool:
    """
    Login using only phone + 2FA password (no OTP).
    If the account already has an active session file, just connect.
    Otherwise send code & login with 2FA.
    """
    await client.connect()
    if await client.is_user_authorized():
        return True

    try:
        # Send code request
        await client.send_code_request(phone)
        # Sign in with 2FA password only (no OTP code — works if no OTP is actually required)
        # Telethon requires a code; if the account doesn't need OTP sometimes this works.
        # Realistically, you need to provide the OTP code. This flow expects
        # the user to provide the code that Telegram sends. For "no OTP" mode,
        # we handle it by reading an existing .session file instead.
        # For ID + 2FA without OTP, try signing in with an empty code + 2FA.
        try:
            await client.sign_in(phone, code="", password=password)
        except Exception:
            # If that fails, we need the code — so this method requires OTP.
            # The .session file upload method is the real "no OTP" way.
            return False
        return True
    except SessionPasswordNeededError:
        # 2FA needed; we already provided it above, but if we get here:
        await client.sign_in(password=password)
        return True
    except Exception as e:
        # Likely needs OTP code
        return False


async def login_with_session(client: TelegramClient) -> bool:
    """Login using an already-existing session file."""
    await client.connect()
    return await client.is_user_authorized()


async def join_private_channel(client: TelegramClient, invite_link: str) -> bool:
    """
    Join a private channel/group using an invite link.
    Supports both t.me/joinchat/... and t.me/+... formats.
    """
    try:
        # Extract the hash
        if "joinchat/" in invite_link:
            hash_part = invite_link.split("joinchat/")[-1].split("?")[0]
        elif "/+" in invite_link:
            hash_part = invite_link.split("/+")[-1].split("?")[0]
        else:
            # Try as a public username
            username = invite_link.strip().lstrip("https://t.me/").lstrip("@")
            channel = await client.get_entity(username)
            await client(JoinChannelRequest(channel))
            return True

        # Remove leading "+" if present
        hash_part = hash_part.lstrip("+")

        # Attempt ImportChatInviteRequest
        await client(ImportChatInviteRequest(hash_part))
        return True
    except Exception as e:
        # Try JoinChannelRequest as fallback
        try:
            entity = await client.get_entity(invite_link.strip())
            await client(JoinChannelRequest(entity))
            return True
        except Exception:
            return False


async def boost_views(client: TelegramClient, channel_entity, msg_id: int) -> bool:
    """Increment view count for a specific message."""
    try:
        await client(GetMessagesViewsRequest(
            peer=channel_entity,
            id=[msg_id],
            increment=True
        ))
        return True
    except Exception:
        return False


async def send_reaction(client: TelegramClient, channel_entity, msg_id: int, emoji: str) -> bool:
    """Send a reaction to a message."""
    try:
        await client(SendReactionRequest(
            peer=channel_entity,
            msg_id=msg_id,
            reaction=[types.ReactionEmoji(emoticon=emoji)]
        ))
        return True
    except Exception:
        return False


async def set_online(client: TelegramClient):
    """Set account status to Online."""
    try:
        await client(functions.account.UpdateStatusRequest(offline=False))
    except Exception:
        pass


async def set_offline(client: TelegramClient):
    """Set account status to Offline."""
    try:
        await client(functions.account.UpdateStatusRequest(offline=True))
    except Exception:
        pass