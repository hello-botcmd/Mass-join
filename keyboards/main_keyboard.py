from telethon import Button

def get_main_keyboard():
    """Main menu inline keyboard."""
    buttons = [
        [Button.inline("📋 Start Join", b"start_join")],
        [Button.inline("📊 Stats", b"stats"),
         Button.inline("👁️ View Booster", b"view_booster")],
        [Button.inline("❤️ Reactions", b"reactions"),
         Button.inline("❓ Help", b"help")],
        [Button.inline("💚 Health", b"health")],
        [Button.inline("🟢 All IDs → Online", b"all_online"),
         Button.inline("🕒 All IDs → Last Seen Recently", b"all_last_seen")],
    ]
    return buttons