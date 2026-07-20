from utils.database import (
    get_all_stats, get_account_stats, add_chat_to_account,
    remove_chat_from_all_accounts, remove_chat_from_account
)


def load_stats() -> dict:
    """Returns {account_id: [list_of_chat_identifiers]}"""
    return get_all_stats()


def save_stats(stats: dict):
    """
    Save full stats dict.
    Since we use per-account operations, this mainly exists as a compatibility
    wrapper. For bulk operations, we iterate.
    """
    for acc_id, chats in stats.items():
        for chat in chats:
            add_chat_to_account(acc_id, chat)


def record_join(account_id: str, chat_identifier: str):
    """Record that an account joined a chat."""
    add_chat_to_account(account_id, chat_identifier)


def get_joined_chats(account_id: str) -> list:
    """Get all chats a specific account has joined."""
    return get_account_stats(account_id)
