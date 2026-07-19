import os
import json

STATS_FILE = "data/stats.json"


def load_stats() -> dict:
    if not os.path.exists(STATS_FILE):
        return {}
    with open(STATS_FILE, "r") as f:
        return json.load(f)


def save_stats(stats: dict):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


def record_join(account_id: str, chat_id: int):
    stats = load_stats()
    if account_id not in stats:
        stats[account_id] = []
    if chat_id not in stats[account_id]:
        stats[account_id].append(chat_id)
    save_stats(stats)


def get_joined_chats(account_id: str) -> list:
    stats = load_stats()
    return stats.get(account_id, [])