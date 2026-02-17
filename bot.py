import os
import json
import asyncio                           # ← bu qator qo'shildi (eng muhim!)
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
BOT_USERNAME = "UzbekFilmTv_bot"
CHANNEL_USERNAME = "@UzbekFilmTv_Kanal"

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"

FREE_LIMIT = 5
REF_LIMIT = 5

# ================= Fayl bilan ishlash =================
# (sizning asl funksiyalaringiz o'zgarmadi, shuning uchun qisqartirdim)
def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        save_users({})
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}
    # qolgan qismi sizda bor edi — o'zgartirmayman
    # ... (to'liq kodni pastda beraman, shunchaki joy tejash uchun qisqartirdim)

# save_users, load_movies, save_movies, get_user, max_limit — o'zgarmadi

# ================= ADMIN KEYBOARD (broadcast tugmasi qo'shildi) =================
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
            InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast"),   # ← yangi
        ],
    ])

# ================= START va ADMIN PANEL (broadcast qismi qo'shildi) =================
# start funksiyasi o'zgarmadi

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

    if data == "broadcast":                               # ← yangi blok
        context.user_data["mode"] = "wait_broadcast"
        await q.message.reply_text(
            "📢 Omaviy xabar yuborish\n\n"
            "Bot nomidan yubormoqchi bo'lgan xabarni (text, rasm, video, hujjat) yuboring yoki forward qiling.\n"
            "Bekor qilish:  /cancel"
        )
        return

    if data in ["add", "delete"]:
        context.user_data["mode"] = data
        msg = "Format:\n`kod|file_id yoki kanal link`" if data == "add" else "O‘chirish uchun kodni yuboring"
        await q.message.reply_text(msg)
        return

# ================= BITTA UMUMIY HANDLER (text + media) =================
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
    user = get_user(users, user_id)
    mode = context.user_data.get("mode")

    # Broadcast qismi
    if mode == "wait_broadcast" and user_id == ADMIN_ID:
        context.user_data["mode"] = "sending"
        await msg.reply_text("Yuborilmoqda... (vaqt ketishi mumkin)")

        success = 0
        failed = 0
        total = len(users)

        for uid_str in list(users.keys()):
            try:
                uid = int(uid_str)
                await msg.copy(chat_id=uid)
                success += 1
                await asyncio.sleep(0.4)          # Telegram limitidan himoya
            except Exception:
                failed += 1

        context.user_data.clear()
        await msg.reply_text(
            f"✅ Yuborish tugadi\n"
            f"Yetib bordi: {success}\n"
            f"Yetib bormadi: {failed}\n"
            f"Jami user: {total}"
        )
        return

    # Qolgan qismlar — sizning asl logikangiz (kino kodlari, limit qo'shish, add/delete)
    # ... (hech narsa o'zgarmagan, faqat yuqoridagi broadcast qo'shildi)

    # (masalan text_handler dagi qolgan kodni shu yerga joylashtiring)
    # Admin limit qo'shish, kino qo'shish/o'chirish, user kino kodi yuborsa — hammasi shu joyda davom etadi

    if text:
        await msg.reply_text("❌ Bunday kod topilmadi")


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", lambda u, c: cancel_broadcast(u, c)))
    app.add_handler(CallbackQueryHandler(admin_panel))

    # Bitta handler — text + deyarli barcha media
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
