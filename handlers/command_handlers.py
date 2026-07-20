
"""
Telegram Account Management Bot
Main entry point — initialises the bot client and registers all handlers.
"""

import os
import sys
import asyncio
import logging
from telethon import TelegramClient, events, Button

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, SUDO_USERS
from keyboards.main_keyboard import get_main_keyboard
from handlers.command_handlers import handle_start, handle_help, handle_remove
from handlers.callback_handlers import handle_callback_query
from handlers.account_handlers import (
    handle_add_account_command,
    handle_phone_input,
    handle_code_input,
    handle_2fa_input,
    handle_session_file_upload,
    handle_session_string_input,
)
from handlers.join_handlers import (
    handle_join_link,
    handle_online_count,
    handle_offline_2min_count,
    handle_last_seen_count,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("AccountBot")


def is_authorized(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in SUDO_USERS


async def main():
    logger.info("Starting Telegram Account Manager Bot...")

    # Await .start() — critical fix
    bot = await TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
    logger.info(f"Bot started! Owner: {OWNER_ID}")

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

    @bot.on(events.NewMessage(pattern=r"^/add_account$"))
    async def add_account_handler(event):
        if not is_authorized(event.sender_id):
            await event.reply("⛔ You are not authorised.")
            return
        await handle_add_account_command(event)

    # ── Dynamic message dispatcher ──

    @bot.on(events.NewMessage)
    async def message_dispatcher(event):
        """Route all incoming text messages to the correct step handler."""
        if not is_authorized(event.sender_id):
            return
        if not event.message.text:
            return

        uid = event.sender_id
        txt = event.message.text.strip()

        # ── Account login flows ──
        from handlers.account_handlers import _login_flows
        if uid in _login_flows:
            step = _login_flows[uid].get("step")
            if step == "awaiting_phone":
                await handle_phone_input(event)
                return
            elif step == "awaiting_code":
                await handle_code_input(event)
                return
            elif step == "awaiting_2fa":
                await handle_2fa_input(event)
                return
            elif step == "awaiting_session":
                await handle_session_string_input(event)
                return

        # ── Join flows ──
        from handlers.join_handlers import _join_flows
        if uid in _join_flows:
            step = _join_flows[uid].get("step")
            if step == "awaiting_link":
                await handle_join_link(event)
                return
            elif step == "awaiting_online_count":
                await handle_online_count(event)
                return
            elif step == "awaiting_offline_2min_count":
                await handle_offline_2min_count(event)
                return
            elif step == "awaiting_last_seen_count":
                await handle_last_seen_count(event)
                return

        # ── View Booster flow ──
        from handlers.callback_handlers import _view_flows
        if uid in _view_flows and _view_flows[uid].get("step") == "awaiting_link":
            from utils.view_booster import run_view_boost
            _view_flows[uid]["link"] = txt
            _view_flows[uid]["step"] = "done"

            status_msg = await event.reply("🔄 **View Booster**\n\nStarting view boost...")
            try:
                result = await run_view_boost(
                    API_ID, API_HASH, txt,
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
                if uid in _view_flows:
                    del _view_flows[uid]
            await event.reply("Use the buttons below to continue.", buttons=get_main_keyboard())
            return

        # ── Reaction flow ──
        from handlers.callback_handlers import _reaction_flows
        if uid in _reaction_flows and _reaction_flows[uid].get("step") == "awaiting_link":
            _reaction_flows[uid]["link"] = txt
            _reaction_flows[uid]["step"] = "awaiting_type"
            from keyboards.reaction_keyboard import get_reaction_type_keyboard
            await event.reply(
                "❤️ **Select Reaction Type**\n\n"
                "🎲 **Mix** — Random emoji on each account\n"
                "👍 **Single** — Same emoji on all accounts",
                buttons=get_reaction_type_keyboard()
            )
            return

    # ── File upload handler (.session files) ──
    @bot.on(events.NewMessage(func=lambda e: e.message.file and e.message.file.name and e.message.file.name.endswith(".session")))
    async def session_file_handler(event):
        if not is_authorized(event.sender_id):
            await event.reply("⛔ You are not authorised.")
            return
        await handle_session_file_upload(event)

    # ── Callback query handler ──
    @bot.on(events.CallbackQuery)
    async def callback_handler(event):
        await handle_callback_query(event)

    logger.info("Bot is ready. Listening for commands...")
    await bot.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
