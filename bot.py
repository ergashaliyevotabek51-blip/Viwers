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
CHANNEL_USERNAME = "@UzbekFilmTv_Kanal"

MANDATORY_CHANNELS = []           # ["@kanal1", "@kanal2", ...] shaklida bo'ladi
MAX_MANDATORY_CHANNELS = 10       # maksimal ruxsat etilgan kanal soni
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
        new_data = {}
        now = datetime.utcnow().isoformat()
        for uid in data:
            try:
                uid_str = str(int(uid))
                new_data[uid_str] = {"used": 0, "referrals": 0, "joined": now}
            except:
                continue
        save_users(new_data)
        return new_data

    cleaned = {}
    for k, v in data.items():
        try:
            uid = str(int(k))
            cleaned[uid] = {
                "used": int(v.get("used", 0)),
                "referrals": int(v.get("referrals", 0)),
                "joined": v.get("joined", datetime.utcnow().isoformat())
            }
        except:
            continue

    if cleaned != data:
        save_users(cleaned)

    return cleaned


def save_users(data: dict):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_movies() -> dict:
    if not os.path.exists(MOVIES_FILE):
        return {}
    try:
        with open(MOVIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def save_movies(data: dict):
    with open(MOVIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(users: dict, user_id: int) -> dict:
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "used": 0,
            "referrals": 0,
            "joined": datetime.utcnow().isoformat()
        }
        save_users(users)
    return users[uid]


def max_limit(user: dict) -> int:
    return FREE_LIMIT + user["referrals"] * REF_LIMIT


# ================= ADMIN KEYBOARD =================
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

    # Majburiy obuna tekshiruvi
    if MANDATORY_CHANNEL and not await is_subscribed(context, user.id):
        await send_subscription_message(update.message)
        return

    users = load_users()
    me = get_user(users, user.id)

    if args and args[0].isdigit():
        ref_id = args[0]
        if ref_id != str(user.id) and ref_id in users and me.get("refed") is None:
            users[ref_id]["referrals"] += 1
            me["refed"] = ref_id
            try:
                await context.bot.send_message(int(ref_id), f"🎉 Yangi do‘st kirdi!\nReferral: {users[ref_id]['referrals']}")
            except:
                pass
            save_users(users)

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
    if user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="HTML")


# ================= ADMIN COMMAND =================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return

    await update.message.reply_text("🛠 Admin panel", reply_markup=admin_keyboard())


# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id

    if q.data == "check_sub":
        if await is_subscribed(context, user_id):
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

    if data == "broadcast":
        context.user_data["mode"] = "wait_broadcast"
        await q.message.reply_text(
            "📢 Omaviy xabar yuborish\n\n"
            "Bot nomidan yubormoqchi bo‘lgan xabarni yuboring yoki forward qiling.\n"
            "Bekor qilish: /cancel"
        )
        return

        if data == "subscription":
        current = "\n".join(f"• {ch}" for ch in MANDATORY_CHANNELS) if MANDATORY_CHANNELS else "Hozircha majburiy kanal yo‘q"
        text = f"<b>Hozirgi majburiy kanallar ({len(MANDATORY_CHANNELS)}/{MAX_MANDATORY_CHANNELS}):</b>\n{current}\n\n"
        text += "Qo‘shish / o‘chirish buyruqlari (bir nechta kanal yozsa ham bo‘ladi):\n"
        text += "• <code>add @kanal1 @kanal2</code>\n"
        text += "• <code>del @kanal1</code>\n"
        text += "• <code>clear</code> — hammasini o‘chirish\n"
        text += "• <code>off</code> yoki <code>yo‘q</code> — majburiy obunani butunlay o‘chirish"
        context.user_data["mode"] = "set_subscription"
        await q.message.reply_text(text, parse_mode="HTML")
        return

    if data in ["add", "delete"]:
        context.user_data["mode"] = data
        msg = "Format:\n`kod|file_id yoki kanal link`" if data == "add" else "O‘chirish uchun kodni yuboring"
        await q.message.reply_text(msg)
        return


# ================= Obuna funksiyalari =================
async def is_subscribed(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    if not MANDATORY_CHANNELS:
        return True

    for channel in MANDATORY_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator", "restricted"]:
                return False
        except TelegramError as e:
            print(f"Obuna tekshirish xatosi {channel}: {e}")
            return False
    return True


async def send_subscription_message(message):
    if not MANDATORY_CHANNELS:
        await message.reply_text("Xatolik: majburiy kanallar hali sozlanmagan.")
        return

    kb = []
    for channel in MANDATORY_CHANNELS:
        clean = channel.lstrip('@')
        kb.append([InlineKeyboardButton(
            f"📢 {clean} ga obuna bo‘lish",
            url=f"https://t.me/{clean}"
        )])

    kb.append([InlineKeyboardButton("✅ Obuna bo‘ldim, tekshirish", callback_data="check_sub")])

    channels_text = "\n".join(f"• {ch}" for ch in MANDATORY_CHANNELS)

    await message.reply_text(
        f"Botdan foydalanish uchun quyidagi {len(MANDATORY_CHANNELS)} ta kanalga obuna bo‘ling:\n\n"
        f"{channels_text}\n\n"
        "Barchasiga obuna bo‘lgach «Tekshirish» tugmasini bosing!",
        reply_markup=InlineKeyboardMarkup(kb)
    )
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

    # Majburiy obuna sozlash
    mode = context.user_data.get("mode")
        if data == "subscription":
        current = "\n".join(f"• {ch}" for ch in MANDATORY_CHANNELS) if MANDATORY_CHANNELS else "Hozircha majburiy kanal yo‘q"
        text = f"<b>Hozirgi majburiy kanallar ({len(MANDATORY_CHANNELS)}/{MAX_MANDATORY_CHANNELS}):</b>\n{current}\n\n"
        text += "Qo‘shish / o‘chirish buyruqlari (bir nechta kanal yozsa ham bo‘ladi):\n"
        text += "• <code>add @kanal1 @kanal2</code>\n"
        text += "• <code>del @kanal1</code>\n"
        text += "• <code>clear</code> — hammasini o‘chirish\n"
        text += "• <code>off</code> yoki <code>yo‘q</code> — majburiy obunani butunlay o‘chirish"
        context.user_data["mode"] = "set_subscription"
        await q.message.reply_text(text, parse_mode="HTML")
        return

    users = load_users()
    movies = load_movies()
    user = get_user(users, user_id)

    # Broadcast
    if mode == "wait_broadcast" and user_id == ADMIN_ID:
        context.user_data["mode"] = "sending_broadcast"
        await msg.reply_text("Yuborilmoqda...")

        success = 0
        failed = 0
        total = len(users)

        for uid_str in list(users.keys()):
            try:
                uid = int(uid_str)
                await msg.copy(chat_id=uid)
                success += 1
                await asyncio.sleep(0.4)
            except Exception:
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
    if user_id == ADMIN_ID and text.lower().startswith("limit "):
        try:
            _, target_uid, extra = text.split()
            target_uid = str(target_uid)
            extra = int(extra)

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
    if user_id == ADMIN_ID and mode in ["add", "delete"]:
        if mode == "add":
            if "|" not in text:
                await msg.reply_text("Format: kod|value")
                return
            code, val = [x.strip() for x in text.split("|", 1)]
            movies[code] = val
            save_movies(movies)
            await msg.reply_text("✅ Kino qo‘shildi")
        elif mode == "delete":
            if text in movies:
                del movies[text]
                save_movies(movies)
                await msg.reply_text("🗑 O‘chirildi")
            else:
                await msg.reply_text("❌ Topilmadi")
        context.user_data.pop("mode", None)
        return

    # User kino so‘radi
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


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", lambda u, c: cancel_broadcast(u, c)))
    app.add_handler(CommandHandler("admin", admin_command))  # /admin komandasi

    app.add_handler(CallbackQueryHandler(admin_panel))

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
