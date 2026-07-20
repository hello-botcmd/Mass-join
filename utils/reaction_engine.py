import asyncio
import random
import re
from utils.telegram_client import create_client, send_reaction
from utils.database import get_all_accounts, get_session_string
from config import API_ID, API_HASH

MIX_EMOJIS = ["👍", "❤️", "🔥", "🎉", "😁", "🤩", "👏", "💯", "🎊", "✨"]
SINGLE_EMOJI = "👍"
REACTION_GAP = 3


def parse_post_link(link: str):
    link = link.strip()
    pattern = r"(?:https?://)?t\.me/(?:c/)?([^/\s?]+)/(\d+)"
    match = re.search(pattern, link)
    if not match:
        raise ValueError("Invalid Telegram post link format.")
    channel_part = match.group(1)
    msg_id = int(match.group(2))
    if channel_part.isdigit():
        return f"-100{channel_part}", msg_id
    else:
        return channel_part, msg_id


async def run_reactions(api_id: int, api_hash: str, post_link: str, mode: str,
                        single_emoji: str = None, progress_callback=None):
    accounts = get_all_accounts()
    if not accounts:
        raise Exception("No accounts available.")

    channel_identifier, msg_id = parse_post_link(post_link)
    results = {"success": 0, "failed": 0, "total": len(accounts)}
    idx = 0

    for account_id, account_data in accounts.items():
        idx += 1
        session_string = account_data.get("session_string", "")
        session_name = account_data.get("session", account_id)

        client = await create_client(
            session_string if session_string else session_name,
            api_id, api_hash
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                results["failed"] += 1
                if progress_callback:
                    await progress_callback(idx, len(accounts), f"{account_data.get('name', account_id)} — not authorized")
                await client.disconnect()
                continue

            try:
                if channel_identifier.startswith("-100"):
                    entity = await client.get_entity(int(channel_identifier))
                else:
                    entity = await client.get_entity(channel_identifier)
            except Exception:
                entity = await client.get_entity(int(channel_identifier))

            if mode == "mix":
                emoji = random.choice(MIX_EMOJIS)
            else:
                emoji = single_emoji or SINGLE_EMOJI

            success = await send_reaction(client, entity, msg_id, emoji)
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1

            if progress_callback:
                status = f"✓ {emoji}" if success else "✗"
                await progress_callback(idx, len(accounts), f"{account_data.get('name', account_id)} {status}")

        except Exception as e:
            results["failed"] += 1
            if progress_callback:
                await progress_callback(idx, len(accounts), f"{account_data.get('name', account_id)} ✗")
        finally:
            await client.disconnect()

        await asyncio.sleep(REACTION_GAP)

    return results
