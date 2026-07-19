from telethon import Button

def get_status_override_keyboard():
    """Override buttons for status."""
    buttons = [
        [Button.inline("🟢 All IDs → Online", b"all_online")],
        [Button.inline("🕒 All IDs → Last Seen Recently", b"all_last_seen")],
        [Button.inline("🔙 Back", b"back_main")],
    ]
    return buttons