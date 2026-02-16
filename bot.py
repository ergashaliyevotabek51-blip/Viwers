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
BOT_USERNAME = "UzbekFilmTv_bot"           # ← o‘zingizniki bilan almashtiring

USERS_FILE  = "users.json"
MOVIES_FILE = "movies.json"

FREE_LIMIT = 5
REF_LIMIT  = 5   # har bir referral uchun +5 ta kino

# ================= USER FILE SAFE OPERATIONS =================

def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        save_users({})
        return {}

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        data = {}

    # Eski list formatini aniqlash va dict ga aylantirish
    if isinstance(data, list):
        new_data = {}
        now = datetime.utcnow().isoformat()
        for old_id in data:
            try:
                uid = str(int(old_id))
                new_data[uid] = {
                    "used": 0,
                    "referrals": 0,
                    "joined": now,
                    "refed": None
                }
            except:
                continue
        save_users(new_data)
        return new_data

    # Dict formatini tozalash / normallashtirish
    cleaned = {}
    for k, v in data.items():
        if not isinstance(v, dict):
            continue
        try:
            uid = str(int(k))  # faqat raqamli ID larni saqlaymiz
            cleaned[uid] = {
                "used": int(v.get("used", 0)),
                "referrals": int(v.get("referrals", 0)),
                "joined": v.get("joined", datetime.utcnow().isoformat()),
                "refed": v.get("refed", None)
            }
        except:
            continue

    if cleaned != data:
        save_users(cleaned)

    return cleaned


def save_users(data: dict):
    # Hech qachon faylni o‘chirmaymiz, faqat yangilaymiz
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(users: dict, user_id: int) -> dict:
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "used": 0,
            "referrals": 0,
            "joined": datetime.utcnow().isoformat(),
            "refed": None
        }
        save_users(users)
    return users[uid]


def max_limit(user: dict) -> int:
    return FREE_LIMIT + user["referrals"] * REF_LIMIT


# ================= ADMIN KEYBOARD (2×2) =================
def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Kino qo‘shish",    callback_data="admin_add_movie"),
            InlineKeyboardButton("➖ Kino o‘chirish",   callback_data="admin_delete_movie"),
        ],
        [
            InlineKeyboardButton("📃 Kinolar ro‘yxati", callback_data="admin_list_movies"),
            InlineKeyboardButton("📊 Statistika",       callback_data="admin_stats"),
        ],
    ])


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    users = load_users()
    me = get_user(users, user.id)

    # Referral logikasi
    if args and args[0].isdigit():
        ref_id = args[0]
        if ref_id != str(user.id) and ref_id in users and me["refed"] is None:
            users[ref_id]["referrals"] += 1
            me["refed"] = ref_id
            try:
                await context.bot.send_message(
                    int(ref_id),
                    f"🎉 Yangi do‘st kirdi!\nReferral soni: {users[ref_id]['referrals']}"
                )
            except:
                pass
            save_users(users)

    text = (
        f"<b>Assalomu alaykum, {user.first_name}!</b> 👋\n\n"
        f"🎬 <b>UzbekFilmTV</b> — eng sara o‘zbek filmlari shu yerdagi bot!\n\n"
        f"🔥 <b>Qanday ishlaydi?</b>\n"
        f"• Kod yuboring (masalan: 12, 45, 107) → kino darhol keladi\n"
        f"• Bepul limit: <b>{FREE_LIMIT} ta kino</b>\n"
        f"• Har bir do‘st taklif qilsangiz → +{REF_LIMIT} ta limit\n\n"
        f"🚀 Kodni yuboring yoki do‘stlaringizni taklif qiling!"
    )

    kb = []
    if user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin_panel")])

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(kb) if kb else None,
        parse_mode="HTML"
    )


# ================= ADMIN PANEL & CALLBACKS =================
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id != ADMIN_ID:
        await query.message.reply_text("Siz admin emassiz.")
        return

    data = query.data

    if data == "admin_panel":
        await query.edit_message_text("🛠 Admin panel", reply_markup=get_admin_keyboard())
        return

    users = load_users()
    movies = load_json(MOVIES_FILE, {})

    if data == "admin_stats":
        text = (
            f"📊 <b>Statistika</b>\n\n"
            f"👥 Foydalanuvchilar: <b>{len(users)}</b>\n"
            f"🎥 Kinolar soni:    <b>{len(movies)}</b>"
        )
        await query.message.reply_text(text, parse_mode="HTML")
        return

    if data == "admin_list_movies":
        if not movies:
            text = "Hozircha hech qanday kino qo‘shilmagan."
        else:
            lines = ["🎬 <b>Kinolar ro‘yxati</b>\n"]
            for i, code in enumerate(sorted(movies.keys()), 1):
                lines.append(f"{i}. <code>{code}</code>")
            text = "\n".join(lines)
        await query.message.reply_text(text, parse_mode="HTML")
        return

    if data in ("admin_add_movie", "admin_delete_movie"):
        mode = "add" if data == "admin_add_movie" else "delete"
        context.user_data["admin_mode"] = mode
        if mode == "add":
            await query.message.reply_text("Format:\n<code>kod|file_id yoki kanal link</code>")
        else:
            await query.message.reply_text("O‘chirish uchun kodni yuboring")
        return


# ================= TEXT / MOVIE HANDLER =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text.strip()
    user_id = msg.from_user.id

    # /cancel
    if text == "/cancel":
        context.user_data.clear()
        await msg.reply_text("❌ Bekor qilindi")
        return

    users  = load_users()
    movies = load_json(MOVIES_FILE, {})

    user = get_user(users, user_id)
    mode = context.user_data.get("admin_mode")

    # Admin kino qo‘shish / o‘chirish
    if user_id == ADMIN_ID and mode in ("add", "delete"):
        if mode == "add":
            if "|" not in text:
                await msg.reply_text("Format: kod|value")
                return
            code, value = [x.strip() for x in text.split("|", 1)]
            movies[code] = value
            save_json(MOVIES_FILE, movies)
            await msg.reply_text(f"✅ Kod <code>{code}</code> qo‘shildi")
        else:  # delete
            if text in movies:
                del movies[text]
                save_json(MOVIES_FILE, movies)
                await msg.reply_text(f"🗑 Kod <code>{text}</code> o‘chirildi")
            else:
                await msg.reply_text("❌ Bunday kod topilmadi")
        context.user_data.pop("admin_mode", None)
        return

    # Oddiy user → kino so‘rayapti
    if text not in movies:
        await msg.reply_text("❌ Bunday kod topilmadi")
        return

    current_limit = max_limit(user)
    if user["used"] >= current_limit:
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        share_text = quote(
            f"Eng zo‘r o‘zbek filmlari shu botda! 🔥\n"
            f"Bepul {FREE_LIMIT} ta + har bir do‘st uchun +{REF_LIMIT} ta!\n\n{ref_link}"
        )
        share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={share_text}"

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("👥 Do‘stlarga ulashish", url=share_url)
        ]])

        await msg.reply_text(
            f"🔒 Limit tugadi!\n\n"
            f"Qolgan: 0/{current_limit}\n"
            f"Do‘stlar: {user['referrals']}",
            reply_markup=kb,
            disable_web_page_preview=True
        )
        return

    # Limit bor → kino beramiz
    user["used"] += 1
    save_users(users)

    remaining = f"{user['used']}/{current_limit}"

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
            channel_id = int("-100" + parts[0])
            msg_id = int(parts[1])

            await context.bot.copy_message(
                chat_id=msg.chat_id,
                from_chat_id=channel_id,
                message_id=msg_id,
                caption=caption,           # yangi caption
                parse_mode="HTML"
            )
        except Exception as e:
            await msg.reply_text(f"Xato: kanal xabari ko‘chirib bo‘lmadi\n({str(e)})")
    else:
        # file_id deb faraz qilamiz (video)
        await msg.reply_video(
            video=val,
            caption=caption,
            parse_mode="HTML"
        )


def load_json(path, default=None)
