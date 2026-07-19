import asyncio
import re
from utils.telegram_client import create_client, boost_views
from utils.name_assigner import load_accounts

VIEW_GAP = 3


def parse_post_link(link: str):
    """
    Parse a Telegram post link like:
    https://t.me/c/1234567890/123
    https://t.me/channelname/123
    Returns (channel_identifier, message_id) or raises ValueError.
    """
    link = link.strip()
    # Match private channel format: t.me/c/XXXXX/YYY or t.me/XXXXX/YYY?...
    pattern = r"(?:https?://)?t\.me/(?:c/)?([^/\s?]+)/(\d+)"
    match = re.search(pattern, link)
    if not match:
        raise ValueError("Invalid Telegram post link format.")
    channel_part = match.group(1)
    msg_id = int(match.group(2))

    # If it's a numeric channel ID (private format: t.me/c/1234567890/123)
    if channel_part.isdigit():
        channel_id = -1000000000000 - int(channel_part)  # noqa: approximate
        # Actually for t.me/c/XXXX format, the actual chat_id in Telegram is -100XXXXXXXXX
        # But we'll use the string as-is and let Telethon resolve it with get_entity
        return f"-100{channel_part}", msg_id
    else:
        return channel_part, msg_id


async def run_view_boost(api_id: int, api_hash: str, post_link: str, progress_callback=None):
    """
    Boost views on a post using all stored accounts.
    """
    accounts = load_accounts()
    if not accounts:
        raise Exception("No accounts available.")

    channel_identifier, msg_id = parse_post_link(post_link)

    results = {"success": 0, "failed": 0, "total": len(accounts)}
    idx = 0

    for account_id, account_data in accounts.items():
        idx += 1
        session_name = account_data.get("session", account_id)
        client = await create_client(session_name, api_id, api_hash)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                results["failed"] += 1
                if progress_callback:
                    await progress_callback(idx, len(accounts), f"{account_data.get('name', account_id)} — not authorized")
                await client.disconnect()
                continue

            # Resolve channel entity
            try:
                if channel_identifier.startswith("-100"):
                    # Numeric ID
                    entity = await client.get_entity(int(channel_identifier))
                else:
                    entity = await client.get_entity(channel_identifier)
            except Exception:
                # Try as chat ID
                entity = await client.get_entity(int(channel_identifier))

            success = await boost_views(client, entity, msg_id)
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1

            if progress_callback:
                status = "✓" if success else "✗"
                await progress_callback(idx, len(accounts), f"{account_data.get('name', account_id)} {status}")

        except Exception as e:
            results["failed"] += 1
            if progress_callback:
                await progress_callback(idx, len(accounts), f"{account_data.get('name', account_id)} ✗ {str(e)[:30]}")
        finally:
            await client.disconnect()

        # Fixed 3s gap
        await asyncio.sleep(VIEW_GAP)

    return results