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
BOT_USERNAME = "UzbekFilmTv_bot"           # o'zingiznikiga o'zgartiring

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"

FREE_LIMIT = 5
REF_LIMIT = 5  # har bir referral uchun +5

# ================= Fayl bilan ishlash - users.json ni himoya qilish =================

def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return {}

    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        data = {}

    # Agar eski list format bo'lsa → dict ga aylantiramiz
    if isinstance(data, list):
        new_data = {}
        now = datetime.utcnow().isoformat()
        for uid in data:
            if isinstance(uid, (int, str)) and str(uid).isdigit():
                uid_str = str(uid)
                new_data[uid_str] = {
                    "used": 0,
                    "referrals": 0,
                    "joined": now
                }
        data = new_data
        # darhol saqlaymiz
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # Dict ni tozalash va standartlashtirish
    cleaned = {}
    for k, v in data.items():
        if not isinstance(v, dict):
            continue
        try:
            cleaned[str(int(k))] = {
                "used": int(v.get("used", 0)),
                "referrals": int(v.get("referrals", 0)),
                "joined": v.get("joined", datetime.utcnow().isoformat())
            }
        except:
            continue

    if cleaned != data:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)

    return cleaned


def save_users(users: dict):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


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


# ================= ADMIN PANEL TUGMALARI (2×2) =================
def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Kino qo‘shish", callback_data="admin_add_movie"),
            InlineKeyboardButton("➖ Kino o‘chirish", callback_data="admin_delete_movie"),
        ],
        [
            InlineKeyboardButton("📃 Kinolar ro‘yxati", callback_data="admin_list_movies"),
            InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"),
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
                await context.bot.send_message(
                    int(ref_id),
                    f"🎉 Yangi do‘st kirdi! Referral: {users[ref_id]['referrals']}"
                )
            except:
                pass
            save_users(users)

    text = (
        f"<b>Assalomu alaykum, {user.first_name}!</b> 👋\n\n"
        f"🎬 <b>UzbekFilmTV</b> — eng sara o‘zbek filmlari shu yerdagi bot!\n\n"
        f"🔥 Kod yuboring (masalan: 12, 45, 107) → kino darhol keladi\n"
        f"• Bepul limit: <b>{FREE_LIMIT} ta</b>\n"
        f"• Har bir do‘st → +{REF_LIMIT} ta limit\n\n"
        f"Kodni yuboring yoki do‘stlaringizni taklif qiling!"
    )

    kb = []
    if user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin_panel")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="HTML")


# ================= ADMIN PANEL HANDLER =================
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
    try:
        with open(MOVIES_FILE, 'r', encoding='utf-8') as f:
            movies = json.load(f)
    except:
        movies = {}

    if data == "admin_stats":
        text = (
            f"📊 <b>Statistika</b>\n\n"
            f"👥 Foydalanuvchilar: <b>{len(users)}</b>\n"
            f"🎥 Kinolar soni:   <b>{len(movies)}</b>"
        )
        await query.message.reply_text(text, parse_mode="HTML")
        return

    if data == "admin_list_movies":
        if not movies:
            text = "Hozircha hech qanday kino qo‘shilmagan."
        else:
            text = "🎬 <b>Kinolar ro‘yxati</b>\n\n"
            for i, code in enumerate(sorted(movies.keys()), 1):
                text += f"{i}. <code>{code}</code>\n"
        await query.message.reply_text(text, parse_mode="HTML")
        return

    if data in ("admin_add_movie", "admin_delete_movie"):
        mode = "add" if data == "admin_add_movie" else "delete"
        context.user_data["mode"] = mode
        msg = "kod|file_id yoki kanal link" if mode == "add" else "o‘chiriladigan kodni yuboring"
        await query.message.reply_text(f"Format:\n{msg}")
        return


# ================= TEXT / KINO HANDLER =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text.strip()
    user_id = msg.from_user.id

    if text == "/cancel":
        context.user_data.clear()
        await msg.reply_text("❌ Bekor qilindi")
        return

    users = load_users()
    try:
        with open(MOVIES_FILE, 'r', encoding='utf-8') as f:
            movies = json.load(f)
    except:
        movies = {}

    user = get_user(users, user_id)
    mode = context.user_data.get("mode")

    # Admin kino qo'shish / o'chirish
    if user_id == ADMIN_ID and mode:
        if mode == "add":
            if "|" not in text:
                await msg.reply_text("Format: kod|qiymat")
                return
            code, val = [x.strip() for x in text.split("|", 1)]
            movies[code] = val
            with open(MOVIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(movies, f, ensure_ascii=False, indent=2)
            await msg.reply_text("✅ Kino qo‘shildi")
        elif mode == "delete":
            if text in movies:
                del movies[text]
                with open(MOVIES_FILE, 'w', encoding='utf-8') as f:
                    json.dump(movies, f, ensure_ascii=False, indent=2)
                await msg.reply_text("🗑 O‘chirildi")
            else:
                await msg.reply_text("❌ Topilmadi")
        context.user_data.clear()
        return

    # Oddiy user kino kodi yubordi
    if text not in movies:
        await msg.reply_text("❌ Bunday kod topilmadi")
        return

    if user["used"] >= max_limit(user):
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        share_text = quote(
            f"Eng zo‘r o‘zbek filmlari shu botda!\n"
            f"Bepul {FREE_LIMIT} ta + do‘st uchun +{REF_LIMIT} ta\n\n{ref_link}"
        )
        share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={share_text}"

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("👥 Do‘stlarga ulashish", url=share_url)
        ]])

        await msg.reply_text(
            f"🔒 Limit tugadi!\n\n"
            f"Qolgan: 0/{max_limit(user)}\n"
            f"Do‘stlar: {user['referrals']}",
            reply_markup=kb
        )
        return

    # Kino beramiz
    user["used"] += 1
    save_users(users)

    remaining = f"{user['used']}/{max_limit(user)}"

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
            channel_id = int("-100" + p[0])
            msg_id = int(p[1])

            await context.bot.copy_message(
                chat_id=msg.chat_id,
                from_chat_id=channel_id,
                message_id=msg_id,
                caption=caption
            )
        except Exception as e:
            await msg.reply_text(f"Kanal xabari ko‘chirib bo‘lmadi: {str(e)}")
    else:
        # file_id deb hisoblaymiz
        await msg.reply_video(
            video=val,
            caption=caption
        )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
