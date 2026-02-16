import os
import json
import traceback
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
if not TOKEN:
    print("CRITICAL: BOT_TOKEN environment variable topilmadi!")
    raise ValueError("BOT_TOKEN yo'q")

ADMIN_ID = 774440841
BOT_USERNAME = "UzbekFilmTv_bot"  # o'zingiznikiga o'zgartiring

USERS_FILE  = "users.json"
MOVIES_FILE = "movies.json"

FREE_LIMIT = 5
REF_LIMIT  = 5

# ================= SAFE FILE OPERATIONS =================

def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        print(f"{USERS_FILE} yo'q → yangi bo'sh dict yaratilmoqda")
        save_users({})
        return {}

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                save_users({})
                return {}
            data = json.loads(content)
    except Exception as e:
        print(f"users.json o'qishda xato: {e}")
        save_users({})
        return {}

    # Eski list formatini dict ga o'tkazish
    if isinstance(data, list):
        print("Eski list format aniqlandi → dict ga konvertatsiya")
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

    # Tozalash va normallashtirish
    cleaned = {}
    for k, v in data.items():
        try:
            uid = str(int(k))
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
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"{USERS_FILE} saqlandi ({len(data)} ta user)")
    except Exception as e:
        print(f"save_users xatosi: {e}")


def load_movies() -> dict:
    if not os.path.exists(MOVIES_FILE):
        save_movies({})
        return {}
    try:
        with open(MOVIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"movies.json xatosi: {e}")
        return {}


def save_movies(data: dict):
    try:
        with open(MOVIES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"save_movies xatosi: {e}")


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


# ================= ADMIN KEYBOARD =================
def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Kino qo‘shish",    callback_data="admin_add"),
            InlineKeyboardButton("➖ Kino o‘chirish",   callback_data="admin_delete"),
        ],
        [
            InlineKeyboardButton("📃 Kinolar ro‘yxati", callback_data="admin_list"),
            InlineKeyboardButton("📊 Statistika",       callback_data="admin_stats"),
        ],
    ])


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    try:
        users = load_users()
        me = get_user(users, user.id)

        if args and args[0].isdigit():
            ref_id = args[0]
            if ref_id != str(user.id) and ref_id in users and me["refed"] is None:
                users[ref_id]["referrals"] += 1
                me["refed"] = ref_id
                try:
                    await context.bot.send_message(
                        int(ref_id),
                        f"🎉 Yangi referral! Soni: {users[ref_id]['referrals']}"
                    )
                except:
                    pass
                save_users(users)

        text = (
            f"<b>Assalomu alaykum, {user.first_name}!</b> 👋\n\n"
            f"🎬 O‘zbek filmlari botiga xush kelibsiz!\n\n"
            f"Kodni yuboring → film keladi\n"
            f"Bepul: {FREE_LIMIT} ta\n"
            f"Do‘st uchun: +{REF_LIMIT} ta\n\n"
            f"Kodni yozing!"
        )

        kb = []
        if user.id == ADMIN_ID:
            kb.append([InlineKeyboardButton("🛠 Admin", callback_data="admin_panel")])

        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="HTML")
    except Exception as e:
        print(f"start handler xatosi: {e}")
        await update.message.reply_text("Texnik xato yuz berdi 😔")


# ================= ADMIN CALLBACK =================
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data
    try:
        if data == "admin_panel":
            await query.edit_message_text("🛠 Admin panel", reply_markup=get_admin_keyboard())
            return

        users = load_users()
        movies = load_movies()

        if data == "admin_stats":
            text = f"👥 Userlar: {len(users)}\n🎥 Kinolar: {len(movies)}"
            await query.message.reply_text(text)
            return

        if data == "admin_list":
            if not movies:
                text = "Kinolar hali yo‘q"
            else:
                text = "Kinolar ro‘yxati:\n" + "\n".join(f"• {k}" for k in sorted(movies))
            await query.message.reply_text(text)
            return

        if data in ("admin_add", "admin_delete"):
            mode = "add" if data == "admin_add" else "delete"
            context.user_data["admin_mode"] = mode
            msg = "kod|file_id yoki link" if mode == "add" else "o‘chiriladigan kod"
            await query.message.reply_text(f"Format: {msg}")
            return
    except Exception as e:
        print(f"admin_callback xatosi: {e}")
        await query.message.reply_text("Admin panelda xato")


# ================= MESSAGE HANDLER =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text.strip()
    uid = msg.from_user.id

    try:
        if text == "/cancel":
            context.user_data.clear()
            await msg.reply_text("Bekor qilindi")
            return

        users = load_users()
        movies = load_movies()
        user = get_user(users, uid)

        mode = context.user_data.get("admin_mode")

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
                    await msg.reply_text("Topilmadi")
            context.user_data.pop("admin_mode", None)
            return

        # oddiy user → kino kodi
        if text not in movies:
            await msg.reply_text("Bunday kod yo‘q")
            return

        limit = max_limit(user)
        if user["used"] >= limit:
            await msg.reply_text(f"Limit tugadi (0/{limit})\nDo‘stlarni taklif qiling!")
            return

        user["used"] += 1
        save_users(users)

        remaining = f"{user['used']}/{limit}"

        caption = (
            "🎬 Kino tayyor 🍿\n"
            f"Qolgan: {remaining}\n\n"
            f"🤖 @{BOT_USERNAME}\n"
            f"📢 @UzbekFilmTv_Kanal"
        )

        val = movies[text]

        if val.startswith("https://t.me/c/"):
            parts = val.replace("https://t.me/c/", "").split("/")
            ch_id = int("-100" + parts[0])
            msg_id = int(parts[1])
            await context.bot.copy_message(
                msg.chat_id,
                ch_id,
                msg_id,
                caption=caption,
                parse_mode="HTML"
            )
        else:
            await msg.reply_video(video=val, caption=caption, parse_mode="HTML")

    except Exception as e:
        print(f"text_handler xatosi:\n{traceback.format_exc()}")
        await msg.reply_text("Xato yuz berdi, admin bilan bog‘laning")


# ================= MAIN =================
def main():
    print("Bot ishga tushmoqda...")
    try:
        app = ApplicationBuilder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(admin_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

        print("Polling boshlanmoqda...")
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        print("===== BOT TO‘LIQ CRASH BO‘LDI =====")
        print(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
