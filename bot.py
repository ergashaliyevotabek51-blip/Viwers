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
BOT_USERNAME = "UzbekFilmTv_bot"  # o'zingiznikiga o'zgartiring

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"

FREE_LIMIT = 5
REF_LIMIT = 5

# ================= Fayl funksiyalari =================

def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        save_users({})
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}

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
        [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie"),
         InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete_movie")],
        [InlineKeyboardButton("📃 Kinolar ro‘yxati", callback_data="list_movies"),
         InlineKeyboardButton("📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton("📢 Ommaviy xabar", callback_data="broadcast")],
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
                await context.bot.send_message(int(ref_id), f"🎉 Yangi do‘st kirdi!\nReferral: {users[ref_id]['referrals']}")
            except:
                pass
            save_users(users)

    text = (
        f"<b>Assalomu alaykum, {user.first_name}!</b> 👋\n\n"
        f"🎬 <b>UzbekFilmTV</b> — eng sara o‘zbek filmlari shu yerdagi bot!\n\n"
        f"🔥 <b>Qanday ishlaydi?</b>\n"
        f"• Kod yuboring (masalan: 12, 45, 107) → kino darhol keladi\n"
        f"• Bepul limit: <b>5 ta kino</b>\n"
        f"• Har bir do‘st taklif qilsangiz → +5 ta limit qo‘shiladi\n\n"
        f"🚀 <b>Tayyormisiz?</b> Kodni yuboring yoki do‘stlaringizni taklif qiling!"
    )

    kb = []
    if user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin_panel")])

    # Stiker yuborish (agar avvalgi kodda bo'lgan bo'lsa)
    # STIKER_ID ni o'zingiznikiga almashtiring yoki olib tashlang
    STIKER_ID = "CAACAgIAAxkBAAIB..."  # ← shu yerni to'ldiring yoki komment qiling
    if STIKER_ID:
        await update.message.reply_sticker(STIKER_ID)

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="HTML")


# ================= ADMIN PANEL & CALLBACK =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data

    if data == "admin_panel":
        await query.edit_message_text("🛠 Admin panel", reply_markup=admin_keyboard())
        return

    if data == "broadcast":
        context.user_data["mode"] = "broadcast"
        await query.message.reply_text(
            "📢 Endi yuborgan xabaringiz (matn, rasm, video...) hammaga jo'natiladi.\n"
            "Bekor qilish uchun /cancel yozing."
        )
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
        msg = "kod|file_id yoki kanal link" if mode == "add" else "o‘chiriladigan kod"
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

    # Admin limit qo'shish
    if uid == ADMIN_ID and text.lower().startswith("limit "):
        parts = text.split()
        if len(parts) != 3:
            await msg.reply_text("Format: limit <user_id> <qancha_kino>")
            return
        try:
            target = str(parts[1])
            extra = int(parts[2])
            if target not in users:
                await msg.reply_text("User topilmadi")
                return
            users[target]["referrals"] += extra // REF_LIMIT
            save_users(users)
            await msg.reply_text(f"User {target} ga qo‘shildi! Yangi limit: {max_limit(users[target])}")
        except:
            await msg.reply_text("Format yoki son xato")
        return

    mode = context.user_data.get("admin_mode")

    # Kino qo'shish / o'chirish
    if uid == ADMIN_ID and mode in ("add", "delete"):
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

    # Ommaviy xabar (broadcast)
    if uid == ADMIN_ID and context.user_data.get("mode") == "broadcast":
        success = 0
        total = len(users)
        for u_id_str in users:
            try:
                u_id = int(u_id_str)
                if msg.text:
                    await context.bot.send_message(u_id, msg.text)
                elif msg.photo:
                    await context.bot.send_photo(u_id, msg.photo[-1].file_id, caption=msg.caption)
                elif msg.video:
                    await context.bot.send_video(u_id, msg.video.file_id, caption=msg.caption)
                elif msg.document:
                    await context.bot.send_document(u_id, msg.document.file_id, caption=msg.caption)
                else:
                    await context.bot.copy_message(u_id, msg.chat_id, msg.message_id)
                success += 1
            except:
                pass
        await msg.reply_text(f"Yuborildi: {success}/{total}")
        context.user_data.clear()
        return

    # Oddiy foydalanuvchi → kino kodi
    if text not in movies:
        await msg.reply_text("❌ Bunday kod topilmadi")
        return

    user = get_user(users, uid)
    lim = max_limit(user)

    if user["used"] >= lim:
        ref_link = f"https://t.me/{BOT_USERNAME}?start={uid}"
        share_text = quote(f"Zo‘r filmlar botida! Bepul 5 + do‘st uchun +5\n{ref_link}")
        share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={share_text}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Do‘stlarga ulashish", url=share_url)]])
        await msg.reply_text(f"Limit tugadi (0/{lim})\nDo‘st taklif qiling!", reply_markup=kb)
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
            p = val.replace("https://t.me/c/", "").split("/")
            await context.bot.copy_message(msg.chat_id, int("-100"+p[0]), int(p[1]), caption=caption)
        except Exception as e:
            await msg.reply_text(f"Xato: {str(e)}")
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
