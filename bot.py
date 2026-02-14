import os
import json
from datetime import datetime
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
TOKEN = os.getenv("BOT_TOKEN")              # Railway envdan olinadi
ADMIN_ID = 774440841                        # o'zingizning ID

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"

FREE_LIMIT = 5
REFERRAL_NEEDED = 3
PREMIUM_LIMIT = 20

BOT_USERNAME = "UzbekFilmTV_bot"            # o'zingiznikiga o'zgartiring

# ================= FILE UTILS =================
def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ================= USER DATA =================
def get_user_data(users: dict, user_id: int):
    uid_str = str(user_id)
    if uid_str not in users:
        users[uid_str] = {
            "used": 0,
            "referrals": 0,
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        save_json(USERS_FILE, users)
    return users[uid_str]

def get_current_limit(user_data: dict) -> int:
    if user_data.get("referrals", 0) >= REFERRAL_NEEDED:
        return PREMIUM_LIMIT
    return FREE_LIMIT

def get_remaining(user_data: dict) -> int:
    lim = get_current_limit(user_data)
    return max(0, lim - user_data.get("used", 0))

# ================= KEYBOARDS =================
def get_main_kb(is_adm: bool):
    kb = []
    if is_adm:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])
    return InlineKeyboardMarkup(kb) if kb else None

def get_search_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton("🔍 Botda qidirish / Yangi filmlar", url=f"https://t.me/{BOT_USERNAME}?start=qidiruv")
    ]])

def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add")],
        [InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back")],
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    users = load_json(USERS_FILE, {})
    user_data = get_user_data(users, uid)

    args = context.args
    if args:
        param = args[0]

        if param == "qidiruv":
            remaining = get_remaining(user_data)
            ref_cnt = user_data.get("referrals", 0)
            lim = get_current_limit(user_data)

            if remaining > 0:
                text = f"Kodni tering! 🎬\n\nQolgan: {remaining}/{lim}\nDo‘stlar: {ref_cnt}/{REFERRAL_NEEDED}"
            else:
                needed = REFERRAL_NEEDED - ref_cnt
                ref_link = f"https://t.me/{BOT_USERNAME}?start={uid}"
                text = (
                    f"🔒 Limit tugadi!\n\n"
                    f"Qolgan: 0/{lim}\nDo‘stlar: {ref_cnt}/{REFERRAL_NEEDED}\n\n"
                    f"Yana {needed} ta do‘st taklif qiling!\n"
                    f"Har biri kirganda limit 20 tagacha ochiladi.\n\n"
                    f"🔗 Havola:\n<code>{ref_link}</code>"
                )
            await update.message.reply_text(text, reply_markup=get_search_kb(), disable_web_page_preview=True)
            return

        # Referral
        try:
            ref_id = int(param)
            if ref_id != uid and str(ref_id) in users:
                users[str(ref_id)]["referrals"] = users[str(ref_id)].get("referrals", 0) + 1
                save_json(USERS_FILE, users)
                await context.bot.send_message(ref_id, f"🎉 Yangi do‘st! Referral: {users[str(ref_id)]['referrals']}/{REFERRAL_NEEDED}")
        except:
            pass

    text = f"Assalomu alaykum, {user.first_name}!\n\nKino uchun kod yuboring (masalan: 12)"
    await update.message.reply_text(text, reply_markup=get_main_kb(is_admin(uid)))

# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    data = query.data

    if data == "admin":
        await query.edit_message_text("🛠 Admin panel", reply_markup=get_admin_kb())
        return

    if data == "back":
        await query.edit_message_text("Bosh sahifa", reply_markup=get_main_kb(True))
        return

    if data == "stats":
        users = load_json(USERS_FILE, {})
        movies = load_json(MOVIES_FILE, {})
        text = f"👥 Userlar: {len(users)}\n🎬 Kinolar: {len(movies)}"
        await query.edit_message_text(text, reply_markup=get_admin_kb())
        return

    if data == "broadcast":
        context.user_data["broadcast_mode"] = True
        await query.edit_message_text(
            "📢 Omaviy xabar rejimi yoqildi!\n\n"
            "Endi yuborgan xabaringiz (matn, rasm, video, audio, hujjat, guruhlashgan media...) hammaga jo'natiladi.\n\n"
            "Bekor qilish uchun /cancel deb yozing."
        )
        return

# ================= OMMAVIY XABAR =================
async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not context.user_data.get("broadcast_mode"):
        return

    if not is_admin(msg.from_user.id):
        context.user_data.pop("broadcast_mode", None)
        return

    users = load_json(USERS_FILE, {})
    success = 0
    total = len(users)

    for uid_str in users:
        try:
            uid = int(uid_str)
            await msg.forward(chat_id=uid)
            success += 1
        except:
            pass

    await msg.reply_text(f"✅ Yuborildi: {success}/{total} userga")
    context.user_data.pop("broadcast_mode", None)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("broadcast_mode"):
        context.user_data.pop("broadcast_mode", None)
        await update.message.reply_text("Omaviy xabar rejimi o‘chirildi.")
    else:
        await update.message.reply_text("Hech qanday rejim yoqilmagan.")

# ================= TEXT HANDLER =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text.strip()
    uid = msg.from_user.id
    users = load_json(USERS_FILE, {})
    user_data = get_user_data(users, uid)
    mode = context.user_data.get("mode")

    # Admin rejimlari
    if is_admin(uid):
        if mode == "add":
            if "|" not in text:
                await msg.reply_text("Format: kod|value")
                return
            code, value = [x.strip() for x in text.split("|", 1)]
            movies = load_json(MOVIES_FILE, {})
            movies[code] = value
            save_json(MOVIES_FILE, movies)
            context.user_data.pop("mode", None)
            await msg.reply_text(f"✅ {code} qo‘shildi!")
            return

        if mode == "delete":
            movies = load_json(MOVIES_FILE, {})
            if text in movies:
                del movies[text]
                save_json(MOVIES_FILE, movies)
                await msg.reply_text(f"🗑 {text} o‘chirildi")
            else:
                await msg.reply_text("Topilmadi")
            context.user_data.pop("mode", None)
            return

    # Kino kodi
    movies = load_json(MOVIES_FILE, {})
    if text in movies:
        remaining = get_remaining(user_data)
        lim = get_current_limit(user_data)

        if remaining <= 0:
            needed = REFERRAL_NEEDED - user_data.get("referrals", 0)
            ref_link = f"https://t.me/{BOT_USERNAME}?start={uid}"
            text_msg = (
                f"🔒 Limit tugadi!\n\n"
                f"Qolgan: 0/{lim}\nDo‘stlar: {user_data.get('referrals', 0)}/{REFERRAL_NEEDED}\n\n"
                f"Yana {needed} ta do‘st taklif qiling!\nHar biri kirganda limit 20 tagacha ochiladi.\n\n"
                f"🔗 Havola:\n<code>{ref_link}</code>"
            )
            await msg.reply_text(text_msg, reply_markup=get_search_kb(), disable_web_page_preview=True)
            return

        value = movies[text]
        kb = get_search_kb()

        try:
            if value.startswith("https://t.me/c/"):
                parts = value.replace("https://t.me/c/", "").split("/")
                ch_id = int("-100" + parts[0])
                m_id = int(parts[1].split("?")[0])
                await context.bot.copy_message(
                    chat_id=msg.chat_id,
                    from_chat_id=ch_id,
                    message_id=m_id,
                    caption=f"🎬 Kino tayyor! Qolgan: {remaining-1}/{lim}",
                    reply_markup=kb
                )
            else:
                await msg.reply_video(
                    video=value,
                    caption=f"🎬 Kino tayyor! Qolgan: {remaining-1}/{lim}",
                    reply_markup=kb
                )
            user_data["used"] += 1
            save_json(USERS_FILE, users)
        except Exception as e:
            await msg.reply_text(f"Xato: {str(e)}")
        return

    await msg.reply_text("❌ Bunday kod topilmadi.")

# ================= ADMIN ACTIONS =================
async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    if query.data == "add":
        context.user_data["mode"] = "add"
        await query.message.reply_text("Kino qo‘shish:\n`kod|file_id yoki https://t.me/c/...`\nMasalan: `45|BAACAgI...` yoki `45|https://t.me/c/123/456`")
        return

    if query.data == "delete":
        context.user_data["mode"] = "delete"
        await query.message.reply_text("O‘chirish uchun kodni yuboring (masalan: 45)")
        return

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(admin_panel))
    app.add_handler(CallbackQueryHandler(admin_actions, pattern="^(add|delete)$"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_handler))  # broadcast rejimi
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))     # kino va admin mode

    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
