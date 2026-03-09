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
TOKEN = os.getenv("BOT_TOKEN")

# Adminlar
ADMIN_IDS = [123456789, 987654321]  # Shu yerga boshqa admin ID qo‘shing

BOT_USERNAME = "UzbekFilmTv_bot"
CHANNEL_USERNAME = "@UzbekFilmTv_Kanal"

# Majburiy kanallar
MANDATORY_CHANNELS = ["@Kanal1", "@Kanal2"]

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"
SETTINGS_FILE = "settings.json"

FREE_LIMIT = 5
REF_LIMIT = 5

# ================= UTILS =================
def load_json(file, default):
    if not os.path.exists(file):
        with open(file,'w',encoding='utf-8') as f:
            json.dump(default,f,ensure_ascii=False,indent=2)
        return default
    try:
        with open(file,'r',encoding='utf-8') as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file,'w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def load_users():
    data = load_json(USERS_FILE,{})
    cleaned = {}
    for k,v in data.items():
        try:
            uid = str(int(k))
            cleaned[uid] = {
                "used": int(v.get("used",0)),
                "referrals": int(v.get("referrals",0)),
                "joined": v.get("joined", datetime.utcnow().isoformat()),
                "refed": v.get("refed",None)
            }
        except:
            continue
    save_json(USERS_FILE,cleaned)
    return cleaned

def save_users(data):
    save_json(USERS_FILE,data)

def load_movies():
    return load_json(MOVIES_FILE,{})

def save_movies(data):
    save_json(MOVIES_FILE,data)

def get_user(users, uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {"used":0,"referrals":0,"joined":datetime.utcnow().isoformat(),"refed":None}
        save_users(users)
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
    users = load_users()
    me = get_user(users,user.id)

    # Majburiy obuna
    if not await is_subscribed(context,user.id):
        await send_subscription_message(update.message)
        return

    # Referral tekshiruvi
    args = context.args
    if args and args[0].isdigit():
        ref_id = args[0]
        if ref_id != str(user.id) and ref_id in users and me.get("refed") is None:
            users[ref_id]["referrals"] += 1
            me["refed"] = ref_id
            try:
                await context.bot.send_message(int(ref_id), f"🎉 Yangi do‘st kirdi! Referral: {users[ref_id]['referrals']}")
            except:
                pass
            save_users(users)

    text = (
        f"<b>Assalomu alaykum, {user.first_name}!</b> 👋\n\n"
        f"🎬 <b>UzbekFilmTV</b> — eng sara o‘zbek filmlari shu yerdagi bot!\n\n"
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

# ================= CALLBACKS =================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data
    users = load_users()
    user = get_user(users,uid)

    if data=="check_sub":
        if await is_subscribed(context,uid):
            await q.edit_message_text("✅ Hammaga obuna! Endi botdan foydalanishingiz mumkin!")
            await q.message.reply_sticker("CAACAgIAAxkBAAEJk1hg1Rj0x1_YourStickerID")
        else:
            await send_subscription_message(q.message)
        return

    if data=="my_limit":
        await q.message.reply_text(f"📊 Sizning limitingiz: {user['used']}/{max_limit(user)}")
        return

# ================= ADMIN LIMIT =================
async def handle_admin_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    uid = str(update.effective_user.id)
    users = load_users()
    if int(uid) in ADMIN_IDS and text.lower().startswith("limit "):
        try:
            _, target_uid, extra = text.split()
            extra = int(extra)
            target_uid = str(target_uid)
            if target_uid in users:
                users[target_uid]["referrals"] += extra // REF_LIMIT
                save_users(users)
                await update.message.reply_text(
                    f"✅ User {target_uid} ga qo‘shimcha limit berildi!\n"
                    f"Yangi referrals: {users[target_uid]['referrals']}\n"
                    f"Jami limit: {max_limit(users[target_uid])}"
                )
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
