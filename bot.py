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
from telegram.error import TelegramError, BadRequest, Forbidden

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")                  # .env yoki muhit o'zgaruvchisidan oling
ADMIN_ID = 774440841                            # o'zingizning ID'ingiz
BOT_USERNAME = "UzbekFilmTv_bot"
CHANNEL_USERNAME = "@UzbekFilmTv_Kanal"

MANDATORY_CHANNELS = []                         # default bo'sh — avval ishlasin
MAX_MANDATORY_CHANNELS = 10

FREE_LIMIT = 5
REF_LIMIT = 5

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"
SETTINGS_FILE = "settings.json"

# ================= SETTINGS =================
def load_settings():
    global MANDATORY_CHANNELS
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                MANDATORY_CHANNELS = data.get("mandatory_channels", [])
        except Exception as e:
            print(f"Settings yuklashda xato: {e}")
            MANDATORY_CHANNELS = []


def save_settings():
    global MANDATORY_CHANNELS
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"mandatory_channels": MANDATORY_CHANNELS}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Settings saqlashda xato: {e}")


load_settings()

# ================= Fayl bilan ishlash =================

def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        save_users({})
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return {}
            return data
    except:
        return {}


def save_users(data: dict):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Users saqlashda xato: {e}")


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
        print(f"Movies saqlashda xato: {e}")


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
def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add"),
         InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete")],
        [InlineKeyboardButton("📃 Kinolar ro‘yxati", callback_data="list_movies"),
         InlineKeyboardButton("📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast")],
        [InlineKeyboardButton("🔒 Majburiy obuna sozlamalari", callback_data="subscription")],
    ])


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[START] User: {update.effective_user.id} ({update.effective_user.username})")
    
    user = update.effective_user
    args = context.args

    subscribed = await is_subscribed(context, user.id)
    print(f"[START] Obuna holati: {subscribed}, Kanallar: {MANDATORY_CHANNELS}")

    if MANDATORY_CHANNELS and not subscribed:
        await send_subscription_message(update.message)
        return

    users = load_users()
    me = get_user(users, user.id)

    if args and len(args) > 0 and args[0].isdigit():
        ref_id = args[0]
        if ref_id != str(user.id) and ref_id in users and me.get("refed") is None:
            users[ref_id]["referrals"] += 1
            me["refed"] = ref_id
            try:
                await context.bot.send_message(int(ref_id), f"🎉 Yangi do‘st! Referral: {users[ref_id]['referrals']}")
            except:
                pass
            save_users(users)

    text = (
        f"<b>Assalomu alaykum, {user.first_name}!</b> 👋\n\n"
        f"🎬 <b>UzbekFilmTV</b> — eng sara o‘zbek filmlari!\n\n"
        f"🔥 Kod yuboring (masalan: 12, 45) → kino darhol keladi\n"
        f"• Bepul: <b>5 ta</b>   • Do‘st uchun: <b>+5 ta</b>\n\n"
        f"Kodni yozing yoki do‘stlaringizni taklif qiling!"
    )

    kb = []
    if user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="HTML")


# ================= ADMIN COMMAND =================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Admin emassiz!")
        return
    await update.message.reply_text("🛠 Admin panel", reply_markup=admin_keyboard())


# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    if q.data == "check_sub":
        if await is_subscribed(context, user_id):
            await q.edit_message_text("✅ Obuna tasdiqlandi!")
        else:
            await q.edit_message_text("❌ Hali hammaga obuna bo‘lmagansiz.")
        return

    if user_id != ADMIN_ID:
        return

    data = q.data

    if data == "admin":
        await q.edit_message_text("🛠 Admin panel", reply_markup=admin_keyboard())
        return

    if data == "stats":
        users = load_users()
        movies = load_movies()
        await q.message.reply_text(f"👥 Userlar: {len(users)}\n🎬 Kinolar: {len(movies)}")
        return

    if data == "list_movies":
        movies = load_movies()
        text = "Kinolar yo‘q." if not movies else "\n".join(f"• {k}" for k in sorted(movies))
        await q.message.reply_text(text)
        return

    if data == "broadcast":
        context.user_data["mode"] = "broadcast"
        await q.message.reply_text("Xabarni yuboring yoki forward qiling.\n/cancel — bekor qilish")
        return

    if data == "subscription":
        curr = "\n".join(f"• {c}" for c in MANDATORY_CHANNELS) or "Yo‘q"
        text = f"<b>Majburiy kanallar ({len(MANDATORY_CHANNELS)}/{MAX_MANDATORY_CHANNELS}):</b>\n{curr}\n\n"
        text += "add @kanal1 @kanal2\n"
        text += "del @kanal1\n"
        text += "clear\n"
        text += "off"
        context.user_data["mode"] = "subscription"
        await q.message.reply_text(text, parse_mode="HTML")
        return

    if data in ["add", "delete"]:
        context.user_data["mode"] = data
        msg = "kod|file_id yoki link" if data == "add" else "O‘chirish uchun kod"
        await q.message.reply_text(msg)
        return


# ================= SUBSCRIPTION CHECK =================
async def is_subscribed(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    if not MANDATORY_CHANNELS:
        return True

    for channel in MANDATORY_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator", "restricted"]:
                return False
        except (Forbidden, BadRequest, TelegramError) as e:
            print(f"Obuna check xatosi {channel}: {type(e).__name__} {e}")
            return False     # bot admin emas yoki kanal yo‘q → bloklaymiz
        except Exception as e:
            print(f"Noma'lum xato {channel}: {e}")
            return False
    return True


async def send_subscription_message(message):
    if not MANDATORY_CHANNELS:
        await message.reply_text("Majburiy kanallar sozlanmagan.")
        return

    kb = []
    for ch in MANDATORY_CHANNELS:
        clean = ch.lstrip('@')
        kb.append([InlineKeyboardButton(f"📢 {clean}", url=f"https://t.me/{clean}")])

    kb.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")])

    channels_list = "\n".join(f"• {c}" for c in MANDATORY_CHANNELS)

    await message.reply_text(
        f"Quyidagi {len(MANDATORY_CHANNELS)} ta kanalga obuna bo‘ling:\n\n"
        f"{channels_list}\n\nKeyin «Tekshirish» tugmasini bosing!",
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    text = msg.text.strip()
    user_id = msg.from_user.id

    print(f"[MSG] {user_id}: {text[:50]}...")

    if text == "/cancel":
        context.user_data.clear()
        await msg.reply_text("Bekor qilindi")
        return

    mode = context.user_data.get("mode")

    # Subscription sozlash
    if mode == "subscription" and user_id == ADMIN_ID:
        global MANDATORY_CHANNELS
        t = text.lower().strip()

        if t in ["off", "yoq", "o'chir", "delete"]:
            MANDATORY_CHANNELS = []
            save_settings()
            await msg.reply_text("Majburiy obuna o‘chirildi")
            context.user_data.pop("mode", None)
            return

        if t == "clear":
            MANDATORY_CHANNELS = []
            save_settings()
            await msg.reply_text("Hammasi tozalandi")
            context.user_data.pop("mode", None)
            return

        words = text.split()
        cmd = words[0].lower() if words else ""

        if cmd == "add":
            added = []
            for ch in words[1:]:
                ch = ch if ch.startswith("@") else "@" + ch
                if ch in MANDATORY_CHANNELS:
                    continue
                if len(MANDATORY_CHANNELS) >= MAX_MANDATORY_CHANNELS:
                    await msg.reply_text(f"Maksimum {MAX_MANDATORY_CHANNELS} ta!")
                    break
                try:
                    await context.bot.get_chat(ch)
                    MANDATORY_CHANNELS.append(ch)
                    added.append(ch)
                except:
                    await msg.reply_text(f"{ch} — xato (bot admin emas yoki topilmadi)")
            if added:
                save_settings()
            await msg.reply_text(f"Qo‘shildi: {', '.join(added) or '-'}\n\n{', '.join(MANDATORY_CHANNELS) or 'bo‘sh'}")

        elif cmd in ["del", "delete", "remove"]:
            removed = []
            for ch in words[1:]:
                ch = ch if ch.startswith("@") else "@" + ch
                if ch in MANDATORY_CHANNELS:
                    MANDATORY_CHANNELS.remove(ch)
                    removed.append(ch)
            if removed:
                save_settings()
            await msg.reply_text(f"O‘chirildi: {', '.join(removed) or '-'}\n\n{', '.join(MANDATORY_CHANNELS) or 'bo‘sh'}")

        context.user_data.pop("mode", None)
        return

    # Broadcast
    if mode == "broadcast" and user_id == ADMIN_ID:
        users = load_users()
        success = failed = 0
        await msg.reply_text("Yuborilmoqda...")

        for uid_str in users:
            try:
                await msg.copy(chat_id=int(uid_str))
                success += 1
                await asyncio.sleep(0.35)
            except:
                failed += 1

        await msg.reply_text(f"Muvaffaqiyatli: {success}\nXato: {failed}\nJami: {len(users)}")
        context.user_data.clear()
        return

    users = load_users()
    movies = load_movies()
    user = get_user(users, user_id)

    # Kino qidirish
    if text in movies:
        if user["used"] >= max_limit(user):
            ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            await msg.reply_text(
                "Limit tugadi!\nDo‘stlaringizni taklif qiling (+5 limit)",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Do‘stlarga ulashish", url=f"https://t.me/share/url?url={quote(ref_link)}")
                ]])
            )
            return

        user["used"] += 1
        save_users(users)

        val = movies[text]
        caption = f"🎬 Qolgan: {user['used']}/{max_limit(user)}"

        try:
            if val.startswith("http"):
                if "t.me/c/" in val:
                    # private channel link
                    parts = val.split("/")[-2:]
                    chat_id = int("-100" + parts[0])
                    msg_id = int(parts[1])
                    await context.bot.copy_message(msg.chat_id, chat_id, msg_id)
                else:
                    await msg.reply_video(val, caption=caption)
            else:
                await msg.reply_text("Noto‘g‘ri formatdagi kino")
        except Exception as e:
            await msg.reply_text(f"Kino yuborishda xato: {str(e)[:80]}")
        return

    await msg.reply_text("Bunday kod topilmadi 😔")


# ================= MAIN =================
def main():
    if not TOKEN:
        print("TOKEN topilmadi! BOT_TOKEN muhit o'zgaruvchisini sozlang.")
        return

    print("Bot ishga tushmoqda...")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    app.run_polling(drop_pending_updates=True, timeout=30, read_timeout=30, write_timeout=30)


if __name__ == "__main__":
    main()
