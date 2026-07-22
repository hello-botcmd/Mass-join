from telethon import Button
def get_reaction_type_keyboard():
    buttons = [
        [Button.inline("🎲 Mix Reactions", b"react_mix")],
        [Button.inline("👍 Single Reaction", b"react_single")],
        [Button.inline("🔙 Back", b"back_main")],
    ]
    return buttons