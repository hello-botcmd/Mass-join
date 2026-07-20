import os
import asyncio
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, GetMessagesViewsRequest, SendReactionRequest
from telethon.tl.functions.account import SetPrivacyRequest, UpdateStatusRequest
from telethon.tl.types import (
    InputPrivacyKeyStatusTimestamp,
    InputPrivacyValueAllowAll,
    InputPrivacyValueDisallowAll,
    ReactionEmoji,
    InputChannel,
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
    """Leave a channel/group by identifier."""
    try:
        # Try to get the entity
        try:
            entity = await client.get_entity(chat_identifier)
        except Exception:
            # Try as an integer ID
            try:
                entity = await client.get_entity(int(chat_identifier))
            except Exception:
                return False

        await client(LeaveChannelRequest(entity))
        return True
    except Exception:
        return False


async def resolve_channel_entity(client: TelegramClient, channel_identifier):
    """
    Resolve a channel entity using multiple methods.
    Returns the entity or None.
    """
    # Method 1: Direct get_entity with string
    try:
        if channel_identifier.startswith("-100"):
            return await client.get_entity(int(channel_identifier))
        else:
            return await client.get_entity(channel_identifier)
    except Exception:
        pass

    # Method 2: Try as integer
    try:
        return await client.get_entity(int(channel_identifier))
    except Exception:
        pass

    # Method 3: Search through dialogs
    try:
        async for dialog in client.iter_dialogs():
            if dialog.entity and hasattr(dialog.entity, 'id'):
                chat_id = getattr(dialog.entity, 'id', None)
                if chat_id and str(chat_id) == channel_identifier.replace("-100", ""):
                    return dialog.entity
                if chat_id and f"-100{abs(chat_id)}" == channel_identifier:
                    return dialog.entity
                if chat_id and str(chat_id) == channel_identifier:
                    return dialog.entity
    except Exception:
        pass

    return None


async def boost_views(client: TelegramClient, channel_entity, msg_id: int) -> bool:
    try:
        await client(GetMessagesViewsRequest(
            peer=channel_entity,
            id=[msg_id],
            increment=True
        ))
        return True
    except Exception as e:
        return False


async def send_reaction(client: TelegramClient, channel_entity, msg_id: int, emoji: str) -> bool:
    try:
        await client(SendReactionRequest(
            peer=channel_entity,
            msg_id=msg_id,
            reaction=[ReactionEmoji(emoticon=emoji)]
        ))
        return True
    except Exception as e:
        return False


async def set_online(client: TelegramClient) -> bool:
    """
    Set account to Online.
    Also resets privacy so last seen is visible (green circle).
    """
    try:
        # First allow everyone to see status
        try:
            await client(SetPrivacyRequest(
                key=InputPrivacyKeyStatusTimestamp(),
                rules=[InputPrivacyValueAllowAll()]
            ))
        except Exception:
            pass
        # Then set online
        await client(UpdateStatusRequest(offline=False))
        return True
    except Exception:
        return False


async def set_offline(client: TelegramClient) -> bool:
    """
    Set account to Offline — shows 'last seen recently' briefly.
    But we use privacy settings to HIDE last seen, showing 'last seen recently' permanently.
    """
    try:
        # First, hide last seen from everyone using privacy settings
        try:
            await client(SetPrivacyRequest(
                key=InputPrivacyKeyStatusTimestamp(),
                rules=[InputPrivacyValueDisallowAll()]
            ))
        except Exception:
            pass
        # Then set offline
        await client(UpdateStatusRequest(offline=True))
        return True
    except Exception:
        return False


async def set_last_seen_recently(client: TelegramClient) -> bool:
    """
    Hide last seen using privacy settings.
    This makes the account show 'last seen recently' to all users permanently.
    """
    try:
        # Hide last seen from everyone
        await client(SetPrivacyRequest(
            key=InputPrivacyKeyStatusTimestamp(),
            rules=[InputPrivacyValueDisallowAll()]
        ))
        # Set offline to make it show 'last seen recently'
        await client(UpdateStatusRequest(offline=True))
        return True
    except Exception:
        return False
