import asyncio
import random
from utils.telegram_client import (
    create_client, send_reaction, resolve_channel_entity, parse_post_link
)
from utils.database import get_all_accounts
from config import API_ID, API_HASH

MIX_EMOJIS = ["👍", "❤️", "🔥", "🎉", "😁", "🤩", "👏", "💯", "🎊", "✨"]
SINGLE_EMOJI = "👍"
REACTION_GAP = 3


async def run_reactions(api_id: int, api_hash: str, post_link: str, mode: str,
                        single_emoji: str = None, progress_callback=None):
    """
    Add reactions to a post using all stored accounts.
    mode: "mix" for random emoji per account, "single" for one fixed emoji.
    Progress callback signature: async func(index, total, status_message)
    """
    accounts = get_all_accounts()
    if not accounts:
        raise Exception("No accounts available.")

    channel_identifier, msg_id = parse_post_link(post_link)
    results = {
        "success": 0,
        "failed": 0,
        "not_member": 0,
        "flood_wait": 0,
        "errors": [],
        "total": len(accounts)
    }
    idx = 0

    for account_id, account_data in accounts.items():
        idx += 1
        session_string = account_data.get("session_string", "")
        session_name = account_data.get("session", account_id)
        account_name = account_data.get("name", account_id)

        client = await create_client(
            session_string if session_string else session_name,
            api_id, api_hash
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                results["failed"] += 1
                msg = f"{account_name} — not authorized"
                results["errors"].append(msg)
                if progress_callback:
                    await progress_callback(idx, len(accounts), f"❌ {msg}")
                await client.disconnect()
                continue

            # Resolve the channel entity
            entity, error = await resolve_channel_entity(client, channel_identifier)
            if entity is None:
                results["failed"] += 1
                results["not_member"] += 1
                msg = f"{account_name} — {error}"
                results["errors"].append(msg)
                if progress_callback:
                    await progress_callback(idx, len(accounts), f"❌ {msg}")
                await client.disconnect()
                continue

            # Pick emoji based on mode
            if mode == "mix":
                emoji = random.choice(MIX_EMOJIS)
            else:
                emoji = single_emoji or SINGLE_EMOJI

            # Send reaction
            success, error_msg = await send_reaction(client, entity, msg_id, emoji)
            if success:
                results["success"] += 1
                if progress_callback:
                    await progress_callback(idx, len(accounts), f"✅ {account_name} — {emoji}")
            else:
                results["failed"] += 1
                if "FLOOD_WAIT" in (error_msg or "").upper():
                    results["flood_wait"] += 1
                    msg = f"{account_name} — flood wait"
                elif "not a member" in (error_msg or "").lower():
                    results["not_member"] += 1
                    msg = f"{account_name} — not a member"
                else:
                    msg = f"{account_name} — {error_msg[:40]}"
                    results["errors"].append(f"{account_name}: {error_msg}")
                if progress_callback:
                    await progress_callback(idx, len(accounts), f"❌ {msg}")

        except Exception as e:
            results["failed"] += 1
            msg = f"{account_name} — error: {str(e)[:40]}"
            results["errors"].append(msg)
            if progress_callback:
                await progress_callback(idx, len(accounts), f"❌ {msg}")
        finally:
            await client.disconnect()

        await asyncio.sleep(REACTION_GAP)

    return results
