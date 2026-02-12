import os
import json
from datetime import datetime
import requests
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, Update
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
TOKEN = os.environ.get("8370792264:AAFH3P9qZPkHQFRBnxjxolGMILTRhYexDb0")
ADMIN_ID = 774440841
BOT_USERNAME = "UzbekFilmTV_bot"

MOVIES_FILE = "movies.json"
USERS_FILE = "users.json"

HF_TOKEN = "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"  # Hugging Face tokeningiz
AI_MODEL = "HuggingFaceH4/zephyr-7b-beta"

# ================= PROXY =================
PROXY = "socks4://142.54.231.38:4145"  
# ================= FILE SYSTEM =================
def load_movies():
    try:
        with open(MOVIES_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_movies(data):
    with open(MOVIES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_admin(user_id):
    return user_id == ADMIN_ID

# ================= AI FUNCTION =================
def ask_ai(user_name, text):
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}"
    }

    prompt = f"""
Assalomu alaykum va rohmatullohi va barokatuhu, {user_name}!

Siz UzbekFilmTV AI bilan suhbatdasiz.
Savol: {text}
Javob:
"""

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 200
        }
    }

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{AI_MODEL}",
            headers=headers,
            json=payload,
            timeout=30  # timeout qo'shdim, uzoq kutmasin
        )
        if response.status_code == 200:
            return response.json()[0]["generated_text"].strip()
        else:
            return f"⚠️ AI xatosi: {response.status_code} - {response.text}"
    except Exception as e:
        return f"⚠️ AI ulanish xatosi: {str(e)}"

# ================= APPLICATION + PROXY =================
application = Application.builder() \
    .token(TOKEN) \
    .proxy(PROXY) \
    .get_updates_proxy(PROXY) \
    .build()

# ================= START =================
@application.add_handler(CommandHandler("start"))
async def start(update, context):
    user_id = str(update.effective_user.id)
    users = load_users()

    ref = update.message.text.split(" ")
    ref_id = ref[1] if len(ref) > 1 else None

    if user_id not in users:
        users[user_id] = {"used": 0, "referrals": 0, "invited_by": ref_id}
        if ref_id and ref_id in users:
            users[ref_id]["referrals"] += 1
        save_users(users)

    name = update.effective_user.first_name
    text = (
        f"🤲 Assalomu alaykum va rohmatullohi va barokatuhu, {name}!\n\n"
        "🎬 UzbekFilmTV rasmiy ravishda ishga tushdi!\n\n"
        "✨ Eng sara o'zbek filmlari shu yerda.\n"
        "📥 Kino olish uchun kod yuboring.\n\n"
        "📌 Masalan: 12"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 UzbekFilmTV AI", callback_data="ai")]
    ]) if not is_admin(update.effective_user.id) else InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Admin Panel", callback_data="admin")],
        [InlineKeyboardButton(text="🤖 UzbekFilmTV AI", callback_data="ai")]
    ])

    await update.message.reply_text(text, reply_markup=kb)

# ================= ADMIN PANEL =================
@application.add_handler(CallbackQueryHandler(pattern="^admin$"))
async def admin_panel(update, context):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kod qo‘shish", callback_data="add")],
        [InlineKeyboardButton(text="➖ Kod o‘chirish", callback_data="delete")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="broadcast")],
    ])

    await query.edit_message_text("🛠 Admin Panel", reply_markup=kb)

# ================= AI PANEL =================
@application.add_handler(CallbackQueryHandler(pattern="^ai$"))
async def ai_panel(update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("🤖 UzbekFilmTV AI ga xush kelibsiz!\n\nSavolingizni yozing...")

# ================= HANDLE ALL MESSAGES =================
@application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND))
async def handle_all(update, context):
    msg = update.message
    user_id = str(msg.from_user.id)
    users = load_users()
    movies = load_movies()

    if user_id not in users:
        return

    text = msg.text.strip()

    # AI so'rov (ai bilan boshlansa)
    if text.lower().startswith("ai "):
        question = text[3:].strip()
        name = msg.from_user.first_name

        await msg.reply_text("🤖 AI o‘ylayapti...")

        answer = ask_ai(name, question)
        await msg.reply_text(answer)
        return

    # DELETE (admin)
    if is_admin(msg.from_user.id) and text.startswith("del "):
        code = text.replace("del ", "").strip()
        if code in movies:
            del movies[code]
            save_movies(movies)
            await msg.reply_text("🗑 O‘chirildi")
        else:
            await msg.reply_text("❌ Topilmadi")
        return

    # MOVIE SYSTEM
    if text in movies:
        if users[user_id]["used"] >= 5 and users[user_id]["referrals"] < 3:
            link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            await msg.reply_text(
                "🔒 5 ta kino ishlatildi!\n\n"
                "🎁 Yana ochish uchun 3 ta do‘st taklif qiling.\n\n"
                f"🔗 Sizning havolangiz:\n{link}"
            )
            return

        users[user_id]["used"] += 1
        save_users(users)

        val = movies[text]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔎 Qidirish", url=f"https://t.me/{BOT_USERNAME}")]
        ])

        if val.startswith("http"):
            parts = val.split("/")
            chat_id = int("-100" + parts[-2])
            message_id = int(parts[-1])
            await context.bot.copy_message(
                chat_id=msg.chat.id,
                from_chat_id=chat_id,
                message_id=message_id,
                reply_markup=kb
            )
        else:
            await msg.reply_video(
                video=val,
                caption="🎬 Kino tayyor! Ulashing do‘stlaringizga 💎",
                reply_markup=kb
            )
        return

    await msg.reply_text("❌ Bunday kod topilmadi")

# ================= MAIN =================
if __name__ == "__main__":
    print("Bot polling boshlanmoqda... (Proxy bilan)")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        bootstrap_retries=-1
    )
