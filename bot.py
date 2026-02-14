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
BOT_USERNAME = "UzbekFilmTV_bot"  # ← BU YERNI O‘Z BOT USERNAME’INGIZGA O‘ZGARTIRING!

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"

FREE_LIMIT = 5
REF_LIMIT = 5  # har bir referral uchun +5 limit

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

def is_admin(user_id):
    return user_id == ADMIN_ID

def get_user(users, user_id):
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "used": 0,
            "referrals": 0,
            "joined": datetime.now().isoformat(),
            "refed": None
        }
        save_json(USERS_FILE, users)
    return users[uid]

def max_limit(user):
    return FREE_LIMIT + user["referrals"] * REF_LIMIT

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    users = load_json(USERS_FILE, {})
    me = get_user(users, user.id)

    # Referral
    if args and args[0].isdigit():
        ref_id = args[0]
        if ref_id != str(user.id) and ref_id in users and me["refed"] is None:
            users[ref_id]["referrals"] += 1
            me["refed"] = ref_id
            try:
                await context.bot.send_message(
                    int(ref_id),
                    f"🎉 Yangi do‘st kirdi!\nReferral: {users[ref_id]['referrals']}"
                )
            except:
                pass
            save_json(USERS_FILE, users)

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
    if is_admin(user.id):
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="HTML")

# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_admin(q.from_user.id):
        return

    if q.data == "admin":
        kb = [
            [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add"),
             InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete")],
            [InlineKeyboardButton("📊 Statistika", callback_data="stats"),
             InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast")],
        ]
        await q.edit_message_text("🛠 Admin panel", reply_markup=InlineKeyboardMarkup(kb))
        return

    if q.data == "broadcast":
        context.user_data["mode"] = "broadcast"
        await q.message.reply_text(
            "📢 Endi yuborgan xabaringiz (matn, rasm, video, audio...) hammaga jo'natiladi.\n"
            "Bekor qilish uchun /cancel yozing."
        )
        return

    if q.data in ["add", "delete"]:
        context.user_data["mode"] = q.data
        if q.data == "add":
            await q.message.reply_text("Format:\n`kod|file_id yoki kanal link`")
        elif q.data == "delete":
            await q.message.reply_text("O‘chirish uchun kodni yuboring")
        return

    if q.data == "stats":
        users = load_json(USERS_FILE, {})
        movies = load_json(MOVIES_FILE, {})
        await q.message.reply_text(f"👥 Userlar: {len(users)}\n🎬 Kinolar: {len(movies)}")

# ================= TEXT HANDLER =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text.strip()
    user_id = msg.from_user.id

    users = load_json(USERS_FILE, {})
    movies = load_json(MOVIES_FILE, {})
    user = get_user(users, user_id)
    mode = context.user_data.get("mode")

    # Cancel
    if text == "/cancel":
        context.user_data.clear()
        await msg.reply_text("❌ Bekor qilindi")
        return

    # Admin userga limit qo‘shish
    if is_admin(user_id) and text.startswith("limit "):
        try:
            _, target_uid, extra = text.split()
            target_uid = str(target_uid)
            extra = int(extra)

            if target_uid in users:
                users[target_uid]["referrals"] += extra // REF_LIMIT
                save_json(USERS_FILE, users)
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

    # Broadcast
    if is_admin(user_id) and mode == "broadcast":
        success = 0
        for uid_str in users:
            try:
                await msg.forward(chat_id=int(uid_str))
                success += 1
            except:
                pass
        await msg.reply_text(f"✅ Yuborildi: {success}/{len(users)} userga")
        context.user_data.clear()
        return

    # Admin add/delete
    if is_admin(user_id):
        if mode == "add":
            if "|" not in text:
                await msg.reply_text("Format: kod|value")
                return
            code, val = [x.strip() for x in text.split("|", 1)]
            movies[code] = val
            save_json(MOVIES_FILE, movies)
            context.user_data.clear()
            await msg.reply_text("✅ Kino qo‘shildi")
            return

        if mode == "delete":
            if text in movies:
                del movies[text]
                save_json(MOVIES_FILE, movies)
                await msg.reply_text("🗑 O‘chirildi")
            else:
                await msg.reply_text("❌ Topilmadi")
            context.user_data.clear()
            return

    # User movie request
    if text in movies:
        if user["used"] >= max_limit(user):
            ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            share_text = (
                f"Eng zo‘r o‘zbek filmlari shu botda! 🔥\n"
                f"Bepul 5 ta kino + har bir do‘st uchun +5 ta limit!\n\n"
                f"{ref_link}"
            )
            share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={quote(share_text)}"

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
        save_json(USERS_FILE, users)

        btn = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "🔍 Botda qidirish / Yangi filmlar",
                url=f"https://t.me/{BOT_USERNAME}?start=qidiruv"
            )
        ]])

        cap = f"🎬 Kino tayyor 🍿\nQolgan: {user['used']}/{max_limit(user)}"

        val = movies[text]
        if val.startswith("https://t.me/c/"):
            p = val.replace("https://t.me/c/", "").split("/")
            await context.bot.copy_message(
                chat_id=msg.chat_id,
                from_chat_id=int("-100" + p[0]),
                message_id=int(p[1]),
                caption=cap,
                reply_markup=btn
            )
        else:
            await msg.reply_video(video=val, caption=cap, reply_markup=btn)
        return

    await msg.reply_text("❌ Bunday kod topilmadi")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_broadcast))
    app.add_handler(CallbackQueryHandler(admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi")

if __name__ == "__main__":
    main()
