import os
import json
import random
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


# ================= JSON =================

def load_json(file, default):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ================= USERS =================

def load_users():
    return load_json(USERS_FILE, {})


def save_users(data):
    save_json(USERS_FILE, data)


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
    return user["limit"] + user["referrals"] * REF_LIMIT


# ================= MOVIES =================

def load_movies():
    return load_json(MOVIES_FILE, {})


def save_movies(data):
    save_json(MOVIES_FILE, data)


# ================= ADMIN =================

def is_admin(uid):
    return uid in ADMINS


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie")],
        [InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete_movie")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")]
    ])


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    fname = update.effective_user.first_name

    users = load_users()
    get_user(users, uid)
    save_users(users)

    text = (
        f"Assalomu alaykum {fname} 👋\n\n"
        f"🎬 UzbekFilmTV bot\n\n"
        f"Kino kodini yuboring."
    )

    kb = []

    if is_admin(uid):
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))


# ================= CALLBACK =================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    data = q.data

    movies = load_movies()

    if data == "admin":
        await q.message.reply_text("Admin panel", reply_markup=admin_keyboard())

    if data == "add_movie":

        context.user_data["mode"] = "wait_forward"

        await q.message.reply_text(
            "Kanal postini forward qiling (video/audio/document)"
        )

    if data == "delete_movie":

        context.user_data["mode"] = "delete_movie"

        await q.message.reply_text("O‘chirish uchun kod yuboring")

    if data == "stats":

        users = load_users()

        await q.message.reply_text(
            f"👥 Userlar: {len(users)}\n"
            f"🎬 Filmlar: {len(movies)}"
        )


# ================= MESSAGE =================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    users = load_users()
    movies = load_movies()

    uid = update.effective_user.id

    user = get_user(users, uid)

    mode = context.user_data.get("mode")

    msg = update.message

    # ================= ADMIN =================

    if is_admin(uid):

        if mode == "wait_forward":

            file_id = None
            file_type = None

            if msg.video:
                file_id = msg.video.file_id
                file_type = "video"

            elif msg.audio:
                file_id = msg.audio.file_id
                file_type = "audio"

            elif msg.document:
                file_id = msg.document.file_id
                file_type = "document"

            elif msg.voice:
                file_id = msg.voice.file_id
                file_type = "voice"

            if not file_id:
                await msg.reply_text("Video/audio/document forward qiling")
                return

            context.user_data["file_id"] = file_id
            context.user_data["file_type"] = file_type

            context.user_data["mode"] = "movie_name"

            await msg.reply_text("Film nomini yuboring")

            return

        if mode == "movie_name":

            context.user_data["movie_name"] = msg.text

            context.user_data["mode"] = "movie_code"

            await msg.reply_text(
                "Kod kiriting (masalan: 1 yoki 25 yoki 300)"
            )

            return

        if mode == "movie_code":

            code = msg.text.strip()

            if code in movies:

                await msg.reply_text("Bu kod band")

                return

            movies[code] = {
                "name": context.user_data["movie_name"],
                "file_id": context.user_data["file_id"],
                "file_type": context.user_data["file_type"],
                "views": 0
            }

            save_movies(movies)

            await msg.reply_text(
                f"✅ Film qo‘shildi\n\n"
                f"Kod: {code}\n"
                f"Nomi: {context.user_data['movie_name']}"
            )

            context.user_data.clear()

            return

        if mode == "delete_movie":

            code = msg.text

            if code in movies:

                del movies[code]

                save_movies(movies)

                await msg.reply_text("Film o‘chirildi")

            else:

                await msg.reply_text("Kod topilmadi")

            context.user_data.clear()

            return

    # ================= USER =================

    text = msg.text

    if text in movies:

        movie = movies[text]

        movies[text]["views"] += 1

        user["used"] += 1

        save_movies(movies)
        save_users(users)

        caption = f"🎬 {movie['name']}"

        if movie["file_type"] == "video":

            await context.bot.send_video(
                chat_id=msg.chat_id,
                video=movie["file_id"],
                caption=caption
            )

        elif movie["file_type"] == "audio":

            await context.bot.send_audio(
                chat_id=msg.chat_id,
                audio=movie["file_id"],
                caption=caption
            )

        elif movie["file_type"] == "document":

            await context.bot.send_document(
                chat_id=msg.chat_id,
                document=movie["file_id"],
                caption=caption
            )

        elif movie["file_type"] == "voice":

            await context.bot.send_voice(
                chat_id=msg.chat_id,
                voice=movie["file_id"]
            )

        return

    await msg.reply_text("Bunday kod yo‘q")


# ================= MAIN =================

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(
        filters.TEXT | filters.VIDEO | filters.AUDIO | filters.Document.ALL,
        message_handler
    ))

    print("Bot ishga tushdi")

    app.run_polling()


if __name__ == "__main__":
    main()
