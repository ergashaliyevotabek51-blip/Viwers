import os
import json
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
HF_TOKEN = os.getenv("HF_TOKEN")
BOT_USERNAME = "UzbekFilmTV_bot"

MOVIES_FILE = "movies.json"
USERS_FILE = "users.json"
AI_MODEL = "HuggingFaceH4/zephyr-7b-beta"

# ================= FILE SYSTEM =================
def load_data(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def is_admin(user_id):
    return user_id == ADMIN_ID

# ================= AI =================
def ask_ai(text):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": text, "parameters": {"max_new_tokens": 200}}

    try:
        r = requests.post(
            f"https://api-inference.huggingface.co/models/{AI_MODEL}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()[0]["generated_text"]
        return "⚠️ AI vaqtincha ishlamayapti."
    except:
        return "⚠️ AI ulanish xatosi."

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    user_id = str(update.effective_user.id)

    args = context.args
    ref = args[0] if args else None

    if user_id not in users:
        users[user_id] = {"used": 0, "referrals": 0}
        if ref and ref in users and ref != user_id:
            users[ref]["referrals"] += 1
        save_data(USERS_FILE, users)

    text = "🎬 UzbekFilmTV ga xush kelibsiz!\n\nKod yuboring."

    if is_admin(update.effective_user.id):
        kb = [
            [InlineKeyboardButton("🛠 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🤖 AI", callback_data="ai")]
        ]
    else:
        kb = [[InlineKeyboardButton("🤖 AI", callback_data="ai")]]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    kb = [
        [InlineKeyboardButton("➕ Kod qo‘shish", callback_data="add")],
        [InlineKeyboardButton("➖ Kod o‘chirish", callback_data="delete")],
        [InlineKeyboardButton("📊 Referal Statistika", callback_data="stats")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back")]
    ]

    await update.callback_query.edit_message_text(
        "🛠 ADMIN PANEL",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= ADD =================
async def add_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["mode"] = "add_code"
    await update.callback_query.message.reply_text("Yangi kod kiriting:")

# ================= DELETE =================
async def delete_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["mode"] = "delete_code"
    await update.callback_query.message.reply_text("O‘chirish uchun kod kiriting:")

# ================= STATS =================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    users = load_data(USERS_FILE)

    total = len(users)
    sorted_users = sorted(users.items(), key=lambda x: x[1]["referrals"], reverse=True)

    text = f"📊 REFERAL STATISTIKA\n\n👥 Jami: {total}\n\n🏆 Top 5:\n"
    for i, (uid, data) in enumerate(sorted_users[:5], 1):
        text += f"{i}. {uid} — {data['referrals']} ta\n"

    await update.callback_query.edit_message_text(text)

# ================= AI PANEL =================
async def ai_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["mode"] = "ai"
    await update.callback_query.message.reply_text("🤖 Savolingizni yozing:")

# ================= BACK =================
async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data.clear()
    await start(update, context)

# ================= TEXT HANDLER =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    users = load_data(USERS_FILE)
    movies = load_data(MOVIES_FILE)
    user_id = str(update.effective_user.id)

    mode = context.user_data.get("mode")

    # ADD
    if mode == "add_code":
        context.user_data["new_code"] = text
        context.user_data["mode"] = "add_value"
        await update.message.reply_text("Video file_id kiriting:")
        return

    if mode == "add_value":
        movies[context.user_data["new_code"]] = text
        save_data(MOVIES_FILE, movies)
        context.user_data.clear()
        await update.message.reply_text("✅ Saqlandi!")
        return

    # DELETE
    if mode == "delete_code":
        if text in movies:
            del movies[text]
            save_data(MOVIES_FILE, movies)
            await update.message.reply_text("🗑 O‘chirildi!")
        else:
            await update.message.reply_text("❌ Topilmadi!")
        context.user_data.clear()
        return

    # AI
    if mode == "ai":
        await update.message.reply_text("🤖 AI o‘ylayapti...")
        answer = ask_ai(text)
        await update.message.reply_text(answer)
        return

    # MOVIE
    if text in movies:
        if users[user_id]["used"] >= 5 and users[user_id]["referrals"] < 3:
            link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            await update.message.reply_text(
                "🔒 5 ta kino ishlatildi!\n\n"
                "3 ta do‘st taklif qiling.\n\n"
                f"Sizning link:\n{link}"
            )
            return

        users[user_id]["used"] += 1
        save_data(USERS_FILE, users)

        await update.message.reply_video(
            video=movies[text],
            caption="🎬 Kino tayyor!"
        )
        return

    await update.message.reply_text("❌ Kod topilmadi")

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin"))
    app.add_handler(CallbackQueryHandler(add_code, pattern="add"))
    app.add_handler(CallbackQueryHandler(delete_code, pattern="delete"))
    app.add_handler(CallbackQueryHandler(stats, pattern="stats"))
    app.add_handler(CallbackQueryHandler(ai_panel, pattern="ai"))
    app.add_handler(CallbackQueryHandler(back, pattern="back"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
