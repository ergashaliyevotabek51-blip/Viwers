import os
import json
import asyncio
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
TOKEN = os.getenv("BOT_TOKEN")              # Muhit o'zgaruvchisidan oling
ADMIN_ID = 774440841
BOT_USERNAME = "UzbekFilmTv_bot"            # o'zgartiring
CHANNEL_USERNAME = "@UzbekFilmTv_Kanal"

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
    except Exception:
        return {}

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
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"users saqlashda xato: {e}")


def load_movies() -> dict:
    if not os.path.exists(MOVIES_FILE):
        return {}
    try:
        with open(MOVIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def save_movies(data: dict):
    try:
        with open(MOVIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"movies saqlashda xato: {e}")


def get_user(users: dict, user_id: int) -> dict:
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"used": 0, "referrals": 0, "joined": datetime.utcnow().isoformat()}
        save_users(users)
    return users[uid]


def max_limit(user: dict) -> int:
    return FREE_LIMIT + user.get("referrals", 0) * REF_LIMIT


# ================= ADMIN KEYBOARD =================
def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add"),
         InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete")],
        [InlineKeyboardButton("📃 Kinolar ro‘yxati", callback_data="list_movies"),
         InlineKeyboardButton("📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast")],
    ])


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    users = load_users()
    me = get_user(users, user.id)

    if args and len(args) > 0 and args[0].isdigit():
        ref_id = args[0]
        if ref_id != str(user.id) and ref_id in users and "refed" not in me:
            users[ref_id]["referrals"] = users[ref_id].get("referrals", 0) + 1
            me["refed"] = ref_id
            try:
                await context.bot.send_message(int(ref_id),
                    f"🎉 Yangi do‘st kirdi! Referral: {users[ref_id]['referrals']}")
            except:
                pass
            save_users(users)

    text = (
        f"<b>Assalomu alaykum, {user.first_name}!</b> 👋\n\n"
        f"🎬 <b>UzbekFilmTV</b> — eng sara o‘zbek filmlari!\n\n"
        f"🔥 Kod yuboring (masalan: 12, 45) → kino darhol keladi\n"
        f"• Bepul: 5 ta\n"
        f"• Har bir do‘st → +5 ta limit\n\n"
        f"🚀 Kod yuboring yoki do‘stlarni taklif qiling!"
    )

    kb = []
    if user.id == ADMIN_ID:
        kb = [[InlineKeyboardButton("🛠 Admin panel", callback_data="admin")]]

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
            text = "Kinolar:\n" + "\n".join(f"• {k}" for k in sorted(movies))
        await q.message.reply_text(text)
        return

    if data == "broadcast":
        context.user_data["mode"] = "broadcast_wait"
        await q.message.reply_text(
            "📢 Omaviy xabar yuborish\n\n"
            "Bot nomidan yubormoqchi bo‘lgan xabarni (matn/rasm/video/hujjat) yuboring yoki forward qiling.\n"
            "/cancel — bekor qilish"
        )
        return

    if data in ["add", "delete"]:
        context.user_data["mode"] = data
        prompt = "Format: kod|file_id yoki https://t.me/c/..." if data == "add" else "O‘chirish uchun kodni yozing"
        await q.message.reply_text(prompt)
        return


# ================= ASOSIY HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id

    text = (msg.text or "").strip()

    if text == "/cancel":
        context.user_data.clear()
        await msg.reply_text("❌ Bekor qilindi")
        return

    users = load_users()
    movies = load_movies()
    mode = context.user_data.get("mode")

    # Broadcast
    if mode == "broadcast_wait" and user_id == ADMIN_ID:
        context.user_data["mode"] = "broadcast_sending"
        await msg.reply_text("Yuborilmoqda... (katta bazada uzoq davom etishi mumkin)")

        success = failed = 0
        total = len(users)

        for uid_str in list(users):
            try:
                await msg.copy(chat_id=int(uid_str))
                success += 1
                await asyncio.sleep(0.42)  # ~2.3 msg/sec – xavfsiz
            except Exception:
                failed += 1

        context.user_data.clear()
        await msg.reply_text(
            f"Yuborish tugadi!\n"
            f"Muvaffaqiyatli: {success}\n"
            f"Xato: {failed}\n"
            f"Jami: {total}"
        )
        return

    # Admin limit
    if user_id == ADMIN_ID and text.lower().startswith("limit "):
        try:
            parts = text.split()
            if len(parts) != 3:
                raise ValueError
            _, uid_str, extra = parts
            extra = int(extra)
            if uid_str in users:
                users[uid_str]["referrals"] = users[uid_str].get("referrals", 0) + (extra // REF_LIMIT)
                save_users(users)
                await msg.reply_text(f"Limit qo‘shildi. Yangi jami: {max_limit(users[uid_str])}")
            else:
                await msg.reply_text("User topilmadi")
        except:
            await msg.reply_text("Misol: limit 123456789 20")
        return

    # Kino qo‘shish / o‘chirish
    if user_id == ADMIN_ID and mode in ["add", "delete"]:
        if mode == "add":
            if "|" not in text:
                await msg.reply_text("Format: kod|value")
                return
            code, value = [x.strip() for x in text.split("|", 1)]
            movies[code] = value
            save_movies(movies)
            await msg.reply_text("✅ Qo‘shildi")
        else:  # delete
            if text in movies:
                del movies[text]
                save_movies(movies)
                await msg.reply_text("🗑 O‘chirildi")
            else:
                await msg.reply_text("Topilmadi")
        context.user_data.pop("mode", None)
        return

    # Oddiy user → kod kiritdi
    if text in movies:
        user = get_user(users, user_id)
        if user["used"] >= max_limit(user):
            ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            txt = quote(f"Zo‘r o‘zbek filmlari shu botda!\nBepul 5 + do‘st uchun +5\n{ref_link}")
            url = f"https://t.me/share/url?url={quote(ref_link)}&text={txt}"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Do‘stlarga ulashish", url=url)]])
            await msg.reply_text("Limit tugadi! Do‘stlaringizni taklif qiling 👆", reply_markup=kb)
            return

        user["used"] += 1
        save_users(users)
        rem = f"{user['used']}/{max_limit(user)}"

        val = movies[text]
        share_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("Botni ulashish", url=f"https://t.me/{BOT_USERNAME}")
        ]])

        caption = f"🎬 Kino tayyor 🍿\nQolgan: {rem}\n\nKino @{BOT_USERNAME} dan\nKanal: {CHANNEL_USERNAME} 📢"

        if val.startswith("https://t.me/c/"):
            try:
                parts = val.replace("https://t.me/c/", "").split("/")
                ch_id = int("-100" + parts[0])
                msg_id = int(parts[1])
                await context.bot.copy_message(
                    chat_id=msg.chat_id,
                    from_chat_id=ch_id,
                    message_id=msg_id,
                    reply_markup=share_kb
                )
                await msg.reply_text(caption, parse_mode="HTML", reply_markup=share_kb)
            except Exception as e:
                await msg.reply_text(f"Kanal xatosi: {e}")
        else:
            await msg.reply_video(video=val, caption=caption, parse_mode="HTML", reply_markup=share_kb)

        return

    if text:
        await msg.reply_text("❌ Bunday kod yo‘q")


# ================= MAIN =================
def main():
    if not TOKEN:
        print("TOKEN topilmadi! BOT_TOKEN muhit o'zgaruvchisini o'rnating.")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", lambda u, c: cancel_broadcast(u, c)))
    app.add_handler(CallbackQueryHandler(admin_panel))

    # Bitta handler — text + media
    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document |
        filters.AUDIO | filters.VOICE | filters.VIDEO_NOTE,
        message_handler
    ))

    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi")


if __name__ == "__main__":
    main()
