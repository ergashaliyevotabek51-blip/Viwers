from database import load_json
from config import SETTINGS_FILE
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_channels():

    settings = load_json(SETTINGS_FILE, {"channels": []})

    return settings.get("channels", [])


async def check_user(context, user_id):

    channels = get_channels()

    if not channels:
        return {}

    result = {}

    for ch in channels:

        try:

            member = await context.bot.get_chat_member(ch, user_id)

            if member.status in ["member", "administrator", "creator"]:
                result[ch] = True
            else:
                result[ch] = False

        except Exception:
            result[ch] = False

    return result


def keyboard(status):

    if not status:
        return None

    kb = []

    for ch, val in status.items():

        icon = "✅" if val else "❌"

        kb.append([
            InlineKeyboardButton(
                f"{icon} {ch}",
                url=f"https://t.me/{ch.replace('@','')}"
            )
        ])

    kb.append([
        InlineKeyboardButton(
            "🔄 Obunani tekshirish",
            callback_data="check_sub"
        )
    ])

    return InlineKeyboardMarkup(kb)
