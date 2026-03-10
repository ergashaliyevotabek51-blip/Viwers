import json
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = "8370792264:AAFC0Zym1W3t_2yI1AipjI-lhmjouwclFNI"
BOT_USERNAME = "UzbekFilmTV_bot"

ADMIN_IDS = [774440841,7818576058]

MANDATORY_CHANNELS = []

MOVIES_FILE="movies.json"

try:
    with open(MOVIES_FILE,"r") as f:
        movies=json.load(f)
except:
    movies={}

users={}

def save_movies():
    with open(MOVIES_FILE,"w") as f:
        json.dump(movies,f)

def is_admin(uid):
    return uid in ADMIN_IDS

def max_limit(user):
    return 5+user.get("referrals",0)*5

def random_movie():
    if not movies:
        return None
    return random.choice(list(movies.keys()))

def trending():
    return sorted(movies.items(),key=lambda x:x[1]["views"],reverse=True)[:10]

# ADMIN KEYBOARD
def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Kino qo‘shish",callback_data="add_movie"),
            InlineKeyboardButton("➖ Kino o‘chirish",callback_data="delete_movie")
        ],
        [
            InlineKeyboardButton("📊 Statistika",callback_data="stats"),
            InlineKeyboardButton("🔥 Top filmlar",callback_data="top_movies")
        ],
        [
            InlineKeyboardButton("📢 Broadcast",callback_data="broadcast"),
            InlineKeyboardButton("🔒 Majburiy obuna",callback_data="subscription")
        ]
    ])

# START
async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id
    name=update.effective_user.first_name

    if str(uid) not in users:
        users[str(uid)]={"used":0,"referrals":0}

    if not await is_subscribed(context,uid):
        await send_subscription(update.message)
        return

    text=f"""
Assalomu alaykum, {name}! 👋

🎬 UzbekFilmTV — eng sara o‘zbek filmlari shu yerdagi bot!

🔥 Kod yuboring (12,45,107)

🎁 Bepul: 5 ta
👥 Do‘st uchun: +5 ta
"""

    kb=[
        [InlineKeyboardButton("📊 Mening limitim",callback_data="limit")],
        [InlineKeyboardButton("🎬 Random film",callback_data="random")],
        [InlineKeyboardButton("🔥 Trend film",callback_data="trend")]
    ]

    if is_admin(uid):
        kb.append([InlineKeyboardButton("🛠 Admin panel",callback_data="admin")])

    await update.message.reply_text(text,reply_markup=InlineKeyboardMarkup(kb))

# CALLBACK
async def callbacks(update:Update,context:ContextTypes.DEFAULT_TYPE):

    q=update.callback_query
    await q.answer()

    uid=q.from_user.id
    data=q.data

    if data=="limit":

        user=users[str(uid)]

        await q.message.reply_text(
            f"📊 Limit: {user['used']}/{max_limit(user)}"
        )

    elif data=="random":

        code=random_movie()

        if not code:
            await q.message.reply_text("❌ Kino yo‘q")
            return

        m=movies[code]

        movies[code]["views"]+=1

        kb=InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Keyingi film",callback_data="random")]
        ])

        await q.message.reply_text(
            f"🎬 {m['name']}\n\n📥 {m['file']}",
            reply_markup=kb
        )

    elif data=="trend":

        top=trending()

        if not top:
            await q.message.reply_text("❌ Trend kino yo‘q")
            return

        text="🔥 Top filmlar\n\n"

        for i,(code,m) in enumerate(top,1):
            text+=f"{i}. {m['name']} ({m['views']})\n"

        await q.message.reply_text(text)

    elif data=="admin":

        if not is_admin(uid):
            return

        await q.message.reply_text(
            "🛠 Admin panel",
            reply_markup=admin_keyboard()
        )

    elif data=="stats":

        await q.message.reply_text(
            f"👥 Userlar: {len(users)}\n🎬 Kinolar: {len(movies)}"
        )

    elif data=="top_movies":

        top=trending()

        text="🔥 Top filmlar\n\n"

        for i,(code,m) in enumerate(top,1):
            text+=f"{i}. {m['name']} ({m['views']})\n"

        await q.message.reply_text(text)

# MESSAGE
async def message_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=str(update.effective_user.id)
    text=(update.message.text or "").strip()

    if uid not in users:
        users[uid]={"used":0,"referrals":0}

    if text in movies:

        if not await is_subscribed(context,int(uid)):
            await send_subscription(update.message)
            return

        m=movies[text]

        users[uid]["used"]+=1
        movies[text]["views"]+=1

        save_movies()

        await update.message.reply_text(
            f"🎬 {m['name']}\n\n📥 {m['file']}"
        )

    else:
        await update.message.reply_text("❌ Bunday kod yo‘q")

# SUB CHECK
async def is_subscribed(context,user):

    if not MANDATORY_CHANNELS:
        return True

    for ch in MANDATORY_CHANNELS:

        try:
            member=await context.bot.get_chat_member(ch,user)

            if member.status not in ["member","administrator","creator"]:
                return False

        except:
            return False

    return True

# SUB MESSAGE
async def send_subscription(message):

    kb=[]

    for ch in MANDATORY_CHANNELS:
        kb.append([
            InlineKeyboardButton(
                f"{ch}",
                url=f"https://t.me/{ch.replace('@','')}"
            )
        ])

    kb.append([InlineKeyboardButton("✅ Tekshirish",callback_data="check")])

    await message.reply_text(
        "❗ Botdan foydalanish uchun kanallarga obuna bo‘ling",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# MAIN
def main():

    app=Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,message_handler))

    print("Bot ishga tushdi...")

    app.run_polling()

if __name__=="__main__":
    main()
