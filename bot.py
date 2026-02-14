import asyncio
import json
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Railway envda o'zgartiring

BOT_USERNAME = "UzbekFilmTV_bot"  # o'zingiznikiga o'zgartiring
MOVIES_FILE = "movies.json"
USERS_FILE = "users.json"

MAX_FREE = 5          # bepul limit
REF_NEED = 3          # shuncha referral kerak limit ochish uchun

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
router = Router()
dp.include_router(router)


# ================== FILE UTILS ==================
def load_json(path: str, default=None):
    if not os.path.exists(path):
        return default or {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSON yuklashda xato: {e}")
        return default or {}


def save_json(path: str, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"JSON saqlashda xato: {e}")


def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID


# ================== FSM ==================
class AddMovie(StatesGroup):
    code = State()
    value = State()


class Broadcast(StatesGroup):
    text = State()


# ================== KEYBOARDS ==================
def get_main_kb(is_admin_user: bool = False):
    kb = []
    if is_admin_user:
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie"),
            InlineKeyboardButton("🗑 Kino o‘chirish", callback_data="del_movie"),
        ],
        [
            InlineKeyboardButton("📊 Statistika", callback_data="stats"),
            InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"),
        ],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")],
    ])


# ================== START & MAIN ==================
@router.message(Command("start"))
async def cmd_start(msg: Message):
    users = load_json(USERS_FILE, {})
    uid = str(msg.from_user.id)

    ref_id = None
    if len(msg.text.split()) > 1:
        ref_id = msg.text.split()[1]

    if uid not in users:
        users[uid] = {
            "used": 0,
            "referrals": 0,
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "username": msg.from_user.username or "",
            "name": msg.from_user.first_name,
        }
        if ref_id and ref_id in users and ref_id != uid:
            users[ref_id]["referrals"] += 1
            save_json(USERS_FILE, users)
            try:
                await bot.send_message(
                    ref_id,
                    f"🎉 Yangi referral! Sizda endi {users[ref_id]['referrals']} ta do‘st."
                )
            except:
                pass

    save_json(USERS_FILE, users)

    text = (
        f"Assalomu alaykum, <b>{msg.from_user.first_name}</b>!\n\n"
        "🎬 <b>UzbekFilmTV</b> botiga xush kelibsiz!\n\n"
        "Kino olish uchun kod yuboring (masalan: <code>12</code>)\n"
        "Eng sara o‘zbek filmlari shu yerda 🌙"
    )

    await msg.answer(text, reply_markup=get_main_kb(is_admin(msg.from_user.id)))


@router.callback_query(F.data == "back_to_main")
async def back_to_main(call: CallbackQuery):
    await call.message.edit_text(
        "Bosh menyuga qaytdingiz ✅",
        reply_markup=get_main_kb(is_admin(call.from_user.id))
    )
    await call.answer()


# ================== ADMIN PANEL ==================
@router.callback_query(F.data == "admin")
async def admin_panel(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Siz admin emassiz!", show_alert=True)
        return

    await call.message.edit_text(
        "<b>🛠 Admin Panel</b>",
        reply_markup=get_admin_kb()
    )
    await call.answer()


@router.callback_query(F.data == "stats")
async def stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    movies = load_json(MOVIES_FILE, {})
    users = load_json(USERS_FILE, {})

    text = (
        f"<b>📊 Statistika</b>\n\n"
        f"🎬 Kinolar soni: <b>{len(movies)}</b>\n"
        f"👥 Ro‘yxatdan o‘tganlar: <b>{len(users)}</b>\n"
        f"📅 Bugungi sana: {datetime.now().strftime('%Y-%m-%d')}"
    )

    await call.message.edit_text(text, reply_markup=get_admin_kb())
    await call.answer()


@router.callback_query(F.data == "add_movie")
async def add_movie_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AddMovie.code)
    await call.message.edit_text("🔢 <b>Kino kodini kiriting</b> (masalan: 45)")
    await call.answer()


@router.message(AddMovie.code)
async def add_movie_code(msg: Message, state: FSMContext):
    code = msg.text.strip()
    if not code.isdigit():
        await msg.answer("Faqat raqam kiriting!")
        return
    await state.update_data(code=code)
    await state.set_state(AddMovie.value)
    await msg.answer(
        "📎 Kino linkini yuboring yoki faylni forward qiling:\n"
        "Misol: <code>https://t.me/c/123456789/456</code>"
    )


@router.message(AddMovie.value)
async def add_movie_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    code = data["code"]
    value = msg.text.strip() if msg.text else ""

    if msg.video:
        value = msg.video.file_id
    elif msg.document:
        value = msg.document.file_id
    elif msg.forward_from_chat and msg.forward_from_message_id:
        value = f"https://t.me/c/{str(msg.forward_from_chat.id)[4:]}/{msg.forward_from_message_id}"

    if not value:
        await msg.answer("Hech narsa topilmadi. Link yoki video forward qiling.")
        return

    movies = load_json(MOVIES_FILE, {})
    movies[code] = value
    save_json(MOVIES_FILE, movies)

    await state.clear()
    await msg.answer(f"✅ Kod <code>{code}</code> qo‘shildi!", reply_markup=get_main_kb(is_admin(msg.from_user.id)))


@router.callback_query(F.data == "del_movie")
async def del_movie_info(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.edit_text(
        "🗑 O‘chirish uchun shunday yozing:\n"
        "<code>del 45</code>\n(yoki oddiy xabarda yozing)"
    )
    await call.answer()


@router.callback_query(F.data == "broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(Broadcast.text)
    await call.message.edit_text("📢 Yuboriladigan xabarni yozing (matn, rasm, video...):")
    await call.answer()


# ================== MAIN HANDLER ==================
@router.message()
async def message_handler(msg: Message, state: FSMContext):
    uid_str = str(msg.from_user.id)
    users = load_json(USERS_FILE, {})
    movies = load_json(MOVIES_FILE, {})

    # Broadcast (admin)
    current_state = await state.get_state()
    if is_admin(msg.from_user.id) and current_state == Broadcast.text.state:
        count = 0
        for user_id in users:
            try:
                await msg.forward(chat_id=user_id)
                count += 1
            except:
                pass
        await msg.answer(f"📢 Broadcast yuborildi: {count} ta userga yetib bordi")
        await state.clear()
        return

    # Delete movie (admin)
    text = msg.text.strip()
    if is_admin(msg.from_user.id) and text.startswith("del "):
        code = text.replace("del ", "").strip()
        if code in movies:
            del movies[code]
            save_json(MOVIES_FILE, movies)
            await msg.answer(f"🗑 Kod <code>{code}</code> o‘chirildi")
        else:
            await msg.answer("❌ Bunday kod topilmadi")
        return

    # Movie kodini qidirish
    if text in movies:
        user_data = users.get(uid_str, {"used": 0, "referrals": 0})

        if user_data["used"] >= MAX_FREE and user_data["referrals"] < REF_NEED:
            ref_link = f"https://t.me/{BOT_USERNAME}?start={uid_str}"
            await msg.answer(
                f"🔒 Limit tugadi!\n\n"
                f"Sizda {user_data['referrals']}/{REF_NEED} ta referral bor.\n"
                f"Limitni ochish uchun yana {REF_NEED - user_data['referrals']} ta do‘st taklif qiling.\n\n"
                f"🔗 Havolangiz:\n<code>{ref_link}</code>",
                disable_web_page_preview=True
            )
            return

        # Limitni oshirishdan oldin yuborish
        val = movies[text]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("🔎 Yangi kinolar", url=f"https://t.me/{BOT_USERNAME}")]
        ])

        success = False
        try:
            if val.startswith("http") and "t.me/c/" in val:
                path = val.split("t.me/c/")[-1]
                parts = path.split("/")
                if len(parts) < 2:
                    raise ValueError("Noto‘g‘ri link")
                channel_str = parts[0]
                msg_str = parts[1].split("?")[0]
                from_chat_id = int("-100" + channel_str)
                message_id = int(msg_str)

                await bot.copy_message(
                    chat_id=msg.chat.id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                    reply_markup=kb
                )
                success = True

            else:
                # file_id deb faraz qilamiz (video/document)
                await msg.answer_video(
                    video=val,
                    caption="🎬 Kino tayyor! Do‘stlaringizga ulashing 🌙",
                    reply_markup=kb
                )
                success = True

        except Exception as e:
            logger.error(f"Kino yuborishda xato {text}: {e}")
            await msg.answer("❌ Ushbu kino hozirda mavjud emas yoki xato bor.")

        if success:
            user_data["used"] += 1
            users[uid_str] = user_data
            save_json(USERS_FILE, users)

        return

    await msg.answer("❌ Bunday kod topilmadi. Iltimos, to‘g‘ri kod yuboring.")


async def main():
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
