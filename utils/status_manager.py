import random
import asyncio
from utils.database import get_session_string
from utils.telegram_client import create_client, set_online, set_offline, change_account_name
from config import API_ID, API_HASH


def random_distribution(account_ids: list, online_count: int, offline_2min_count: int, last_seen_count: int):
    """
    Randomly assign accounts to three categories.
    Returns a dict: {account_id: "online"} / "offline_2min" / "last_seen_recently"
    """
    total = len(account_ids)
    online_count = min(online_count, total)
    offline_2min_count = min(offline_2min_count, total - online_count)
    last_seen_count = min(last_seen_count, total - online_count - offline_2min_count)

    shuffled = account_ids.copy()
    random.shuffle(shuffled)

    status_map = {}
    idx = 0

    for _ in range(online_count):
        status_map[shuffled[idx]] = "online"
        idx += 1

    for _ in range(offline_2min_count):
        status_map[shuffled[idx]] = "offline_2min"
        idx += 1

    for _ in range(last_seen_count):
        status_map[shuffled[idx]] = "last_seen_recently"
        idx += 1

    while idx < len(shuffled):
        status_map[shuffled[idx]] = "last_seen_recently"
        idx += 1

    return status_map


async def apply_status(client, status: str):
    """
    Apply a status to a client.
    - "online": set online (green circle)
    - "offline_2min": set offline (shows 'last seen recently' then exact time)
    - "last_seen_recently": set offline (shows 'last seen recently')
    """
    if status == "online":
        return await set_online(client)
    else:
        # Both offline_2min and last_seen_recently → go offline
        return await set_offline(client)
