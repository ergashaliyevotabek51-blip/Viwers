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
        "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:",
        reply_markup=kb
    )

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kino qo‘shish (forward)", callback_data="add_movie_forward"),
         InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete_movie")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats"),
         InlineKeyboardButton("🔥 Top filmlar", callback_data="top_movies")],
        [InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast"),
         InlineKeyboardButton("🔒 Majburiy obuna", callback_data="subscription")],
        [InlineKeyboardButton("💠 Limit qo‘shish", callback_data="add_limit")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    fname = update.effective_user.first_name
    users = load_users()
    get_user(users, uid)
    save_users(users)

    if not await check_user_subscribed(context, uid):
        await send_subscription_message(update.message, context)
        return

    text = (
        f"Assalomu alaykum, {fname}! 👋\n\n"
        f"🎬 UzbekFilmTV — eng sara o‘zbek filmlari!\n\n"
        f"Kod yuboring → film darhol keladi\n"
    )

    kb = [
        [InlineKeyboardButton("🎟 Mening limitim", callback_data="my_limit")],
        [InlineKeyboardButton("🎬 Random film", callback_data="rand_movie")],
        [InlineKeyboardButton("🔥 Trend filmlar", callback_data="trend_movie")]
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

    if data == "admin":
        await q.message.reply_text("🛠 Admin panel", reply_markup=admin_keyboard())

    if data == "add_movie_forward":
        context.user_data["mode"] = "wait_movie_forward"
        await q.message.reply_text(
            "1️⃣ Kanal postini forward qiling yoki file yuboring"
        )

    if data == "next_movie":
        code = random_movie(movies)
        if not code:
            return
        m = movies[code]

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Keyingi film", callback_data="next_movie")],
            [InlineKeyboardButton("🎬 Ulashish", url=f"https://t.me/{BOT_USERNAME}")]
        ])

        await context.bot.send_video(
            q.message.chat_id,
            m["file_id"],
            caption=f"🎬 {m['name']}",
            reply_markup=kb
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    users = load_users()
    movies = load_movies()

    mode = context.user_data.get("mode")

    # ===== ADMIN MEDIA QABUL =====

    if is_admin(update.effective_user.id) and mode == "wait_movie_forward":

        msg = update.message

        file_id = None
        file_type = None

        if msg.video:
            file_id = msg.video.file_id
            file_type = "video"

        elif msg.document:
            file_id = msg.document.file_id
            file_type = "document"

        elif msg.audio:
            file_id = msg.audio.file_id
            file_type = "audio"

        elif msg.voice:
            file_id = msg.voice.file_id
            file_type = "voice"

        elif msg.animation:
            file_id = msg.animation.file_id
            file_type = "animation"

        if not file_id:
            await msg.reply_text("Video yoki media yuboring")
            return

        context.user_data["movie_file_id"] = file_id
        context.user_data["movie_file_type"] = file_type

        context.user_data["mode"] = "wait_movie_code"

        await msg.reply_text("2️⃣ Kino kodini kiriting (masalan: 25)")

        return

    if mode == "wait_movie_code":

        code = update.message.text

        if code in movies:
            await update.message.reply_text("Bu kod band")
            return

        context.user_data["movie_code"] = code
        context.user_data["mode"] = "wait_movie_name"

        await update.message.reply_text("3️⃣ Film nomini kiriting")

        return

    if mode == "wait_movie_name":

        name = update.message.text

        code = context.user_data["movie_code"]
        file_id = context.user_data["movie_file_id"]
        file_type = context.user_data["movie_file_type"]

        movies[code] = {
            "name": name,
            "file_id": file_id,
            "file_type": file_type,
            "views": 0
        }

        save_movies(movies)

        await update.message.reply_text("✅ Film muvaffaqiyatli qo‘shildi")

        context.user_data.clear()

        return

    # ===== USER KOD YOZSA =====

    if not update.message.text:
        return

    text = update.message.text.strip()

    if text in movies:

        user = get_user(users, update.effective_user.id)

        m = movies[text]

        movies[text]["views"] += 1
        user["used"] += 1

        save_movies(movies)
        save_users(users)

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Keyingi film", callback_data="next_movie")],
            [InlineKeyboardButton("🎬 Ulashish", url=f"https://t.me/{BOT_USERNAME}")]
        ])

        await context.bot.send_video(
            update.effective_chat.id,
            m["file_id"],
            caption=f"🎬 {m['name']}",
            reply_markup=kb
        )

        return

    await update.message.reply_text("Bunday kod topilmadi")

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(
        filters.VIDEO |
        filters.Document.ALL |
        filters.AUDIO |
        filters.VOICE |
        filters.ANIMATION,
        message_handler
    ))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Bot ishga tushdi")

    app.run_polling()

if __name__ == "__main__":
    main()
