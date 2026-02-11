import asyncio
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ================= CONFIG =================
TOKEN = "8370792264:AAFH3P9qZPkHQFRBnxjxolGMILTRhYexDb0"
ADMIN_ID = 774440841
BOT_USERNAME = "UzbekFilmTV_bot"

MOVIES_FILE = "movies.json"
USERS_FILE = "users.json"

bot = Bot(TOKEN)
dp = Dispatcher()

# ================= FILE SYSTEM =================
def load_movies():
    try:
        with open(MOVIES_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_movies(data):
    with open(MOVIES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_admin(user_id):
    return user_id == ADMIN_ID

# ================= FSM =================
class AddMovie(StatesGroup):
    code = State()
    value = State()

class BroadcastState(StatesGroup):
    media = State()

# ================= START =================
@dp.message(Command("start"))
async def start(msg: Message):

    users = load_users()
    user_id = str(msg.from_user.id)

    ref = msg.text.split(" ")
    ref_id = None
    if len(ref) > 1:
        ref_id = ref[1]

    if user_id not in users:
        users[user_id] = {
            "used": 0,
            "referrals": 0,
            "invited_by": ref_id if ref_id else None
        }

        if ref_id and ref_id in users:
            users[ref_id]["referrals"] += 1

        save_users(users)

    name = msg.from_user.first_name

    text = (
        f"🤲 Assalomu alaykum va rohmatullohi va barokatuhu, {name}!\n\n"
        "🎬 UzbekFilmTV rasmiy ravishda ishga tushdi!\n\n"
        "✨ Eng sara o'zbek filmlari shu yerda.\n"
        "📥 Kino olish uchun kod yuboring.\n\n"
        "📌 Masalan: 12"
    )

    kb = None
    if is_admin(msg.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛠 Admin Panel", callback_data="admin")]
        ])

    await msg.answer(text, reply_markup=kb)

# ================= ADMIN PANEL =================
@dp.callback_query(F.data == "admin")
async def admin_panel(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kod qo‘shish", callback_data="add")],
        [InlineKeyboardButton(text="➖ Kod o‘chirish", callback_data="delete")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="broadcast")],
    ])

    await call.message.edit_text("🛠 Admin Panel", reply_markup=kb)

# ================= ADD MOVIE =================
@dp.callback_query(F.data == "add")
async def add_movie_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddMovie.code)
    await call.message.answer("🔢 Kodni kiriting (masalan 12):")

@dp.message(AddMovie.code)
async def get_code(msg: Message, state: FSMContext):
    await state.update_data(code=msg.text.strip())
    await state.set_state(AddMovie.value)
    await msg.answer("📎 Kanal post linkini yoki file_id yuboring:")

@dp.message(AddMovie.value)
async def save_movie(msg: Message, state: FSMContext):
    data = await state.get_data()
    movies = load_movies()
    movies[data["code"]] = msg.text.strip()
    save_movies(movies)
    await state.clear()
    await msg.answer("✅ Kino saqlandi!")

# ================= HANDLE ALL =================
@dp.message()
async def handle_all(msg: Message):

    users = load_users()
    movies = load_movies()

    user_id = str(msg.from_user.id)

    if user_id not in users:
        return

    text = msg.text.strip()

    # DELETE
    if is_admin(msg.from_user.id) and text.startswith("del "):
        code = text.replace("del ", "")
        if code in movies:
            del movies[code]
            save_movies(movies)
            await msg.answer("🗑 O‘chirildi")
        else:
            await msg.answer("❌ Topilmadi")
        return

    # MOVIE SYSTEM
    if text in movies:

        # LIMIT SYSTEM
        if users[user_id]["used"] >= 5 and users[user_id]["referrals"] < 3:
            link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            await msg.answer(
                "🔒 5 ta kino ishlatildi!\n\n"
                "🎁 Yana ochish uchun 3 ta do‘st taklif qiling.\n\n"
                f"🔗 Sizning havolangiz:\n{link}"
            )
            return

        users[user_id]["used"] += 1
        save_users(users)

        val = movies[text]

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔎 Qidirish",
                url=f"https://t.me/{BOT_USERNAME}"
            )]
        ])

        if val.startswith("http"):
            parts = val.split("/")
            chat_id = int("-100" + parts[-2])
            message_id = int(parts[-1])

            await bot.copy_message(
                chat_id=msg.chat.id,
                from_chat_id=chat_id,
                message_id=message_id,
                reply_markup=kb
            )
        else:
            await msg.answer_video(
                video=val,
                caption="🎬 Kino tayyor! Ulashing do‘stlaringizga 💎",
                reply_markup=kb
            )
        return

    await msg.answer("❌ Bunday kod topilmadi")

# ================= STATS =================
@dp.callback_query(F.data == "stats")
async def stats(call: CallbackQuery):
    movies = load_movies()
    users = load_users()

    text = (
        f"📊 Statistika\n\n"
        f"🎬 Kino: {len(movies)}\n"
        f"👥 User: {len(users)}\n"
        f"📅 {datetime.now().strftime('%d-%m-%Y')}"
    )

    await call.message.answer(text)

# ================= BROADCAST =================
@dp.callback_query(F.data == "broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.media)
    await call.message.answer("📢 Xabarni yuboring (text, rasm yoki video):")

@dp.message(BroadcastState.media)
async def broadcast_send(msg: Message, state: FSMContext):
    users = load_users()

    for user_id in users:
        try:
            await msg.copy_to(user_id)
        except:
            pass

    await msg.answer("📢 Yuborildi!")
    await state.clear()

# ================= MAIN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  import requests

HF_TOKEN = "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"
AI_MODEL = "HuggingFaceH4/zephyr-7b-beta"
def ask_ai(user_name, text):
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}"
    }

    prompt = f"""
Assalomu alaykum va rohmatullohi va barokatuhu, {user_name}!

Siz UzbekFilmTV AI bilan suhbatdasiz.
Savol: {text}
Javob:
"""

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 200
        }
    }

    response = requests.post(
        f"https://api-inference.huggingface.co/models/{AI_MODEL}",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        return response.json()[0]["generated_text"]
    else:
        return "⚠️ AI vaqtincha ishlamayapti."

[InlineKeyboardButton(text="🤖 UzbekFilmTV AI", callback_data="ai")]
@dp.callback_query(F.data == "ai")
async def ai_panel(call: CallbackQuery):
    await call.message.answer(
        "🤖 UzbekFilmTV AI ga xush kelibsiz!\n\nSavolingizni yozing..."
    )
      # AI CHAT
    if text.lower().startswith("ai "):
        question = text[3:]
        name = msg.from_user.first_name

        await msg.answer("🤖 AI o‘ylayapti...")

        answer = ask_ai(name, question)

        await msg.answer(answer)
        return
      pip install requests
  


      

  
