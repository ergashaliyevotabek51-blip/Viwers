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
TOKEN = os.getenv("BOT_TOKEN")  # Bot token
BOT_USERNAME = "UzbekFilmTV_bot"

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"

FREE_LIMIT = 5
REF_LIMIT = 5

ADMINS = [774440841]  # Admin ID
DEFAULT_CHANNEL_ID = 3695159513  # Default kanal ID (faqat ID bo‘lsa ishlatiladi)

MANDATORY_CHANNELS = []  # Majburiy obuna kanallari (admin sozlashi mumkin)

# ================= HELPERS =================
def load_json(file, default):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_users():
    return load_json(USERS_FILE, {})

def save_users(users):
    save_json(USERS_FILE, users)

def load_movies():
    return load_json(MOVIES_FILE, {})

def save_movies(movies):
    save_json(MOVIES_FILE, movies)

def get_user(users, uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "used": 0,
            "referrals": 0,
            "limit": FREE_LIMIT,
            "joined": datetime.utcnow().isoformat()
        }
    return users[uid]

def max_limit(user):
    return user.get("limit", FREE_LIMIT) + user["referrals"] * REF_LIMIT

def trending(movies):
    return sorted(movies.items(), key=lambda x: x[1].get("views", 0), reverse=True)[:10]

def random_movie(movies):
    if not movies:
        return None
    return random.choice(list(movies.keys()))

def is_admin(uid):
    return uid in ADMINS

def subscription_keyboard(status):
    kb = []
    for ch, val in status.items():
        icon = "✅" if val else "❌"
        kb.append([InlineKeyboardButton(f"{icon} {ch}", url=f"https://t.me/{ch.lstrip('@')}")])
    kb.append([InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(kb)

# ================= SUBSCRIPTION CHECK =================
async def check_user_subscribed(context, user_id):
    if not MANDATORY_CHANNELS:
        return True
    for ch in MANDATORY_CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

async def send_subscription_message(message, context):
    status = {ch: False for ch in MANDATORY_CHANNELS}
    kb = subscription_keyboard(status)
    await message.reply_text(
        "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:",
        reply_markup=kb
    )

# ================= ADMIN KEYBOARD =================
def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie")],
        [InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete_movie")],
        [InlineKeyboardButton("🔎 Kino qidirish", callback_data="search_movie")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast")],
        [InlineKeyboardButton("🔒 Majburiy obuna", callback_data="subscription")],
        [InlineKeyboardButton("💠 Limit qo‘shish", callback_data="add_limit")]
    ])

# ================= START HANDLER =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    fname = update.effective_user.first_name
    users = load_users()
    get_user(users, uid)
    save_users(users)

    # Check subscription
    if not await check_user_subscribed(context, uid):
        await send_subscription_message(update.message, context)
        return

    kb = [
        [InlineKeyboardButton("🎟 Mening limitim", callback_data="my_limit")],
        [InlineKeyboardButton("🎬 Random film", callback_data="rand_movie")],
        [InlineKeyboardButton("🔥 Trend filmlar", callback_data="trend_movie")],
        [InlineKeyboardButton("🎥 Kino katalog", callback_data="movie_catalog")],
        [InlineKeyboardButton("👥 Do‘st taklif qilish", callback_data="ref_link")]
    ]

    if is_admin(uid):
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(
        f"Assalomu alaykum, {fname}! 👋\n\n🎬 <b>UzbekFilmTV</b> — eng sara o‘zbek filmlari!\n"
        f"Kod yuboring → film darhol keladi\n"
        f"• Bepul: {FREE_LIMIT} ta   • Do‘st uchun: +{REF_LIMIT} ta\n\n"
        f"🚀 Kodni yozing yoki do‘stlaringizni taklif qiling!",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="HTML"
    )

# ================= CALLBACK HANDLER =================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data
    users = load_users()
    movies = load_movies()
    user = get_user(users, uid)

    # ================= USER CALLBACKS =================
    if data == "my_limit":
        await q.message.reply_text(f"🔢 Limitingiz: {user['used']}/{max_limit(user)}\nDo‘stlar soni: {user['referrals']}")
        return

    if data == "ref_link":
        await q.message.reply_text(f"Sizning referal linkingiz:\nhttps://t.me/{BOT_USERNAME}?start={uid}")
        return

    if data == "rand_movie":
        code = random_movie(movies)
        if code:
            await send_movie_by_code(context, q.message.chat_id, code)
        return

    if data == "next_movie":
        code = random_movie(movies)
        if code:
            await send_movie_by_code(context, q.message.chat_id, code)
        return

    if data == "trend_movie":
        text = "🔥 Top filmlar:\n"
        for i, (code, m) in enumerate(trending(movies), 1):
            text += f"{i}. {m['name']} — {code} ({m.get('views',0)} ta ko‘rilgan)\n"
        await q.message.reply_text(text)
        return

    if data == "movie_catalog":
        kb = []
        for code, m in list(movies.items())[:20]:
            kb.append([InlineKeyboardButton(m["name"], callback_data=f"watch_{code}")])
        await q.message.reply_text("🎬 Kino katalog", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("watch_"):
        code = data.replace("watch_", "")
        if code in movies:
            await send_movie_by_code(context, q.message.chat_id, code)
        return

    # ================= ADMIN CALLBACKS =================
    if not is_admin(uid):
        return

    if data == "admin":
        await q.message.reply_text("🛠 Admin panel", reply_markup=admin_keyboard())

    elif data == "add_movie":
        context.user_data["mode"] = "add_movie"
        await q.message.reply_text("Kino qo‘shish uchun format:\nkod | link yoki message_id | film nomi\nMasalan:\nnussa01 | https://t.me/c/... | Nussa Udalaydi")
        return

    elif data == "delete_movie":
        context.user_data["mode"] = "delete_movie"
        await q.message.reply_text("O‘chirish uchun kodni yuboring:")
        return

# ================= SEND MOVIE FUNCTION =================
async def send_movie_by_code(context, chat_id, code):
    movies = load_movies()
    m = movies[code]
    movies[code]["views"] = m.get("views",0) +1
    save_movies(movies)

    text = f"🎬 <b>{m['name']}</b>\n"
    if str(m.get("msg_id","")).startswith("http") or str(m.get("msg_id","")).startswith("https://t.me/c/"):
        text += f"{m['msg_id']}\nPrivate kanal bo‘lsa, avval kanalga a’zo bo‘ling!"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Keyingi film", callback_data="next_movie")],
        [InlineKeyboardButton("🔗 Ulashish", url=f"https://t.me/{BOT_USERNAME}")]
    ])
    await context.bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")

# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    uid = update.effective_user.id
    users = load_users()
    movies = load_movies()
    user = get_user(users, uid)
    mode = context.user_data.get("mode","")

    if text.lower() == "/cancel":
        context.user_data.clear()
        await update.message.reply_text("❌ Bekor qilindi")
        return

    # ============= ADMIN MODES =============
    if is_admin(uid):

        # ADD MOVIE
        if mode == "add_movie":
            try:
                parts = [x.strip() for x in text.split("|")]
                if len(parts)<3:
                    await update.message.reply_text("Format xato. Kod | link yoki id | nom")
                    return

                code, link_or_id, name = parts

                if code in movies:
                    await update.message.reply_text("❌ Bu kod allaqachon band!")
                    return

                # default kanal id agar raqam bo‘lsa
                if link_or_id.isdigit():
                    channel_id = DEFAULT_CHANNEL_ID
                    msg_id = int(link_or_id)
                    link = f"https://t.me/c/{channel_id}/{msg_id}"
                else:
                    link = link_or_id

                movies[code] = {"name": name, "msg_id": link, "views":0}
                save_movies(movies)
                await update.message.reply_text(f"✅ Film qo‘shildi!\n{code} | {link} | {name}")
                context.user_data.clear()
                return
            except Exception as e:
                await update.message.reply_text(f"Xato: {str(e)}")
                return

        # DELETE MOVIE
        if mode == "delete_movie":
            if text in movies:
                del movies[text]
                save_movies(movies)
                await update.message.reply_text(f"🗑 {text} o‘chirildi")
            else:
                await update.message.reply_text("Kod topilmadi")
            context.user_data.clear()
            return

    # ============= USER MOVIE REQUEST =============
    if text in movies:
        # subscription check
        if not await check_user_subscribed(context, uid):
            await send_subscription_message(update.message, context)
            return

        await send_movie_by_code(context, update.message.chat_id, text)
        user["used"] +=1
        save_users(users)
        return

    # ============= SEARCH / SUGGESTION =============
    # film nomi bo'yicha qidiruv
    found = []
    for code,m in movies.items():
        if text.lower() in m["name"].lower():
            found.append(f"{m['name']} — {code}")
    if found:
        await update.message.reply_text("🎬 Topilgan filmlar:\n" + "\n".join(found[:10]))
        return

    # noto‘g‘ri kod tavsiya
    suggestions = []
    for code in movies:
        if text.lower() in code.lower():
            suggestions.append(code)
    if suggestions:
        await update.message.reply_text("❌ Kod topilmadi. Balki:\n" + "\n".join(suggestions[:5]))
    else:
        await update.message.reply_text("❌ Film topilmadi. Kino katalogdan tanlang.")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
