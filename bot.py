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
TOKEN = "8370792264:AAFC0Zym1W3t_2yI1AipjI-lhmjouwclFNI"  # BotFather token
BOT_USERNAME = "UzbekFilmTV_bot"

# Bir nechta admin
ADMIN_IDS = [774440841, 7818576058]

BOT_USERNAME = "UzbekFilmTv_bot"

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"
SETTINGS_FILE = "settings.json"

FREE_LIMIT = 5
REF_LIMIT = 5

# ================= SETTINGS =================
def load_settings():
    default = {"mandatory_channels": [], "admins": ADMIN_IDS}
    if not os.path.exists(SETTINGS_FILE):
        save_json(SETTINGS_FILE, default)
        return default
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file,'w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

settings = load_settings()
MANDATORY_CHANNELS = settings.get("mandatory_channels", [])
ADMIN_IDS = settings.get("admins", ADMIN_IDS)

# ================= USERS & MOVIES =================
def load_json_file(file, default):
    if not os.path.exists(file):
        save_json(file, default)
        return default
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

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

    if not await is_subscribed(context, user.id):
        await send_subscription_message(update.message)
        return

    args = context.args
    if args and args[0].isdigit():
        ref_id = args[0]
        if ref_id != str(user.id) and ref_id in users and u.get("refed") is None:
            users[ref_id]["referrals"] += 1
            u["refed"] = ref_id
            save_users()

    text = (
        f"<b>Assalomu alaykum, {user.first_name}!</b> 👋\n\n"
        f"🎬 UzbekFilmTV — eng sara o‘zbek filmlari shu yerdagi bot!\n\n"
        f"🔥 Kod yuboring (masalan: 12, 45, 107) → kino darhol keladi\n"
        f"• Bepul: 5 ta\n• Do‘st uchun: +5 ta\n\n"
        f"🚀 Kodni yozing yoki do‘stlaringizni taklif qiling!"
    )

    kb=[
        [InlineKeyboardButton("📊 Mening limitim", callback_data="my_limit")],
        [InlineKeyboardButton("🎬 Random film", callback_data="random_film")],
        [InlineKeyboardButton("🔥 Trend film", callback_data="trend_film")]
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
            await q.message.reply_sticker("CAACAgIAAxkBAAEJk1hg1Rj0x1_YourStickerID")
        else:
            await send_subscription_message(q.message)
        return

    if q.data=="my_limit":
        await q.message.reply_text(f"📊 Sizning limitingiz: {u['used']}/{max_limit(u)}")
        return

# ================= ADMIN LIMIT =================
async def handle_admin_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    uid = str(update.effective_user.id)
    if int(uid) in ADMIN_IDS and text.lower().startswith("limit "):
        try:
            _, target_uid, extra = text.split()
            target_uid = str(target_uid)
            extra = int(extra)
            if target_uid in users:
                users[target_uid]["referrals"] += extra // REF_LIMIT
                save_users()
                await update.message.reply_text(f"✅ User {target_uid} ga qo‘shimcha limit berildi!")
            else:
                await update.message.reply_text("❌ Bunday user topilmadi")
        except:
            await update.message.reply_text("Format noto‘g‘ri!\nMisol: limit 123456789 15")
        return

# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_admin_limit(update, context)
    # Shu yerga kino kodi, Random/Trend/Next film, broadcast va referral logikasi qo‘shiladi

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
