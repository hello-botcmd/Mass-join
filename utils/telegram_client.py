import os
import asyncio
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, GetMessagesViewsRequest, SendReactionRequest

SESSION_DIR = "data/sessions"
os.makedirs(SESSION_DIR, exist_ok=True)


async def create_client(session_name_or_string: str, api_id: int, api_hash: str) -> TelegramClient:
    """
    Create a client from either a session string or a session file name.
    If the string is longer than 50 chars, treat it as a StringSession.
    Otherwise treat it as a file-based session name.
    """
    if len(session_name_or_string) > 50:
        # It's a session string
        client = TelegramClient(StringSession(session_name_or_string), api_id, api_hash)
    else:
        session_path = os.path.join(SESSION_DIR, session_name_or_string)
        client = TelegramClient(session_path, api_id, api_hash)
    return client


async def get_session_string(client: TelegramClient) -> str:
    """Export the current session as a string."""
    return client.session.save()


async def login_with_password(client: TelegramClient, phone: str, password: str) -> bool:
    await client.connect()
    if await client.is_user_authorized():
        return True
    try:
        await client.send_code_request(phone)
        try:
            await client.sign_in(phone, code="", password=password)
        except Exception:
            return False
        return True
    except SessionPasswordNeededError:
        await client.sign_in(password=password)
        return True
    except Exception:
        return False


async def login_with_session(client: TelegramClient) -> bool:
    await client.connect()
    return await client.is_user_authorized()


async def change_account_name(client: TelegramClient, new_first_name: str) -> bool:
    """Change the Telegram account's first name to the given name."""
    try:
        await client(functions.account.UpdateProfileRequest(
            first_name=new_first_name,
            last_name=""
        ))
        return True
    except Exception:
        return False


async def join_private_channel(client: TelegramClient, invite_link: str) -> bool:
    try:
        if "joinchat/" in invite_link:
            hash_part = invite_link.split("joinchat/")[-1].split("?")[0]
        elif "/+" in invite_link:
            hash_part = invite_link.split("/+")[-1].split("?")[0]
        else:
            username = invite_link.strip().lstrip("https://t.me/").lstrip("@")
            channel = await client.get_entity(username)
            await client(JoinChannelRequest(channel))
            return True

        hash_part = hash_part.lstrip("+")
        await client(ImportChatInviteRequest(hash_part))
        return True
    except Exception:
        try:
            entity = await client.get_entity(invite_link.strip())
            await client(JoinChannelRequest(entity))
            return True
        except Exception:
            return False


async def boost_views(client: TelegramClient, channel_entity, msg_id: int) -> bool:
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
    """Set account status to Online — shows green circle."""
    try:
        await client(functions.account.UpdateStatusRequest(offline=False))
        return True
    except Exception:
        return False


async def set_offline(client: TelegramClient):
    """Set account status to Offline — shows 'last seen recently'."""
    try:
        await client(functions.account.UpdateStatusRequest(offline=True))
        return True
    except Exception:
        return False
