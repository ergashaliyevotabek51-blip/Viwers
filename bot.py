import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")  # Railway Variables'da bo'ladi
ADMIN_ID = 774440841  # o'zingning Telegram ID

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"

# ================= FILE UTILS =================
def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users = load_json(USERS_FILE, [])

    if user.id not in users:
        users.append(user.id)
        save_json(USERS_FILE, users)

    text = (
        f"🤲 Assalomu alaykum, {user.first_name}!\n\n"
        "🎬 UzbekFilmTV botiga xush kelibsiz.\n\n"
        "📩 Kino olish uchun kod yuboring.\n"
        "Masalan: 12"
    )

    keyboard = []
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await update.message.reply_text(text, reply_markup=reply_markup)

# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    keyboard = [
        [
            InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add"),
            InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete"),
        ],
        [
            InlineKeyboardButton("📊 Statistika", callback_data="stats"),
        ],
    ]

    await query.edit_message_text(
        "🛠 Admin panel",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ================= ADMIN ACTIONS =================
async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    if query.data == "add":
        context.user_data["mode"] = "add"
        await query.message.reply_text(
            "📝 Kino qo‘shish:\n\n"
            "Format:\n"
            "`kod|file_id`\n\n"
            "Masalan:\n"
            "`12|BAACAgIA...`",
            parse_mode="Markdown",
        )

    elif query.data == "delete":
        context.user_data["mode"] = "delete"
        await query.message.reply_text(
            "🗑 O‘chirish uchun faqat kodni yuboring.\nMasalan: 12"
        )

    elif query.data == "stats":
        users = load_json(USERS_FILE, [])
        movies = load_json(MOVIES_FILE, {})
        await query.message.reply_text(
            f"📊 Statistika\n\n"
            f"👥 Userlar: {len(users)}\n"
            f"🎬 Kinolar: {len(movies)}"
        )

# ================= TEXT HANDLER =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    movies = load_json(MOVIES_FILE, {})
    mode = context.user_data.get("mode")

    # ===== ADMIN ADD =====
    if is_admin(user_id) and mode == "add":
        if "|" not in text:
            await update.message.reply_text("❌ Format noto‘g‘ri.")
            return

        code, file_id = text.split("|", 1)
        movies[code.strip()] = file_id.strip()
        save_json(MOVIES_FILE, movies)

        context.user_data.clear()
        await update.message.reply_text("✅ Kino qo‘shildi!")
        return

    # ===== ADMIN DELETE =====
    if is_admin(user_id) and mode == "delete":
        if text in movies:
            del movies[text]
            save_json(MOVIES_FILE, movies)
            await update.message.reply_text("🗑 O‘chirildi!")
        else:
            await update.message.reply_text("❌ Topilmadi.")
        context.user_data.clear()
        return

    # ===== USER MOVIE =====
    if text in movies:
        await update.message.reply_video(
            video=movies[text],
            caption="🎬 Kino tayyor! Yoqimli tomosha 🍿",
        )
        return

    await update.message.reply_text("❌ Bunday kod topilmadi.")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin$"))
    app.add_handler(CallbackQueryHandler(admin_actions))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
