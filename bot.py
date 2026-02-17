import os
import json
from datetime import datetime
from urllib.parse import quote
import asyncio

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
if not TOKEN:
    raise ValueError("BOT_TOKEN muhit o'zgaruvchisi topilmadi!")

ADMIN_ID = 774440841
BOT_USERNAME = "UzbekFilmTv_bot"
CHANNEL_USERNAME = "@UzbekFilmTv_Kanal"

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"

FREE_LIMIT = 5
REF_LIMIT = 5

# ================= Fayl funksiyalari =================

def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(data: dict):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"users.json saqlashda xato: {e}")


def load_movies() -> dict:
    if not os.path.exists(MOVIES_FILE):
        return {}
    try:
        with open(MOVIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_movies(data: dict):
    try:
        with open(MOVIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"movies.json saqlashda xato: {e}")


def get_user(users: dict, user_id: int) -> dict:
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"used": 0, "referrals": 0, "joined": datetime.utcnow().isoformat()}
        save_users(users)
    return users[uid]


def max_limit(user: dict) -> int:
    return FREE_LIMIT + user.get("referrals", 0) * REF_LIMIT


# ================= Klaviaturalar =================

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
        [
            InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast"),
        ],
    ])


# ================= /start =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    users = load_users()
    me = get_user(users, user.id)

    if len(args) > 0 and args[0].isdigit():
        ref_id = args[0]
        if ref_id != str(user.id) and ref_id in users and "refed" not in me:
            users[ref_id]["referrals"] = users[ref_id].get("referrals", 0) + 1
            me["refed"] = ref_id
            try:
                await context.bot.send_message(int(ref_id),
                    f"🎉 Yangi do‘st! Referral: {users[ref_id]['referrals']}")
            except:
                pass
            save_users(users)

    text = (
        f"<b>Assalomu alaykum, {user.first_name}!</b> 👋\n\n"
        f"🎬 UzbekFilmTV — o‘zbek filmlari botida!\n\n"
        f"Kod yuboring → kino keladi\n"
        f"Bepul: 5 ta  •  Do‘st uchun: +5 ta\n\n"
        f"Tayyor bo‘lsangiz kod yozing!"
    )

    kb = []
    if user.id == ADMIN_ID:
        kb = [[InlineKeyboardButton("🛠 Admin", callback_data="admin")]]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="HTML")


# ================= Admin panel =================

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
        await q.message.reply_text(f"Userlar: {len(users)}\nKinolar: {len(movies)}")
        return

    if data == "list_movies":
        if not movies:
            text = "Kinolar yo‘q"
        else:
            text = "Kinolar:\n" + "\n".join(f"• {code}" for code in sorted(movies))
        await q.message.reply_text(text)
        return

    if data == "broadcast":
        context.user_data["mode"] = "wait_broadcast"
        await q.message.reply_text(
            "Omaviy xabar yuborish\n\n"
            "Endi botga yubormoqchi bo‘lgan xabarni (matn/rasm/video) yuboring yoki forward qiling.\n"
            "/cancel — chiqish"
        )
        return

    if data in ["add", "delete"]:
        context.user_data["mode"] = data
        prompt = "kod|link yoki file_id" if data == "add" else "o‘chirish uchun kod"
        await q.message.reply_text(prompt)
        return


# ================= Asosiy xabar handleri =================

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

    # Broadcast rejimi
    if mode == "wait_broadcast" and user_id == ADMIN_ID:
        context.user_data["mode"] = "sending_broadcast"
        await msg.reply_text("Yuborilmoqda...")

        success = 0
        failed = 0
        total = len(users)

        for uid_str in list(users.keys()):
            try:
                await msg.copy(chat_id=int(uid_str))
                success += 1
                await asyncio.sleep(0.45)  # juda muhim – tez yuborsangiz bloklanasiz
            except Exception:
                failed += 1

        context.user_data.clear()
        await msg.reply_text(
            f"Tugadi!\nMuvaffaqiyat: {success}\nXato: {failed}\nJami: {total}"
        )
        return

    # Admin limit qo‘shish
    if user_id == ADMIN_ID and text.lower().startswith("limit "):
        try:
            _, uid, val = text.split()
            val = int(val)
            if uid in users:
                users[uid]["referrals"] = users[uid].get("referrals", 0) + (val // REF_LIMIT)
                save_users(users)
                await msg.reply_text(f"Limit qo‘shildi → {max_limit(users[uid])}")
            else:
                await msg.reply_text("User topilmadi")
        except:
            await msg.reply_text("Misol: limit 123456789 25")
        return

    # Kino qo‘shish / o‘chirish
    if user_id == ADMIN_ID and mode in ["add", "delete"]:
        if mode == "add":
            if "|" not in text:
                await msg.reply_text("Format: kod|qiymat")
                return
            code, val = [x.strip() for x in text.split("|", 1)]
            movies[code] = val
            save_movies(movies)
            await msg.reply_text("✅ Qo‘shildi")
        else:
            if text in movies:
                del movies[text]
                save_movies(movies)
                await msg.reply_text("🗑 O‘chirildi")
            else:
                await msg.reply_text("Topilmadi")
        context.user_data.pop("mode", None)
        return

    # Foydalanuvchi kod yubordi
    if text in movies:
        user = get_user(users, user_id)
        if user["used"] >= max_limit(user):
            ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            txt = quote(f"Zo‘r filmlar shu botda!\nBepul 5 + do‘st uchun +5\n{ref_link}")
            share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={txt}"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Ulashish", url=share_url)]])
            await msg.reply_text("Limit tugadi! Do‘st taklif qiling 👆", reply_markup=kb)
            return

        user["used"] += 1
        save_users(users)
        rem = f"{user['used']}/{max_limit(user)}"

        val = movies[text]
        share_kb = InlineKeyboardMarkup([[InlineKeyboardButton("Botni ulashish", url=f"https://t.me/{BOT_USERNAME}")]])

        caption = f"🎬 Kino tayyor\nQolgan: {rem}\n\n@{BOT_USERNAME} • {CHANNEL_USERNAME}"

        try:
            if val.startswith("https://t.me/c/"):
                parts = val.replace("https://t.me/c/", "").split("/")
                ch = int("-100" + parts[0])
                mid = int(parts[1])
                await context.bot.copy_message(msg.chat_id, ch, mid, reply_markup=share_kb)
                await msg.reply_text(caption, parse_mode="HTML", reply_markup=share_kb)
            else:
                await msg.reply_video(val, caption=caption, parse_mode="HTML", reply_markup=share_kb)
        except Exception as e:
            await msg.reply_text(f"Xato: {str(e)[:200]}")
        return

    if text:
        await msg.reply_text("Bunday kod yo‘q")


# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", lambda u, c: cancel_broadcast(u, c)))
    app.add_handler(CallbackQueryHandler(admin_panel))

    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VIDEO | filters.VIDEO_NOTE |
        filters.Document | filters.AUDIO | filters.VOICE,
        message_handler
    ))

    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi")


if __name__ == "__main__":
    main()
