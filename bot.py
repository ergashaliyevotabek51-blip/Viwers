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
TOKEN = os.getenv("BOT_TOKEN")  # Railway Variables da BOT_TOKEN sifatida bo'lishi kerak
BOT_USERNAME = "UzbekFilmTV_bot"

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"
SETTINGS_FILE = "settings.json"

FREE_LIMIT = 5
REF_LIMIT = 5

# ================= ADMIN & CHANNELS =================
DEFAULT_ADMINS = [774440841]
MANDATORY_CHANNELS = []  # Admin panel orqali sozlanadi

# ================= HELPERS =================
def load_json(file, default):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data,f, indent=4)

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
    uid=str(uid)
    if uid not in users:
        users[uid] = {"used":0,"referrals":0,"limit":FREE_LIMIT,"joined":datetime.utcnow().isoformat()}
    return users[uid]

def max_limit(user):
    return user.get("limit", FREE_LIMIT) + user["referrals"]*REF_LIMIT

def load_movies():
    return load_json(MOVIES_FILE, {})

def save_movies(movies):
    save_json(MOVIES_FILE, movies)

def trending(movies_dict):
    return sorted(movies_dict.items(), key=lambda x:x[1].get("views",0), reverse=True)[:10]

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
            if member.status not in ["member","administrator","creator"]:
                return False
        except:
            return False
    return True

def subscription_keyboard(status):
    kb=[]
    for ch,val in status.items():
        icon="✅" if val else "❌"
        kb.append([InlineKeyboardButton(f"{icon} {ch}", url=f"https://t.me/{ch.lstrip('@')}")])
    kb.append([InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(kb)

async def send_subscription_message(message, context):
    status = {}
    for ch in MANDATORY_CHANNELS:
        status[ch] = False
    kb = subscription_keyboard(status)
    await message.reply_text(
        "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=kb
    )

# ================= ADMIN KEYBOARD =================
def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie"),
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
        f"🎬 <b>UzbekFilmTV</b> — eng sara o‘zbek filmlari shu yerdagi bot!\n\n"
        f"🔥 Kod yuboring (masalan: 12, 45, 107) → kino darhol keladi\n"
        f"• Bepul: 5 ta   • Do‘st uchun: +5 ta\n\n"
        f"🚀 Kodni yozing yoki do‘stlaringizni taklif qiling!"
    )
    kb = [
        [InlineKeyboardButton("🎟 Mening limitim", callback_data="my_limit")],
        [InlineKeyboardButton("🎬 Random film", callback_data="rand_movie")],
        [InlineKeyboardButton("🔥 Trend film", callback_data="trend_movie")]
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

    # ================= USER BUTTONS =================
    if data=="my_limit":
        await q.message.reply_text(f"🔢 Sizning limitingiz: {user['used']}/{max_limit(user)}\nDo‘stlar: {user['referrals']}")
        return
    elif data=="rand_movie":
        code = random_movie(movies)
        if code:
            m = movies[code]
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Keyingi film", callback_data="next_movie")],
                [InlineKeyboardButton("🔗 Ulashish", url=f"https://t.me/{BOT_USERNAME}")]
            ])
            await q.message.reply_text(f"🎬 {m['name']}\n📥 Yuklab olish: {m['file']}", reply_markup=kb)
        else:
            await q.message.reply_text("❌ Hozircha kinolar yo‘q")
        return
    elif data=="trend_movie":
        top = trending(movies)
        text="🔥 Trend filmlar:\n"
        for i,(code,m) in enumerate(top,1):
            text+=f"{i}. {m['name']} — {m.get('views',0)}\n"
        await q.message.reply_text(text)
        return

    # ================= ADMIN BUTTONS =================
    if not is_admin(uid):
        return

    mode = context.user_data.get("mode")
    if data=="admin":
        await q.message.reply_text("🛠 Admin panel", reply_markup=admin_keyboard())
    elif data=="add_movie":
        context.user_data["mode"]="add_movie"
        await q.message.reply_text("Kino postini forward qiling")
    elif data=="delete_movie":
        context.user_data["mode"]="delete_movie"
        await q.message.reply_text("O‘chirish uchun kino kodini yuboring")
    elif data=="stats":
        await q.message.reply_text(f"👥 Userlar: {len(users)}\n🎬 Kinolar: {len(movies)}")
    elif data=="top_movies":
        top = trending(movies)
        text="🔥 Top 10 filmlar\n\n"
        for i,(code,m) in enumerate(top,1):
            text+=f"{i}. {m['name']} — {m.get('views',0)}\n"
        await q.message.reply_text(text)
    elif data=="broadcast":
        context.user_data["mode"]="wait_broadcast"
        await q.message.reply_text("📢 Omaviy xabar rejimi. Xabar yuboring. /cancel bilan bekor qilish")
    elif data=="subscription":
        context.user_data["mode"]="set_subscription"
        current = ", ".join(MANDATORY_CHANNELS) if MANDATORY_CHANNELS else "Majburiy kanal yo‘q"
        await q.message.reply_text(f"Hozirgi majburiy kanallar: {current}\nYangi kanal username yuboring (@Channel)\nYo‘q qilish uchun: off yoki yo‘q")
    elif data=="add_limit":
        context.user_data["mode"]="add_limit"
        await q.message.reply_text("Limit qo‘shish uchun: user_id limit_miqdor (masalan: 116 10)")
    elif data=="next_movie":
        code = random_movie(movies)
        if code:
            m = movies[code]
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Keyingi film", callback_data="next_movie")],
                [InlineKeyboardButton("🔗 Ulashish", url=f"https://t.me/{BOT_USERNAME}")]
            ])
            await q.message.reply_text(f"🎬 {m['name']}\n📥 Yuklab olish: {m['file']}", reply_markup=kb)
    elif data=="check_sub":
        if await check_user_subscribed(context, uid):
            await q.edit_message_text("✅ Hammaga obuna! Botdan foydalanishingiz mumkin!")
        else:
            await q.edit_message_text("❌ Hali barcha kanallarga obuna bo‘lmagansiz")

# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    uid = str(update.effective_user.id)
    users = load_users()
    movies = load_movies()
    user = get_user(users, uid)
    mode = context.user_data.get("mode")

    if uid not in users:
        users[uid]=user

    # CANCEL
    if text.lower()=="/cancel":
        context.user_data.clear()
        await update.message.reply_text("❌ Bekor qilindi")
        return

    # ================= ADMIN MODES =================
    if mode=="add_limit" and is_admin(int(uid)):
        try:
            parts = text.split()
            target_id = parts[0]
            limit_amount = int(parts[1])
            target_user = get_user(users, target_id)
            target_user["limit"]=limit_amount
            save_users(users)
            await update.message.reply_text(f"✅ {target_id} foydalanuvchiga {limit_amount} limit berildi")
        except:
            await update.message.reply_text("❌ Format: user_id limit_miqdor")
        context.user_data.pop("mode", None)
        return

    # ================= SUBSCRIPTION =================
    if mode=="set_subscription" and is_admin(int(uid)):
        global MANDATORY_CHANNELS
        if text.lower() in ["off","yo‘q"]:
            MANDATORY_CHANNELS=[]
            await update.message.reply_text("✅ Majburiy obuna o‘chirildi")
        else:
            ch = text.strip()
            if not ch.startswith("@"):
                ch = "@"+ch
            MANDATORY_CHANNELS.append(ch)
            await update.message.reply_text(f"✅ Kanal qo‘shildi: {ch}")
        context.user_data.pop("mode",None)
        return

    # ================= BROADCAST =================
    if mode=="wait_broadcast" and is_admin(int(uid)):
        for u in users.keys():
            try:
                await update.message.copy(chat_id=int(u))
            except:
                continue
        await update.message.reply_text("📤 Omaviy xabar yuborildi")
        context.user_data.clear()
        return

    # ================= ADD MOVIE =================
    if mode=="add_movie" and is_admin(int(uid)):
        if update.message.forward_from_chat:
            context.user_data["movie_msg"] = update.message.forward_from_message_id
            context.user_data["movie_chat"] = update.message.forward_from_chat.id
            context.user_data["mode"] = "movie_name"
            await update.message.reply_text("Endi film nomini yuboring")
            return

    if mode=="movie_name" and is_admin(int(uid)):
        name=text
        code=str(len(movies)+1)
        chat=str(context.user_data["movie_chat"]).replace("-100","")
        msg=context.user_data["movie_msg"]
        link=f"https://t.me/c/{chat}/{msg}"
        movies[code]={"name":name,"file":link,"views":0}
        save_movies(movies)
        await update.message.reply_text(f"✅ Kino qo‘shildi\nKod: {code}")
        context.user_data.clear()
        return

    # ================= DELETE MOVIE =================
    if mode=="delete_movie" and is_admin(int(uid)):
        if text in movies:
            del movies[text]
            save_movies(movies)
            await update.message.reply_text("🗑 O‘chirildi")
        else:
            await update.message.reply_text("❌ Kod topilmadi")
        context.user_data.clear()
        return

    # ================= SHOW MOVIE =================
    if text in movies:
        if not await check_user_subscribed(context, int(uid)):
            await send_subscription_message(update.message, context)
            return
        m = movies[text]
        movies[text]["views"] += 1
        user["used"] += 1
        save_movies(movies)
        save_users(users)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Keyingi film", callback_data="next_movie")],
            [InlineKeyboardButton("🔗 Ulashish", url=f"https://t.me/{BOT_USERNAME}")]
        ])
        await update.message.reply_text(f"🎬 {m['name']}\n📥 Yuklab olish: {m['file']}", reply_markup=kb)
        return

    await update.message.reply_text("❌ Bunday kod topilmadi")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__=="__main__":
    main()
