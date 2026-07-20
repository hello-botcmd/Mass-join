"""MongoDB database wrapper for all persistent storage."""

import os
from pymongo import MongoClient, ASCENDING
from config import MONGO_URI, MONGO_DB_NAME

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGO_URI)
        _db = _client[MONGO_DB_NAME]
        _db.accounts.create_index("account_id", unique=True)
        _db.name_assignments.create_index("name", unique=True)
    return _db


def close_db():
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None


# ── Accounts Collection ──

def get_all_accounts() -> dict:
    db = get_db()
    accounts = {}
    for doc in db.accounts.find():
        acc_id = doc.pop("account_id")
        accounts[acc_id] = doc
        doc.pop("_id", None)
    return accounts


def get_account(account_id: str) -> dict:
    db = get_db()
    doc = db.accounts.find_one({"account_id": account_id})
    if doc:
        doc.pop("_id", None)
        doc.pop("account_id", None)
        return doc
    return {}


def save_account(account_id: str, data: dict):
    db = get_db()
    doc = data.copy()
    doc["account_id"] = account_id
    db.accounts.replace_one({"account_id": account_id}, doc, upsert=True)


def delete_account(account_id: str):
    db = get_db()
    db.accounts.delete_one({"account_id": account_id})


def get_accounts_count() -> int:
    db = get_db()
    return db.accounts.count_documents({})


def get_session_string(account_id: str) -> str:
    """Get the stored session string for an account."""
    db = get_db()
    doc = db.accounts.find_one({"account_id": account_id})
    if doc:
        return doc.get("session_string", "")
    return ""


def update_account_field(account_id: str, field: str, value):
    """Update a single field on an account document."""
    db = get_db()
    db.accounts.update_one(
        {"account_id": account_id},
        {"$set": {field: value}}
    )


# ── Name Assignments ──

def mark_name_used(name: str):
    db = get_db()
    db.name_assignments.update_one(
        {"name": name},
        {"$set": {"name": name, "used": True}},
        upsert=True
    )


def is_name_used(name: str) -> bool:
    db = get_db()
    doc = db.name_assignments.find_one({"name": name})
    return doc is not None


def get_all_used_names() -> set:
    db = get_db()
    return {doc["name"] for doc in db.name_assignments.find({"used": True})}


# ── Stats Collection ──

def get_all_stats() -> dict:
    db = get_db()
    stats = {}
    for doc in db.stats.find():
        acc_id = doc.pop("account_id")
        stats[acc_id] = doc.get("chats", [])
    return stats


def get_account_stats(account_id: str) -> list:
    db = get_db()
    doc = db.stats.find_one({"account_id": account_id})
    if doc:
        return doc.get("chats", [])
    return []


def add_chat_to_account(account_id: str, chat_identifier: str):
    db = get_db()
    db.stats.update_one(
        {"account_id": account_id},
        {"$addToSet": {"chats": chat_identifier}},
        upsert=True
    )


def remove_chat_from_all_accounts(chat_identifier: str):
    db = get_db()
    db.stats.update_many(
        {},
        {"$pull": {"chats": chat_identifier}}
    )


def remove_chat_from_account(account_id: str, chat_identifier: str):
    db = get_db()
    db.stats.update_one(
        {"account_id": account_id},
        {"$pull": {"chats": chat_identifier}}
    )
