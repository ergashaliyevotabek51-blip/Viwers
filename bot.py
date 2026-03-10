import os
import json
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")  # Railway yoki boshqa joyda BOT_TOKEN deb saqlang
BOT_USERNAME = "UzbekFilmTV_bot"

USERS_FILE    = "users.json"
MOVIES_FILE   = "movies.json"
SETTINGS_FILE = "settings.json"

FREE_LIMIT = 5
REF_LIMIT  = 5

DEFAULT_ADMINS = [774440841]  # o'zingizning ID'ingizni qoldiring
MANDATORY_CHANNELS = []       # admin paneldan sozlanadi

# ================= HELPERS =================
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

# ================= SUBSCRIPTION =================
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

# ================= ADMIN KEYBOARD =================
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

# ================= START HANDLER =================
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
        f"🎬 <b>UzbekFilmTV</b> — eng sara o‘zbek filmlari!\n\n"
        f"Kod yuboring → film darhol keladi\n"
        f"• Bepul: {FREE_LIMIT} ta   • Do‘st uchun: +{REF_LIMIT} ta\n\n"
        f"🚀 Kodni yozing yoki do‘stlaringizni taklif qiling!"
    )
    kb = [
        [InlineKeyboardButton("🎟 Mening limitim", callback_data="my_limit")],
        [InlineKeyboardButton("🎬 Random film", callback_data="rand_movie")],
        [InlineKeyboardButton("🔥 Trend filmlar", callback_data="trend_movie")]
    ]
    if is_admin(uid):
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# ================= CALLBACK HANDLER =================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data
    users = load_users()
    movies = load_movies()
    user = get_user(users, uid)

    if data == "my_limit":
        await q.message.reply_text(
            f"🔢 Limitingiz: {user['used']}/{max_limit(user)}\n"
            f"Do‘stlar soni: {user['referrals']}"
        )
        return

    if data == "rand_movie":
        code = random_movie(movies)
        if code:
            m = movies[code]
            if "file_id" in m:
                if m["file_type"] == "video":
                    await context.bot.send_video(q.message.chat_id, m["file_id"], caption=m["name"])
                else:
                    await context.bot.send_document(q.message.chat_id, m["file_id"], caption=m["name"])
            else:
                await q.message.reply_text(f"🎬 {m['name']}\n{m.get('file', 'Havola yo‘q')}")
        else:
            await q.message.reply_text("Hozircha filmlar yo‘q")
        return

    if data == "trend_movie":
        top = trending(movies)
        text = "🔥 Trend filmlar:\n\n"
        for i, (code, m) in enumerate(top, 1):
            text += f"{i}. {m['name']} — {m.get('views', 0)} ta\n"
        await q.message.reply_text(text)
        return

    if not is_admin(uid):
        return

    if data == "admin":
        await q.message.reply_text("🛠 Admin panel", reply_markup=admin_keyboard())

    elif data == "add_movie_forward":
        context.user_data["mode"] = "wait_movie_forward"
        await q.message.reply_text("Kinoni (video yoki document) botga forward qiling:")

    elif data == "delete_movie":
        context.user_data["mode"] = "delete_movie"
        await q.message.reply_text("O‘chirish uchun kodni yuboring:")

    elif data == "stats":
        await q.message.reply_text(f"👥 Foydalanuvchilar: {len(users)}\n🎬 Filmlar: {len(movies)}")

    elif data == "top_movies":
        top = trending(movies)
        text = "🔥 Top 10 filmlar:\n\n"
        for i, (code, m) in enumerate(top, 1):
            text += f"{i}. {m['name']} — {m.get('views', 0)}\n"
        await q.message.reply_text(text)

    elif data == "broadcast":
        context.user_data["mode"] = "wait_broadcast"
        await q.message.reply_text("Xabarni yuboring (/cancel — bekor qilish)")

    elif data == "subscription":
        context.user_data["mode"] = "set_subscription"
        current = ", ".join(MANDATORY_CHANNELS) or "yo‘q"
        await q.message.reply_text(f"Majburiy kanallar: {current}\n\nYangi kanal yoki off/yo‘q")

    elif data == "add_limit":
        context.user_data["mode"] = "add_limit"
        await q.message.reply_text("user_id yangi_limit\nMasalan: 123456789 20")

    elif data == "next_movie":
        code = random_movie(movies)
        if code:
            m = movies[code]
            if "file_id" in m:
                if m["file_type"] == "video":
                    await context.bot.send_video(q.message.chat_id, m["file_id"], caption=m["name"])
                else:
                    await context.bot.send_document(q.message.chat_id, m["file_id"], caption=m["name"])
            else:
                await q.message.reply_text(f"🎬 {m['name']}\n{m.get('file', 'Havola yo‘q')}")
        return

    elif data == "check_sub":
        if await check_user_subscribed(context, uid):
            await q.edit_message_text("✅ Obuna tasdiqlandi!")
        else:
            await q.edit_message_text("❌ Hali obuna bo‘lmagansiz")

# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    uid_str = str(update.effective_user.id)
    users = load_users()
    movies = load_movies()
    user = get_user(users, uid_str)
    mode = context.user_data.get("mode", "")

    if text.lower() == "/cancel":
        context.user_data.clear()
        await update.message.reply_text("❌ Bekor qilindi")
        return

    if is_admin(update.effective_user.id):

        if mode == "add_limit":
            try:
                parts = text.split()
                target_id = parts[0]
                new_limit = int(parts[1])
                target = get_user(users, target_id)
                old = target.get("limit", FREE_LIMIT)
                target["limit"] = new_limit
                save_users(users)
                await update.message.reply_text(f"✅ {target_id}: {old} → {new_limit}")
            except:
                await update.message.reply_text("Format: user_id limit")
            context.user_data.pop("mode", None)
            return

        if mode == "wait_movie_forward":
            if update.message.video:
                file_id = update.message.video.file_id
                file_type = "video"
            elif update.message.document:
                file_id = update.message.document.file_id
                file_type = "document"
            else:
                await update.message.reply_text("Iltimos, video yoki document forward qiling")
                return

            context.user_data["movie_file_id"] = file_id
            context.user_data["movie_file_type"] = file_type
            context.user_data["mode"] = "add_movie_name_forward"
            await update.message.reply_text("Film nomini yuboring:")
            return

        if mode == "add_movie_name_forward":
            context.user_data["movie_name"] = text
            context.user_data["mode"] = "add_movie_code_forward"
            await update.message.reply_text("Kod tanlang (masalan: film01, nussa777, super):")
            return

        if mode == "add_movie_code_forward":
            code = text.strip()
            if code in movies:
                await update.message.reply_text("❌ Bu kod allaqachon band!")
                return

            file_id = context.user_data.get("movie_file_id")
            file_type = context.user_data.get("movie_file_type")
            name = context.user_data.get("movie_name", "Noma'lum film")

            movies[code] = {
                "name": name,
                "file_id": file_id,
                "file_type": file_type,
                "views": 0
            }
            save_movies(movies)
            await update.message.reply_text(
                f"✅ Film qo‘shildi!\nKod: {code}\nNomi: {name}\nTuri: {file_type}"
            )
            context.user_data.clear()
            return

        if mode == "delete_movie":
            if text in movies:
                name = movies[text]["name"]
                del movies[text]
                save_movies(movies)
                await update.message.reply_text(f"🗑 {name} ({text}) o‘chirildi")
            else:
                await update.message.reply_text("Kod topilmadi")
            context.user_data.clear()
            return

        if mode == "wait_broadcast":
            count = 0
            for u in users:
                try:
                    await update.message.copy(chat_id=int(u))
                    count += 1
                except:
                    pass
            await update.message.reply_text(f"Xabar {count} kishiga yetkazildi")
            context.user_data.clear()
            return

        if mode == "set_subscription":
            global MANDATORY_CHANNELS
            if text.lower() in ["off", "yo‘q", "o‘chir"]:
                MANDATORY_CHANNELS = []
                await update.message.reply_text("Majburiy obuna o‘chirildi")
            else:
                ch = text.strip()
                if not ch.startswith("@"):
                    ch = "@" + ch
                if ch not in MANDATORY_CHANNELS:
                    MANDATORY_CHANNELS.append(ch)
                    await update.message.reply_text(f"Kanal qo‘shildi: {ch}")
            context.user_data.pop("mode", None)
            return

    # USER KOD YOZSA
    if text in movies:
        if not await check_user_subscribed(context, update.effective_user.id):
            await send_subscription_message(update.message, context)
            return

        m = movies[text]
        movies[text]["views"] = m.get("views", 0) + 1
        user["used"] += 1
        save_movies(movies)
        save_users(users)

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Keyingi film", callback_data="next_movie")],
            [InlineKeyboardButton("🔗 Ulashish", url=f"https://t.me/{BOT_USERNAME}")]
        ])

        if "file_id" in m and m["file_id"]:
            if m["file_type"] == "video":
                await context.bot.send_video(
                    update.effective_chat.id,
                    m["file_id"],
                    caption=f"🎬 <b>{m['name']}</b>",
                    reply_markup=kb,
                    parse_mode="HTML"
                )
            else:
                await context.bot.send_document(
                    update.effective_chat.id,
                    m["file_id"],
                    caption=f"🎬 <b>{m['name']}</b>",
                    reply_markup=kb,
                    parse_mode="HTML"
                )
        else:
            await update.message.reply_text(
                f"🎬 <b>{m['name']}</b>\n\nHavola: {m.get('file', 'yo‘q')}",
                reply_markup=kb,
                parse_mode="HTML"
            )
        return

    await update.message.reply_text("Bunday kod topilmadi")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    # Forward qilingan media uchun handler
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, message_handler))

    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
