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
    print("BOT_TOKEN topilmadi!")
    exit(1)

ADMIN_IDS = [774440841]  # ← O‘ZINGIZNING HAQIQIY ID’INGIZNI SHU YERGA YOZING!

BOT_USERNAME = "UzbekFilmTv_bot"
CHANNEL_USERNAME = "@UzbekFilmTv_Kanal"

MANDATORY_CHANNELS = []  # Admin paneldan qo‘shiladi

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"
SETTINGS_FILE = "settings.json"
STATS_FILE = "stats.json"

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
        except:
            MANDATORY_CHANNELS = []


def save_settings():
    global MANDATORY_CHANNELS
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"mandatory_channels": MANDATORY_CHANNELS}, f, ensure_ascii=False, indent=2)
    except:
        pass


load_settings()

# ================= STATISTIKA =================
def load_stats() -> dict:
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_stats(data: dict):
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

# ================= Fayl bilan ishlash =================
def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        save_users({})
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
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
    stats = load_stats()

    if data == "stats":
        text = f"👥 Umumiy userlar: {len(users)}\n"
        text += f"🎬 Umumiy kinolar: {len(movies)}\n\n"

        if stats:
            text += "🔥 Eng mashhur filmlar (top-10):\n"
            sorted_stats = sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
            for code, info in sorted_stats:
                name = info.get("name", "Noma'lum")
                count = info["count"]
                text += f"• {name} (kod: {code}) — {count} marta\n"
        else:
            text += "Hozircha statistika yo‘q."

        await q.message.reply_text(text)
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
        msg = "Format: kod|file_id yoki link|film_nomi" if data == "add_movie" else "O‘chirish uchun kod"
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

    # Admin funksiyalari
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

        # Statistika uchun hisoblash
        stats = load_stats()
        if text not in stats:
            stats[text] = {"count": 0, "name": "Noma'lum film"}
        stats[text]["count"] += 1
        # film nomini movies dan olish
        val = movies[text]
        if "|" in val:
            parts = val.split("|")
            if len(parts) > 1:
                stats[text]["name"] = parts[-1].strip()
        save_stats(stats)

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
            channel_id = int("-100" + p[0])
            msg_id = int(p[1])

            await context.bot.copy_message(
                chat_id=msg.chat_id,
                from_chat_id=channel_id,
                message_id=msg_id,
                reply_markup=share_kb
            )

            extra = (
                f"🎬 Kino tayyor 🍿\n"
                f"Qolgan: {remaining}\n\n"
                f"Kino <b>@{BOT_USERNAME}</b> dan yuklandi\n"
                f"Telegram kanal: <b>{CHANNEL_USERNAME}</b> 📢"
            )

            await msg.reply_text(extra, parse_mode="HTML", reply_markup=share_kb)

        else:
            caption = (
                f"🎬 Kino tayyor 🍿\n"
                f"Qolgan: {remaining}\n\n"
                f"Kino <b>@{BOT_USERNAME}</b> dan yuklandi\n"
                f"Telegram kanal: <b>{CHANNEL_USERNAME}</b> 📢"
            )

            await msg.reply_video(
                video=val,
                caption=caption,
                reply_markup=share_kb,
                parse_mode="HTML"
            )

        return

    if text:
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

    await admin_panel(update, context)


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("cancel", lambda u, c: context.user_data.clear() or u.message.reply_text("❌ Bekor qilindi")))

    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
