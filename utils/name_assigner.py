import os
from utils.database import (
    get_all_accounts, save_account, get_all_used_names, mark_name_used, is_name_used
)

NAME_FILE = "data/name.txt"


def load_accounts() -> dict:
    """Returns {account_id: {name, phone, session, status}}"""
    return get_all_accounts()


def save_accounts(accounts: dict):
    """Save all accounts. Note: we use save_account() per account for upserts."""
    for acc_id, data in accounts.items():
        save_account(acc_id, data)


def get_used_names() -> set:
    """Get all names already assigned to accounts from DB."""
    return get_all_used_names()


def get_next_name() -> str:
    """
    Reads name.txt, returns the first line whose name is not yet used
    in MongoDB. Marks it as used.
    """
    used = get_used_names()

    if not os.path.exists(NAME_FILE):
        count = len(load_accounts())
        name = f"User_{count + 1}"
        mark_name_used(name)
        return name

    with open(NAME_FILE, "r") as f:
        for line in f:
            name = line.strip()
            if name and not is_name_used(name):
                mark_name_used(name)
                return name

    # Fallback if all names are used
    count = len(load_accounts())
    name = f"User_{count + 1}"
    mark_name_used(name)
    return name
