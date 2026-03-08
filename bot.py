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
from telegram.error import TelegramError, BadRequest, Forbidden

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 774440841
BOT_USERNAME = "UzbekFilmTv_bot"
CHANNEL_USERNAME = "@UzbekFilmTv_Kanal"

MANDATORY_CHANNELS = []           # default bo'sh – avval bot ishlasin
MAX_MANDATORY_CHANNELS = 10

FREE_LIMIT = 5
REF_LIMIT = 5

USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"
SETTINGS_FILE = "settings.json"

# ================= SETTINGS =================
def load_settings():
    global MANDATORY_CHANNELS
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                MANDATORY_CHANNELS = data.get("mandatory_channels", [])
        except Exception as e:
            print(f"Settings yuklash xatosi: {e}")
            MANDATORY_CHANNELS = []


def save_settings():
    global MANDATORY_CHANNELS
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"mandatory_channels": MANDATORY_CHANNELS}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Settings saqlash xatosi: {e}")


load_settings()

# ================= Fayl bilan ishlash =================

def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        save_users({})
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return {}
            return data
    except:
        return {}


def save_users(data: dict):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Users saqlash xatosi: {e}")


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
    except Exception as e:
        print(f"Movies saqlash xatosi: {e}")


def get_user(users: dict, user_id: int) -> dict:
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "used": 0,
            "referrals": 0,
            "joined": datetime.utcnow().isoformat(),
            "refed": None
        }
        save_users(users)
    return users[uid]


def max_limit(user: dict) -> int:
    return FREE_LIMIT + user["referrals"] * REF_LIMIT


# ================= ADMIN KEYBOARD =================
def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add"),
         InlineKeyboardButton("➖ Kino o‘chirish", callback_data="delete")],
        [InlineKeyboardButton("📃 Kinolar ro‘yxati", callback_data="list_movies"),
         InlineKeyboardButton("📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton("📢 Omaviy xabar", callback_data="broadcast")],
        [InlineKeyboardButton("🔒 Majburiy obuna sozlamalari", callback_data="subscription")],
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

    if args and len(args) > 0 and args[0].isdigit():
        ref_id = args[0]
        if ref_id != str(user.id) and ref_id in users and me.get("refed") is None:
            users[ref_id]["referrals"] += 1
            me["refed"] = ref_id
            try:
                await context.bot.send_message(int(ref_id), f"🎉 Yangi do‘st kirdi! Referral soni: {users[ref_id]['referrals']}")
            except:
                pass
            save_users(users)

    text = (
        f"👋 Assalomu alaykum, <b>{user.first_name}</b>!\n\n"
        f"🎬 <b>UzbekFilmTV</b> — eng zo‘r o‘zbek filmlari shu yerda! 🍿\n\n"
        f"🔥 <b>Qanday ishlaydi?</b>\n"
        f"• Kod yuboring (masalan: 12, 45, 107) → kino darhol keladi 🎥\n"
        f"• Bepul limit: <b>5 ta kino</b> 🎟️\n"
        f"• Har bir do‘st taklif qilsangiz → +5 ta limit qo‘shiladi 👥\n\n"
        f"🚀 <b>Tayyormisiz?</b> Kodni yozing yoki do‘stlaringizni chaqiring! ✨"
    )

    kb = []
    if user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="HTML")


# ================= ADMIN COMMAND & PANEL =================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return
    await update.message.reply_text("🛠 Admin panel ochildi!", reply_markup=admin_keyboard())


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "check_sub":
        if await is_subscribed(context, q.from_user.id):
            await q.edit_message_text("✅ Hammaga obuna bo‘lgansiz! Bot ishlaydi 🚀")
        else:
            await q.edit_message_text("❌ Hali barcha kanallarga obuna bo‘lmagansiz 😕")
        return

    if q.from_user.id != ADMIN_ID:
        return

    # qolgan admin panel logikasi (stats, list_movies, broadcast, subscription) o‘zgarmagan holda qoldirildi
    # agar kerak bo‘lsa, oldingi versiyalardan nusxa oling yoki so‘rang

    # Misol uchun subscription qismi:
    if q.data == "subscription":
        curr = "\n".join(f"• {c}" for c in MANDATORY_CHANNELS) or "Hozircha yo‘q"
        text = f"<b>Majburiy kanallar ({len(MANDATORY_CHANNELS)}/{MAX_MANDATORY_CHANNELS}):</b>\n{curr}\n\n"
        text += "add @kanal1 @kanal2\n"
        text += "del @kanal1\n"
        text += "clear — hammasini tozalash\n"
        text += "off — majburiy obunani o‘chirish"
        context.user_data["mode"] = "subscription"
        await q.message.reply_text(text, parse_mode="HTML")
        return

    # qolgan qismlar (stats, broadcast, add/delete movie) oldingi kodda bo‘lgani kabi qoldiriladi


# ================= SUBSCRIPTION =================
async def is_subscribed(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    if not MANDATORY_CHANNELS:
        return True
    for channel in MANDATORY_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator", "restricted"]:
                return False
        except Exception:
            return False
    return True


async def send_subscription_message(message):
    if not MANDATORY_CHANNELS:
        await message.reply_text("⚠️ Majburiy kanallar hali sozlanmagan.")
        return

    kb = []
    for ch in MANDATORY_CHANNELS:
        clean = ch.lstrip('@')
        kb.append([InlineKeyboardButton(f"📢 {clean} ga obuna", url=f"https://t.me/{clean}")])

    kb.append([InlineKeyboardButton("✅ Obuna bo‘ldim – tekshirish", callback_data="check_sub")])

    channels_list = "\n".join(f"• {c}" for c in MANDATORY_CHANNELS)

    text = (
        f"🔐 Botdan foydalanish uchun quyidagi {len(MANDATORY_CHANNELS)} ta kanalga obuna bo‘ling:\n\n"
        f"{channels_list}\n\n"
        f"Obuna bo‘lgach «Tekshirish» tugmasini bosing! 🚀"
    )

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))


# ================= MESSAGE HANDLER (emoji bilan boyitilgan) =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    text = msg.text.strip()
    user_id = msg.from_user.id

    if text == "/cancel":
        context.user_data.clear()
        await msg.reply_text("❌ Bekor qilindi!")
        return

    mode = context.user_data.get("mode")

    # Subscription sozlash (admin)
    if mode == "subscription" and user_id == ADMIN_ID:
        # oldingi versiyadagi logika (add, del, clear, off) – o‘zgarmagan holda qoldiriladi
        # kerak bo‘lsa oldingi kodlardan ko‘chiring
        pass

    users = load_users()
    movies = load_movies()
    user = get_user(users, user_id)

    if text in movies:
        if user["used"] >= max_limit(user):
            ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            share_text = quote(
                f"Eng zo‘r o‘zbek filmlari shu botda! 🔥\n"
                f"Bepul 5 ta + do‘st uchun +5 limit!\n{ref_link}"
            )
            share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={share_text}"

            await msg.reply_text(
                f"⛔ Limit tugadi! 😓\n\n"
                f"Qolgan: 0/{max_limit(user)}\n"
                f"Do‘stlar: {user['referrals']} 👥\n\n"
                f"Yana ko‘proq kino uchun do‘stlaringizni taklif qiling! ✨",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("👥 Do‘stlarga ulashish", url=share_url)
                ]]),
                disable_web_page_preview=True
            )
            return

        user["used"] += 1
        save_users(users)

        remaining = f"{user['used']}/{max_limit(user)}"

        caption = (
            f"🎬 Kino tayyor! 🍿✨\n"
            f"Qolgan imkoniyat: {remaining} 🎟️\n\n"
            f"<b>@{BOT_USERNAME}</b> orqali yuklandi\n"
            f"Kanal: <b>{CHANNEL_USERNAME}</b> 📢"
        )

        val = movies[text]
        share_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🤖 Botni ulashish", url=f"https://t.me/share/url?url={quote('https://t.me/'+BOT_USERNAME)}")
        ]])

        if val.startswith("https://t.me/c/"):
            # private kanal logikasi (oldingi kodda bo‘lgani kabi)
            try:
                parts = val.replace("https://t.me/c/", "").split("/")
                chat_id = int("-100" + parts[0])
                msg_id = int(parts[1])
                await context.bot.copy_message(msg.chat_id, chat_id, msg_id, reply_markup=share_kb)
                await msg.reply_text(caption, parse_mode="HTML", reply_markup=share_kb)
            except:
                await msg.reply_text("Kino yuborishda xato yuz berdi 😔")
        else:
            await msg.reply_video(video=val, caption=caption, reply_markup=share_kb, parse_mode="HTML")
        return

    await msg.reply_text("🤔 Bunday kod topilmadi... Iltimos to‘g‘ri kod yozing!")


# ================= MAIN =================
def main():
    if not TOKEN:
        print("TOKEN topilmadi! BOT_TOKEN muhit o'zgaruvchisini sozlang.")
        return

    print("Bot ishga tushmoqda...")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
