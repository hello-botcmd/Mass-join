import os
import asyncio
import re
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, ChannelPrivateError, ChatAdminRequiredError
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest, GetChannelsRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, GetMessagesViewsRequest, SendReactionRequest
from telethon.tl.functions.account import SetPrivacyRequest, UpdateStatusRequest
from telethon.tl.types import (
    InputPrivacyKeyStatusTimestamp,
    InputPrivacyValueAllowAll,
    InputPrivacyValueDisallowAll,
    ReactionEmoji,
    InputChannel,
    Message,
    Channel,
    Chat,
)

SESSION_DIR = "data/sessions"
os.makedirs(SESSION_DIR, exist_ok=True)


async def create_client(session_name_or_string: str, api_id: int, api_hash: str) -> TelegramClient:
    if len(session_name_or_string) > 50:
        client = TelegramClient(StringSession(session_name_or_string), api_id, api_hash)
    else:
        session_path = os.path.join(SESSION_DIR, session_name_or_string)
        client = TelegramClient(session_path, api_id, api_hash)
    return client


async def get_session_string(client: TelegramClient) -> str:
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


async def leave_channel(client: TelegramClient, chat_identifier) -> bool:
    try:
        try:
            entity = await client.get_entity(chat_identifier)
        except Exception:
            try:
                entity = await client.get_entity(int(chat_identifier))
            except Exception:
                return False
        await client(LeaveChannelRequest(entity))
        return True
    except Exception:
        return False


def parse_post_link(link: str):
    """
    Parse a Telegram post link.
    Supports:
    - https://t.me/c/1234567890/123
    - https://t.me/channelname/123
    - t.me/c/1234567890/123
    - t.me/channelname/123
    Returns (channel_identifier, message_id)
    """
    link = link.strip()
    # Remove trailing query params
    link = link.split("?")[0]
    link = link.split("&")[0]

    pattern = r"(?:https?://)?t\.me/(?:c/)?([^/\s?]+)/(\d+)"
    match = re.search(pattern, link)
    if not match:
        raise ValueError("Invalid Telegram post link format. Expected: https://t.me/c/12345/123 or https://t.me/channelname/123")

    channel_part = match.group(1)
    msg_id = int(match.group(2))

    if channel_part.isdigit():
        # Private channel format: t.me/c/1234567890/123
        # The actual Telegram chat ID is -100 followed by this number
        return f"-100{channel_part}", msg_id
    else:
        # Public channel: t.me/username/123
        return channel_part, msg_id


async def resolve_channel_entity(client: TelegramClient, channel_identifier) -> tuple:
    """
    Resolve a channel entity by trying multiple methods.
    Returns (entity, error_message) tuple.
    If entity is None, check error_message for why.
    """
    # Method 1: Direct get_entity with the identifier as-is
    try:
        entity = await client.get_entity(channel_identifier)
        if entity:
            return entity, None
    except ValueError as e:
        pass
    except Exception as e:
        pass

    # Method 2: Try as integer (for -100XXXX format)
    try:
        int_id = int(channel_identifier)
        entity = await client.get_entity(int_id)
        if entity:
            return entity, None
    except Exception:
        pass

    # Method 3: Try with @ prefix
    try:
        if not channel_identifier.startswith("@"):
            entity = await client.get_entity(f"@{channel_identifier}")
            if entity:
                return entity, None
    except Exception:
        pass

    # Method 4: Search through dialogs (only works if account is a member)
    try:
        async for dialog in client.iter_dialogs():
            if not dialog.entity:
                continue
            e = dialog.entity
            # Check by string ID
            e_id = getattr(e, 'id', None)
            if e_id:
                e_id_str = str(e_id)
                # Check raw ID
                clean_id = channel_identifier.replace("-100", "").lstrip("-")
                if clean_id in e_id_str or e_id_str in channel_identifier:
                    return e, None
            # Check by username
            username = getattr(e, 'username', None)
            if username:
                clean_username = channel_identifier.lstrip("@").lower()
                if username.lower() == clean_username:
                    return e, None
            # Check by title
            title = getattr(e, 'title', None)
            if title and channel_identifier.lower() in title.lower():
                return e, None
    except Exception:
        pass

    # Method 5: Try extracting numeric ID from -100XXXX format
    try:
        # If format is -100XXXX, try to extract the numeric part
        if channel_identifier.startswith("-100"):
            num_part = channel_identifier[4:]
            if num_part.isdigit():
                # Also try without -100 prefix
                try:
                    entity = await client.get_entity(int(num_part))
                    if entity:
                        return entity, None
                except Exception:
                    pass
    except Exception:
        pass

    return None, "Channel not found. Make sure the account has joined this channel first."


async def boost_views(client: TelegramClient, channel_entity, msg_id: int) -> tuple:
    """
    Boost views on a message.
    Returns (success: bool, error_message: str)
    Note: Telegram only allows view increment ONCE per account per message per day.
    """
    try:
        result = await client(GetMessagesViewsRequest(
            peer=channel_entity,
            id=[msg_id],
            increment=True
        ))
        return True, None
    except Exception as e:
        error_str = str(e)
        if "FLOOD_WAIT" in error_str:
            return False, f"Flood wait: {error_str}"
        return False, error_str


async def send_reaction(client: TelegramClient, channel_entity, msg_id: int, emoji: str) -> tuple:
    """
    Send a reaction to a message.
    Returns (success: bool, error_message: str)
    """
    try:
        await client(SendReactionRequest(
            peer=channel_entity,
            msg_id=msg_id,
            reaction=[ReactionEmoji(emoticon=emoji)]
        ))
        return True, None
    except Exception as e:
        error_str = str(e)
        if "FLOOD_WAIT" in error_str:
            return False, f"Flood wait: {error_str}"
        if "CHANNEL_PRIVATE" in error_str or "USER_NOT_PARTICIPANT" in error_str:
            return False, "Account not a member of this channel"
        return False, error_str


async def set_online(client: TelegramClient) -> bool:
    """Set account to Online with visible last seen (green circle)."""
    try:
        try:
            await client(SetPrivacyRequest(
                key=InputPrivacyKeyStatusTimestamp(),
                rules=[InputPrivacyValueAllowAll()]
            ))
        except Exception:
            pass
        await client(UpdateStatusRequest(offline=False))
        return True
    except Exception:
        return False


async def set_offline(client: TelegramClient) -> bool:
    """Set account to Offline."""
    try:
        await client(UpdateStatusRequest(offline=True))
        return True
    except Exception:
        return False


async def set_last_seen_recently(client: TelegramClient) -> bool:
    """
    Hide last seen from everyone using privacy settings.
    This makes the account permanently show 'last seen recently' to all users.
    """
    try:
        await client(SetPrivacyRequest(
            key=InputPrivacyKeyStatusTimestamp(),
            rules=[InputPrivacyValueDisallowAll()]
        ))
        await client(UpdateStatusRequest(offline=True))
        return True
    except Exception:
        return False
