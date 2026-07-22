from telethon import events, Button
from keyboards.reaction_keyboard import get_reaction_type_keyboard
from utils.reaction_engine import run_reactions

user_states = {}

def save_user_data(user_id, data):
    if user_id not in user_states:
        user_states[user_id] = {}
    user_states[user_id].update(data)

def get_user_data(user_id):
    return user_states.get(user_id, {})

@client.on(events.CallbackQuery(pattern=b"react_mix"))
async def react_mix_handler(event):
    await event.answer("Mix Reactions Selected")
    save_user_data(event.sender_id, {"reaction_mode": "mix", "reaction_emoji": None})
    await event.edit("Now send the Telegram post link:", buttons=Button.force_reply())

@client.on(events.CallbackQuery(pattern=b"react_single"))
async def react_single_handler(event):
    await event.answer("Single Reaction Selected")
    save_user_data(event.sender_id, {"reaction_mode": "single", "reaction_emoji": None})
    await event.edit("Select an emoji:", buttons=[
        [Button.inline("👍", b"set_emoji_👍"), Button.inline("❤️", b"set_emoji_❤️")],
        [Button.inline("🔥", b"set_emoji_🔥"), Button.inline("🎉", b"set_emoji_🎉")],
        [Button.inline("Custom Emoji", b"set_emoji_custom")],
        [Button.inline("🔙 Back", b"back_to_reaction_type")]
    ])

@client.on(events.CallbackQuery(pattern=b"set_emoji_(.+)"))
async def set_emoji_handler(event):
    emoji = event.pattern_match.group(1).decode('utf-8')
    save_user_data(event.sender_id, {"reaction_emoji": emoji})
    await event.answer(f"Emoji set: {emoji}")
    await event.edit(f"Emoji selected: {emoji}\n\nNow send the post link:", buttons=Button.force_reply())

@client.on(events.CallbackQuery(pattern=b"back_to_reaction_type"))
async def back_to_reaction_type(event):
    await event.edit("Choose reaction type:", buttons=get_reaction_type_keyboard())

@client.on(events.NewMessage(pattern=r'https?://t\.me/'))
async def post_link_handler(event):
    user_id = event.sender_id
    post_link = event.text.strip()
    user_data = get_user_data(user_id)
    mode = user_data.get("reaction_mode")
    single_emoji = user_data.get("reaction_emoji")

    if not mode:
        await event.reply("Please select Mix or Single first.")
        return

    await event.reply(f"Starting reactions...\nMode: {mode.upper()}")

    async def progress_callback(idx, total, status):
        try:
            await event.reply(f"[{idx}/{total}] {status}")
        except:
            pass

    try:
        results = await run_reactions(
            api_id=API_ID,
            api_hash=API_HASH,
            post_link=post_link,
            mode=mode,
            single_emoji=single_emoji,
            progress_callback=progress_callback
        )
        summary = f"""
Reaction Task Completed
Total: {results['total']}
Success: {results['success']}
Failed: {results['failed']}
Not Member: {results['not_member']}
Flood: {results['flood_wait']}
"""
        await event.reply(summary)
    except Exception as e:
        await event.reply(f"Error: {str(e)}")