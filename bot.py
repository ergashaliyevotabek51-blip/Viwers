import os
import json
import random
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = "UzbekFilmTV_bot"  # o'zingiznikiga o'zgartiring

USERS_FILE    = "users.json"
MOVIES_FILE   = "movies.json"
SETTINGS_FILE = "settings.json"

FREE_LIMIT = 5
REF_LIMIT  = 5
ITEMS_PER_PAGE = 8  # katalogda bir sahifadagi film soni

ADMINS = [774440841,7818576058]

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

def load_users():    return load_json(USERS_FILE, {})
def save_users(data): save_json(USERS_FILE, data)

def load_movies():   return load_json(MOVIES_FILE, {})
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

def get_referral_link(uid):
    return f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"

# ==================== PAGINATION HELPER ====================
def build_catalog_keyboard(page=0, movies_list=None):
    if movies_list is None:
        movies = load_movies()
        movies_list = sorted(movies.items(), key=lambda x: x[1].get("name", "").lower())

    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = movies_list[start:end]

    kb = []
    for code, data in page_items:
        kb.append([InlineKeyboardButton(data["name"], callback_data=f"play_{code}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Oldingi", callback_data=f"cat_{page-1}"))
    if end < len(movies_list):
        nav.append(InlineKeyboardButton("Keyingi ▶️", callback_data=f"cat_{page+1}"))

    if nav:
        kb.append(nav)

    kb.append([InlineKeyboardButton("🔙 Asosiy menyuga", callback_data="main_menu")])

    return InlineKeyboardMarkup(kb)

# ==================== MAJBURIY OBUNA ====================
# (oldingi kod bilan bir xil, o'zgartirilmagan)

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    settings = load_settings()
    channels = settings.get("channels", [])
    if not channels:
        return True
    for channel in channels:
        try:
            chat_id = channel if channel.startswith("@") else f"@{channel.lstrip('@')}"
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            print(f"Obuna xatosi {channel}: {e}")
            return False
    return True

def subscription_keyboard():
    settings = load_settings()
    kb = []
    for ch in settings.get("channels", []):
        clean = ch.lstrip('@')
        kb.append([InlineKeyboardButton(f"🔔 Obuna bo‘ling: @{clean}", url=f"https://t.me/{clean}")])
    kb.append([InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(kb)

async def send_subscription_message(target, context):
    kb = subscription_keyboard()
    text = "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling va tekshirish tugmasini bosing:"
    if hasattr(target, "reply_text"):
        await target.reply_text(text, reply_markup=kb)
    else:
        await target.edit_message_text(text, reply_markup=kb)

# ==================== ASOSIY MENYU ====================
def main_menu_keyboard(has_admin=False):
    kb = [
        [InlineKeyboardButton("🎟 Mening limitim", callback_data="limit")],
        [InlineKeyboardButton("🎬 Random film", callback_data="random")],
        [InlineKeyboardButton("🔥 Trend filmlar", callback_data="trend")],
        [InlineKeyboardButton("🎥 Kino katalog", callback_data="catalog_0")],
        [InlineKeyboardButton("👥 Do‘st taklif qilish", callback_data="referral")]
    ]
    if has_admin:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid_str = str(user.id)
    name = user.first_name or "Do‘st"

    users = load_users()
    user_data = get_user(users, uid_str)

    # Referal tekshirish
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            ref_id = arg[4:]
            if ref_id != uid_str and ref_id in users:
                users[ref_id]["referrals"] = users[ref_id].get("referrals", 0) + 1
                save_users(users)
                try:
                    await context.bot.send_message(ref_id, "Do‘stingiz botga kirdi! +5 limit qo‘shildi 🎉")
                except:
                    pass

    save_users(users)

    if not await check_subscription(context, user.id):
        await send_subscription_message(update.message, context)
        return

    text = (
        f"Assalomu alaykum, {name}! 👋\n\n"
        f"🎬 <b>UzbekFilmTV</b> — eng sara o‘zbek filmlari!\n\n"
        f"Kod yozing yoki menyudan tanlang ↓\n"
        f"Limit: {user_data['used']}/{max_limit(user_data)}"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu_keyboard(is_admin(user.id)),
        parse_mode="HTML"
    )

# ==================== CALLBACK QUERY ====================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid = q.from_user.id
    uid_str = str(uid)
    users = load_users()
    movies = load_movies()
    user_data = get_user(users, uid_str)

    if data == "check_sub":
        if await check_subscription(context, uid):
            await q.edit_message_text("✅ Obuna tasdiqlandi! Botdan foydalaning 🎬")
        else:
            await send_subscription_message(q.message, context)
        return

    if not await check_subscription(context, uid):
        await send_subscription_message(q.message, context)
        return

    if data == "limit":
        lim = max_limit(user_data)
        await q.message.reply_text(f"🎟 Sizning limitingiz: {user_data['used']}/{lim}")
        return

    if data == "random":
        code = random_movie(movies)
        if not code:
            await q.message.reply_text("Hozircha film yo‘q 😔")
            return
        m = movies[code]
        await forward_film(context, q.message.chat_id, m)
        return

    if data == "trend":
        top = trending(movies)
        if not top:
            await q.message.reply_text("Hali trend yo‘q")
            return
        text = "🔥 Eng ko‘p ko‘rilganlar:\n\n" + "\n".join(
            f"{i}. {m['name']} — {m.get('views',0)} ta" for i, (_, m) in enumerate(top, 1)
        )
        await q.message.reply_text(text)
        return

    if data.startswith("cat_"):
        page = int(data.split("_")[1])
        kb = build_catalog_keyboard(page)
        await q.edit_message_text("🎥 Kino katalogi", reply_markup=kb)
        return

    if data.startswith("play_"):
        code = data[5:]
        if code in movies:
            m = movies[code]
            movies[code]["views"] = m.get("views", 0) + 1
            user_data["used"] += 1
            save_movies(movies)
            save_users(users)
            await forward_film(context, q.message.chat_id, m)
        return

    if data == "referral":
        link = get_referral_link(uid_str)
        text = (
            "👥 Do‘stlaringizni taklif qiling!\n\n"
            f"Havola: {link}\n\n"
            f"Har bir do‘st uchun +{REF_LIMIT} limit qo‘shiladi 🎁"
        )
        await q.message.reply_text(text)
        return

    if data == "main_menu":
        await q.edit_message_text("Asosiy menyu", reply_markup=main_menu_keyboard(is_admin(uid)))
        return

    if not is_admin(uid):
        return

    # Admin qismi (oldingidek)
    if data == "admin":
        kb = [
            [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add")],
            [InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete")],
            [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
            [InlineKeyboardButton("🔥 Top filmlar", callback_data="top")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton("🔒 Majburiy obuna", callback_data="sub")],
            [InlineKeyboardButton("💠 Limit qo‘shish", callback_data="limit_add")]
        ]
        await q.message.reply_text("🛠 Admin panel", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    # ... qolgan admin funksiyalari (stats, top, delete, broadcast, limit_add, add_channel) oldingidek qoldiriladi

# ==================== FILMNI FORWARD QILISH + INLINE TUGMALAR ====================
async def forward_film(context: ContextTypes.DEFAULT_TYPE, chat_id, movie_data):
    await context.bot.forward_message(
        chat_id=chat_id,
        from_chat_id=movie_data["from_chat_id"],
        message_id=movie_data["message_id"]
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Keyingi film", callback_data="random")],
        [InlineKeyboardButton("🔥 Trend filmlar", callback_data="trend")],
        [InlineKeyboardButton("🎥 Kino katalog", callback_data="catalog_0")],
        [InlineKeyboardButton("🔗 Ulashish", url=f"https://t.me/share/url?url={BOT_USERNAME}")]
    ])

    await context.bot.send_message(
        chat_id,
        "Yana bir film tanlaysizmi? 👇",
        reply_markup=kb
    )

# ==================== XABARLAR (qidiruv + noto'g'ri kod) ====================
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    uid_str = str(update.effective_user.id)
    mode = context.user_data.get("mode")
    text = (message.text or "").strip()

    users = load_users()
    movies = load_movies()
    user_data = get_user(users, uid_str)

    if mode:
        # admin rejimlari (add_movie, movie_code, movie_name, delete, broadcast, limit_add, add_channel)
        # oldingi kod bilan bir xil qoldiriladi — bu yerda faqat qisqartirib ko'rsatilgan
        if mode == "add_movie":
            if not (message.video or message.document or message.animation):
                await message.reply_text("Faqat video/document/animation qabul qilinadi.")
                return
            context.user_data["from_chat_id"] = message.chat.id
            context.user_data["message_id"]   = message.message_id
            context.user_data["name"]         = message.caption or "Nomsiz"
            context.user_data["mode"]         = "movie_code"
            await message.reply_text("✅ Saqlandi! Kod kiriting (uzb001 masalan)")
            return

        if mode == "movie_code":
            context.user_data["code"] = text
            context.user_data["mode"] = "movie_name"
            await message.reply_text("Film nomini to‘liq yozing")
            return

        if mode == "movie_name":
            code = context.user_data.get("code")
            movies[code] = {
                "name": text,
                "from_chat_id": context.user_data["from_chat_id"],
                "message_id": context.user_data["message_id"],
                "views": 0
            }
            save_movies(movies)
            await message.reply_text(f"🎉 Qo‘shildi!\nKod: {code}\nNom: {text}")
            context.user_data.clear()
            return

        # qolgan mode'lar (delete_movie, broadcast, limit_add, add_channel) — oldingidek

    # QIDIRUV + NOTO'G'RI KOD
    if text:
        if text in movies:
            # kod topilsa
            if user_data["used"] >= max_limit(user_data):
                await message.reply_text(
                    "Limit tugadi 😔\n\n"
                    f"Do‘stlaringizni taklif qiling va +{REF_LIMIT} limit oling!\n"
                    f"Havola: {get_referral_link(uid_str)}"
                )
                return

            if not await check_subscription(context, update.effective_user.id):
                await send_subscription_message(message, context)
                return

            m = movies[text]
            movies[text]["views"] = m.get("views", 0) + 1
            user_data["used"] += 1
            save_movies(movies)
            save_users(users)

            await forward_film(context, message.chat_id, m)
            return

        # Qidiruv
        found = []
        query = text.lower()
        for code, m in movies.items():
            if query in m["name"].lower():
                found.append((code, m["name"]))

        if found:
            kb = []
            for code, name in found[:12]:  # cheklov
                kb.append([InlineKeyboardButton(name, callback_data=f"play_{code}")])
            kb.append([InlineKeyboardButton("🔙 Menyuga", callback_data="main_menu")])

            await message.reply_text(
                f"“{text}” bo‘yicha topilgan filmlar:",
                reply_markup=InlineKeyboardMarkup(kb)
            )
            return

        # Hech narsa topilmasa
        await message.reply_text(
            f"“{text}” bo‘yicha hech narsa topilmadi 😔\n\n"
            "Quyidagilarni sinab ko‘ring:\n"
            "• Random film tugmasi\n"
            "• Kino katalog\n"
            "• Trend filmlar",
            reply_markup=main_menu_keyboard(is_admin(update.effective_user.id))
        )
        return

# ==================== MAIN ====================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))

    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
