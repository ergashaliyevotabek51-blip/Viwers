import os
import json
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = "UzbekFilmTV_bot"  # ← o'zingiznikiga o'zgartiring

USERS_FILE    = "users.json"
MOVIES_FILE   = "movies.json"
SETTINGS_FILE = "settings.json"

FREE_LIMIT = 5
REF_LIMIT  = 5

ADMINS = [774440841, 7818576058]  # ← o'zingizning ID

# ==================== YORDAMCHI FUNKSİYALAR ====================
def load_json(file, default):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_users(): return load_json(USERS_FILE, {})
def save_users(data): save_json(USERS_FILE, data)

def load_movies(): return load_json(MOVIES_FILE, {})
def save_movies(data): save_json(MOVIES_FILE, data)

def load_settings(): return load_json(SETTINGS_FILE, {"channels": []})
def save_settings(data): save_json(SETTINGS_FILE, data)

def is_admin(uid): return uid in ADMINS

def get_user(users, uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "used": 0,
            "limit": FREE_LIMIT,
            "referrals": 0,
            "joined": datetime.utcnow().isoformat()
        }
    return users[uid]

def max_limit(user):
    return user["limit"] + user["referrals"] * REF_LIMIT

# ==================== MAJBURIY OBUNA ====================
async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    settings = load_settings()
    channels = settings.get("channels", [])
    if not channels: return True
    for ch in channels:
        try:
            chat = ch if ch.startswith("@") else f"@{ch.lstrip('@')}"
            member = await context.bot.get_chat_member(chat, user_id)
            if member.status in ["left", "kicked"]: return False
        except:
            return False
    return True

def subscription_keyboard():
    settings = load_settings()
    kb = []
    for ch in settings.get("channels", []):
        clean = ch.lstrip('@')
        kb.append([InlineKeyboardButton(f"🔔 @{clean}", url=f"https://t.me/{clean}")])
    kb.append([InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(kb)

async def send_subscription_message(target, context):
    kb = subscription_keyboard()
    text = "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:"
    if hasattr(target, "reply_text"):
        await target.reply_text(text, reply_markup=kb)
    else:
        await target.edit_message_text(text, reply_markup=kb)

# ==================== ASOSIY MENYU ====================
def main_menu_kb(is_adm=False):
    kb = [
        [InlineKeyboardButton("🎟 Mening limitim", callback_data="my_limit")],
        [InlineKeyboardButton("🎬 Random film",    callback_data="random")],
        [InlineKeyboardButton("🔥 Trend filmlar",   callback_data="trend")],
        [InlineKeyboardButton("🎥 Kino katalog",    callback_data="catalog")],
        [InlineKeyboardButton("👥 Do‘st taklif qilish", callback_data="invite")]
    ]
    if is_adm:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(kb)

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name or "Do‘st"

    users = load_users()
    get_user(users, uid)
    save_users(users)

    if not await check_subscription(context, uid):
        await send_subscription_message(update.message, context)
        return

    text = f"Salom, {name}! 👋\n\nKod yozing yoki quyidagi tugmalardan tanlang ↓"
    await update.message.reply_text(text, reply_markup=main_menu_kb(is_admin(uid)))

# ==================== CALLBACK HANDLER ====================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid = q.from_user.id
    users = load_users()
    movies = load_movies()
    u = get_user(users, uid)

    if data == "check_sub":
        if await check_subscription(context, uid):
            await q.edit_message_text("✅ Obuna tasdiqlandi!")
        else:
            await send_subscription_message(q.message, context)
        return

    if not await check_subscription(context, uid):
        await send_subscription_message(q.message, context)
        return

    if data == "my_limit":
        lim = max_limit(u)
        await q.message.reply_text(f"Limit: {u['used']}/{lim}")
        return

    if data == "random":
        if not movies:
            await q.message.reply_text("Hozircha film yo‘q")
            return
        code = random.choice(list(movies.keys()))
        m = movies[code]
        await context.bot.forward_message(
            q.message.chat_id,
            from_chat_id=m["from_chat_id"],
            message_id=m["message_id"]
        )
        return

    if data == "trend":
        top = sorted(movies.items(), key=lambda x: x[1].get("views", 0), reverse=True)[:10]
        if not top:
            await q.message.reply_text("Hali trend yo‘q")
            return
        txt = "🔥 Trend:\n\n" + "\n".join(f"{i}. {m['name']} — {m.get('views',0)} ta" for i,(c,m) in enumerate(top,1))
        await q.message.reply_text(txt)
        return

    if data == "catalog":
        if not movies:
            await q.message.reply_text("Katalog bo‘sh")
            return
        kb = []
        for code, m in list(movies.items())[:15]:
            kb.append([InlineKeyboardButton(m["name"], callback_data=f"film_{code}")])
        kb.append([InlineKeyboardButton("🔙 Menyuga", callback_data="back_main")])
        await q.edit_message_text("Tanlang:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("film_"):
        code = data[5:]
        if code in movies:
            m = movies[code]
            movies[code]["views"] = m.get("views", 0) + 1
            u["used"] += 1
            save_movies(movies)
            save_users(users)
            await context.bot.forward_message(
                q.message.chat_id,
                from_chat_id=m["from_chat_id"],
                message_id=m["message_id"]
            )
        return

    if data == "invite":
        link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
        await q.message.reply_text(
            f"Do‘stlaringizni taklif qiling!\n\nHavola: {link}\n\nHar bir do‘st uchun +{REF_LIMIT} limit"
        )
        return

    if data == "back_main":
        await q.edit_message_text("Asosiy menyu", reply_markup=main_menu_kb(is_admin(uid)))
        return

    # ──────── ADMIN PANEL ────────
    if not is_admin(uid): return

    if data == "admin_panel":
        kb = [
            [InlineKeyboardButton("➕ Kino qo‘shish",     callback_data="add_film")],
            [InlineKeyboardButton("➖ Kino o‘chirish",    callback_data="del_film")],
            [InlineKeyboardButton("📊 Statistika",        callback_data="stats")],
            [InlineKeyboardButton("🔥 Top filmlar",       callback_data="top")],
            [InlineKeyboardButton("📢 Broadcast",         callback_data="broadcast")],
            [InlineKeyboardButton("🔒 Majburiy obuna",    callback_data="force_sub")],
            [InlineKeyboardButton("💠 Limit qo‘shish",    callback_data="add_limit")]
        ]
        await q.edit_message_text("Admin panel", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data == "stats":
        await q.message.reply_text(f"Users: {len(users)}\nFilmlar: {len(movies)}")
        return

    if data == "top":
        top = sorted(movies.items(), key=lambda x: x[1].get("views", 0), reverse=True)[:10]
        txt = "Top:\n\n" + "\n".join(f"{i}. {m['name']} — {m.get('views',0)}" for i,(c,m) in enumerate(top,1))
        await q.message.reply_text(txt or "Hali yo‘q")
        return

    # qolgan admin rejimlari (add_film, del_film, broadcast, add_limit, force_sub) — context.user_data bilan
    simple_modes = {
        "add_film":   "add_movie",
        "del_film":   "delete_movie",
        "broadcast":  "broadcast",
        "add_limit":  "limit_add",
        "force_sub":  "add_channel"
    }
    if data in simple_modes:
        context.user_data["mode"] = simple_modes[data]
        texts = {
            "add_movie":     "Film/video forward qiling",
            "delete_movie":  "O‘chiriladigan kodni yuboring",
            "broadcast":     "Xabarni yuboring (hammaga boradi)",
            "limit_add":     "user_id limit (mas: 123456 10)",
            "add_channel":   "Kanal @username yoki off"
        }
        await q.message.reply_text(texts[simple_modes[data]])
        return

# ==================== MESSAGE HANDLER ====================
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.text: return

    text = msg.text.strip()
    mode = context.user_data.get("mode")

    users = load_users()
    movies = load_movies()

    # Admin rejimlari (qo‘shish, o‘chirish va boshqalar) — oldingi versiyalardagi kabi
    if mode == "add_movie":
        if msg.video or msg.document or msg.animation:
            context.user_data["from_chat_id"] = msg.chat.id
            context.user_data["message_id"]   = msg.message_id
            context.user_data["mode"]         = "add_code"
            await msg.reply_text("✅ Saqlandi!\nKod kiriting (masalan: uzb001)")
        else:
            await msg.reply_text("Video yoki document forward qiling")
        return

    if mode == "add_code":
        context.user_data["code"] = text
        context.user_data["mode"] = "add_name"
        await msg.reply_text("Film nomini yozing")
        return

    if mode == "add_name":
        code = context.user_data.get("code")
        if code:
            movies[code] = {
                "name": text,
                "from_chat_id": context.user_data["from_chat_id"],
                "message_id": context.user_data["message_id"],
                "views": 0
            }
            save_movies(movies)
            await msg.reply_text(f"✅ Qo‘shildi!\nKod: {code}")
        context.user_data.clear()
        return

    if mode == "delete_movie":
        if text in movies:
            del movies[text]
            save_movies(movies)
            await msg.reply_text("O‘chirildi")
        else:
            await msg.reply_text("Topilmadi")
        context.user_data.clear()
        return

    # qolgan mode'lar (broadcast, limit_add, add_channel) shu tarzda davom ettirilishi mumkin

    # oddiy foydalanuvchi kod yuborsa
    if text in movies:
        if not await check_subscription(context, msg.from_user.id):
            await send_subscription_message(msg, context)
            return
        m = movies[text]
        movies[text]["views"] = m.get("views", 0) + 1
        users[str(msg.from_user.id)]["used"] += 1
        save_movies(movies)
        save_users(users)
        await context.bot.forward_message(
            msg.chat_id,
            m["from_chat_id"],
            m["message_id"]
        )
        return

    await msg.reply_text("Bunday kod yo‘q. Menyudan tanlang 👆")

# ==================== MAIN ====================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))

    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
