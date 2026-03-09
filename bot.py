import os
import json
import random
import asyncio
from datetime import datetime
from urllib.parse import quote
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

# ================= CONFIG =================
TOKEN = os.getenv("8370792264:AAFC0Zym1W3t_2yI1AipjI-lhmjouwclFNI")
BOT_USERNAME = "UzbekFilmTv_bot"
CHANNEL_USERNAME = "@UzbekFilmTv_Kanal"

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"
SETTINGS_FILE = "settings.json"

FREE_LIMIT = 5
REF_LIMIT = 5

# ================= HELPERS =================
def save_json(file, data):
    with open(file,'w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def load_json_file(file, default):
    if not os.path.exists(file):
        save_json(file, default)
        return default
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

# ================= SETTINGS =================
settings = load_json_file(SETTINGS_FILE, {"mandatory_channels": [], "admins": []})
MANDATORY_CHANNELS = settings.get("mandatory_channels", [])
ADMIN_IDS = settings.get("admins", [])

# ================= USERS & MOVIES =================
users = load_json_file(USERS_FILE, {})
movies = load_json_file(MOVIES_FILE, {})

def save_users():
    save_json(USERS_FILE, users)

def save_movies():
    save_json(MOVIES_FILE, movies)

def get_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {"used":0,"referrals":0,"joined":datetime.utcnow().isoformat(),"refed":None}
        save_users()
    return users[uid]

def max_limit(user):
    return FREE_LIMIT + user["referrals"] * REF_LIMIT

# ================= SUBSCRIPTION =================
async def is_subscribed(context, uid):
    if not MANDATORY_CHANNELS:
        return True
    for ch in MANDATORY_CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, uid)
            if member.status not in ["member","administrator","creator"]:
                return False
        except:
            return False
    return True

async def send_subscription_message(message):
    uid = message.from_user.id
    kb=[]
    for ch in MANDATORY_CHANNELS:
        try:
            member = await message.bot.get_chat_member(ch, uid)
            status = "✅" if member.status in ["member","administrator","creator"] else "❌"
        except:
            status = "❌"
        kb.append([InlineKeyboardButton(f"{ch} {status}", url=f"https://t.me/{ch.lstrip('@')}")])
    kb.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")])
    await message.reply_text(
        "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:\nObuna bo‘lganingizdan keyin 'Tekshirish' tugmasini bosing.",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user.id)

    if MANDATORY_CHANNELS and not await is_subscribed(context, user.id):
        await send_subscription_message(update.message)
        return

    text = (
        f"<b>Assalomu alaykum, {user.first_name}!</b> 👋\n\n"
        f"🎬 UzbekFilmTV — eng sara o‘zbek filmlari shu yerdagi bot!\n\n"
        f"🔥 Kod yuboring (masalan: 12, 45, 107) → kino darhol keladi\n"
        f"• Bepul: 5 ta   • Do‘st uchun: +5 ta\n\n"
        f"🚀 Kodni yozing yoki do‘stlaringizni taklif qiling!"
    )

    kb=[
        [InlineKeyboardButton("📊 Mening limitim", callback_data="my_limit")],
        [InlineKeyboardButton("🎬 Random Film", callback_data="random_film")],
        [InlineKeyboardButton("🔥 Trend Film", callback_data="trend_film")]
    ]
    if user.id in ADMIN_IDS:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# ================= CALLBACK HANDLER =================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = get_user(uid)

    if q.data=="check_sub":
        if await is_subscribed(context, uid):
            await q.edit_message_text("✅ Hammaga obuna! Endi botdan foydalanishingiz mumkin!")
        else:
            await send_subscription_message(q.message)
        return

    if q.data=="my_limit":
        await q.message.reply_text(f"📊 Sizning limitingiz: {u['used']}/{max_limit(u)}")
        return

    if q.data=="random_film":
        if not movies:
            await q.message.reply_text("❌ Hozircha kinolar yo‘q.")
            return
        code = random.choice(list(movies.keys()))
        await send_movie(q.message, uid, code)
        return

    if q.data=="trend_film":
        if not movies:
            await q.message.reply_text("❌ Hozircha kinolar yo‘q.")
            return
        # trend = top 10 so‘ralgan kinolar
        trend = sorted(movies.items(), key=lambda x: x[1].get("used",0), reverse=True)[:10]
        text="🔥 Trend kinolar:\n"
        for code, val in trend:
            text+=f"{code} | {val}\n"
        await q.message.reply_text(text)
        return

    if q.data=="admin" and uid in ADMIN_IDS:
        kb = [
            [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add")],
            [InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete")],
            [InlineKeyboardButton("📃 Kinolar ro‘yxati", callback_data="list_movies")],
            [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
            [InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast")],
            [InlineKeyboardButton("🔒 Majburiy obuna", callback_data="subscription")],
            [InlineKeyboardButton("🎯 Limit berish", callback_data="give_limit")]
        ]
        await q.edit_message_text("🛠 Admin panel", reply_markup=InlineKeyboardMarkup(kb))
        return

# ================= SEND MOVIE =================
async def send_movie(message, uid, code):
    u = get_user(uid)
    if u["used"] >= max_limit(u):
        await message.reply_text("🔒 Limit tugadi! Do‘stlaringizni taklif qiling!")
        return
    u["used"] +=1
    save_users()
    val = movies[code]
    await message.reply_text(f"🎬 Kino tayyor: {val}\nQolgan: {max_limit(u)-u['used']}/{max_limit(u)}")

# ================= ADMIN LIMIT =================
async def handle_admin_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    uid = update.effective_user.id
    if uid in ADMIN_IDS and text.lower().startswith("limit "):
        try:
            _, target_uid, extra = text.split()
            target_uid = str(target_uid)
            extra = int(extra)
            if target_uid in users:
                users[target_uid]["referrals"] += extra // REF_LIMIT
                save_users()
                await update.message.reply_text(f"✅ User {target_uid} ga qo‘shimcha limit berildi!\nYangi limit: {max_limit(users[target_uid])}")
            else:
                await update.message.reply_text("❌ Bunday user topilmadi")
        except:
            await update.message.reply_text("Format noto‘g‘ri!\nMisol: limit 123456789 15")
        return

# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_admin_limit(update, context)
    await update.message.reply_text("🎬 Kodni yuboring yoki admin uchun /admin yozing")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
