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
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 774440841
BOT_USERNAME = "BOT_USERNAME"  # @ belgisiz yoz

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"

FREE_LIMIT = 5
REF_LIMIT = 5

# ================= FILE UTILS =================
def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(user_id):
    return user_id == ADMIN_ID

def get_user(users, user_id):
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "used": 0,
            "referrals": 0,
            "joined": datetime.now().isoformat()
        }
    return users[uid]

def max_limit(user):
    return FREE_LIMIT + user["referrals"] * REF_LIMIT

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    users = load_json(USERS_FILE, {})
    me = get_user(users, user.id)

    # ===== REFERRAL =====
    if args and args[0].isdigit():
        ref_id = args[0]
        if ref_id != str(user.id) and ref_id in users:
            if "refed" not in me:
                users[ref_id]["referrals"] += 1
                me["refed"] = ref_id
                try:
                    await context.bot.send_message(
                        chat_id=int(ref_id),
                        text=f"🎉 Yangi do‘st kirdi!\nReferral: {users[ref_id]['referrals']}"
                    )
                except:
                    pass

    save_json(USERS_FILE, users)

    text = (
        f"🎬 Assalomu alaykum, {user.first_name}!\n\n"
        f"📩 Kino olish uchun kod yuboring.\n\n"
        f"🎁 Limit: {me['used']}/{max_limit(me)}"
    )

    kb = []
    if is_admin(user.id):
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None)

# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id):
        return

    kb = [
        [
            InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add"),
            InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete"),
        ],
        [
            InlineKeyboardButton("📊 Statistika", callback_data="stats"),
            InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast"),
        ],
    ]

    await q.edit_message_text("🛠 Admin panel", reply_markup=InlineKeyboardMarkup(kb))

# ================= ADMIN ACTIONS =================
async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id):
        return

    if q.data in ["add", "delete", "broadcast"]:
        context.user_data["mode"] = q.data

    if q.data == "add":
        await q.message.reply_text(
            "Format:\n`kod|file_id yoki kanal link`",
            parse_mode="Markdown"
        )

    elif q.data == "delete":
        await q.message.reply_text("O‘chirish uchun kodni yuboring")

    elif q.data == "stats":
        users = load_json(USERS_FILE, {})
        movies = load_json(MOVIES_FILE, {})
        await q.message.reply_text(
            f"👥 Userlar: {len(users)}\n🎬 Kinolar: {len(movies)}"
        )

    elif q.data == "broadcast":
        await q.message.reply_text(
            "📢 Endi yuborgan xabaringiz hammaga jo‘natiladi\nBekor qilish: /cancel"
        )

# ================= TEXT HANDLER =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    users = load_json(USERS_FILE, {})
    movies = load_json(MOVIES_FILE, {})
    user = get_user(users, user_id)
    mode = context.user_data.get("mode")

    # ===== CANCEL =====
    if text == "/cancel":
        context.user_data.clear()
        await update.message.reply_text("❌ Bekor qilindi")
        return

    # ===== BROADCAST =====
    if is_admin(user_id) and mode == "broadcast":
        for uid in users:
            try:
                await update.message.forward(chat_id=int(uid))
            except:
                pass
        context.user_data.clear()
        await update.message.reply_text("✅ Omaviy xabar yuborildi")
        return

    # ===== ADMIN ADD =====
    if is_admin(user_id) and mode == "add":
        if "|" not in text:
            await update.message.reply_text("❌ Format xato")
            return
        code, val = text.split("|", 1)
        movies[code.strip()] = val.strip()
        save_json(MOVIES_FILE, movies)
        context.user_data.clear()
        await update.message.reply_text("✅ Kino qo‘shildi")
        return

    # ===== ADMIN DELETE =====
    if is_admin(user_id) and mode == "delete":
        if text in movies:
            del movies[text]
            save_json(MOVIES_FILE, movies)
            await update.message.reply_text("🗑 O‘chirildi")
        else:
            await update.message.reply_text("❌ Topilmadi")
        context.user_data.clear()
        return

    # ===== SEARCH START =====
    if text == "qidiruv":
        await update.message.reply_text(
            f"🔍 Kodni kiriting\n"
            f"🎁 Limit: {user['used']}/{max_limit(user)}\n"
            f"👥 Referral: {user['referrals']}\n\n"
            f"🔗 Havola:\nhttps://t.me/{BOT_USERNAME}?start={user_id}"
        )
        return

    # ===== USER MOVIE =====
    if text in movies:
        if user["used"] >= max_limit(user):
            await update.message.reply_text(
                "❌ Limit tugadi!\n\n"
                f"🔗 Referral havola:\nhttps://t.me/{BOT_USERNAME}?start={user_id}"
            )
            return

        user["used"] += 1
        save_json(USERS_FILE, users)

        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔍 Botda qidirish / Yangi filmlar",
                url=f"https://t.me/{BOT_USERNAME}?start=qidiruv"
            )]
        )

        cap = f"🎬 Kino tayyor 🍿\nQolgan: {user['used']}/{max_limit(user)}"

        val = movies[text]
        if val.startswith("https://t.me/c/"):
            p = val.replace("https://t.me/c/", "").split("/")
            await context.bot.copy_message(
                chat_id=update.message.chat_id,
                from_chat_id=int("-100" + p[0]),
                message_id=int(p[1]),
                caption=cap,
                reply_markup=btn
            )
        else:
            await update.message.reply_video(
                video=val,
                caption=cap,
                reply_markup=btn
            )
        return

    await update.message.reply_text("❌ Bunday kod topilmadi")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin$"))
    app.add_handler(CallbackQueryHandler(admin_actions))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, text_handler))

    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
