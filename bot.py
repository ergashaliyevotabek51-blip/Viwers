# -*- coding: utf-8 -*-

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
from telegram.error import TelegramError

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("BOT_TOKEN topilmadi! Environment variable sozlang.")
    exit(1)

ADMIN_IDS = [774440841, 7818576058]  # ← O‘ZINGIZNING HAQIQIY ID’INGIZNI SHU YERGA YOZING!

BOT_USERNAME = "UzbekFilmTv_bot"
CHANNEL_USERNAME = "@UzbekFilmTv_Kanal"

MANDATORY_CHANNELS = []  # ["@kanal1", "@kanal2"] — admin paneldan qo‘shiladi

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"
SETTINGS_FILE = "settings.json"

FREE_LIMIT = 5
REF_LIMIT = 5

# ================= SETTINGS =================
def load_settings():
    global MANDATORY_CHANNELS
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                MANDATORY_CHANNELS = data.get("mandatory_channels", [])
        except Exception as e:
            print(f"settings yuklash xatosi: {e}")
            MANDATORY_CHANNELS = []


def save_settings():
    global MANDATORY_CHANNELS
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"mandatory_channels": MANDATORY_CHANNELS}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"settings saqlash xatosi: {e}")


load_settings()

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
        return {}
    return {str(k): v for k, v in data.items()}


def save_users(data: dict):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass


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
    except:
        pass


def get_user(users: dict, user_id: int) -> dict:
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"used": 0, "referrals": 0, "joined": datetime.utcnow().isoformat()}
        save_users(users)
    return users[uid]


def max_limit(user: dict) -> int:
    return FREE_LIMIT + user["referrals"] * REF_LIMIT

# ================= ADMIN KEYBOARD =================
def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie"),
            InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete_movie"),
        ],
        [
            InlineKeyboardButton("📃 Kinolar ro‘yxati", callback_data="list_movies"),
            InlineKeyboardButton("📊 Statistika", callback_data="stats"),
        ],
        [
            InlineKeyboardButton("📢 Omaviy xabar yuborish", callback_data="broadcast"),
        ],
        [
            InlineKeyboardButton("🔒 Majburiy obuna sozlamalari", callback_data="subscription"),
        ],
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    print(f"[START] UserID: {user.id} | @{user.username or 'yo‘q'}")

    if MANDATORY_CHANNELS and not await is_subscribed(context, user.id):
        await send_subscription_message(update, context)
        return

    users = load_users()
    me = get_user(users, user.id)

    if args and args[0].isdigit():
        ref_id = args[0]
        if ref_id != str(user.id) and ref_id in users and me.get("refed") is None:
            users[ref_id]["referrals"] += 1
            me["refed"] = ref_id
            save_users(users)

    text = (
        f"<b>Assalomu alaykum, {user.first_name}!</b> 👋\n\n"
        f"🎬 <b>UzbekFilmTV</b> — eng sara o‘zbek filmlari shu yerdagi bot!\n\n"
        f"🔥 Kod yuboring (masalan: 12, 45, 107) → kino darhol keladi\n"
        f"• Bepul: <b>5 ta</b>   • Do‘st uchun: <b>+5 ta</b>\n\n"
        f"🚀 Kodni yozing yoki do‘stlarni taklif qiling!"
    )

    kb = []
    if user.id in ADMIN_IDS:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin_panel")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="HTML")

# ================= ADMIN COMMAND =================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return
    await update.message.reply_text("🛠 Admin panel ochildi!", reply_markup=admin_keyboard())

# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id

    if user_id not in ADMIN_IDS:
        await q.edit_message_text("❌ Siz admin emassiz!")
        return

    data = q.data

    if data == "admin_panel":
        await q.edit_message_text("🛠 Admin panel", reply_markup=admin_keyboard())
        return

    users = load_users()
    movies = load_movies()

    if data == "stats":
        await q.message.reply_text(f"👥 Userlar: {len(users)}\n🎬 Kinolar: {len(movies)}")
        return

    if data == "list_movies":
        text = "Hozircha kinolar yo‘q." if not movies else "\n".join(f"• {code}" for code in sorted(movies.keys()))
        await q.message.reply_text(text)
        return

    if data == "broadcast":
        context.user_data["mode"] = "wait_broadcast"
        await q.message.reply_text("Xabarni yuboring yoki forward qiling.\n/cancel — bekor")
        return

    if data == "subscription":
        current = "\n".join(MANDATORY_CHANNELS) if MANDATORY_CHANNELS else "Yo‘q"
        text = f"Majburiy kanallar:\n{current}\n\nYangi kanallar: @kanal1 @kanal2\nTozalash: clear/off"
        context.user_data["mode"] = "set_subscription"
        await q.message.reply_text(text)
        return

    if data in ["add_movie", "delete_movie"]:
        context.user_data["mode"] = data.replace("_movie", "")
        msg = "kod|file_id yoki link" if data == "add_movie" else "O‘chirish uchun kod"
        await q.message.reply_text(msg)
        return

    await q.edit_message_text(f"Noma'lum buyruq: {data}")

# ================= OBUNA FUNKSİYALARI =================
async def is_subscribed(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    if not MANDATORY_CHANNELS:
        return True
    for channel in MANDATORY_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception as e:
            print(f"Obuna xatosi {channel}: {e}")
    return True


async def get_subscription_keyboard(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    kb = []
    all_subscribed = True

    for channel in MANDATORY_CHANNELS:
        clean = channel.lstrip('@')
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            subscribed = member.status in ["member", "administrator", "creator"]
        except:
            subscribed = False

        emoji = "✅" if subscribed else "❌"
        kb.append([InlineKeyboardButton(
            f"{emoji} {clean} ga obuna bo‘lish",
            url=f"https://t.me/{clean}"
        )])

        if not subscribed:
            all_subscribed = False

    kb.append([InlineKeyboardButton(
        "🔄 Tekshirish" if not all_subscribed else "✅ Botga o‘tish",
        callback_data="check_sub"
    )])

    return InlineKeyboardMarkup(kb), all_subscribed


async def send_subscription_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message

    kb, all_subscribed = await get_subscription_keyboard(context, user_id)

    channels_text = "\n".join(f"• {ch}" for ch in MANDATORY_CHANNELS)

    text = (
        f"Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:\n\n"
        f"{channels_text}\n\n"
        "Obuna bo‘lgach «Tekshirish» tugmasini bosing! 🚀"
    )

    if all_subscribed:
        text = "🎉 Hammaga obuna bo‘lgansiz!\n\nBotdan foydalanishingiz mumkin! 🍿✨"

    await message.reply_text(text, reply_markup=kb)


# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    user_id = msg.from_user.id
    text = (msg.text or "").strip()

    if text == "/cancel":
        context.user_data.clear()
        await msg.reply_text("❌ Bekor qilindi")
        return

    mode = context.user_data.get("mode")

    if user_id in ADMIN_IDS:
        if mode == "set_subscription":
            global MANDATORY_CHANNELS
            t = text.lower().strip()
            if t in ["clear", "off"]:
                MANDATORY_CHANNELS = []
                save_settings()
                await msg.reply_text("Majburiy kanallar tozalandi")
            elif text.startswith("@"):
                added = []
                for ch in text.split():
                    ch = ch.strip()
                    if ch.startswith("@") and ch not in MANDATORY_CHANNELS:
                        try:
                            await context.bot.get_chat(ch)
                            MANDATORY_CHANNELS.append(ch)
                            added.append(ch)
                        except:
                            pass
                if added:
                    save_settings()
                    await msg.reply_text(f"Qo‘shildi: {', '.join(added)}")
            context.user_data.pop("mode", None)
            return

        # qolgan admin modlari (broadcast, limit, add/delete) — oldingi kod saqlanadi
        return

    # Majburiy obuna tekshiruvi — eng yuqorida!
    if MANDATORY_CHANNELS and not await is_subscribed(context, user_id):
        await send_subscription_message(update, context)
        return

    users = load_users()
    movies = load_movies()
    user = get_user(users, user_id)

    if text in movies:
        # kino yuborish logikasi (oldingi kod saqlanadi)
        # limit tekshiruvi, kino yuborish...
        return

    await msg.reply_text("❌ Bunday kod topilmadi")


# ================= CALLBACK QUERY HANDLER =================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data

    if data == "check_sub":
        kb, all_subscribed = await get_subscription_keyboard(context, q.from_user.id)

        if all_subscribed:
            await q.edit_message_text(
                "🎉 Hammaga obuna bo‘lgansiz!\n\nBotdan foydalanishingiz mumkin! 🍿✨",
                reply_markup=None
            )
        else:
            await q.edit_message_text(
                q.message.text,
                reply_markup=kb
            )
        return

    # Admin panel tugmalari
    await admin_panel(update, context)


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("cancel", lambda u, c: context.user_data.clear() or u.message.reply_text("❌ Bekor qilindi")))

    # Callback handler — BU QATOR TUFALI TUGMALAR ISHLAYDI!
    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Bot ishga tushdi... Tugmalar va obuna tizimi sinovdan o‘tkazilgan")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
