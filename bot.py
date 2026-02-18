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
ADMIN_ID = 774440841
BOT_USERNAME = "UzbekFilmTv_bot"
CHANNEL_USERNAME = "@UzbekFilmTv_Kanal"  # bu sizning asl kanalingiz

# Yangi: majburiy obuna kanali (admin panel orqali o'zgartiriladi)
MANDATORY_CHANNEL = None  # None bo'lsa majburiy obuna yo'q
# MANDATORY_CHANNEL = "@sizningmajburiykanal"  # misol

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"
SETTINGS_FILE = "settings.json"  # yangi fayl - sozlamalarni saqlash uchun

FREE_LIMIT = 5
REF_LIMIT = 5

# ================= SETTINGS (majburiy kanalni saqlash) =================
def load_settings():
    global MANDATORY_CHANNEL
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                MANDATORY_CHANNEL = data.get("mandatory_channel")
        except:
            pass

def save_settings():
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"mandatory_channel": MANDATORY_CHANNEL}, f, ensure_ascii=False, indent=2)

load_settings()  # bot ishga tushganda yuklaymiz

# ================= Fayl bilan ishlash (qolganlari o'zgarmadi) =================
# load_users, save_users, load_movies, save_movies, get_user, max_limit – sizda bor, qisqartirdim

# ================= ADMIN KEYBOARD (yangi tugma qo'shildi) =================
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
        [
            InlineKeyboardButton("🔒 Majburiy obuna sozlamalari", callback_data="subscription"),
        ],
    ])


# ================= START (obuna tekshiruvi qo'shildi) =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if MANDATORY_CHANNEL and not await is_subscribed(user.id):
        await send_subscription_message(update.message)
        return

    # qolgan start logikasi (referral, matn yuborish)
    users = load_users()
    me = get_user(users, user.id)

    # referral kodi qismi (sizda bor)

    text = (
        f"<b>Assalomu alaykum, {user.first_name}!</b> 👋\n\n"
        f"🎬 <b>UzbekFilmTV</b> — eng sara o‘zbek filmlari shu yerdagi bot!\n\n"
        # ... qolgan matn ...
    )

    kb = []
    if user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="HTML")


# ================= Obuna tekshiruvi =================
async def is_subscribed(user_id: int) -> bool:
    if not MANDATORY_CHANNEL:
        return True
    try:
        member = await context.bot.get_chat_member(
            chat_id=MANDATORY_CHANNEL,
            user_id=user_id
        )
        return member.status in ["member", "administrator", "creator"]
    except TelegramError as e:
        print(f"Obuna tekshiruv xatosi: {e}")
        return False  # xavfsizlik uchun False qaytaramiz


async def send_subscription_message(message):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📣 Kanalga obuna bo‘lish", url=f"https://t.me/{MANDATORY_CHANNEL.lstrip('@')}")],
        [InlineKeyboardButton("✅ Obuna bo‘ldim, tekshirish", callback_data="check_sub")]
    ])
    await message.reply_text(
        "Botdan foydalanish uchun quyidagi kanalga obuna bo‘ling:\n\n"
        f"🔗 {MANDATORY_CHANNEL}\n\n"
        "Obuna bo‘lgandan keyin «Obuna bo‘ldim, tekshirish» tugmasini bosing!",
        reply_markup=kb,
        parse_mode="HTML"
    )


# ================= Callback query (tekshirish tugmasi) =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id

    if q.data == "check_sub":
        if await is_subscribed(user_id):
            await q.edit_message_text("✅ Obuna tasdiqlandi! Endi botdan foydalanishingiz mumkin.")
        else:
            await q.edit_message_text("❌ Hali obuna bo‘lmagansiz. Iltimos kanalga qo‘shiling.")
        return

    if user_id != ADMIN_ID:
        return

    data = q.data

    if data == "admin":
        await q.edit_message_text("🛠 Admin panel", reply_markup=admin_keyboard())
        return

    if data == "subscription":
        current = MANDATORY_CHANNEL or "Majburiy obuna yo‘q"
        text = f"Hozirgi majburiy kanal: {current}\n\n"
        text += "Yangi kanal username ni yuboring (masalan: @MyChannel)\n"
        text += "Yo‘q qilish uchun: off yoki yo‘q deb yozing"
        context.user_data["mode"] = "set_subscription"
        await q.message.reply_text(text)
        return

    # qolgan admin funksiyalari (stats, list_movies, broadcast, add/delete) – o'zgarmaydi


# ================= Message handler (yangi mode qo'shildi) =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    text = (msg.text or "").strip()

    if text == "/cancel":
        context.user_data.clear()
        await msg.reply_text("❌ Bekor qilindi")
        return

    mode = context.user_data.get("mode")

    if mode == "set_subscription" and user_id == ADMIN_ID:
        if text.lower() in ["off", "yo‘q", "yoq", "delete"]:
            global MANDATORY_CHANNEL
            MANDATORY_CHANNEL = None
            save_settings()
            await msg.reply_text("✅ Majburiy obuna o‘chirildi")
        else:
            if text.startswith("@"):
                channel = text
            else:
                channel = "@" + text.lstrip("@")
            try:
                # kanal mavjudligini tekshirish uchun get_chat_member sinab ko'ramiz
                await context.bot.get_chat_member(channel, ADMIN_ID)
                global MANDATORY_CHANNEL
                MANDATORY_CHANNEL = channel
                save_settings()
                await msg.reply_text(f"✅ Majburiy kanal o‘rnatildi: {channel}")
            except TelegramError:
                await msg.reply_text("❌ Bunday kanal topilmadi yoki bot admin emas")
        context.user_data.pop("mode", None)
        return

    # qolgan butun logika (kino kodlari, limit qo'shish, broadcast, add/delete) – o'zgarmaydi
    # ... sizning asl kodingizni shu yerga joylashtiring ...

    # misol uchun oddiy kod tekshiruvi oldidan obuna tekshiruvi qo'shish
    if text in movies:
        if MANDATORY_CHANNEL and not await is_subscribed(user_id):
            await send_subscription_message(msg)
            return
        # keyin kino yuborish logikasi davom etadi


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", lambda u, c: cancel_broadcast(u, c)))
    app.add_handler(CallbackQueryHandler(admin_panel))

    # Alohida handlerlar – sizning versiyangiz uchun xavfsiz
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(MessageHandler(filters.PHOTO, message_handler))
    app.add_handler(MessageHandler(filters.VIDEO, message_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, message_handler))
    app.add_handler(MessageHandler(filters.AUDIO, message_handler))
    app.add_handler(MessageHandler(filters.VOICE, message_handler))
    app.add_handler(MessageHandler(filters.VIDEO_NOTE, message_handler))

    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi")


if __name__ == "__main__":
    main()
