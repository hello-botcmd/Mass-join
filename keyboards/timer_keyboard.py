from telethon import Button

def get_timer_keyboard():
    """2×2 grid for timer gap selection."""
    buttons = [
        [Button.inline("1s", b"timer_1"),
         Button.inline("2s", b"timer_2")],
        [Button.inline("5s", b"timer_5"),
         Button.inline("10s", b"timer_10")],
    ]
    return buttons