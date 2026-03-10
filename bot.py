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
TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = "UzbekFilmTV_bot"

USERS_FILE    = "users.json"
MOVIES_FILE   = "movies.json"
SETTINGS_FILE = "settings.json"

FREE_LIMIT = 5
REF_LIMIT  = 5

DEFAULT_ADMINS = [774440841]
MANDATORY_CHANNELS = []

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

def load_movies():
    return load_json(MOVIES_FILE, {})

def save_movies(movies):
    save_json(MOVIES_FILE, movies)

def trending(movies_dict):
    return sorted(movies_dict.items(), key=lambda x: x[1].get("views", 0), reverse=True)[:10]

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
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

async def send_subscription_message(message, context):
    status = {ch: False for ch in MANDATORY_CHANNELS}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{'✅' if v else '❌'} {ch}", url=f"https://t.me/{ch.lstrip('@')}")]
        for ch, v in status.items()
    ] + [[InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub")]])
    await message.reply_text("Obuna bo‘ling:", reply_markup=kb)

# ================= ADMIN KEYBOARD =================
def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie")],
        [InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete_movie")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton("🔥 Top filmlar", callback_data="top_movies")],
        [InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast")],
        [InlineKeyboardButton("🔒 Majburiy obuna", callback_data="subscription")],
        [InlineKeyboardButton("💠 Limit qo‘shish", callback_data="add_limit")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users = load_users()
    get_user(users, uid)
    save_users(users)

    if not await check_user_subscribed(context, uid):
        await send_subscription_message(update.message, context)
        return

    text = f"Assalomu alaykum!\nKod yuboring → film keladi\nBepul: {FREE_LIMIT} ta"
    kb = [
        [InlineKeyboardButton("🎟 Limitim", callback_data="my_limit")],
        [InlineKeyboardButton("🎬 Random", callback_data="rand_movie")],
        [InlineKeyboardButton("🔥 Top", callback_data="trend_movie")]
    ]
    if is_admin(uid):
        kb.append([InlineKeyboardButton("🛠 Admin", callback_data="admin")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

# ================= CALLBACK =================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid = q.from_user.id
    movies = load_movies()

    if data == "my_limit":
        user = get_user(load_users(), uid)
        await q.message.reply_text(f"Limit: {user['used']}/{max_limit(user)}")
        return

    if data == "rand_movie":
        code = random_movie(movies)
        if code:
            m = movies[code]
            await q.message.reply_text(f"{m['name']}\n{m['file']}")
        return

    if data == "trend_movie":
        top = trending(movies)[:5]
        text = "Top:\n" + "\n".join(f"{i+1}. {m['name']} ({m.get('views',0)})" for i,(c,m) in enumerate(top))
        await q.message.reply_text(text)
        return

    if not is_admin(uid):
        return

    if data == "admin":
        await q.message.reply_text("Admin panel", reply_markup=admin_keyboard())

    elif data == "add_movie":
        await q.message.reply_text(
            "Formatda yuboring:\n"
            "kod | link yoki message_id | nom\n\n"
            "Misollar:\n"
            "nussa01 | https://t.me/c/3695159513/50 | Nussa Udalaydi\n"
            "777 | 123 | Super film"
        )
        context.user_data["mode"] = "add_movie_simple"

    elif data == "delete_movie":
        context.user_data["mode"] = "delete_movie"
        await q.message.reply_text("O‘chirish uchun kod yuboring:")

    elif data == "stats":
        users = load_users()
        await q.message.reply_text(f"Userlar: {len(users)}\nKinolar: {len(load_movies())}")

    # boshqa tugmalar...

# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    uid_str = str(update.effective_user.id)
    mode = context.user_data.get("mode")

    if text.lower() == "/cancel":
        context.user_data.clear()
        await update.message.reply_text("Bekor qilindi")
        return

    users = load_users()
    movies = load_movies()

    if is_admin(update.effective_user.id) and mode == "add_movie_simple":
        try:
            parts = [p.strip() for p in text.split("|")]
            if len(parts) != 3:
                raise ValueError

            code, raw_link_or_id, name = parts

            # linkni to'g'rilash
            if raw_link_or_id.isdigit():
                # faqat id bo'lsa → default kanal ID bilan to'ldirish
                channel_id = "3695159513"  # o'zingizning asosiy private kanal ID ni shu yerga yozing
                link = f"https://t.me/c/{channel_id}/{raw_link_or_id}"
            elif raw_link_or_id.startswith("https://t.me/c/") or raw_link_or_id.startswith("t.me/c/"):
                link = raw_link_or_id
            else:
                link = raw_link_or_id  # oddiy link bo'lsa ham qabul qilamiz

            if code in movies:
                await update.message.reply_text("Bu kod band!")
                return

            movies[code] = {"name": name, "file": link, "views": 0}
            save_movies(movies)
            await update.message.reply_text(f"✅ Qo‘shildi!\nKod: {code}\n{link}\n{name}")

        except:
            await update.message.reply_text("Format xato! kod | link yoki id | nom")

        context.user_data.pop("mode", None)
        return

    if is_admin(update.effective_user.id) and mode == "delete_movie":
        if text in movies:
            del movies[text]
            save_movies(movies)
            await update.message.reply_text("O‘chirildi")
        else:
            await update.message.reply_text("Kod topilmadi")
        context.user_data.pop("mode", None)
        return

    # oddiy foydalanuvchi kod yozsa
    if text in movies:
        if not await check_user_subscribed(context, update.effective_user.id):
            await send_subscription_message(update.message, context)
            return

        m = movies[text]
        m["views"] = m.get("views", 0) + 1
        get_user(users, uid_str)["used"] += 1
        save_movies(movies)
        save_users(users)

        extra = ""
        if "t.me/c/" in m["file"]:
            extra = "\n\n<i>Private kanal → avval kanalga a’zo bo‘ling!</i>"

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Keyingi", callback_data="rand_movie")],
            [InlineKeyboardButton("Ulashish", url=f"https://t.me/{BOT_USERNAME}")]
        ])

        await update.message.reply_text(
            f"🎬 <b>{m['name']}</b>\n\n{m['file']}{extra}",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    await update.message.reply_text("Kod topilmadi")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot ishlayapti...")
    app.run_polling()

if __name__ == "__main__":
    main()
