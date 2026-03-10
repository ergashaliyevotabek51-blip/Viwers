import os
import json
import random
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = "UzbekFilmTV_bot"

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"
SETTINGS_FILE = "settings.json"

FREE_LIMIT = 5
REF_LIMIT = 5

DEFAULT_ADMINS = [774440841]
MANDATORY_CHANNELS = []


def load_json(file, default):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_admins():
    settings = load_json(SETTINGS_FILE, {"admins": DEFAULT_ADMINS})
    return settings.get("admins", DEFAULT_ADMINS)


def is_admin(uid):
    return uid in get_admins()


def load_users():
    return load_json(USERS_FILE, {})


def save_users(users):
    save_json(USERS_FILE, users)


def get_user(users, uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "used": 0,
            "referrals": 0,
            "limit": FREE_LIMIT,
            "joined": datetime.utcnow().isoformat()
        }
    return users[uid]


def max_limit(user):
    return user.get("limit", FREE_LIMIT) + user["referrals"] * REF_LIMIT


def load_movies():
    return load_json(MOVIES_FILE, {})


def save_movies(movies):
    save_json(MOVIES_FILE, movies)


def trending(movies_dict):
    return sorted(movies_dict.items(), key=lambda x: x[1].get("views", 0), reverse=True)[:10]


def random_movie(movies_dict):
    if not movies_dict:
        return None
    return random.choice(list(movies_dict.keys()))


async def check_user_subscribed(context, user_id):
    if not MANDATORY_CHANNELS:
        return True
    for ch in MANDATORY_CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True


def subscription_keyboard(status):
    kb = []
    for ch, val in status.items():
        icon = "✅" if val else "❌"
        kb.append([InlineKeyboardButton(f"{icon} {ch}", url=f"https://t.me/{ch.lstrip('@')}")])
    kb.append([InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(kb)


async def send_subscription_message(message, context):
    status = {ch: False for ch in MANDATORY_CHANNELS}
    kb = subscription_keyboard(status)
    await message.reply_text(
        "Botdan foydalanish uchun kanallarga obuna bo‘ling:",
        reply_markup=kb
    )


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kino qo‘shish (link)", callback_data="add_movie_link"),
         InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete_movie")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats"),
         InlineKeyboardButton("🔥 Top filmlar", callback_data="top_movies")],
        [InlineKeyboardButton("🔎 Kino qidirish", callback_data="search_movie")],
        [InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast"),
         InlineKeyboardButton("🔒 Majburiy obuna", callback_data="subscription")],
        [InlineKeyboardButton("💠 Limit qo‘shish", callback_data="add_limit")]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    fname = update.effective_user.first_name

    users = load_users()
    user = get_user(users, uid)

    if context.args:
        ref_id = context.args[0]
        if ref_id != str(uid) and ref_id in users:
            ref_user = get_user(users, ref_id)
            if "referred_by" not in user:
                user["referred_by"] = ref_id
                ref_user["referrals"] += 1
                try:
                    await context.bot.send_message(
                        int(ref_id),
                        f"🎉 Siz yangi foydalanuvchi taklif qildingiz!\n+{REF_LIMIT} limit!"
                    )
                except:
                    pass

    save_users(users)

    if not await check_user_subscribed(context, uid):
        await send_subscription_message(update.message, context)
        return

    text = (
        f"Assalomu alaykum {fname}!\n\n"
        "🎬 UzbekFilmTV bot\n"
        "Kod yuboring → film keladi\n"
    )

    kb = [
        [InlineKeyboardButton("🎟 Mening limitim", callback_data="my_limit")],
        [InlineKeyboardButton("🎬 Random film", callback_data="rand_movie")],
        [InlineKeyboardButton("🔥 Trend filmlar", callback_data="trend_movie")],
        [InlineKeyboardButton("👥 Do‘st taklif qilish", callback_data="ref_link")]
    ]

    if is_admin(uid):
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    data = q.data

    users = load_users()
    movies = load_movies()
    user = get_user(users, uid)

    if data == "ref_link":
        link = f"https://t.me/{BOT_USERNAME}?start={uid}"
        await q.message.reply_text(f"Sizning referal linkingiz:\n{link}")
        return

    if data == "my_limit":
        await q.message.reply_text(
            f"Limit: {user['used']}/{max_limit(user)}\nReferal: {user['referrals']}"
        )
        return

    if data == "rand_movie":
        code = random_movie(movies)
        if code:
            m = movies[code]
            await context.bot.copy_message(
                chat_id=q.message.chat_id,
                from_chat_id="@" + m["channel"],
                message_id=m["msg_id"]
            )
        return

    if data == "trend_movie":
        top = trending(movies)
        text = "🔥 Trend filmlar\n\n"
        for i, (code, m) in enumerate(top, 1):
            text += f"{i}. {m['name']} ({code})\n"
        await q.message.reply_text(text)
        return

    if not is_admin(uid):
        return

    if data == "admin":
        await q.message.reply_text("Admin panel", reply_markup=admin_keyboard())

    elif data == "add_movie_link":
        context.user_data["mode"] = "wait_movie_link"
        await q.message.reply_text("Kanal post linkini yuboring")

    elif data == "search_movie":
        context.user_data["mode"] = "search_movie"
        await q.message.reply_text("Film nomini yozing")

    elif data == "delete_movie":
        context.user_data["mode"] = "delete_movie"
        await q.message.reply_text("O‘chirish uchun kod yuboring")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text
    uid = update.effective_user.id

    users = load_users()
    movies = load_movies()
    user = get_user(users, uid)

    mode = context.user_data.get("mode")

    if mode == "wait_movie_link":

        pattern = r"https://t\.me/([^/]+)/(\d+)"
        match = re.match(pattern, text)

        if not match:
            await update.message.reply_text("Link noto‘g‘ri")
            return

        context.user_data["channel"] = match.group(1)
        context.user_data["msg_id"] = int(match.group(2))
        context.user_data["mode"] = "wait_code"

        await update.message.reply_text("Film kodi:")
        return

    if mode == "wait_code":

        if text in movies:
            await update.message.reply_text("Kod band")
            return

        context.user_data["code"] = text
        context.user_data["mode"] = "wait_name"

        await update.message.reply_text("Film nomi:")
        return

    if mode == "wait_name":

        code = context.user_data["code"]

        movies[code] = {
            "name": text,
            "channel": context.user_data["channel"],
            "msg_id": context.user_data["msg_id"],
            "views": 0
        }

        save_movies(movies)

        await update.message.reply_text("Film qo‘shildi")

        context.user_data.clear()
        return

    if mode == "search_movie":

        res = []

        for code, m in movies.items():
            if text.lower() in m["name"].lower():
                res.append(f"{m['name']} — {code}")

        if res:
            await update.message.reply_text("\n".join(res))
        else:
            await update.message.reply_text("Topilmadi")

        context.user_data.clear()
        return

    if mode == "delete_movie":

        if text in movies:
            del movies[text]
            save_movies(movies)
            await update.message.reply_text("O‘chirildi")
        else:
            await update.message.reply_text("Kod topilmadi")

        context.user_data.clear()
        return

    if text in movies:

        m = movies[text]

        user["used"] += 1
        movies[text]["views"] += 1

        save_movies(movies)
        save_users(users)

        await context.bot.copy_message(
            chat_id=update.effective_chat.id,
            from_chat_id="@" + m["channel"],
            message_id=m["msg_id"]
        )

        return

    suggestions = []

    for code in movies:
        if text.lower() in code.lower():
            suggestions.append(code)

    if suggestions:
        sug = "\n".join(suggestions[:5])
        await update.message.reply_text(
            f"Kod topilmadi.\nBalki:\n{sug}"
        )
    else:
        await update.message.reply_text("Kod topilmadi")


def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Bot ishga tushdi")

    app.run_polling()


if __name__ == "__main__":
    main()
