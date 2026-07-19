#!/usr/bin/env python3
"""
Telegram Account Management Bot
Main entry point — initialises the bot client and registers all handlers.
"""

import os
import sys
import asyncio
import logging
from telethon import TelegramClient, events, Button

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, SUDO_USERS
from keyboards.main_keyboard import get_main_keyboard

# Import handlers
from handlers.command_handlers import handle_start, handle_help, handle_remove
from handlers.callback_handlers import handle_callback_query
from handlers.account_handlers import (
    handle_add_account_command,
    handle_phone_input,
    handle_code_input,
    handle_2fa_input,
    handle_session_file_upload,
)
from handlers.join_handlers import (
    handle_join_link,
    handle_online_count,
    handle_offline_2min_count,
    handle_last_seen_count,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("AccountBot")

# ── Auth check helper ──
def is_authorized(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in SUDO_USERS


async def main():
    """Initialise and run the bot."""
    logger.info("Starting Telegram Account Manager Bot...")

    # Create the bot client
    bot = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
    logger.info(f"Bot started! Owner: {OWNER_ID}, Sudo: {SUDO_USERS}")

    # ── Command Handlers ──

    @bot.on(events.NewMessage(pattern=r"^/start$"))
    async def start_handler(event):
        await handle_start(event)

    @bot.on(events.NewMessage(pattern=r"^/help$"))
    async def help_handler(event):
        await handle_help(event)

    @bot.on(events.NewMessage(pattern=r"^/remove"))
    async def remove_handler(event):
        await handle_remove(event)

    @bot.on(events.NewMessage(pattern=r"^/add_account"))
    async def add_account_handler(event):
        if not is_authorized(event.sender_id):
            await event.reply("⛔ You are not authorised.")
            return
        await handle_add_account_command(event)

    # ── Message Handlers for Multi-step Flows ──

    @bot.on(events.NewMessage(func=lambda e: e.sender_id in _get_users_in_flow("awaiting_phone")))
    async def phone_input_handler(event):
        await handle_phone_input(event)

    @bot.on(events.NewMessage(func=lambda e: e.sender_id in _get_users_in_flow("awaiting_code")))
    async def code_input_handler(event):
        await handle_code_input(event)

    @bot.on(events.NewMessage(func=lambda e: e.sender_id in _get_users_in_flow("awaiting_2fa")))
    async def twofa_input_handler(event):
        await handle_2fa_input(event)

    @bot.on(events.NewMessage(func=lambda e: e.sender_id in _get_users_in_flow("awaiting_link_join")))
    async def join_link_handler(event):
        await handle_join_link(event)

    @bot.on(events.NewMessage(func=lambda e: e.sender_id in _get_users_in_flow("awaiting_online_count")))
    async def online_count_handler(event):
        await handle_online_count(event)

    @bot.on(events.NewMessage(func=lambda e: e.sender_id in _get_users_in_flow("awaiting_offline_2min_count")))
    async def offline_2min_handler(event):
        await handle_offline_2min_count(event)

    @bot.on(events.NewMessage(func=lambda e: e.sender_id in _get_users_in_flow("awaiting_last_seen_count")))
    async def last_seen_handler(event):
        await handle_last_seen_count(event)

    # ── View Booster & Reaction Link Inputs ──
    @bot.on(events.NewMessage(func=lambda e: e.sender_id in _get_users_in_flow_view()))
    async def view_booster_link_handler(event):
        from utils.view_booster import run_view_boost
        user_id = event.sender_id
        from handlers.callback_handlers import _view_flows

        link = event.message.text.strip()
        _view_flows[user_id]["link"] = link
        _view_flows[user_id]["step"] = "done"

        status_msg = await event.reply("🔄 **View Booster**\n\nStarting view boost...")

        try:
            result = await run_view_boost(
                API_ID, API_HASH, link,
                progress_callback=lambda i, t, s: None
            )
            await status_msg.edit(
                f"✅ **View Booster complete!**\n"
                f"Success: {result['success']} | Failed: {result['failed']}\n"
                f"Total accounts used: {result['total']}"
            )
        except Exception as e:
            await status_msg.edit(f"❌ Error: {str(e)}")
        finally:
            if user_id in _view_flows:
                del _view_flows[user_id]

        await event.reply("Use the buttons below to continue.", buttons=get_main_keyboard())

    @bot.on(events.NewMessage(func=lambda e: e.sender_id in _get_users_in_flow_reaction()))
    async def reaction_link_handler(event):
        user_id = event.sender_id
        from handlers.callback_handlers import _reaction_flows

        link = event.message.text.strip()
        _reaction_flows[user_id]["link"] = link
        _reaction_flows[user_id]["step"] = "awaiting_type"

        from keyboards.reaction_keyboard import get_reaction_type_keyboard
        await event.reply(
            "❤️ **Select Reaction Type**\n\n"
            "🎲 **Mix** — Random emoji on each account\n"
            "👍 **Single** — Same emoji on all accounts",
            buttons=get_reaction_type_keyboard()
        )

    # ── Callback Query Handler ──
    @bot.on(events.CallbackQuery)
    async def callback_handler(event):
        await handle_callback_query(event)

    # ── File Upload Handler (for .session files) ──
    @bot.on(events.NewMessage(func=lambda e: e.message.file and e.message.file.name and e.message.file.name.endswith(".session")))
    async def session_file_handler(event):
        if not is_authorized(event.sender_id):
            await event.reply("⛔ You are not authorised.")
            return
        await handle_session_file_upload(event)

    # ── Run ──
    logger.info("Bot is ready. Listening for commands...")
    await bot.run_until_disconnected()


# ── Helper: track users by flow step ──

def _get_users_in_flow(step: str) -> set:
    """Return user IDs currently in a specific step of the login/join flow."""
    from handlers.account_handlers import _login_flows
    from handlers.join_handlers import _join_flows

    users = set()
    for uid, flow in _login_flows.items():
        if flow.get("step") == step:
            users.add(uid)
    for uid, flow in _join_flows.items():
        if flow.get("step") == step:
            users.add(uid)
    return users


def _get_users_in_flow_view() -> set:
    """Return user IDs waiting for a view booster link."""
    from handlers.callback_handlers import _view_flows
    return {uid for uid, flow in _view_flows.items() if flow.get("step") == "awaiting_link"}


def _get_users_in_flow_reaction() -> set:
    """Return user IDs waiting for a reaction link."""
    from handlers.callback_handlers import _reaction_flows
    return {uid for uid, flow in _reaction_flows.items() if flow.get("step") == "awaiting_link"}


# ── Entry Point ──
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
