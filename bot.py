import json
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================
TOKEN = "YOUR_BOT_TOKEN_HERE"  # BotFather token
BOT_USERNAME = "UzbekFilmTV_bot"

# Adminlar
ADMIN_IDS = [774440841, 7818576058]

# Majburiy kanallar
MANDATORY_CHANNELS = []  # @kanalusername qo‘shiladi

# Fayllar
USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"

# Limitlar
FREE_LIMIT = 5
REF_LIMIT = 5

# ================= DATA =================
try:
    with open(MOVIES_FILE, "r") as f:
        movies = json.load(f)
except:
    movies = {}

try:
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
except:
    users = {}

# ================= HELPERS =================
def save_movies(data):
    with open(MOVIES_FILE,"w") as f:
        json.dump(data,f)

def save_users():
    with open(USERS_FILE,"w") as f:
        json.dump(users,f)

def is_admin(uid):
    return uid in ADMIN_IDS

def max_limit(user):
    return FREE_LIMIT + user.get("referrals",0)*REF_LIMIT

def trending(movies_dict):
    return sorted(movies_dict.items(), key=lambda x:x[1].get("views",0), reverse=True)[:10]

def random_movie(movies_dict):
    if not movies_dict:
        return None
    return random.choice(list(movies_dict.keys()))

# ================= ADMIN KEYBOARD =================
def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie"),
            InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete_movie")
        ],
        [
            InlineKeyboardButton("📊 Statistika", callback_data="stats"),
            InlineKeyboardButton("🔥 Top filmlar", callback_data="top_movies")
        ],
        [
            InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast"),
            InlineKeyboardButton("🔒 Majburiy obuna", callback_data="subscription")
        ],
        [
            InlineKeyboardButton("➕ Limit qo‘shish", callback_data="add_limit")
        ]
    ])

# ================= SUBSCRIPTION =================
async def is_subscribed(context, user_id):
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

async def send_subscription_message(message):
    kb=[]
    for ch in MANDATORY_CHANNELS:
        kb.append([InlineKeyboardButton(f"{ch} ❌", url=f"https://t.me/{ch.lstrip('@')}")])
    kb.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")])
    await message.reply_text(
        "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", 
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    fname = update.effective_user.first_name
    if uid not in users:
        users[uid] = {"used":0,"referrals":0,"joined":datetime.utcnow().isoformat()}
        save_users()

    # Majburiy obuna tekshirish
    if not await is_subscribed(context, int(uid)):
        await send_subscription_message(update.message)
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

    if is_admin(int(uid)):
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# ================= CALLBACK HANDLER =================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(q.from_user.id)
    data = q.data

    if data=="my_limit":
        user = users.get(uid,{"used":0,"referrals":0})
        await q.message.reply_text(f"🔢 Sizning limitingiz: {user['used']}/{max_limit(user)}\nDo‘stlar: {user['referrals']}")
        return

    elif data=="rand_movie":
        code = random_movie(movies)
        if code:
            m = movies[code]
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Keyingi film", callback_data="next_movie")]])
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

    # ================= ADMIN =================
    if not is_admin(int(uid)):
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
        await q.message.reply_text(
            f"Hozirgi majburiy kanallar: {current}\nYangi kanal username yuboring (masalan: @MyChannel)\nYo‘q qilish uchun: off yoki yo‘q"
        )
    elif data=="add_limit":
        context.user_data["mode"]="add_limit"
        await q.message.reply_text("Limit qo‘shish uchun foydalanuvchi ID sini yuboring")
    elif data=="next_movie":
        code=random_movie(movies)
        if code:
            m = movies[code]
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Keyingi film", callback_data="next_movie")]])
            await q.message.reply_text(f"🎬 {m['name']}\n📥 Yuklab olish: {m['file']}", reply_markup=kb)
    elif data=="check_sub":
        if await is_subscribed(context, int(uid)):
            await q.edit_message_text("✅ Hammaga obuna! Botdan foydalanishingiz mumkin!")
        else:
            await q.edit_message_text("❌ Hali barcha kanallarga obuna bo‘lmagansiz")

# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = (update.message.text or "").strip()
    user = users.get(uid,{"used":0,"referrals":0})
    mode = context.user_data.get("mode")

    if uid not in users:
        users[uid] = user
        save_users()

    if text.lower()=="/cancel":
        context.user_data.clear()
        await update.message.reply_text("❌ Bekor qilindi")
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
        context.user_data["mode"]="sending_broadcast"
        await update.message.reply_text("📤 Yuborilmoqda...")
        success=0
        failed=0
        total=len(users)
        for user_id in users.keys():
            try:
                await update.message.copy(chat_id=int(user_id))
                success+=1
            except:
                failed+=1
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ Omaviy yuborish tugadi!\nMuvaffaqiyatli: {success}\nMuvaffaqiyatsiz: {failed}\nJami userlar: {total}"
        )
        return

    # ================= ADD LIMIT =================
    if mode=="add_limit" and is_admin(int(uid)):
        target_id = text.strip()
        if target_id in users:
            users[target_id]["used"] = 0
            save_users()
            await update.message.reply_text(f"✅ {target_id} foydalanuvchining limiti tiklandi!")
        else:
            await update.message.reply_text("❌ Foydalanuvchi topilmadi")
        context.user_data.pop("mode", None)
        return

    # ================= ADD MOVIE =================
    if mode=="add_movie" and is_admin(int(uid)):
        if update.message.forward_from_chat:
            context.user_data["movie_msg"]=update.message.forward_from_message_id
            context.user_data["movie_chat"]=update.message.forward_from_chat.id
            context.user_data["mode"]="movie_name"
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
        if not await is_subscribed(context, int(uid)):
            await send_subscription_message(update.message)
            return
        m = movies[text]
        movies[text]["views"] += 1
        user["used"] += 1
        save_movies(movies)
        save_users()
        kb=InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Keyingi film", callback_data="next_movie")]])
        await update.message.reply_text(f"🎬 {m['name']}\n📥 Yuklab olish:\n{m['file']}", reply_markup=kb)
        return

    await update.message.reply_text("❌ Bunday kod topilmadi")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,message_handler))
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__=="__main__":
    main()
