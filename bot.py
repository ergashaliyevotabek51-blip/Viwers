import os
import json
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = "UzbekFilmTV_bot"

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"
SETTINGS_FILE = "settings.json"

FREE_LIMIT = 5
REF_LIMIT = 5

ADMINS = [774440841]  # o'zingizning IDingizni qo'ying

# ===== HELPERS =====
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

def save_users(x):
    save_json(USERS_FILE, x)

def load_movies():
    return load_json(MOVIES_FILE, {})

def save_movies(x):
    save_json(MOVIES_FILE, x)

def load_settings():
    return load_json(SETTINGS_FILE, {"channels": []})

def save_settings(x):
    save_json(SETTINGS_FILE, x)

def is_admin(uid):
    return uid in ADMINS

def get_user(users, uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "used": 0,
            "limit": FREE_LIMIT,
            "referrals": 0,
            "joined": datetime.utcnow().isoformat()
        }
    return users[uid]

def max_limit(user):
    return user["limit"] + user["referrals"] * REF_LIMIT

def trending(movies):
    return sorted(movies.items(), key=lambda x: x[1].get("views", 0), reverse=True)[:10]

def random_movie(movies):
    if not movies:
        return None
    return random.choice(list(movies.keys()))

async def check_subscription(context, user_id):
    settings = load_settings()
    channels = settings.get("channels", [])
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    users = load_users()
    get_user(users, uid)
    save_users(users)

    text = (
        f"Assalomu alaykum, 𝐎𝐭𝐚𝐛𝐞𝐤! 👋\n\n"
        f"🎬 UzbekFilmTV — eng sara o‘zbek filmlari!\n\n"
        f"Kod yuboring → film darhol keladi\n"
        f"• Bepul: {FREE_LIMIT} ta   • Do‘st uchun: +{REF_LIMIT} ta\n\n"
        f"🚀 Kodni yozing yoki do‘stlaringizni taklif qiling!"
    )

    kb = [
        [InlineKeyboardButton("🎟 Mening limitim", callback_data="limit")],
        [InlineKeyboardButton("🎬 Random film", callback_data="random")],
        [InlineKeyboardButton("🔥 Trend filmlar", callback_data="trend")]
    ]

    if is_admin(uid):
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

# ===== CALLBACK =====
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid = q.from_user.id

    users = load_users()
    movies = load_movies()
    user = get_user(users, uid)

    if data == "limit":
        await q.message.reply_text(f"🎟 Limit: {user['used']}/{max_limit(user)}")
    elif data == "random":
        code = random_movie(movies)
        if not code:
            await q.message.reply_text("Film yo‘q")
            return
        m = movies[code]
        await context.bot.send_video(q.message.chat_id, m["file_id"], caption=m.get("caption", m["name"]))
    elif data == "trend":
        top = trending(movies)
        text = "🔥 Trend filmlar\n\n"
        for i, (code, m) in enumerate(top, 1):
            text += f"{i}. {m['name']} — {m.get('views',0)} ta\n"
        await q.message.reply_text(text)
    elif data == "admin" and is_admin(uid):
        kb = [
            [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add")],
            [InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete")],
            [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
            [InlineKeyboardButton("🔥 Top filmlar", callback_data="top")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton("🔒 Majburiy obuna", callback_data="sub")],
            [InlineKeyboardButton("💠 Limit qo‘shish", callback_data="limit_add")]
        ]
        await q.message.reply_text("Admin panel", reply_markup=InlineKeyboardMarkup(kb))
    elif data == "stats" and is_admin(uid):
        await q.message.reply_text(f"👥 Users: {len(users)}\n🎬 Movies: {len(movies)}")
    elif data == "top" and is_admin(uid):
        top = trending(movies)
        text = "🔥 Top filmlar\n\n"
        for i, (code, m) in enumerate(top, 1):
            text += f"{i}. {m['name']} — {m.get('views',0)} ta\n"
        await q.message.reply_text(text)
    elif data == "add" and is_admin(uid):
        context.user_data["mode"] = "add_movie"
        await q.message.reply_text("Filmni forward qiling (video, document, audio, voice, animation)")
    elif data == "delete" and is_admin(uid):
        context.user_data["mode"] = "delete_movie"
        await q.message.reply_text("Kod yuboring")
    elif data == "broadcast" and is_admin(uid):
        context.user_data["mode"] = "broadcast"
        await q.message.reply_text("Xabar yuboring")
    elif data == "limit_add" and is_admin(uid):
        context.user_data["mode"] = "limit_add"
        await q.message.reply_text("user_id limit")
    elif data == "sub" and is_admin(uid):
        context.user_data["mode"] = "add_channel"
        await q.message.reply_text("Kanal username yuboring")

# ===== MESSAGE HANDLER =====
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    mode = context.user_data.get("mode")
    users = load_users()
    movies = load_movies()

    # === KINO QO'SHISH ===
    if mode == "add_movie":
        msg = update.message
        if msg.video:
            file_id = msg.video.file_id
        elif msg.document:
            file_id = msg.document.file_id
        elif msg.audio:
            file_id = msg.audio.file_id
        elif msg.voice:
            file_id = msg.voice.file_id
        elif msg.animation:
            file_id = msg.animation.file_id
        else:
            await msg.reply_text("Iltimos video, document, audio, voice yoki animation yuboring")
            return

        context.user_data["file"] = file_id
        context.user_data["caption"] = update.message.caption or ""
        context.user_data["mode"] = "movie_code"
        await msg.reply_text("Film kodi kiriting")
        return

    if mode == "movie_code":
        context.user_data["code"] = text
        context.user_data["mode"] = "movie_name"
        await update.message.reply_text("Film nomini kiriting")
        return

    if mode == "movie_name":
        code = context.user_data["code"]
        movies[code] = {
            "name": text,
            "file_id": context.user_data["file"],
            "caption": context.user_data.get("caption", text),
            "views": 0
        }
        save_movies(movies)
        await update.message.reply_text("Film qo‘shildi")
        context.user_data.clear()
        return

    # === KINO O'CHIRISH ===
    if mode == "delete_movie":
        if text in movies:
            del movies[text]
            save_movies(movies)
            await update.message.reply_text("Film o‘chirildi")
        else:
            await update.message.reply_text("Topilmadi")
        context.user_data.clear()
        return

    # === BROADCAST ===
    if mode == "broadcast":
        count = 0
        for u in users:
            try:
                await update.message.copy(chat_id=int(u))
                count += 1
            except:
                pass
        await update.message.reply_text(f"{count} ta userga yuborildi")
        context.user_data.clear()
        return

    # === LIMIT QO'SHISH ===
    if mode == "limit_add":
        try:
            uid2, limit = text.split()
            users[uid2]["limit"] = int(limit)
            save_users(users)
            await update.message.reply_text("Limit qo‘shildi")
        except:
            await update.message.reply_text("Format: user_id limit")
        context.user_data.clear()
        return

    # === KANAL QO'SHISH ===
    if mode == "add_channel":
        settings = load_settings()
        if text not in settings.get("channels", []):
            settings.setdefault("channels", []).append(text)
            save_settings(settings)
        await update.message.reply_text("Kanal qo‘shildi")
        context.user_data.clear()
        return

    # === USER KOD BO'YICHA KINO ===
    if text in movies:
        m = movies[text]
        movies[text]["views"] = m.get("views", 0) + 1
        user = get_user(users, update.effective_user.id)
        user["used"] += 1
        save_movies(movies)
        save_users(users)
        await context.bot.send_video(
            update.effective_chat.id,
            m["file_id"],
            caption=m.get("caption", m["name"])
        )
        return

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.ALL, messages))
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
