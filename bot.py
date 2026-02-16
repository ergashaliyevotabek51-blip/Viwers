import os
import json
from datetime import datetime
from urllib.parse import quote
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
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 774440841
BOT_USERNAME = "UzbekFilmTv_bot"           # ← o'zingiznikiga o'zgartiring!

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"

FREE_LIMIT = 5
REF_LIMIT = 5  # har bir referral uchun +5 ta kino

# ================= Fayl bilan ishlash =================

def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        save_users({})
        return {}

    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}

    # Eski list format → dict ga konvert
    if isinstance(data, list):
        new_data = {}
        now = datetime.utcnow().isoformat()
        for uid in data:
            try:
                uid_str = str(int(uid))
                new_data[uid_str] = {"used": 0, "referrals": 0, "joined": now}
            except:
                continue
        save_users(new_data)
        return new_data

    # Tozalash va standartlashtirish
    cleaned = {}
    for k, v in data.items():
        try:
            uid = str(int(k))
            cleaned[uid] = {
                "used": int(v.get("used", 0)),
                "referrals": int(v.get("referrals", 0)),
                "joined": v.get("joined", datetime.utcnow().isoformat())
            }
        except:
            continue

    if cleaned != data:
        save_users(cleaned)

    return cleaned


def save_users(data: dict):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_movies() -> dict:
    if not os.path.exists(MOVIES_FILE):
        return {}
    try:
        with open(MOVIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def save_movies(data: dict):
    with open(MOVIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(users: dict, user_id: int) -> dict:
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "used": 0,
            "referrals": 0,
            "joined": datetime.utcnow().isoformat()
        }
        save_users(users)
    return users[uid]


def max_limit(user: dict) -> int:
    return FREE_LIMIT + user["referrals"] * REF_LIMIT


# ================= ADMIN KEYBOARD =================
def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Kino qo‘shish",    callback_data="add_movie"),
            InlineKeyboardButton("➖ Kino o‘chirish",   callback_data="delete_movie"),
        ],
        [
            InlineKeyboardButton("📃 Kinolar ro‘yxati", callback_data="list_movies"),
            InlineKeyboardButton("📊 Statistika",       callback_data="stats"),
        ],
    ])


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    users = load_users()
    me = get_user(users, user.id)

    # Referral
    if args and args[0].isdigit():
        ref_id = args[0]
        if ref_id != str(user.id) and ref_id in users and "refed" not in me:
            users[ref_id]["referrals"] += 1
            me["refed"] = ref_id
            try:
                await context.bot.send_message(int(ref_id), f"Yangi referral! Soni: {users[ref_id]['referrals']}")
            except:
                pass
            save_users(users)

    text = (
        f"<b>Assalomu alaykum, {user.first_name}!</b> 👋\n\n"
        f"🎬 O‘zbek filmlari botiga xush kelibsiz!\n\n"
        f"Kod yuboring → film keladi\n"
        f"Bepul limit: {FREE_LIMIT} ta\n"
        f"Do‘st uchun: +{REF_LIMIT} ta\n\n"
        f"Kodni yozing!"
    )

    kb = []
    if user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin_panel")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="HTML")


# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data

    if data == "admin_panel":
        await query.edit_message_text("🛠 Admin panel", reply_markup=admin_keyboard())
        return

    users = load_users()
    movies = load_movies()

    if data == "stats":
        await query.message.reply_text(f"👥 Userlar: {len(users)}\n🎥 Kinolar: {len(movies)}")
        return

    if data == "list_movies":
        if not movies:
            text = "Hozircha kinolar yo‘q."
        else:
            text = "Kinolar ro‘yxati:\n" + "\n".join(f"• {k}" for k in sorted(movies.keys()))
        await query.message.reply_text(text)
        return

    if data in ("add_movie", "delete_movie"):
        mode = "add" if data == "add_movie" else "delete"
        context.user_data["admin_mode"] = mode
        msg = "kod|file_id yoki https://t.me/c/..." if mode == "add" else "o‘chiriladigan kod"
        await query.message.reply_text(f"Format:\n{msg}")
        return


# ================= TEXT HANDLER =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text.strip()
    uid = msg.from_user.id

    users = load_users()
    movies = load_movies()

    if text == "/cancel":
        context.user_data.clear()
        await msg.reply_text("❌ Bekor qilindi")
        return

    # Admin limit qo‘shish buyrug‘i
    if uid == ADMIN_ID and text.lower().startswith("limit "):
        parts = text.split()
        if len(parts) != 3:
            await msg.reply_text("Format: limit <user_id> <qancha_kino>\nMisol: limit 123456789 15")
            return
        try:
            target = str(parts[1])
            extra = int(parts[2])
            if target not in users:
                await msg.reply_text("User topilmadi")
                return
            users[target]["referrals"] += extra // REF_LIMIT
            save_users(users)
            new_lim = max_limit(users[target])
            await msg.reply_text(f"User {target} ga qo‘shildi!\nYangi limit: {new_lim}")
        except:
            await msg.reply_text("Format yoki son xato")
        return

    mode = context.user_data.get("admin_mode")

    # Admin kino qo‘shish / o‘chirish
    if uid == ADMIN_ID and mode:
        if mode == "add":
            if "|" not in text:
                await msg.reply_text("Format: kod|qiymat")
                return
            code, value = [x.strip() for x in text.split("|", 1)]
            movies[code] = value
            save_movies(movies)
            await msg.reply_text(f"✅ {code} qo‘shildi")
        elif mode == "delete":
            if text in movies:
                del movies[text]
                save_movies(movies)
                await msg.reply_text(f"🗑 {text} o‘chirildi")
            else:
                await msg.reply_text("Kod topilmadi")
        context.user_data.pop("admin_mode", None)
        return

    # Oddiy foydalanuvchi kino so‘radi
    if text not in movies:
        await msg.reply_text("❌ Bunday kod yo‘q")
        return

    user = get_user(users, uid)
    lim = max_limit(user)

    if user["used"] >= lim:
        ref_link = f"https://t.me/{BOT_USERNAME}?start={uid}"
        share_text = quote(f"Zo‘r o‘zbek filmlari bot! Bepul {FREE_LIMIT} ta + do‘st uchun +{REF_LIMIT} ta\n{ref_link}")
        share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={share_text}"

        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Do‘stlarga ulashish", url=share_url)]])
        await msg.reply_text(f"Limit tugadi (0/{lim})\nDo‘stlaringizni taklif qiling!", reply_markup=kb)
        return

    user["used"] += 1
    save_users(users)

    remaining = f"{user['used']}/{lim}"

    caption = (
        "🎬 Kino tayyor 🍿\n"
        f"Qolgan: {remaining}\n\n"
        f"🤖 @{BOT_USERNAME}\n"
        f"📢 @UzbekFilmTv_Kanal"
    )

    val = movies[text]

    if val.startswith("https://t.me/c/"):
        try:
            parts = val.replace("https://t.me/c/", "").split("/")
            ch = int("-100" + parts[0])
            mid = int(parts[1])
            await context.bot.copy_message(msg.chat_id, ch, mid, caption=caption)
        except Exception as e:
            await msg.reply_text(f"Kanal xatosi: {str(e)}")
    else:
        await msg.reply_video(video=val, caption=caption)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
