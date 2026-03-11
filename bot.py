import json
import os
import random
import logging
from datetime import datetime
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ==================== KONFIGURATSIYA ====================
BOT_USERNAME = "UzbekFilmTV_bot"
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# ADMIN ID lar ro'yxati
ADMIN_IDS = [
    "774440841, 7818576058",
]

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# JSON fayllar yo'li
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
MOVIES_FILE = os.path.join(DATA_DIR, "movies.json")
CHANNELS_FILE = os.path.join(DATA_DIR, "channels.json")
ADMINS_FILE = os.path.join(DATA_DIR, "admins.json")
REQUESTS_FILE = os.path.join(DATA_DIR, "requests.json")

# ==================== JSON YORDAMCHI FUNKSIYALAR ====================
def load_json(filename: str) -> dict:
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(filename: str, data: dict):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_users() -> dict:
    return load_json(USERS_FILE)

def save_users(users: dict):
    save_json(USERS_FILE, users)

def get_movies() -> dict:
    return load_json(MOVIES_FILE)

def save_movies(movies: dict):
    save_json(MOVIES_FILE, movies)

def get_channels() -> dict:
    return load_json(CHANNELS_FILE)

def save_channels(channels: dict):
    save_json(CHANNELS_FILE, channels)

def get_admins() -> dict:
    file_admins = load_json(ADMINS_FILE)
    for admin_id in ADMIN_IDS:
        if admin_id not in file_admins:
            file_admins[admin_id] = {
                "role": "super_admin",
                "added_at": datetime.now().isoformat(),
                "source": "config"
            }
    return file_admins

def save_admins(admins: dict):
    save_json(ADMINS_FILE, admins)

def get_requests() -> dict:
    return load_json(REQUESTS_FILE)

def save_requests(requests: dict):
    save_json(REQUESTS_FILE, requests)

# ==================== FOYDALANUVCHI FUNKSIYALARI ====================
def get_or_create_user(user_id: str, username: str = None, first_name: str = None) -> dict:
    users = get_users()
    if user_id not in users:
        users[user_id] = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "limit": 5,
            "referrals": 0,
            "joined_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "favorites": [],
            "history": [],
            "banned": False
        }
        save_users(users)
    else:
        users[user_id]["last_activity"] = datetime.now().isoformat()
        if username:
            users[user_id]["username"] = username
        if first_name:
            users[user_id]["first_name"] = first_name
        save_users(users)
    return users[user_id]

def is_admin(user_id: str) -> bool:
    if user_id in ADMIN_IDS:
        return True
    admins = get_admins()
    return user_id in admins

def is_super_admin(user_id: str) -> bool:
    return user_id == ADMIN_IDS[0]

def is_banned(user_id: str) -> bool:
    users = get_users()
    return users.get(user_id, {}).get("banned", False)

def check_limit(user_id: str) -> bool:
    users = get_users()
    user = users.get(user_id, {})
    return user.get("limit", 0) > 0

def decrease_limit(user_id: str):
    users = get_users()
    if user_id in users and users[user_id]["limit"] > 0:
        users[user_id]["limit"] -= 1
        save_users(users)

def add_limit(user_id: str, amount: int):
    users = get_users()
    if user_id in users:
        users[user_id]["limit"] += amount
        save_users(users)

def add_referral(referrer_id: str):
    users = get_users()
    if referrer_id in users:
        users[referrer_id]["referrals"] += 1
        users[referrer_id]["limit"] += 5
        save_users(users)

def add_to_history(user_id: str, movie_code: str):
    users = get_users()
    if user_id in users:
        if movie_code not in users[user_id]["history"]:
            users[user_id]["history"].insert(0, movie_code)
            users[user_id]["history"] = users[user_id]["history"][:20]
            save_users(users)

def toggle_favorite(user_id: str, movie_code: str) -> bool:
    users = get_users()
    if user_id in users:
        if movie_code in users[user_id]["favorites"]:
            users[user_id]["favorites"].remove(movie_code)
            save_users(users)
            return False
        else:
            users[user_id]["favorites"].append(movie_code)
            save_users(users)
            return True

def increment_movie_views(movie_code: str):
    movies = get_movies()
    if movie_code in movies:
        movies[movie_code]["views"] = movies[movie_code].get("views", 0) + 1
        save_movies(movies)

def get_trending_movies(limit: int = 10) -> List[tuple]:
    movies = get_movies()
    sorted_movies = sorted(movies.items(), key=lambda x: x[1].get("views", 0), reverse=True)
    return sorted_movies[:limit]

def get_random_movie() -> Optional[tuple]:
    movies = get_movies()
    if not movies:
        return None
    return random.choice(list(movies.items()))

def search_movies(query: str) -> List[tuple]:
    movies = get_movies()
    results = []
    query = query.lower()
    for code, data in movies.items():
        if query in code.lower() or query in data.get("name", "").lower():
            results.append((code, data))
    return results

# ==================== KLAVIATURALAR ====================
def get_main_keyboard(user_id: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🎟 Mening limitim", callback_data="my_limit"),
         InlineKeyboardButton("🎬 Random film", callback_data="random_movie")],
        [InlineKeyboardButton("🔥 Trend filmlar", callback_data="trending"),
         InlineKeyboardButton("🎥 Kino katalog", callback_data="catalog")],
        [InlineKeyboardButton("👥 Do'st taklif qilish", callback_data="referral"),
         InlineKeyboardButton("🆕 Yangi filmlar", callback_data="new_movies")],
        [InlineKeyboardButton("⭐ Mashhur filmlar", callback_data="popular"),
         InlineKeyboardButton("🎭 Janrlar", callback_data="genres")],
        [InlineKeyboardButton("❤️ Sevimlilar", callback_data="favorites"),
         InlineKeyboardButton("📊 Mening statistikam", callback_data="my_stats")]
    ]
    
    if is_admin(str(user_id)):
        buttons.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(buttons)

def get_movie_keyboard(movie_code: str, user_id: str) -> InlineKeyboardMarkup:
    users = get_users()
    is_fav = movie_code in users.get(str(user_id), {}).get("favorites", [])
    fav_text = "❤️ Sevimlidan olib tashlash" if is_fav else "❤️ Sevimliga qo'shish"
    
    buttons = [
        [InlineKeyboardButton("▶️ Keyingi film", callback_data="random_movie"),
         InlineKeyboardButton("🔥 Trend filmlar", callback_data="trending")],
        [InlineKeyboardButton("🎥 Kino katalog", callback_data="catalog"),
         InlineKeyboardButton("🔗 Ulashish", callback_data=f"share_{movie_code}")],
        [InlineKeyboardButton(fav_text, callback_data=f"fav_{movie_code}")]
    ]
    return InlineKeyboardMarkup(buttons)

def get_admin_keyboard(user_id: str = None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("➕ Kino qo'shish", callback_data="add_movie"),
         InlineKeyboardButton("➖ Kino o'chirish", callback_data="delete_movie")],
        [InlineKeyboardButton("✏️ Kino tahrirlash", callback_data="edit_movie"),
         InlineKeyboardButton("🔍 Kino qidirish", callback_data="search_admin")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats"),
         InlineKeyboardButton("🔥 Top filmlar", callback_data="top_movies")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"),
         InlineKeyboardButton("🔒 Majburiy obuna", callback_data="manage_channels")],
        [InlineKeyboardButton("💠 Limit qo'shish", callback_data="add_limit"),
         InlineKeyboardButton("👤 User ban", callback_data="ban_user")],
        [InlineKeyboardButton("♻️ Unban", callback_data="unban_user"),
         InlineKeyboardButton("📦 Backup", callback_data="backup")],
        [InlineKeyboardButton("📥 Import", callback_data="import_data"),
         InlineKeyboardButton("📤 Export", callback_data="export_data")],
        [InlineKeyboardButton("📥 Kino so'rovlari", callback_data="movie_requests")],
        [InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")]
    ]
    
    if user_id and is_super_admin(user_id):
        buttons.insert(-1, [InlineKeyboardButton("👮 Admin qo'shish", callback_data="add_admin"),
                           InlineKeyboardButton("❌ Admin o'chirish", callback_data="remove_admin")])
    
    return InlineKeyboardMarkup(buttons)

def get_genres_keyboard() -> InlineKeyboardMarkup:
    movies = get_movies()
    genres = list(set(m.get("genre", "Noma'lum") for m in movies.values() if m.get("genre")))
    
    buttons = []
    row = []
    for i, genre in enumerate(genres[:10]):
        row.append(InlineKeyboardButton(genre, callback_data=f"genre_{genre}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def get_catalog_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    movies = get_movies()
    movie_list = list(movies.items())
    per_page = 10
    start = page * per_page
    end = start + per_page
    current_movies = movie_list[start:end]
    
    buttons = []
    for code, data in current_movies:
        text = f"{data.get('name', code)} ({code})"
        buttons.append([InlineKeyboardButton(text, callback_data=f"movie_{code}")])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"catalog_{page-1}"))
    if end < len(movie_list):
        nav_buttons.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"catalog_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    channels = get_channels()
    buttons = []
    
    for i, (channel_id, info) in enumerate(channels.items(), 1):
        url = info.get("invite_link", f"https://t.me/{channel_id.replace('@', '')}")
        buttons.append([InlineKeyboardButton(f"📢 Kanal {i}", url=url)])
    
    buttons.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

# ==================== TEKSHIRUV FUNKSIYALARI ====================
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    channels = get_channels()
    if not channels:
        return True
    
    for channel_id in channels:
        try:
            member = await context.bot.get_chat_member(channel_id, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            continue
    return True

# ==================== HANDLERLAR ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    
    if context.args and context.args[0].startswith("ref"):
        referrer_id = context.args[0].replace("ref", "")
        users = get_users()
        if referrer_id in users and referrer_id != user_id and user_id not in users:
            add_referral(referrer_id)
    
    get_or_create_user(user_id, user.username, user.first_name)
    
    if is_banned(user_id):
        await update.message.reply_text("❌ Siz botdan bloklangansiz.")
        return
    
    if not await check_subscription(user.id, context):
        text = f"👋 Xush kelibsiz!\n\nBotdan foydalanish uchun quyidagi kanallarga obuna bo'ling:"
        await update.message.reply_text(text, reply_markup=get_subscription_keyboard())
        return
    
    if is_admin(user_id):
        welcome_text = (
            f"🎬 Assalomu alaykum, {user.first_name}!\n\n"
            f"🎥 @{BOT_USERNAME} ga xush kelibsiz!\n"
            f"👮 Siz admin sifatidasiz!\n\n"
            f"🎟 Sizning limit: Cheksiz\n"
            f"📝 Kino kodini yuboring yoki menyudan tanlang"
        )
    else:
        welcome_text = (
            f"🎬 Assalomu alaykum, {user.first_name}!\n\n"
            f"🎥 @{BOT_USERNAME} ga xush kelibsiz!\n\n"
            f"🎟 Sizning limit: 5 ta kino\n"
            f"📝 Kino kodini yuboring yoki menyudan tanlang"
        )
    
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(user_id))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    text = update.message.text
    
    if is_banned(user_id):
        return
    
    if not await check_subscription(user.id, context):
        await update.message.reply_text("❌ Avval kanallarga obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return
    
    if context.user_data.get("adding_movie"):
        await process_add_movie(update, context)
        return
    
    if context.user_data.get("adding_limit"):
        await process_add_limit(update, context)
        return
    
    if context.user_data.get("banning_user"):
        await process_ban_user(update, context)
        return
    
    if context.user_data.get("adding_channel"):
        await process_add_channel(update, context)
        return
    
    if context.user_data.get("broadcasting"):
        await process_broadcast(update, context)
        return
    
    if context.user_data.get("adding_admin"):
        await process_add_admin(update, context)
        return
    
    movies = get_movies()
    if text in movies:
        await send_movie(update, context, text)
        return
    
    results = search_movies(text)
    if results:
        if len(results) == 1:
            await send_movie(update, context, results[0][0])
        else:
            text_msg = "🔍 Topilgan kinolar:\n\n"
            keyboard = []
            for code, data in results[:10]:
                text_msg += f"🎬 {data.get('name', code)} - `{code}`\n"
                keyboard.append([InlineKeyboardButton(data.get('name', code), callback_data=f"movie_{code}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
            await update.message.reply_text(text_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        similar = random.sample(list(movies.items()), min(5, len(movies))) if movies else []
        text_msg = "❌ Kino topilmadi. Balki quyidagilardan birini izlagandirsiz:\n\n"
        keyboard = []
        for code, data in similar:
            text_msg += f"🎬 {data.get('name', code)} - `{code}`\n"
            keyboard.append([InlineKeyboardButton(data.get('name', code), callback_data=f"movie_{code}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
        await update.message.reply_text(text_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, movie_code: str, query=None):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id) and not check_limit(user_id):
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
        text = (
            "❌ Sizning limitingiz tugadi!\n\n"
            f"👥 Do'stlaringizni taklif qiling va +5 limit oling:\n{ref_link}"
        )
        if query:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return
    
    movies = get_movies()
    if movie_code not in movies:
        return
    
    movie = movies[movie_code]
    
    try:
        await context.bot.forward_message(
            chat_id=update.effective_chat.id,
            from_chat_id=movie["channel_id"],
            message_id=movie["message_id"]
        )
        
        if not is_admin(user_id):
            decrease_limit(user_id)
        
        increment_movie_views(movie_code)
        add_to_history(user_id, movie_code)
        
        if is_admin(user_id):
            caption = "✅ Kino yuborildi!\n👮 Admin rejimi (limit cheksiz)"
        else:
            remaining = get_users()[user_id]["limit"]
            caption = f"✅ Kino yuborildi!\n🎟 Qolgan limit: {remaining}"
        
        if query:
            await query.message.reply_text(caption, reply_markup=get_movie_keyboard(movie_code, user_id))
        else:
            await update.message.reply_text(caption, reply_markup=get_movie_keyboard(movie_code, user_id))
            
    except Exception as e:
        logger.error(f"Error forwarding movie: {e}")
        error_msg = "❌ Kino yuborishda xatolik. Iltimos, keyinroq urinib ko'ring."
        if query:
            await query.answer(error_msg, show_alert=True)
        else:
            await update.message.reply_text(error_msg)

# ==================== CALLBACK HANDLERLAR ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    data = query.data
    
    if is_banned(user_id) and not data.startswith("unban"):
        await query.edit_message_text("❌ Siz botdan bloklangansiz.")
        return
    
    if not await check_subscription(update.effective_user.id, context) and data != "check_sub":
        await query.edit_message_text("❌ Avval kanallarga obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return
    
    try:
        if data == "main_menu":
            await show_main_menu(query, user_id)
        
        elif data == "check_sub":
            if await check_subscription(update.effective_user.id, context):
                await show_main_menu(query, user_id)
            else:
                await query.answer("❌ Hali obuna bo'lmagansiz!", show_alert=True)
        
        elif data == "my_limit":
            await show_limit(query, user_id)
        
        elif data == "random_movie":
            await send_random_movie(query, context, user_id)
        
        elif data == "trending":
            await show_trending(query)
        
        elif data == "catalog":
            await query.edit_message_text("🎥 Kino katalogi:", reply_markup=get_catalog_keyboard(0))
        
        elif data.startswith("catalog_"):
            page = int(data.split("_")[1])
            await query.edit_message_text("🎥 Kino katalogi:", reply_markup=get_catalog_keyboard(page))
        
        elif data == "referral":
            await show_referral(query, user_id)
        
        elif data == "new_movies":
            await show_new_movies(query)
        
        elif data == "popular":
            await show_popular(query)
        
        elif data == "genres":
            await query.edit_message_text("🎭 Janrni tanlang:", reply_markup=get_genres_keyboard())
        
        elif data.startswith("genre_"):
            await show_movies_by_genre(query, data.replace("genre_", ""))
        
        elif data == "favorites":
            await show_favorites(query, user_id)
        
        elif data == "my_stats":
            await show_stats(query, user_id)
        
        elif data.startswith("movie_"):
            movie_code = data.replace("movie_", "")
            await send_movie_by_query(query, context, movie_code, user_id)
        
        elif data.startswith("fav_"):
            movie_code = data.replace("fav_", "")
            await toggle_favorite_movie(query, user_id, movie_code)
        
        elif data.startswith("share_"):
            await share_movie(query, data.replace("share_", ""))
        
        elif data == "admin_panel":
            await show_admin_panel(query, user_id)
        
        elif data == "add_movie":
            await start_add_movie(query, context)
        
        elif data == "delete_movie":
            await start_delete_movie(query)
        
        elif data.startswith("del_movie_"):
            await delete_movie(query, data.replace("del_movie_", ""))
        
        elif data == "stats":
            await show_admin_stats(query)
        
        elif data == "top_movies":
            await show_top_movies(query)
        
        elif data == "broadcast":
            await start_broadcast(query, context)
        
        elif data == "manage_channels":
            await manage_channels(query)
        
        elif data == "add_channel":
            await start_add_channel(query, context)
        
        elif data == "remove_channel":
            await start_remove_channel(query)
        
        elif data.startswith("rem_channel_"):
            await remove_channel(query, data.replace("rem_channel_", ""))
        
        elif data == "add_limit":
            await start_add_limit(query, context)
        
        elif data == "ban_user":
            await start_ban_user(query, context)
        
        elif data == "unban_user":
            await start_unban_user(query)
        
        elif data.startswith("unban_user_"):
            await unban_user(query, data.replace("unban_user_", ""))
        
        elif data == "backup":
            await create_backup(query)
        
        elif data == "export_data":
            await export_data(query)
        
        elif data == "movie_requests":
            await show_movie_requests(query)
        
        elif data == "add_admin":
            await start_add_admin(query, context)
        
        elif data == "remove_admin":
            await start_remove_admin(query)
        
        elif data.startswith("rem_admin_"):
            await remove_admin(query, data.replace("rem_admin_", ""))
            
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await query.answer("❌ Xatolik yuz berdi!", show_alert=True)

# ==================== YORDAMCHI FUNKSIYALAR ====================
async def show_main_menu(query, user_id: str):
    text = (
        "🎬 Asosiy menyu\n\n"
        "🎟 Mening limitim - Qolgan kino limitingiz\n"
        "🎬 Random film - Tasodifiy kino\n"
        "🔥 Trend filmlar - Eng ko'p ko'rilganlar\n"
        "🎥 Kino katalog - Barcha kinolar\n"
        "👥 Do'st taklif qilish - Referal link\n"
        "🆕 Yangi filmlar - So'nggi qo'shilganlar\n"
        "⭐ Mashhur filmlar - Top reyting\n"
        "🎭 Janrlar - Janr bo'yicha\n"
        "❤️ Sevimlilar - Saqlangan kinolar\n"
        "📊 Mening statistikam - Shaxsiy statistika"
    )
    await query.edit_message_text(text, reply_markup=get_main_keyboard(user_id))

async def show_limit(query, user_id: str):
    users = get_users()
    user = users.get(user_id, {})
    
    if is_admin(user_id):
        text = (
            "🎟 Sizning limitingiz: ♾️ Cheksiz (Admin)\n\n"
            "👮 Siz admin sifatidasiz, limit cheklanmagan!"
        )
    else:
        limit = user.get("limit", 0)
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
        
        text = (
            f"🎟 Sizning limitingiz: {limit} ta kino\n\n"
            f"👥 Har bir referal uchun +5 limit:\n{ref_link}"
        )
    
    await query.edit_message_text(text, reply_markup=get_main_keyboard(user_id))

async def send_random_movie(query, context, user_id: str):
    movie = get_random_movie()
    if not movie:
        await query.answer("❌ Hozircha kinolar mavjud emas!", show_alert=True)
        return
    
    await send_movie_by_query(query, context, movie[0], user_id)

async def send_movie_by_query(query, context, movie_code: str, user_id: str):
    if not is_admin(user_id) and not check_limit(user_id):
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
        text = (
            "❌ Sizning limitingiz tugadi!\n\n"
            f"👥 Do'stlaringizni taklif qiling va +5 limit oling:\n{ref_link}"
        )
        await query.edit_message_text(text)
        return
    
    movies = get_movies()
    if movie_code not in movies:
        await query.answer("❌ Kino topilmadi!", show_alert=True)
        return
    
    movie = movies[movie_code]
    
    try:
        await context.bot.forward_message(
            chat_id=query.message.chat_id,
            from_chat_id=movie["channel_id"],
            message_id=movie["message_id"]
        )
        
        if not is_admin(user_id):
            decrease_limit(user_id)
        
        increment_movie_views(movie_code)
        add_to_history(user_id, movie_code)
        
        if is_admin(user_id):
            caption = f"🎬 {movie.get('name', movie_code)}\n✅ Kino yuborildi!\n👮 Admin rejimi"
        else:
            remaining = get_users()[user_id]["limit"]
            caption = f"🎬 {movie.get('name', movie_code)}\n✅ Kino yuborildi!\n🎟 Qolgan limit: {remaining}"
        
        await query.message.reply_text(caption, reply_markup=get_movie_keyboard(movie_code, user_id))
        
    except Exception as e:
        logger.error(f"Error forwarding movie: {e}")
        await query.answer("❌ Kino yuborishda xatolik!", show_alert=True)

async def show_trending(query):
    trending = get_trending_movies(10)
    if not trending:
        await query.answer("❌ Hozircha kinolar mavjud emas!", show_alert=True)
        return
    
    text = "🔥 Top 10 eng ko'p ko'rilgan filmlar:\n\n"
    keyboard = []
    
    for i, (code, data) in enumerate(trending, 1):
        views = data.get("views", 0)
        text += f"{i}. {data.get('name', code)} - {views} marta\n"
        keyboard.append([InlineKeyboardButton(f"{i}. {data.get('name', code)}", callback_data=f"movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_referral(query, user_id: str):
    users = get_users()
    ref_count = users.get(user_id, {}).get("referrals", 0)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    
    text = (
        f"👥 Do'stlaringizni taklif qiling!\n\n"
        f"📊 Sizning referallaringiz: {ref_count}\n"
        f"🎁 Har bir referal uchun: +5 limit\n\n"
        f"🔗 Sizning linkingiz:\n`{ref_link}`"
    )
    
    share_url = f"https://t.me/share/url?url={ref_link}&text=🎬%20Zo'r%20kino%20bot!"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Ulashish", url=share_url)],
        [InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def show_new_movies(query):
    movies = get_movies()
    sorted_movies = sorted(movies.items(), key=lambda x: x[1].get("added_at", ""), reverse=True)[:10]
    
    if not sorted_movies:
        await query.answer("❌ Hozircha kinolar mavjud emas!", show_alert=True)
        return
    
    text = "🆕 So'nggi qo'shilgan filmlar:\n\n"
    keyboard = []
    
    for code, data in sorted_movies:
        text += f"🎬 {data.get('name', code)} - `{code}`\n"
        keyboard.append([InlineKeyboardButton(data.get('name', code), callback_data=f"movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_popular(query):
    await show_trending(query)

async def show_movies_by_genre(query, genre: str):
    movies = get_movies()
    genre_movies = [(c, d) for c, d in movies.items() if d.get("genre") == genre]
    
    if not genre_movies:
        await query.answer("❌ Bu janrda kinolar topilmadi!", show_alert=True)
        return
    
    text = f"🎭 {genre} janridagi filmlar:\n\n"
    keyboard = []
    
    for code, data in genre_movies[:20]:
        text += f"🎬 {data.get('name', code)} - `{code}`\n"
        keyboard.append([InlineKeyboardButton(data.get('name', code), callback_data=f"movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="genres")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_favorites(query, user_id: str):
    users = get_users()
    favorites = users.get(user_id, {}).get("favorites", [])
    movies = get_movies()
    
    if not favorites:
        await query.edit_message_text(
            "❤️ Sevimli filmlaringiz yo'q\n\nKino katalogidan tanlang!",
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    text = "❤️ Sevimli filmlaringiz:\n\n"
    keyboard = []
    
    for code in favorites[:20]:
        if code in movies:
            data = movies[code]
            text += f"🎬 {data.get('name', code)} - `{code}`\n"
            keyboard.append([InlineKeyboardButton(data.get('name', code), callback_data=f"movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_stats(query, user_id: str):
    users = get_users()
    user = users.get(user_id, {})
    movies = get_movies()
    
    total_watched = len(user.get("history", []))
    favorites = len(user.get("favorites", []))
    referrals = user.get("referrals", 0)
    
    if is_admin(user_id):
        role = "👮 Admin"
        limit_text = "♾️ Cheksiz"
    else:
        role = "👤 Foydalanuvchi"
        limit_text = str(user.get('limit', 0))
    
    text = (
        f"📊 Sizning statistikangiz\n\n"
        f"🎬 Ko'rilgan kinolar: {total_watched}\n"
        f"❤️ Sevimli filmlar: {favorites}\n"
        f"👥 Taklif qilingan do'stlar: {referrals}\n"
        f"🎟 Joriy limit: {limit_text}\n"
        f"🎭 Status: {role}\n"
        f"📅 Qo'shilgan sana: {user.get('joined_at', 'Noma\'lum')[:10]}"
    )
    
    await query.edit_message_text(text, reply_markup=get_main_keyboard(user_id))

async def toggle_favorite_movie(query, user_id: str, movie_code: str):
    is_added = toggle_favorite(user_id, movie_code)
    action = "qo'shildi" if is_added else "olib tashlandi"
    
    await query.answer(f"❤️ Sevimlilarga {action}!", show_alert=True)
    await query.edit_message_reply_markup(reply_markup=get_movie_keyboard(movie_code, user_id))

async def share_movie(query, movie_code: str):
    movies = get_movies()
    if movie_code not in movies:
        await query.answer("❌ Kino topilmadi!", show_alert=True)
        return
    
    movie = movies[movie_code]
    share_text = f"🎬 {movie.get('name', movie_code)}\n\n🎥 Kino bot: @{BOT_USERNAME}\nKod: {movie_code}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Do'stlarga yuborish", url=f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}&text={share_text}")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data=f"movie_{movie_code}")]
    ])
    
    await query.edit_message_text(share_text, reply_markup=keyboard)

# ==================== ADMIN FUNKSIYALARI ====================
async def show_admin_panel(query, user_id: str):
    if not is_admin(user_id):
        await query.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    
    total_users = len(get_users())
    total_movies = len(get_movies())
    
    if is_super_admin(user_id):
        role = "👑 Super Admin"
    else:
        role = "👮 Admin"
    
    text = (
        f"🛠 Admin panel\n"
        f"🎭 Sizning status: {role}\n\n"
        f"👥 Foydalanuvchilar: {total_users}\n"
        f"🎬 Kinolar: {total_movies}\n"
        f"📢 Majburiy kanallar: {len(get_channels())}"
    )
    
    await query.edit_message_text(text, reply_markup=get_admin_keyboard(user_id))

async def start_add_movie(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["adding_movie"] = {"step": "forward"}
    await query.edit_message_text(
        "➕ Kino qo'shish\n\n"
        "1️⃣ Kanaldan film/video/document forward qiling\n"
        "2️⃣ Kod kiriting (masalan: uzb001)\n"
        "3️⃣ Film nomini yozing\n\n"
        "❌ Bekor qilish: /cancel"
    )

async def process_add_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data.get("adding_movie", {})
    step = user_data.get("step")
    
    if update.message.forward_from_chat:
        user_data["channel_id"] = update.message.forward_from_chat.id
        user_data["message_id"] = update.message.forward_from_message_id
        user_data["step"] = "code"
        
        await update.message.reply_text(
            "✅ Saqlandi! Endi kod kiriting (masalan: uzb001, film123):"
        )
    
    elif step == "code":
        code = update.message.text.strip().lower()
        if not code:
            await update.message.reply_text("❌ Kod bo'sh bo'lishi mumkin emas!")
            return
        
        movies = get_movies()
        if code in movies:
            await update.message.reply_text("❌ Bu kod allaqachon mavjud! Boshqa kod kiriting:")
            return
        
        user_data["code"] = code
        user_data["step"] = "name"
        await update.message.reply_text("✅ Kod saqlandi! Endi film nomini to'liq yozing:")
    
    elif step == "name":
        name = update.message.text.strip()
        user_data["name"] = name
        user_data["step"] = "genre"
        await update.message.reply_text(
            "✅ Nom saqlandi! Janr kiriting (ixtiyoriy, yo'q bo'lsa 'skip' deb yozing):"
        )
    
    elif step == "genre":
        genre = update.message.text.strip()
        if genre.lower() == "skip":
            genre = ""
        
        movies = get_movies()
        movies[user_data["code"]] = {
            "code": user_data["code"],
            "name": user_data["name"],
            "genre": genre,
            "channel_id": user_data["channel_id"],
            "message_id": user_data["message_id"],
            "views": 0,
            "added_at": datetime.now().isoformat(),
            "added_by": str(update.effective_user.id)
        }
        save_movies(movies)
        
        del context.user_data["adding_movie"]
        
        genre_text = genre if genre else "Noma'lum"
        
        await update.message.reply_text(
            f"✅ Kino muvaffaqiyatli qo'shildi!\n\n"
            f"🎬 Kod: {user_data['code']}\n"
            f"📝 Nomi: {user_data['name']}\n"
            f"🎭 Janr: {genre_text}",
            reply_markup=get_admin_keyboard(str(update.effective_user.id))
        )

async def start_delete_movie(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    movies = get_movies()
    if not movies:
        await query.edit_message_text("❌ Kinolar mavjud emas!", reply_markup=get_admin_keyboard(str(query.from_user.id)))
        return
    
    keyboard = []
    for code, data in list(movies.items())[:20]:
        keyboard.append([InlineKeyboardButton(f"{data.get('name', code)} ({code})", callback_data=f"del_movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    await query.edit_message_text("➖ O'chirish uchun kinoni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_movie(query, movie_code: str):
    movies = get_movies()
    if movie_code in movies:
        del movies[movie_code]
        save_movies(movies)
        await query.answer("✅ Kino o'chirildi!", show_alert=True)
    
    await start_delete_movie(query)

async def show_admin_stats(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    users = get_users()
    movies = get_movies()
    
    total_users = len(users)
    total_movies = len(movies)
    banned_users = sum(1 for u in users.values() if u.get("banned"))
    total_views = sum(m.get("views", 0) for m in movies.values())
    
    text = (
        f"📊 Bot statistikasi\n\n"
        f"👥 Jami foydalanuvchilar: {total_users}\n"
        f"🎬 Jami kinolar: {total_movies}\n"
        f"👁 Jami ko'rilishlar: {total_views}\n"
        f"🚫 Bloklangan foydalanuvchilar: {banned_users}\n"
        f"📢 Majburiy kanallar: {len(get_channels())}\n"
        f"👮 Adminlar: {len(get_admins())}"
    )
    
    await query.edit_message_text(text, reply_markup=get_admin_keyboard(str(query.from_user.id)))

async def show_top_movies(query):
    await show_trending(query)

async def start_broadcast(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["broadcasting"] = True
    await query.edit_message_text(
        "📢 Broadcast xabar\n\n"
        "Yuboriladigan xabarni kiriting:\n"
        "❌ Bekor qilish: /cancel"
    )

async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("broadcasting"):
        return
    
    del context.user_data["broadcasting"]
    
    users = get_users()
    sent = 0
    failed = 0
    
    status_msg = await update.message.reply_text("📤 Yuborilmoqda...")
    
    for user_id in users:
        try:
            await update.message.copy(chat_id=int(user_id))
            sent += 1
        except Exception:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ Broadcast yakunlandi!\n\n"
        f"✓ Muvaffaqiyatli: {sent}\n"
        f"✗ Xatolik: {failed}"
    )

async def manage_channels(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    channels = get_channels()
    
    text = "🔒 Majburiy obuna kanallari:\n\n"
    keyboard = []
    
    for i, (ch_id, info) in enumerate(channels.items(), 1):
        text += f"{i}. {info.get('name', ch_id)}\n"
        keyboard.append([InlineKeyboardButton(f"❌ {info.get('name', ch_id)}", callback_data=f"rem_channel_{ch_id}")])
    
    keyboard.extend([
        [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]
    ])
    
    await query.edit_message_text(text or "Kanallar mavjud emas", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_add_channel(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["adding_channel"] = True
    await query.edit_message_text(
        "➕ Kanal qo'shish\n\n"
        "Kanal ID sini yuboring (masalan: -1001234567890):\n"
        "❌ Bekor qilish: /cancel"
    )

async def process_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("adding_channel"):
        return
    
    channel_id = update.message.text.strip()
    
    try:
        chat = await context.bot.get_chat(channel_id)
        channels = get_channels()
        channels[str(chat.id)] = {
            "name": chat.title,
            "invite_link": chat.invite_link or (f"https://t.me/{chat.username}" if chat.username else "")
        }
        save_channels(channels)
        
        del context.user_data["adding_channel"]
        await update.message.reply_text(f"✅ Kanal qo'shildi: {chat.title}")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {str(e)}\n\nTo'g'ri kanal ID kiriting!")

async def start_remove_channel(query):
    await manage_channels(query)

async def remove_channel(query, channel_id: str):
    channels = get_channels()
    if channel_id in channels:
        del channels[channel_id]
        save_channels(channels)
        await query.answer("✅ Kanal o'chirildi!", show_alert=True)
    
    await manage_channels(query)

async def start_add_limit(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["adding_limit"] = {"step": "user"}
    await query.edit_message_text(
        "💠 Limit qo'shish\n\n"
        "Foydalanuvchi ID sini kiriting:\n"
        "❌ Bekor qilish: /cancel"
    )

async def process_add_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data.get("adding_limit", {})
    step = user_data.get("step")
    
    if step == "user":
        user_id = update.message.text.strip()
        users = get_users()
        
        if user_id not in users:
            await update.message.reply_text("❌ Foydalanuvchi topilmadi!")
            return
        
        context.user_data["adding_limit"]["target_user"] = user_id
        context.user_data["adding_limit"]["step"] = "amount"
        await update.message.reply_text("Enda qo'shiladigan limit miqdorini kiriting:")
    
    elif step == "amount":
        try:
            amount = int(update.message.text.strip())
            target_user = context.user_data["adding_limit"]["target_user"]
            add_limit(target_user, amount)
            
            del context.user_data["adding_limit"]
            await update.message.reply_text(f"✅ {target_user} ga {amount} limit qo'shildi!")
        except ValueError:
            await update.message.reply_text("❌ Raqam kiriting!")

async def start_ban_user(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["banning_user"] = True
    await query.edit_message_text(
        "👤 User ban qilish\n\n"
        "Foydalanuvchi ID sini kiriting:\n"
        "❌ Bekor qilish: /cancel"
    )

async def process_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("banning_user"):
        return
    
    user_id = update.message.text.strip()
    users = get_users()
    
    if user_id not in users:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi!")
        return
    
    if is_admin(user_id):
        await update.message.reply_text("❌ Adminni ban qilish mumkin emas!")
        del context.user_data["banning_user"]
        return
    
    users[user_id]["banned"] = True
    save_users(users)
    
    del context.user_data["banning_user"]
    await update.message.reply_text(f"✅ {user_id} bloklandi!")

async def start_unban_user(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    users = get_users()
    banned = [(uid, u) for uid, u in users.items() if u.get("banned")]
    
    if not banned:
        await query.edit_message_text("Bloklangan foydalanuvchilar yo'q!", reply_markup=get_admin_keyboard(str(query.from_user.id)))
        return
    
    keyboard = []
    for uid, u in banned[:20]:
        name = u.get("first_name", "Noma'lum")
        keyboard.append([InlineKeyboardButton(f"♻️ {name} ({uid})", callback_data=f"unban_user_{uid}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    await query.edit_message_text("Blokdan ochish uchun tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

async def unban_user(query, user_id: str):
    users = get_users()
    if user_id in users:
        users[user_id]["banned"] = False
        save_users(users)
        await query.answer("✅ Foydalanuvchi blokdan chiqarildi!", show_alert=True)
    
    await start_unban_user(query)

async def create_backup(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    import shutil
    from datetime import datetime
    
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copytree(DATA_DIR, backup_dir)
    
    await query.answer(f"✅ Backup yaratildi: {backup_dir}", show_alert=True)

async def export_data(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    for filename in [USERS_FILE, MOVIES_FILE, CHANNELS_FILE]:
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                await query.message.reply_document(f)
    
    await query.answer("✅ Eksport yakunlandi!", show_alert=True)

async def show_movie_requests(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    requests = get_requests()
    
    if not requests:
        await query.edit_message_text("So'rovlar yo'q!", reply_markup=get_admin_keyboard(str(query.from_user.id)))
        return
    
    text = "📥 Kino so'rovlari:\n\n"
    for req_id, req in list(requests.items())[:10]:
        text += f"👤 {req.get('user', 'Noma\'lum')}: {req.get('text', '')}\n"
        text += f"📅 {req.get('date', 'Noma\'lum')}\n\n"
    
    await query.edit_message_text(text, reply_markup=get_admin_keyboard(str(query.from_user.id)))

# ==================== SUPER ADMIN FUNKSIYALARI ====================
async def start_add_admin(query, context):
    if not is_super_admin(str(query.from_user.id)):
        await query.answer("❌ Faqat super admin qo'sha oladi!", show_alert=True)
        return
    
    context.user_data["adding_admin"] = True
    await query.edit_message_text(
        "👮 Admin qo'shish\n\n"
        "Yangi admin ID sini kiriting:\n"
        "❌ Bekor qilish: /cancel"
    )

async def process_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("adding_admin"):
        return
    
    new_admin_id = update.message.text.strip()
    
    if new_admin_id == str(update.effective_user.id):
        await update.message.reply_text("❌ O'zingizni qo'sha olmaysiz!")
        del context.user_data["adding_admin"]
        return
    
    admins = get_admins()
    
    if new_admin_id in admins:
        await update.message.reply_text("❌ Bu foydalanuvchi allaqachon admin!")
        del context.user_data["adding_admin"]
        return
    
    admins[new_admin_id] = {
        "role": "admin",
        "added_at": datetime.now().isoformat(),
        "added_by": str(update.effective_user.id),
        "source": "manual"
    }
    save_admins(admins)
    
    del context.user_data["adding_admin"]
    await update.message.reply_text(f"✅ {new_admin_id} admin qilindi!")

async def start_remove_admin(query):
    if not is_super_admin(str(query.from_user.id)):
        await query.answer("❌ Faqat super admin o'chira oladi!", show_alert=True)
        return
    
    admins = get_admins()
    
    removable_admins = [(aid, a) for aid, a in admins.items() 
                       if a.get("source") == "manual" and aid != str(query.from_user.id)]
    
    if not removable_admins:
        await query.edit_message_text("O'chiriladigan adminlar yo'q!", reply_markup=get_admin_keyboard(str(query.from_user.id)))
        return
    
    keyboard = []
    for aid, a in removable_admins:
        name = a.get("name", "Noma'lum")
        keyboard.append([InlineKeyboardButton(f"❌ {name} ({aid})", callback_data=f"rem_admin_{aid}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    await query.edit_message_text("O'chirish uchun adminni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

async def remove_admin(query, admin_id: str):
    if not is_super_admin(str(query.from_user.id)):
        return
    
    admins = get_admins()
    if admin_id in admins and admins[admin_id].get("source") == "manual":
        del admins[admin_id]
        save_admins(admins)
        await query.answer("✅ Admin o'chirildi!", show_alert=True)
    
    await start_remove_admin(query)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi!", reply_markup=get_main_keyboard(str(update.effective_user.id)))

# ==================== ASOSIY FUNKSIYA ====================
def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Iltimos, BOT_TOKEN ni kodga qo'shing!")
        return
    
    if not ADMIN_IDS or ADMIN_IDS[0] == "123456789":
        print("⚠️ WARNING: Iltimos, ADMIN_IDS ni o'zgartiring!")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print(f"✅ @{BOT_USERNAME} bot ishga tushdi...")
    print(f"👮 Adminlar: {', '.join(ADMIN_IDS)}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
