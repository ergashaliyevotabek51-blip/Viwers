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
CHANNEL_USERNAME = "@UzbekFilmTv_Kanal"    # kanal username (agar kerak bo'lsa)

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"

FREE_LIMIT = 5
REF_LIMIT = 5

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
        [
            InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add"),
            InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete"),
        ],
        [
            InlineKeyboardButton("📃 Kinolar ro‘yxati", callback_data="list_movies"),
            InlineKeyboardButton("📊 Statistika", callback_data="stats"),
        ],
    ])


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    users = load_users()
    me = get_user(users, user.id)

    if args and args[0].isdigit():
        ref_id = args[0]
        if ref_id != str(user.id) and ref_id in users and me.get("refed") is None:
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
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="HTML")


# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.from_user.id != ADMIN_ID:
        return

    data = q.data

    if data == "admin":
        await q.edit_message_text("🛠 Admin panel", reply_markup=admin_keyboard())
        return

    users = load_users()
    movies = load_movies()

    if data == "stats":
        await q.message.reply_text(f"👥 Userlar: {len(users)}\n🎬 Kinolar: {len(movies)}")
        return

    if data == "list_movies":
        if not movies:
            text = "Hozircha kinolar yo‘q."
        else:
            text = "Kinolar ro‘yxati:\n" + "\n".join(f"• {code}" for code in sorted(movies.keys()))
        await q.message.reply_text(text)
        return

    if data in ["add", "delete"]:
        context.user_data["mode"] = data
        msg = "Format:\n`kod|file_id yoki kanal link`" if data == "add" else "O‘chirish uchun kodni yuboring"
        await q.message.reply_text(msg)
        return


# ================= TEXT HANDLER =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text.strip()
    user_id = msg.from_user.id

    users = load_users()
    movies = load_movies()
    user = get_user(users, user_id)
    mode = context.user_data.get("mode")

    if text == "/cancel":
        context.user_data.clear()
        await msg.reply_text("❌ Bekor qilindi")
        return

    # Admin limit qo‘shish
    if user_id == ADMIN_ID and text.lower().startswith("limit "):
        try:
            _, target_uid, extra = text.split()
            target_uid = str(target_uid)
            extra = int(extra)

            if target_uid in users:
                users[target_uid]["referrals"] += extra // REF_LIMIT
                save_users(users)
                new_max = max_limit(users[target_uid])
                await msg.reply_text(
                    f"User {target_uid} ga qo‘shimcha limit berildi!\n"
                    f"Yangi referrals: {users[target_uid]['referrals']}\n"
                    f"Jami limit: {new_max}"
                )
            else:
                await msg.reply_text("Bunday user topilmadi")
        except:
            await msg.reply_text("Format noto‘g‘ri!\nMisol: limit 123456789 15")
        return

    # Kino qo‘shish / o‘chirish
    if user_id == ADMIN_ID and mode in ["add", "delete"]:
        if mode == "add":
            if "|" not in text:
                await msg.reply_text("Format: kod|value")
                return
            code, val = [x.strip() for x in text.split("|", 1)]
            movies[code] = val
            save_movies(movies)
            await msg.reply_text("✅ Kino qo‘shildi")
        elif mode == "delete":
            if text in movies:
                del movies[text]
                save_movies(movies)
                await msg.reply_text("🗑 O‘chirildi")
            else:
                await msg.reply_text("❌ Topilmadi")
        context.user_data.pop("mode", None)
        return

    # User kino so‘radi
    if text in movies:
        if user["used"] >= max_limit(user):
            ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            share_text = quote(
                f"Eng zo‘r o‘zbek filmlari shu botda! 🔥\n"
                f"Bepul 5 ta kino + har bir do‘st uchun +5 ta limit!\n\n"
                f"{ref_link}"
            )
            share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={share_text}"

            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("👥 Do‘stlarga ulashish", url=share_url)
            ]])

            await msg.reply_text(
                f"🔒 Limit tugadi!\n\n"
                f"Qolgan: 0/{max_limit(user)}\n"
                f"Do‘stlar soni: {user['referrals']}\n\n"
                f"Yana ko‘proq kino uchun do‘stlaringizni taklif qiling!",
                reply_markup=kb,
                disable_web_page_preview=True
            )
            return

        user["used"] += 1
        save_users(users)

        remaining = f"{user['used']}/{max_limit(user)}"

        # Ulashish tugmasi
        ref_link = f"https://t.me/{BOT_USERNAME}"
        share_text = quote(
            f"Eng zo‘r o‘zbek filmlari shu botda! 🔥\n"
            f"Kodni yuboring → kino darhol keladi!\n"
            f"{ref_link}"
        )
        share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={share_text}"

        share_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🤖 Botni do‘stlarga ulashish", url=share_url)
        ]])

        val = movies[text]

        if val.startswith("https://t.me/c/"):
            p = val.replace("https://t.me/c/", "").split("/")
            channel_id = int("-100" + p[0])
            msg_id = int(p[1])

            # 1. Kanal xabarini ASLI HOLATIDA ko'chirish (asl caption saqlanadi)
            await context.bot.copy_message(
                chat_id=msg.chat_id,
                from_chat_id=channel_id,
                message_id=msg_id,
                reply_markup=share_kb
            )

            # 2. Pastga reply qilib qo'shimcha matn
            extra = (
                f"🎬 Kino tayyor 🍿\n"
                f"Qolgan: {remaining}\n\n"
                f"Kino <b>@{BOT_USERNAME}</b> dan yuklandi\n"
                f"Telegram kanal: <b>{CHANNEL_USERNAME}</b> 📢"
            )

            await msg.reply_text(extra, parse_mode="HTML", reply_markup=share_kb)

        else:
            # file_id bo'lsa
            caption = (
                f"🎬 Kino tayyor 🍿\n"
                f"Qolgan: {remaining}\n\n"
                f"Kino <b>@{BOT_USERNAME}</b> dan yuklandi\n"
                f"Telegram kanal: <b>{CHANNEL_USERNAME}</b> 📢"
            )

            await msg.reply_video(
                video=val,
                caption=caption,
                reply_markup=share_kb,
                parse_mode="HTML"
            )

        return

    await msg.reply_text("❌ Bunday kod topilmadi")


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", lambda u, c: cancel_broadcast(u, c)))
    app.add_handler(CallbackQueryHandler(admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi")


if __name__ == "__main__":
    main()
