import asyncio
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

BOT_USERNAME = "UzbekFilmTV_bot"
MOVIES_FILE = "movies.json"
USERS_FILE = "users.json"

MAX_FREE = 5
REF_NEED = 3

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ================== FILE UTILS ==================
def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def is_admin(uid):
    return uid == ADMIN_ID

# ================== FSM ==================
class AddMovie(StatesGroup):
    code = State()
    value = State()

class Broadcast(StatesGroup):
    text = State()

# ================== START ==================
@dp.message(Command("start"))
async def start(msg: Message):
    users = load_json(USERS_FILE, {})
    uid = str(msg.from_user.id)

    ref = None
    if len(msg.text.split()) > 1:
        ref = msg.text.split()[1]

    if uid not in users:
        users[uid] = {
            "used": 0,
            "referrals": 0,
            "joined": datetime.now().strftime("%Y-%m-%d")
        }
        if ref and ref in users and ref != uid:
            users[ref]["referrals"] += 1
        save_json(USERS_FILE, users)

    text = (
        f"🤲 Assalomu alaykum va rohmatullohi va barokatuhu, {msg.from_user.first_name}!\n\n"
        "🎬 **UzbekFilmTV** rasmiy botiga xush kelibsiz!\n\n"
        "📥 Kino olish uchun **kod yuboring**.\n"
        "Masalan: `12`\n\n"
        "🌙 Eng sara o‘zbek kinolari siz uchun."
    )

    kb = []
    if is_admin(msg.from_user.id):
        kb.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin")])

    await msg.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# ================== ADMIN PANEL ==================
@dp.callback_query(F.data == "admin")
async def admin_panel(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add"),
            InlineKeyboardButton("🗑 Kino o‘chirish", callback_data="del")
        ],
        [
            InlineKeyboardButton("📊 Statistika", callback_data="stats"),
            InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")
        ],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back")]
    ])

    await call.message.edit_text("🛠 **Admin Panel**", reply_markup=kb)

@dp.callback_query(F.data == "back")
async def back(call: CallbackQuery):
    await start(call.message)

# ================== ADD MOVIE ==================
@dp.callback_query(F.data == "add")
async def add_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddMovie.code)
    await call.message.answer("🔢 Kino kodini kiriting:")

@dp.message(AddMovie.code)
async def add_code(msg: Message, state: FSMContext):
    await state.update_data(code=msg.text.strip())
    await state.set_state(AddMovie.value)
    await msg.answer("📎 Kino linki yoki file_id yuboring:")

@dp.message(AddMovie.value)
async def add_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    movies = load_json(MOVIES_FILE, {})
    movies[data["code"]] = msg.text.strip()
    save_json(MOVIES_FILE, movies)
    await state.clear()
    await msg.answer("✅ Kino muvaffaqiyatli qo‘shildi!")

# ================== DELETE MOVIE ==================
@dp.callback_query(F.data == "del")
async def del_info(call: CallbackQuery):
    await call.message.answer("🗑 O‘chirish uchun yozing:\n`del 12`")

# ================== STATS ==================
@dp.callback_query(F.data == "stats")
async def stats(call: CallbackQuery):
    movies = load_json(MOVIES_FILE, {})
    users = load_json(USERS_FILE, {})

    await call.message.answer(
        f"📊 **Statistika**\n\n"
        f"🎬 Kinolar: {len(movies)}\n"
        f"👥 Userlar: {len(users)}"
    )

# ================== BROADCAST ==================
@dp.callback_query(F.data == "broadcast")
async def bc_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(Broadcast.text)
    await call.message.answer("📢 Yuboriladigan xabarni yozing:")

# ================== MESSAGE HANDLER ==================
@dp.message()
async def handler(msg: Message, state: FSMContext):
    users = load_json(USERS_FILE, {})
    movies = load_json(MOVIES_FILE, {})
    uid = str(msg.from_user.id)
    text = msg.text.strip()

    # Broadcast send
    if is_admin(msg.from_user.id) and await state.get_state() == Broadcast.text.state:
        for u in users:
            try:
                await bot.send_message(u, text)
            except:
                pass
        await msg.answer("📢 Broadcast yuborildi!")
        await state.clear()
        return

    # Delete
    if is_admin(msg.from_user.id) and text.startswith("del "):
        code = text.replace("del ", "")
        if code in movies:
            del movies[code]
            save_json(MOVIES_FILE, movies)
            await msg.answer("🗑 O‘chirildi")
        else:
            await msg.answer("❌ Topilmadi")
        return

    # Movie request
    if text in movies:
        if users[uid]["used"] >= MAX_FREE and users[uid]["referrals"] < REF_NEED:
            ref_link = f"https://t.me/{BOT_USERNAME}?start={uid}"
            await msg.answer(
                "🔒 Limit tugadi!\n\n"
                "🎁 Ochish uchun 3 ta do‘st taklif qiling.\n\n"
                f"🔗 Sizning havolangiz:\n{ref_link}"
            )
            return

        users[uid]["used"] += 1
        save_json(USERS_FILE, users)

        val = movies[text]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("🔎 Qidirish", url=f"https://t.me/{BOT_USERNAME}")]
        ])

        if val.startswith("http"):
            parts = val.split("/")
            chat_id = int("-100" + parts[-2])
            msg_id = int(parts[-1])
            await bot.copy_message(
                chat_id=msg.chat.id,
                from_chat_id=chat_id,
                message_id=msg_id,
                reply_markup=kb
            )
        else:
            await msg.answer_video(
                video=val,
                caption="🎬 Kino tayyor! Ulashing do‘stlaringizga 🌙",
                reply_markup=kb
            )
        return

    await msg.answer("❌ Bunday kod topilmadi")

# ================== MAIN ==================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
