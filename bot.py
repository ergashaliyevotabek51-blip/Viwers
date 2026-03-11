import os
import json
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = "UzbekFilmTV_bot"

USERS_FILE    = "users.json"
MOVIES_FILE   = "movies.json"
SETTINGS_FILE = "settings.json"

FREE_LIMIT = 5
REF_LIMIT  = 5

ADMINS = [774440841, 7818576058]           # ← o'zingizning real ID

# ==================== YORDAMCHI FUNKSİYALAR ====================
def load_json(file, default):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_users():    return load_json(USERS_FILE, {})
def save_users(data): save_json(USERS_FILE, data)

def load_movies():   return load_json(MOVIES_FILE, {})
def save_movies(data): save_json(MOVIES_FILE, data)

def load_settings(): return load_json(SETTINGS_FILE, {"channels": []})
def save_settings(data): save_json(SETTINGS_FILE, data)

def is_admin(uid): return uid in ADMINS

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
    return random.choice(list(movies.keys())) if movies else None

# ==================== MAJBURIY OBUNA ====================
async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    settings = load_settings()
    channels = settings.get("channels", [])
    if not channels:
        return True

    for channel in channels:
        try:
            # kanal nomini to'g'ri formatda olish
            chat_id = channel if channel.startswith("@") else f"@{channel.lstrip('@')}"
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status in ["left", "kicked"]:
                return False
            # member, administrator, creator — hammasi ruxsat
        except Exception as e:
            # bot kanalga qo'shilmagan yoki kanal mavjud emas bo'lsa
            print(f"Obuna tekshiruv xatosi {channel}: {e}")
            return False   # xavfsizroq — xato bo'lsa obuna talab qilamiz
    return True

def subscription_keyboard():
    settings = load_settings()
    kb = []
    for ch in settings.get("channels", []):
        clean = ch.lstrip('@')
        kb.append([InlineKeyboardButton(
            f"🔔 Obuna bo‘ling: @{clean}",
            url=f"https://t.me/{clean}"
        )])
    kb.append([InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(kb)

async def send_subscription_message(msg_or_query, context):
    kb = subscription_keyboard()
    text = "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling va tekshirish tugmasini bosing:"
    if hasattr(msg_or_query, "reply_text"):
        await msg_or_query.reply_text(text, reply_markup=kb)
    else:
        await msg_or_query.edit_message_text(text, reply_markup=kb)

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    name = user.first_name or "Do‘st"

    users = load_users()
    get_user(users, uid)
    save_users(users)

    if not await check_subscription(context, uid):
        await send_subscription_message(update.message, context)
        return

    text = (
        f"Assalomu alaykum, {name}! 👋\n\n"
        f"🎬 <b>UzbekFilmTV</b> — eng sara o‘zbek filmlari va seriallari!\n\n"
        f"Kod yuboring → film darhol keladi\n"
        f"• Bepul: {FREE_LIMIT} ta   • Do‘st uchun: +{REF_LIMIT} ta\n\n"
        f"🚀 Kod yozing yoki do‘stlaringizni taklif qiling!"
    )

    kb = [
        [InlineKeyboardButton("🎟 Mening limitim", callback_data="limit")],
        [InlineKeyboardButton("🎲 Random film",   callback_data="random")],
        [InlineKeyboardButton("🔥 Trend filmlar",  callback_data="trend")]
    ]

    if is_admin(uid):
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# ==================== CALLBACK ====================
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
            await q.edit_message_text("✅ Obuna tasdiqlandi! Botdan foydalanishingiz mumkin 🎥")
        else:
            await send_subscription_message(q.message, context)
        return

    if not await check_subscription(context, uid):
        await send_subscription_message(q.message, context)
        return

    if data == "limit":
        await q.message.reply_text(f"🎟 Limit: {user['used']}/{max_limit(user)}")
        return

    if data == "random":
        code = random_movie(movies)
        if not code:
            await q.message.reply_text("Hozircha hech qanday film yo‘q 😔")
            return
        m = movies[code]
        await context.bot.send_video(q.message.chat_id, m["file_id"], caption=m.get("caption", m["name"]))
        return

    if data == "trend":
        top = trending(movies)
        if not top:
            await q.message.reply_text("Hali trend filmlar yo‘q")
            return
        text = "🔥 Trend filmlar:\n\n" + "\n".join(
            f"{i}. {m['name']} — {m.get('views',0)} ta"
            for i, (_, m) in enumerate(top, 1)
        )
        await q.message.reply_text(text)
        return

    if not is_admin(uid):
        return

    if data == "admin":
        kb = [
            [InlineKeyboardButton("➕ Kino qo‘shish",     callback_data="add")],
            [InlineKeyboardButton("➖ Kino o‘chirish",    callback_data="delete")],
            [InlineKeyboardButton("📊 Statistika",        callback_data="stats")],
            [InlineKeyboardButton("🔥 Top filmlar",       callback_data="top")],
            [InlineKeyboardButton("📢 Broadcast",         callback_data="broadcast")],
            [InlineKeyboardButton("🔒 Majburiy obuna",    callback_data="sub")],
            [InlineKeyboardButton("💠 Limit qo‘shish",    callback_data="limit_add")]
        ]
        await q.message.reply_text("🛠 <b>Admin panel</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    if data == "stats":
        await q.message.reply_text(f"👥 Users: {len(users)}\n🎬 Movies: {len(movies)}")
        return

    if data == "top":
        top = trending(movies)
        text = "🔥 Top filmlar:\n\n" + "\n".join(
            f"{i}. {m['name']} — {m.get('views',0)} ta"
            for i, (_, m) in enumerate(top, 1)
        ) or "Hali film yo‘q"
        await q.message.reply_text(text)
        return

    # rejimga o'tish
    mode_map = {
        "add":       "add_movie",
        "delete":    "delete_movie",
        "broadcast": "broadcast",
        "limit_add": "limit_add",
        "sub":       "add_channel"
    }
    if data in mode_map:
        context.user_data["mode"] = mode_map[data]
        prompts = {
            "add_movie":    "Film/video/document/gif/... yuboring yoki forward qiling",
            "delete_movie": "O‘chirmoqchi bo‘lgan kodni yuboring",
            "broadcast":    "Hammaga yubormoqchi bo‘lgan xabarni yuboring",
            "limit_add":    "Format: user_id limit   (masalan: 123456789 10)",
            "add_channel":  "Kanal username yuboring (masalan: @testkanal)\nO‘chirish uchun: off yoki yo‘q"
        }
        await q.message.reply_text(prompts[mode_map[data]])

# ==================== XABARLAR ====================
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    uid_str = str(update.effective_user.id)
    mode = context.user_data.get("mode")
    text = (message.text or "").strip()

    users  = load_users()
    movies = load_movies()

    # ─── KINO QO‘SHISH ───
    if mode == "add_movie":
        file_id = None
        caption = message.caption or ""

        if message.video:      file_id = message.video.file_id
        elif message.document: file_id = message.document.file_id
        elif message.animation: file_id = message.animation.file_id
        elif message.audio:    file_id = message.audio.file_id
        elif message.voice:    file_id = message.voice.file_id

        if file_id:
            context.user_data["file"]    = file_id
            context.user_data["caption"] = caption
            context.user_data["mode"]    = "movie_code"
            await message.reply_text("✅ Qabul qilindi!\nEndi qisqa kod kiriting (masalan: uzb001)")
        else:
            await message.reply_text("Video/document/gif/audio/voice yuboring yoki forward qiling.")
        return

    if mode == "movie_code":
        if not text:
            await message.reply_text("Kod bo‘sh bo‘lmaydi.")
            return
        context.user_data["code"] = text
        context.user_data["mode"] = "movie_name"
        await message.reply_text("Filmning to‘liq nomini yozing")
        return

    if mode == "movie_name":
        code = context.user_data.get("code")
        if not code or not text:
            await message.reply_text("Xatolik. /start dan boshlang.")
            context.user_data.clear()
            return

        movies[code] = {
            "name": text,
            "file_id": context.user_data["file"],
            "caption": context.user_data.get("caption", text),
            "views": 0
        }
        save_movies(movies)
        await message.reply_text(f"🎉 Qo‘shildi!\nKod: {code}\nNom: {text}")
        context.user_data.clear()
        return

    # ─── Boshqa admin rejimlari ───
    if mode == "delete_movie":
        if text in movies:
            del movies[text]
            save_movies(movies)
            await message.reply_text(f"O‘chirildi: {text}")
        else:
            await message.reply_text("Topilmadi.")
        context.user_data.clear()
        return

    if mode == "broadcast":
        count = 0
        for u in users:
            try:
                await message.copy(chat_id=int(u))
                count += 1
            except:
                pass
        await message.reply_text(f"{count} ta userga yuborildi.")
        context.user_data.clear()
        return

    if mode == "limit_add":
        try:
            uid2, lim = text.split(maxsplit=1)
            users[uid2]["limit"] = int(lim)
            save_users(users)
            await message.reply_text(f"{uid2} limiti {lim} ga o‘zgartirildi.")
        except:
            await message.reply_text("Format: user_id limit")
        context.user_data.clear()
        return

    if mode == "add_channel":
        settings = load_settings()
        channels = settings.get("channels", [])

        txt = text.strip().lower()
        if txt in ("off", "yo‘q", "o‘chir", "yoq"):
            settings["channels"] = []
            save_settings(settings)
            await message.reply_text("✅ Majburiy obuna o‘chirildi")
            context.user_data.clear()
            return

        # username ni tozalash
        clean = text.strip().lstrip('@').split()[0]  # birinchi so‘z
        if not clean:
            await message.reply_text("Kanal nomi bo‘sh bo‘lmaydi.")
            return

        channel_name = f"@{clean}"

        if channel_name in channels:
            await message.reply_text(f"Bu kanal allaqachon qo‘shilgan: {channel_name}")
        else:
            channels.append(channel_name)
            settings["channels"] = channels
            save_settings(settings)
            await message.reply_text(f"✅ Qo‘shildi: {channel_name}\n\n"
                                     f"Test qilish uchun /start bosing yoki boshqa kanal qo‘shing.")

        context.user_data.clear()
        return

    # ─── Oddiy foydalanuvchi kod yuborsa ───
    if text and text in movies:
        if not await check_subscription(context, update.effective_user.id):
            await send_subscription_message(message, context)
            return

        m = movies[text]
        movies[text]["views"] = m.get("views", 0) + 1
        users[uid_str]["used"] += 1
        save_movies(movies)
        save_users(users)

        await context.bot.send_video(
            message.chat_id,
            m["file_id"],
            caption=m.get("caption", m["name"])
        )
        return

    # Kod topilmadi
    if text and not mode:
        await message.reply_text("❌ Bunday kod mavjud emas!\nTo‘g‘ri kod yozing.")

# ==================== MAIN ====================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, messages))

    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
