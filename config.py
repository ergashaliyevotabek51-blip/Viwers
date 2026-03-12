from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_users, get_movies, get_channels
from config import ADMIN_IDS

def is_admin(user_id: str) -> bool:
    return user_id in ADMIN_IDS

def is_super_admin(user_id: str) -> bool:
    return ADMIN_IDS and user_id == ADMIN_IDS[0]

def get_main_keyboard(user_id: str) -> InlineKeyboardMarkup:
    """Asosiy menyu - chiroyli dizayn"""
    buttons = [
        [InlineKeyboardButton("🎟 Мening limitim", callback_data="my_limit"),
         InlineKeyboardButton("🎬 Random film", callback_data="random_movie")],
        [InlineKeyboardButton("🔥 Trend filmlar", callback_data="trending"),
         InlineKeyboardButton("🎥 Kino katalog", callback_data="catalog")],
        [InlineKeyboardButton("👥 Do'stlarni taklif qilish", callback_data="referral")],
        [InlineKeyboardButton("🆕 Yangi filmlar", callback_data="new_movies"),
         InlineKeyboardButton("⭐ Mashhur filmlar", callback_data="popular")],
        [InlineKeyboardButton("🎭 Janrlar", callback_data="genres"),
         InlineKeyboardButton("❤️ Sevimlilar", callback_data="favorites")],
        [InlineKeyboardButton("📊 Mening statistikam", callback_data="my_stats")]
    ]
    
    if is_admin(user_id):
        buttons.append([InlineKeyboardButton("🛠 Admin panel", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(buttons)

def get_movie_keyboard(movie_code: str, user_id: str) -> InlineKeyboardMarkup:
    """Kino yuborilganda chiqqan tugmalar"""
    users = get_users()
    is_fav = movie_code in users.get(user_id, {}).get("favorites", [])
    fav_text = "❤️ Sevimlidan olib tashlash" if is_fav else "❤️ Sevimliga qo'shish"
    fav_emoji = "💔" if is_fav else "❤️"
    
    buttons = [
        [InlineKeyboardButton("▶️ Keyingi film", callback_data="random_movie"),
         InlineKeyboardButton("🔥 Trend filmlar", callback_data="trending")],
        [InlineKeyboardButton("🎥 Kino katalog", callback_data="catalog"),
         InlineKeyboardButton("🔗 Ulashish", callback_data=f"share_{movie_code}")],
        [InlineKeyboardButton(f"{fav_emoji} {fav_text}", callback_data=f"fav_{movie_code}")]
    ]
    return InlineKeyboardMarkup(buttons)

def get_admin_keyboard(user_id: str = None) -> InlineKeyboardMarkup:
    """Admin panel"""
    buttons = [
        [InlineKeyboardButton("➕ Kino qo'shish", callback_data="add_movie"),
         InlineKeyboardButton("➖ Kino o'chirish", callback_data="delete_movie")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats"),
         InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("🔒 Majburiy obuna", callback_data="manage_channels"),
         InlineKeyboardButton("💠 Limit qo'shish", callback_data="add_limit")],
        [InlineKeyboardButton("👤 User ban", callback_data="ban_user"),
         InlineKeyboardButton("♻️ Unban", callback_data="unban_user")],
        [InlineKeyboardButton("📦 Backup", callback_data="backup"),
         InlineKeyboardButton("📤 Export", callback_data="export_data")],
        [InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")]
    ]
    
    if user_id and is_super_admin(user_id):
        buttons.insert(-1, [InlineKeyboardButton("👮 Admin qo'shish", callback_data="add_admin"),
                           InlineKeyboardButton("❌ Admin o'chirish", callback_data="remove_admin")])
    
    return InlineKeyboardMarkup(buttons)

def get_genres_keyboard() -> InlineKeyboardMarkup:
    """Janrlar"""
    movies = get_movies()
    genres = list(set(m.get("genre", "🎬 Boshqa") for m in movies.values() if m.get("genre")))
    
    buttons = []
    row = []
    for genre in genres[:10]:
        emoji = "🎭" if "drama" in genre.lower() else "😂" if "komed" in genre.lower() else "💕" if "romant" in genre.lower() else "🔥" if "action" in genre.lower() else "🎬"
        row.append(InlineKeyboardButton(f"{emoji} {genre}", callback_data=f"genre_{genre}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def get_catalog_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """Kino katalogi"""
    movies = get_movies()
    movie_list = list(movies.items())
    per_page = 10
    start = page * per_page
    end = start + per_page
    current_movies = movie_list[start:end]
    
    buttons = []
    for code, data in current_movies:
        name = data.get('name', code)
        views = data.get('views', 0)
        text = f"🎬 {name[:20]}{'...' if len(name) > 20 else ''} ({code}) 👁{views}"
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
    """Majburiy obuna"""
    channels = get_channels()
    buttons = []
    
    for i, (channel_id, info) in enumerate(channels.items(), 1):
        url = info.get("invite_link", "")
        if not url and channel_id.startswith("@"):
            url = f"https://t.me/{channel_id[1:]}"
        elif not url:
            url = f"https://t.me/c/{channel_id.replace('-100', '')}"
        buttons.append([InlineKeyboardButton(f"📢 {info.get('name', f'Kanal {i}')}", url=url)])
    
    buttons.append([InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

def get_channels_keyboard() -> InlineKeyboardMarkup:
    """Kanallar boshqaruvi"""
    channels = get_channels()
    buttons = []
    
    for ch_id, info in channels.items():
        buttons.append([InlineKeyboardButton(f"❌ {info.get('name', ch_id)}", callback_data=f"rem_channel_{ch_id}")])
    
    buttons.append([InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_channel")])
    buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)
