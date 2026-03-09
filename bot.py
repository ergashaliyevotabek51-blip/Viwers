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

# ================= CONFIG =================
TOKEN = "BOT_TOKEN"  # BotFather token
BOT_USERNAME = "UzbekFilmTV_bot"

# Bir nechta admin
ADMIN_IDS = [774440841, 7818576058]

# Foydalanuvchi va kino fayllari
MOVIES_FILE = "movies.json"

# ================= DATA =================
try:
    with open(MOVIES_FILE, "r") as f:
        movies = json.load(f)
except:
    movies = {}

users = {}

# ================= HELPERS =================
def is_admin(uid):
    return uid in ADMIN_IDS

def save_movies(data):
    with open(MOVIES_FILE, "w") as f:
        json.dump(data, f)

def trending(movies_dict):
    # eng ko'p ishlatilgan 10 film
    return sorted(movies_dict.items(), key=lambda x:x[1]["views"], reverse=True)[:10]

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
        ]
    ])

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in users:
        users[uid] = {"used":0}
    await update.message.reply_text("🎬 Kino kodi yoki admin panel uchun /admin yozing")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Siz admin emassiz")
        return
    await update.message.reply_text("🛠 Admin panel", reply_markup=admin_keyboard())

# ================= CALLBACKS =================
async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if not is_admin(uid):
        return
    data = q.data

    if data=="add_movie":
        context.user_data["mode"]="add_movie"
        await q.message.reply_text("Kino postini forward qiling")

    elif data=="delete_movie":
        context.user_data["mode"]="delete_movie"
        await q.message.reply_text("O‘chirish uchun kino kodini yuboring")

    elif data=="stats":
        await q.message.reply_text(f"👥 Userlar: {len(users)}\n🎬 Kinolar: {len(movies)}")

    elif data=="top_movies":
        top = trending(movies)
        text = "🔥 Top 10 filmlar\n\n"
        for i, (code, m) in enumerate(top, 1):
            text += f"{i}. {m['name']} — {m['views']}\n"
        await q.message.reply_text(text)

    elif data=="next_movie":
        code = random_movie(movies)
        if code:
            await q.message.reply_text(f"🎬 Keyingi kino kodi: {code}")

# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    mode = context.user_data.get("mode")
    if uid not in users:
        users[uid] = {"used":0}

    # ================= ADD MOVIE =================
    if mode=="add_movie" and is_admin(uid):
        if update.message.forward_from_chat:
            context.user_data["movie_msg"]=update.message.forward_from_message_id
            context.user_data["movie_chat"]=update.message.forward_from_chat.id
            context.user_data["mode"]="movie_name"
            await update.message.reply_text("Endi film nomini yuboring")
            return

    if mode=="movie_name" and is_admin(uid):
        name = text
        code = str(len(movies)+1)
        chat = str(context.user_data["movie_chat"]).replace("-100","")
        msg = context.user_data["movie_msg"]
        link = f"https://t.me/c/{chat}/{msg}"
        movies[code] = {"name":name, "file":link, "views":0}
        save_movies(movies)
        await update.message.reply_text(f"✅ Kino qo‘shildi\nKod: {code}")
        context.user_data.clear()
        return

    # ================= DELETE MOVIE =================
    if mode=="delete_movie" and is_admin(uid):
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
        m = movies[text]
        movies[text]["views"] += 1
        users[uid]["used"] += 1
        save_movies(movies)

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Keyingi film", callback_data="next_movie")],
            [InlineKeyboardButton("🔗 Ulashish", url=f"https://t.me/{BOT_USERNAME}")]
        ])
        await update.message.reply_text(
            f"🎬 {m['name']}\n📥 Yuklab olish:\n{m['file']}",
            reply_markup=kb
        )
        return

    # ================= UNKNOWN =================
    await update.message.reply_text("❌ Bunday kod topilmadi")

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(admin_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__=="__main__":
    main()
