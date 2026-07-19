from telethon import Button

def get_reaction_type_keyboard():
    """Mix or Single reaction options."""
    buttons = [
        [Button.inline("🎲 Mix", b"react_mix")],
        [Button.inline("👍 Single", b"react_single")],
        [Button.inline("🔙 Back", b"back_main")],
    ]
    return buttons