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

ADMINS = [774440841, 7818576058]  # ← o'zingizning real ID'ingizni qo'ying

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

# ===== SUBSCRIPTION CHECK =====
async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id):
    settings = load_settings()
    channels = settings.get("channels", [])
    if not channels:
        return True
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

def subscription_keyboard():
    settings = load_settings()
    kb = []
    for ch in settings.get("channels", []):
        kb.append([InlineKeyboardButton(f"🔔 Obuna bo‘ling: {ch}", url=f"https://t.me/{ch.lstrip('@')}")])
    kb.append([InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(kb)

async def send_subscription_message(update_or_message, context):
    kb = subscription_keyboard()
    await (update_or_message.reply_text if hasattr(update_or_message, 'reply_text') else update_or_message.edit_text)(
        "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:",
        reply_markup=kb
    )

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    users = load_users()
    get_user(users, uid)
    save_users(users)

    if not await check_subscription(context, uid):
        await send_subscription_message(update.message, context)
        return

    text = (
        f"Assalomu alaykum, {name}! 👋\n\n"
        f"🎬 UzbekFilmTV — eng sara o‘zbek filmlari!\n\n"
        f"Kod yuboring → film darhol keladi\n"
        f"• Bepul: {FREE_LIMIT} ta   • Do‘st uchun: +{REF_LIMIT} ta har bir do‘st\n\n"
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

    if data == "check_sub":
        if await check_subscription(context, uid):
            await q.edit_message_text("✅ Obuna tasdiqlandi! Endi botdan foydalanishingiz mumkin.")
        else:
            await send_subscription_message(q.message, context)
        return

    if not await check_subscription(context, uid):
        await send_subscription_message(q.message, context)
        return

    if data == "limit":
        await q.message.reply_text(f"🎟 Sizning limitingiz: {user['used']}/{max_limit(user)}")
        return

    if data == "random":
        code = random_movie(movies)
        if not code:
            await q.message.reply_text("Hozircha hech qanday film qo'shilmagan 😔")
            return
        m = movies[code]
        await context.bot.send_video(q.message.chat_id, m["file_id"], caption=m.get("caption", m["name"]))
        return

    if data == "trend":
        top = trending(movies)
        if not top:
            await q.message.reply_text("Hali trend filmlar yo‘q")
            return
        text = "🔥 Eng ko‘p ko‘rilgan filmlar:\n\n"
        for i, (code, m) in enumerate(top, 1):
            text += f"{i}. {m['name']} — {m.get('views',0)} ta ko‘rilgan\n"
        await q.message.reply_text(text)
        return

    if not is_admin(uid):
        return

    # ── Admin panel ──
    if data == "admin":
        kb = [
            [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add")],
            [InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete")],
            [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
            [InlineKeyboardButton("🔥 Top filmlar", callback_data="top")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton("🔒 Majburiy obuna", callback_data="sub")],
            [InlineKeyboardButton("💠 Limit qo‘shish", callback_data="limit_add")]
        ]
        await q.message.reply_text("🛠 Admin panel", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data == "stats":
        await q.message.reply_text(f"👥 Foydalanuvchilar: {len(users)}\n🎬 Filmlar soni: {len(movies)}")
    elif data == "top":
        top = trending(movies)
        text = "🔥 Top filmlar (ko‘rishlar bo‘yicha):\n\n"
        for i, (code, m) in enumerate(top, 1):
            text += f"{i}. {m['name']} — {m.get('views',0)} ta\n"
        await q.message.reply_text(text or "Hali film qo‘shilmagan")
    elif data in ("add", "delete", "broadcast", "limit_add", "sub"):
        context.user_data["mode"] = {
            "add": "add_movie",
            "delete": "delete_movie",
            "broadcast": "broadcast",
            "limit_add": "limit_add",
            "sub": "add_channel"
        }[data]
        texts = {
            "add_movie": "Filmni forward qiling (video/document/audio/voice/gif)",
            "delete_movie": "O‘chirmoqchi bo‘lgan film kodini yuboring",
            "broadcast": "Hamma foydalanuvchilarga yubormoqchi bo‘lgan xabarni yuboring",
            "limit_add": "Format: user_id yangi_limit\nMasalan: 123456789 10",
            "add_channel": "Kanal username yuboring (@ bilan)\nYoki o‘chirish uchun: off / yo‘q"
        }
        await q.message.reply_text(texts[context.user_data["mode"]])

# ===== MESSAGE HANDLER =====
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text is None:
        return

    text = update.message.text.strip()
    uid_str = str(update.effective_user.id)
    mode = context.user_data.get("mode")
    users = load_users()
    movies = load_movies()

    # ─────────────── Admin rejimlari ───────────────
    if mode == "add_movie":
        msg = update.message
        file_id = None
        if msg.video:      file_id = msg.video.file_id
        elif msg.document: file_id = msg.document.file_id
        elif msg.audio:    file_id = msg.audio.file_id
        elif msg.voice:    file_id = msg.voice.file_id
        elif msg.animation: file_id = msg.animation.file_id

        if not file_id:
            await msg.reply_text("Faqat video, document, audio, voice yoki animation qabul qilinadi!")
            return

        context.user_data["file"] = file_id
        context.user_data["caption"] = msg.caption or ""
        context.user_data["mode"] = "movie_code"
        await msg.reply_text("Endi film uchun qisqa kod kiriting (masalan: uzb001)")
        return

    if mode == "movie_code":
        context.user_data["code"] = text
        context.user_data["mode"] = "movie_name"
        await update.message.reply_text("Filmning to‘liq nomini yozing")
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
        await update.message.reply_text(f"✅ Film qo‘shildi!\nKod: <b>{code}</b>\nNom: {text}")
        context.user_data.clear()
        return

    if mode == "delete_movie":
        if text in movies:
            del movies[text]
            save_movies(movies)
            await update.message.reply_text(f"🗑 Film o‘chirildi: {text}")
        else:
            await update.message.reply_text("Bunday kod topilmadi.")
        context.user_data.clear()
        return

    if mode == "broadcast":
        count = 0
        for u in users:
            try:
                await update.message.copy(chat_id=int(u))
                count += 1
            except:
                pass
        await update.message.reply_text(f"Xabar {count} ta foydalanuvchiga yetkazildi.")
        context.user_data.clear()
        return

    if mode == "limit_add":
        try:
            uid2, lim = text.split()
            users[uid2]["limit"] = int(lim)
            save_users(users)
            await update.message.reply_text(f"User {uid2} uchun limit {lim} ga o‘zgartirildi.")
        except:
            await update.message.reply_text("Noto‘g‘ri format!\nMisol: 123456789 15")
        context.user_data.clear()
        return

    if mode == "add_channel":
        settings = load_settings()
        channels = settings.get("channels", [])
        txt = text.lower()
        if txt in ["off", "yo‘q", "o‘chir", "yoq"]:
            settings["channels"] = []
            save_settings(settings)
            await update.message.reply_text("✅ Majburiy obuna o‘chirildi")
        else:
            clean = text.strip().lstrip('@')
            ch = f"@{clean}" if not clean.startswith('@') else clean
            if ch not in channels:
                channels.append(ch)
                settings["channels"] = channels
                save_settings(settings)
                await update.message.reply_text(f"✅ Kanal qo‘shildi: {ch}")
            else:
                await update.message.reply_text(f"Bu kanal allaqachon ro‘yxatda.")
        context.user_data.clear()
        return

    # ─────────────── Oddiy foydalanuvchi kodi ───────────────
    if text in movies:
        if not await check_subscription(context, update.effective_user.id):
            await send_subscription_message(update.message, context)
            return

        m = movies[text]
        movies[text]["views"] = m.get("views", 0) + 1
        users[uid_str]["used"] += 1
        save_movies(movies)
        save_users(users)

        await context.bot.send_video(
            update.effective_chat.id,
            m["file_id"],
            caption=m.get("caption", m["name"])
        )
        return

    # ─── ENG MUHIMI ─── Kod topilmaganda javob beramiz
    if not mode:  # faqat oddiy kod yuborilganda (admin rejimida emas)
        # Bir nechta stiker ID (o‘zingizniki bilan almashtirishingiz mumkin)
        sad_stickers = [
            "CAACAgIAAxkBAAEKAAJlkW5AAW3AAZfZ3v9zAAHsAAIBAQACm7i8AAHs2AABNgQ",  # yig'layotgan
            "CAACAgIAAxkBAAEKAAJlkW5AAW3AAZfZ3v9zAAHsAAIBAQACm7i8AAHs2AABNgQ",
            "CAACAgEAAxkBAAEKAAJlkW5AAW3AAZfZ3v9zAAHsAAIBAQACm7i8AAHs2AABNgQ"
        ]
        try:
            await update.message.reply_sticker(random.choice(sad_stickers))
        except:
            pass  # agar stiker topilmasa jim qoladi

        await update.message.reply_text(
            "❌ Bunday kod topilmadi!\n\n"
            "Iltimos, to‘g‘ri kod yuboring yoki admin panel orqali yangi film qo‘shing 🎥"
        )

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, messages))
    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
