import os
import json

ACCOUNTS_FILE = "data/accounts.json"
NAME_FILE = "data/name.txt"


def load_accounts() -> dict:
    if not os.path.exists(ACCOUNTS_FILE):
        return {}
    with open(ACCOUNTS_FILE, "r") as f:
        return json.load(f)


def save_accounts(accounts: dict):
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=2)


def get_used_names() -> set:
    accounts = load_accounts()
    return {a.get("name") for a in accounts.values() if a.get("name")}


def get_next_name() -> str:
    """
    Reads name.txt, returns the first line whose name is not yet used
    in accounts.json. Marks it as used by returning it.
    """
    if not os.path.exists(NAME_FILE):
        return f"User_{len(load_accounts()) + 1}"

    used = get_used_names()
    with open(NAME_FILE, "r") as f:
        for line in f:
            name = line.strip()
            if name and name not in used:
                return name
    # Fallback if all names are used
    return f"User_{len(load_accounts()) + 1}"