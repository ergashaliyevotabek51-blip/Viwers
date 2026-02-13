import os
import json
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)

# ========= CONFIG =========
TOKEN = os.getenv("BOT_TOKEN")          # Railway Variables’da bo‘ladi
ADMIN_ID = int(os.getenv("ADMIN_ID"))   # Railway Variables’da bo‘ladi
BOT_USERNAME = "UzbekFilmTV_bot"

MOVIES_FILE = "movies.json"
USERS_FILE = "users.json"

# ========= FILE UTILS =========
def load_json(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_json(USERS_FILE, {})
    user_id = str(update.effective_user.id)

    # referal
    if user_id not in users:
        users[user_id] = {"used": 0, "ref": 0}
        if context.args:
            ref = context.args[0]
            if ref in users:
                users[ref]["ref"] += 1
        save_json(USERS_FILE, users)

    text = (
        "🤲 Assalomu alaykum va rohmatullohi va barokatuhu!\n\n"
        "🎬 UzbekFilmTV botiga xush kelibsiz!\n\n"
        "📥 Kino olish uchun kod yuboring.\n"
        "📌 Masalan: 12"
    )

    kb = None
    if update.effective_user.id == ADMIN_ID:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛠 Admin panel", callback_data="admin")]
        ])

    await update.message.reply_text(text, reply_markup=kb)

# ========= ADMIN PANEL =========
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kod qo‘shish", callback_data="add")],
        [InlineKeyboardButton("➖ Kod o‘chirish", callback_data="del")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")]
    ])

    await query.edit_message_text("🛠 Admin Panel", reply_markup=kb)

# ========= ADD CODE =========
async def add_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["step"] = "add_code"
    await update.callback_query.message.reply_text(
        "➕ Kod va file_id ni yuboring:\n\nMasalan:\n12 AgACAgIA..."
    )

# ========= DELETE CODE =========
async def del_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["step"] = "del_code"
    await update.callback_query.message.reply_text("➖ O‘chiriladigan kodni yozing:")

# ========= STATS =========
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    movies = load_json(MOVIES_FILE, {})
    users = load_json(USERS_FILE, {})
    text = (
        f"📊 Statistika\n\n"
        f"🎬 Kinolar: {len(movies)}\n"
        f"👥 Userlar: {len(users)}"
    )
    await update.callback_query.message.reply_text(text)

# ========= MESSAGE HANDLER =========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = str(update.effective_user.id)

    movies = load_json(MOVIES_FILE, {})
    users = load_json(USERS_FILE, {})

    step = context.user_data.get("step")

    # ===== ADMIN ADD =====
    if step == "add_code" and update.effective_user.id == ADMIN_ID:
        try:
            code, value = text.split(" ", 1)
            movies[code] = value
            save_json(MOVIES_FILE, movies)
            context.user_data.clear()
            await update.message.reply_text("✅ Kod qo‘shildi!")
        except:
            await update.message.reply_text("❌ Format xato")
        return

    # ===== ADMIN DELETE =====
    if step == "del_code" and update.effective_user.id == ADMIN_ID:
        if text in movies:
            del movies[text]
            save_json(MOVIES_FILE, movies)
            await update.message.reply_text("🗑 O‘chirildi")
        else:
            await update.message.reply_text("❌ Topilmadi")
        context.user_data.clear()
        return

    # ===== MOVIE SEND =====
    if text in movies:
        if users[user_id]["used"] >= 5 and users[user_id]["ref"] < 3:
            link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            await update.message.reply_text(
                "🔒 Limit tugadi!\n\n"
                "🎁 Yana ochish uchun 3 do‘st taklif qiling:\n"
                f"{link}"
            )
            return

        users[user_id]["used"] += 1
        save_json(USERS_FILE, users)

        await update.message.reply_video(
            video=movies[text],
            caption="🎬 Kino tayyor!\n✨ UzbekFilmTV"
        )
        return

    await update.message.reply_text("❌ Bunday kod topilmadi")

# ========= MAIN =========
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin"))
    app.add_handler(CallbackQueryHandler(add_code, pattern="add"))
    app.add_handler(CallbackQueryHandler(del_code, pattern="del"))
    app.add_handler(CallbackQueryHandler(stats, pattern="stats"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot ishga tushdi")
    app.run_polling()

if __name__ == "__main__":
    main()
