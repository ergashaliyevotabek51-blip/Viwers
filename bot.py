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
ADMIN_IDS = [774440841]  # o'zingizning ID + qo'shimcha adminlar qo'shing

BOT_USERNAME = "UzbekFilmTv_bot"
CHANNEL_USERNAME = "@UzbekFilmTv_Kanal"

MANDATORY_CHANNELS = []  # admin paneldan qo'shiladi

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
        [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add")],
        [InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete")],
        [InlineKeyboardButton("📃 Kinolar ro‘yxati", callback_data="list_movies")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast")],
        [InlineKeyboardButton("🔒 Majburiy obuna", callback_data="subscription")],
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if MANDATORY_CHANNELS and not await is_subscribed(context, user.id):
        await send_subscription_message(update.message)
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
        f"• Bepul limit: <b>5 ta</b>\n"
        f"• Har bir do‘st taklif qilsangiz → +5 ta limit qo‘shiladi\n\n"
        f"🚀 Tayyormisiz? Kodni yuboring yoki do‘stlaringizni taklif qiling!"
    )

    kb = []
    if user.id in ADMIN_IDS:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="HTML")

# ================= ADMIN COMMAND =================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Siz admin emassiz!")
        return

    await update.message.reply_text("🛠 Admin panel", reply_markup=admin_keyboard())

# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id

    if user_id not in ADMIN_IDS:
        return

    data = q.data

    if data == "admin":
        await q.edit_message_text("🛠 Admin panel", reply_markup=admin_keyboard())
        return

    users = load_users()
    movies = load_movies()

    if data == "stats":
        text = f"👥 Userlar: {len(users)}\n🎬 Kinolar: {len(movies)}"
        await q.message.reply_text(text)
        return

    if data == "list_movies":
        if not movies:
            text = "Hozircha kinolar yo‘q."
        else:
            text = "Kinolar ro‘yxati:\n" + "\n".join(f"• {code}" for code in sorted(movies.keys()))
        await q.message.reply_text(text)
        return

    if data == "broadcast":
        context.user_data["mode"] = "broadcast"
        await q.message.reply_text("Xabarni yuboring yoki forward qiling.\n/cancel — bekor")
        return

    if data == "subscription":
        current = "\n".join(MANDATORY_CHANNELS) if MANDATORY_CHANNELS else "Majburiy obuna yo‘q"
        text = f"Hozirgi majburiy kanallar:\n{current}\n\n"
        text += "Yangi kanallarni qo‘shish uchun: @kanal1 @kanal2 formatida yuboring\n"
        text += "Tozalash uchun: clear yoki off deb yozing"
        context.user_data["mode"] = "subscription"
        await q.message.reply_text(text)
        return

    if data == "add":
        context.user_data["mode"] = "add"
        await q.message.reply_text("Format:\n`kod|file_id yoki link|film_nomi`")
        return

    if data == "delete":
        context.user_data["mode"] = "delete"
        await q.message.reply_text("O‘chirish uchun kodni yuboring")
        return

    await q.edit_message_text("Noma'lum buyruq")

# ================= OBUNA FUNKSİYALARI =================
async def is_subscribed(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    if not MANDATORY_CHANNELS:
        return True
    for channel in MANDATORY_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except TelegramError as e:
            print(f"Obuna tekshirish xatosi {channel}: {e}")
            return False
    return True


async def send_subscription_message(message):
    kb = []
    for channel in MANDATORY_CHANNELS:
        clean = channel.lstrip('@')
        kb.append([InlineKeyboardButton(
            f"📣 {clean} ga obuna bo‘lish",
            url=f"https://t.me/{clean}"
        )])

    kb.append([InlineKeyboardButton("✅ Obuna bo‘ldim, tekshirish", callback_data="check_sub")])

    channels_text = "\n".join(f"• {ch}" for ch in MANDATORY_CHANNELS)

    await message.reply_text(
        f"Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:\n\n"
        f"{channels_text}\n\n"
        "Obuna bo‘lgandan keyin tugmani bosing!",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    text = (msg.text or "").strip()

    if text == "/cancel":
        context.user_data.clear()
        await msg.reply_text("❌ Bekor qilindi")
        return

    mode = context.user_data.get("mode")

    # Majburiy obuna sozlash
    if mode == "subscription" and user_id in ADMIN_IDS:
        global MANDATORY_CHANNELS
        t = text.lower().strip()

        if t in ["clear", "off", "yo‘q"]:
            MANDATORY_CHANNELS = []
            save_settings()
            await msg.reply_text("✅ Majburiy kanallar tozalandi")
        else:
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

    # Broadcast
    if mode == "broadcast" and user_id in ADMIN_IDS:
        context.user_data["mode"] = "sending_broadcast"
        await msg.reply_text("Yuborilmoqda...")

        users = load_users()
        success = failed = 0
        total = len(users)

        for uid_str in list(users.keys()):
            try:
                uid = int(uid_str)
                await msg.copy(chat_id=uid)
                success += 1
                await asyncio.sleep(0.4)
            except:
                failed += 1

        context.user_data.clear()
        await msg.reply_text(
            f"✅ Omaviy yuborish tugadi!\n"
            f"Muvaffaqiyatli: {success}\n"
            f"Muvaffaqiyatsiz: {failed}\n"
            f"Jami userlar: {total}"
        )
        return

    # Admin limit qo‘shish
    if user_id in ADMIN_IDS and text.lower().startswith("limit "):
        try:
            _, target_uid, extra = text.split()
            target_uid = str(target_uid)
            extra = int(extra)

            users = load_users()
            if target_uid in users:
                users[target_uid]["referrals"] += extra // REF_LIMIT
                save_users(users)
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

    # Kino qo‘shish / o‘chirish
    if user_id in ADMIN_IDS and mode in ["add", "delete"]:
        if mode == "add":
            if "|" not in text:
                await msg.reply_text("Format: kod|file_id yoki link|film_nomi")
                return
            parts = text.split("|", 2)
            code = parts[0].strip()
            val = parts[1].strip()
            name = parts[2].strip() if len(parts) > 2 else "Noma'lum film"
            movies = load_movies()
            movies[code] = val
            save_movies(movies)
            await msg.reply_text(f"✅ Kino qo‘shildi!\nKod: {code}\nFilm: {name}")
        elif mode == "delete":
            movies = load_movies()
            if text in movies:
                del movies[text]
                save_movies(movies)
                await msg.reply_text("🗑 O‘chirildi")
            else:
                await msg.reply_text("❌ Topilmadi")
        context.user_data.pop("mode", None)
        return

    # Majburiy obuna tekshiruvi
    if MANDATORY_CHANNELS and not await is_subscribed(context, user_id):
        await send_subscription_message(msg)
        return

    # User kino so‘radi
    users = load_users()
    movies = load_movies()
    user = get_user(users, user_id)

    if text in movies:
        if user["used"] >= max_limit(user):
            ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            share_text = quote(
                f"Eng zo‘r o‘zbek filmlari shu botda! 🔥\n"
                f"Bepul 5 ta kino + har bir do‘st uchun +5 ta limit!\n\n"
                f"{ref_link}"
            )
            share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={share_text}"

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
        save_users(users)

        remaining = f"{user['used']}/{max_limit(user)}"

        ref_link = f"https://t.me/{BOT_USERNAME}"
        share_text = quote(
            f"Eng zo‘r o‘zbek filmlari shu botda! 🔥\n"
            f"Kodni yuboring → kino darhol keladi!\n"
            f"{ref_link}"
        )
        share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={share_text}"

        share_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🤖 Botni do‘stlarga ulashish", url=share_url)
        ]])

        val = movies[text]

        if val.startswith("https://t.me/c/"):
            p = val.replace("https://t.me/c/", "").split("/")
