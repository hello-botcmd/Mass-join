from telethon import Button


def get_main_keyboard():
    """Main menu inline keyboard."""
    buttons = [
        [Button.inline("📋 Start Join", b"start_join")],
        [Button.inline("📊 Stats", b"stats"),
         Button.inline("👁️ View Booster", b"view_booster")],
        [Button.inline("➕ Add Account", b"add_account_menu"),
         Button.inline("❤️ Reactions", b"reactions")],
        [Button.inline("💚 Health", b"health"),
         Button.inline("❓ Help", b"help")],
        [Button.inline("🟢 All IDs → Online", b"all_online"),
         Button.inline("🕒 All IDs → Last Seen Recently", b"all_last_seen")],
    ]
    return buttons


def get_add_account_keyboard():
    """Two options for adding an account."""
    buttons = [
        [Button.inline("📱 Phone + OTP + 2FA", b"add_by_phone")],
        [Button.inline("🔑 Session String / File", b"add_by_session")],
        [Button.inline("🔙 Back", b"back_main")],
    ]
    return buttons
