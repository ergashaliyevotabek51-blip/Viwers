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

FREE_LIMIT = 5
REF_LIMIT = 5

ADMINS = [774440841]
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


def load_users():
    return load_json(USERS_FILE, {})


def save_users(users):
    save_json(USERS_FILE, users)


def load_movies():
    return load_json(MOVIES_FILE, {})


def save_movies(movies):
    save_json(MOVIES_FILE, movies)


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


def trending(movies):
    return sorted(movies.items(), key=lambda x: x[1].get("views", 0), reverse=True)[:10]


def random_movie(movies):
    if not movies:
        return None
    return random.choice(list(movies.keys()))


def is_admin(uid):
    return uid in ADMINS


async def send_movie(context, chat_id, movie):

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Keyingi film", callback_data="next_movie")],
        [InlineKeyboardButton("🔥 Trend filmlar", callback_data="trend_movie")],
        [InlineKeyboardButton("🎥 Kino katalog", callback_data="movie_catalog")]
    ])

    await context.bot.copy_message(
        chat_id=chat_id,
        from_chat_id="@" + movie["channel"],
        message_id=movie["msg_id"],
        reply_markup=kb
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id
    fname = update.effective_user.first_name

    users = load_users()
    user = get_user(users, uid)

    if context.args:
        ref = context.args[0]

        if ref != str(uid) and ref in users:

            if "referred_by" not in user:

                user["referred_by"] = ref
                users[ref]["referrals"] += 1

                try:
                    await context.bot.send_message(
                        int(ref),
                        f"🎉 Siz yangi foydalanuvchi taklif qildingiz!\n+{REF_LIMIT} limit"
                    )
                except:
                    pass

    save_users(users)

    kb = [
        [InlineKeyboardButton("🎟 Mening limitim", callback_data="my_limit")],
        [InlineKeyboardButton("🎬 Random film", callback_data="rand_movie")],
        [InlineKeyboardButton("🔥 Trend filmlar", callback_data="trend_movie")],
        [InlineKeyboardButton("🎥 Kino katalog", callback_data="movie_catalog")],
        [InlineKeyboardButton("👥 Do‘st taklif qilish", callback_data="ref_link")]
    ]

    if is_admin(uid):
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(
        f"Assalomu alaykum {fname}!\n🎬 UzbekFilmTV bot",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    users = load_users()
    movies = load_movies()
    user = get_user(users, uid)

    data = q.data

    if data == "my_limit":

        await q.message.reply_text(
            f"Limit: {user['used']}/{max_limit(user)}\nReferal: {user['referrals']}"
        )
        return

    if data == "ref_link":

        link = f"https://t.me/{BOT_USERNAME}?start={uid}"

        await q.message.reply_text(f"Sizning referal linkingiz:\n{link}")
        return

    if data == "rand_movie":

        code = random_movie(movies)

        if code:
            await send_movie(context, q.message.chat_id, movies[code])

        return

    if data == "next_movie":

        code = random_movie(movies)

        if code:
            await send_movie(context, q.message.chat_id, movies[code])

        return

    if data == "trend_movie":

        text = "🔥 Trend filmlar\n\n"

        for i, (code, m) in enumerate(trending(movies), 1):
            text += f"{i}. {m['name']} — {code}\n"

        await q.message.reply_text(text)
        return

    if data == "movie_catalog":

        kb = []

        for code, m in list(movies.items())[:20]:
            kb.append([
                InlineKeyboardButton(m["name"], callback_data=f"watch_{code}")
            ])

        await q.message.reply_text(
            "🎬 Kino katalog",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    if data.startswith("watch_"):

        code = data.replace("watch_", "")

        if code in movies:
            await send_movie(context, q.message.chat_id, movies[code])

        return

    if not is_admin(uid):
        return

    if data == "admin":

        kb = [
            [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie")],
            [InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete_movie")],
            [InlineKeyboardButton("🔎 Kino qidirish", callback_data="search_movie")],
        ]

        await q.message.reply_text(
            "Admin panel",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data == "add_movie":

        context.user_data["mode"] = "add_link"

        await q.message.reply_text("Kanal post linkini yuboring")

    elif data == "delete_movie":

        context.user_data["mode"] = "delete"

        await q.message.reply_text("Kod yuboring")

    elif data == "search_movie":

        context.user_data["mode"] = "search"

        await q.message.reply_text("Film nomi yozing")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text

    uid = update.effective_user.id

    users = load_users()
    movies = load_movies()
    user = get_user(users, uid)

    mode = context.user_data.get("mode")

    if mode == "add_link":

        match = re.match(r"https://t\.me/([^/]+)/(\d+)", text)

        if not match:
            await update.message.reply_text("Link noto‘g‘ri")
            return

        context.user_data["channel"] = match.group(1)
        context.user_data["msg"] = int(match.group(2))
        context.user_data["mode"] = "add_code"

        await update.message.reply_text("Film kodi:")
        return

    if mode == "add_code":

        if text in movies:
            await update.message.reply_text("Kod band")
            return

        context.user_data["code"] = text
        context.user_data["mode"] = "add_name"

        await update.message.reply_text("Film nomi:")
        return

    if mode == "add_name":

        movies[context.user_data["code"]] = {
            "name": text,
            "channel": context.user_data["channel"],
            "msg_id": context.user_data["msg"],
            "views": 0
        }

        save_movies(movies)

        await update.message.reply_text("Film qo‘shildi")

        context.user_data.clear()
        return

    if mode == "delete":

        if text in movies:

            del movies[text]

            save_movies(movies)

            await update.message.reply_text("O‘chirildi")

        else:

            await update.message.reply_text("Topilmadi")

        context.user_data.clear()
        return

    if mode == "search":

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

    if text in movies:

        m = movies[text]

        user["used"] += 1
        movies[text]["views"] += 1

        save_movies(movies)
        save_users(users)

        await send_movie(context, update.effective_chat.id, m)

        return

    results = []

    for code, m in movies.items():
        if text.lower() in m["name"].lower():
            results.append(f"{m['name']} — {code}")

    if results:
        await update.message.reply_text(
            "Topilgan filmlar:\n" + "\n".join(results[:10])
        )
        return

    suggestions = []

    for code in movies:
        if text.lower() in code.lower():
            suggestions.append(code)

    if suggestions:

        await update.message.reply_text(
            "Kod topilmadi.\nBalki:\n" + "\n".join(suggestions[:5])
        )

    else:

        await update.message.reply_text("Film topilmadi")


def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Bot ishga tushdi")

    app.run_polling()


if __name__ == "__main__":
    main()
