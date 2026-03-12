from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_users, get_movies, get_channels
from config import ADMIN_IDS

# ========== ESKI (5-10 qatorlar) ==========
def is_admin(user_id: str) -> bool:
    return user_id in ADMIN_IDS

def is_super_admin(user_id: str) -> bool:
    return ADMIN_IDS and user_id == ADMIN_IDS[0]

# ========== YANGI (5-26 qatorlar) ==========
def is_admin(user_id: str) -> bool:
    """Admin tekshiruvi - config VA database'dan"""
    # 1. config.py dagi super adminlar
    if user_id in ADMIN_IDS:
        return True
    
    # 2. database'dagi qo'shilgan adminlar
    try:
        admins = get_admins()
        if user_id in admins:
            return True
    except Exception as e:
        print(f"is_admin xato: {e}")
    
    return False

def is_super_admin(user_id: str) -> bool:
    """Faqat config.py dagi birinchi admin"""
    return ADMIN_IDS and user_id == ADMIN_IDS[0]


def is_super_admin(user_id: str) -> bool:
    return ADMIN_IDS and user_id == ADMIN_IDS[0]

def get_main_keyboard(user_id: str) -> InlineKeyboardMarkup:
    """Asosiy menyu - Zamonaviy dizayn"""
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
    fav_text = "💔 Olib tashlash" if is_fav else "❤️ Saqlash"
    fav_data = f"remove_fav_{movie_code}" if is_fav else f"add_fav_{movie_code}"
    
    buttons = [
        [InlineKeyboardButton("▶️ Keyingi film", callback_data="random_movie"),
         InlineKeyboardButton("🔥 Trend", callback_data="trending")],
        [InlineKeyboardButton("🎥 Katalog", callback_data="catalog"),
         InlineKeyboardButton("🔗 Ulashish", callback_data=f"share_{movie_code}")],
        [InlineKeyboardButton(f"{fav_text}", callback_data=f"fav_{movie_code}")],
        [InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(buttons)

def get_admin_keyboard(user_id: str = None) -> InlineKeyboardMarkup:
    """Admin panel - Super Admin uchun maxsus"""
    
    # Asosiy admin tugmalari
    buttons = [
        [InlineKeyboardButton("➕ Kino qo'shish", callback_data="add_movie"),
         InlineKeyboardButton("➖ Kino o'chirish", callback_data="delete_movie")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats"),
         InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("🔒 Majburiy obuna", callback_data="manage_channels"),
         InlineKeyboardButton("💠 Limit qo'shish", callback_data="add_limit")],
        [InlineKeyboardButton("👤 Ban", callback_data="ban_user"),
         InlineKeyboardButton("♻️ Unban", callback_data="unban_user")],
        [InlineKeyboardButton("📦 Backup", callback_data="backup"),
         InlineKeyboardButton("📤 Export", callback_data="export_data")],
    ]
    
    # Super Admin uchun qo'shimcha tugmalar
    if user_id and is_super_admin(user_id):
        buttons.append([
            InlineKeyboardButton("👑 Admin qo'shish", callback_data="add_admin"),
            InlineKeyboardButton("❌ Admin o'chirish", callback_data="remove_admin")
        ])
    
    # Orqaga tugmasi alohida qatorda
    buttons.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(buttons)

def get_genres_keyboard() -> InlineKeyboardMarkup:
    """Janrlar - Chiroyli dizayn"""
    movies = get_movies()
    genres = list(set(m.get("genre", "🎬 Boshqa") for m in movies.values() if m.get("genre")))
    
    # Emoji tanlash
    def get_emoji(genre):
        genre = genre.lower()
        if "drama" in genre:
            return "🎭"
        elif "komed" in genre or "komediya" in genre:
            return "😂"
        elif "romant" in genre or "sevgi" in genre:
            return "💕"
        elif "action" in genre or "jangari" in genre:
            return "🔥"
        elif "sarguzasht" in genre:
            return "🗺"
        elif "tarix" in genre or "tarixiy" in genre:
            return "🏛"
        elif "qo'rqinchli" in genre or "ujas" in genre:
            return "👻"
        else:
            return "🎬"
    
    buttons = []
    row = []
    for genre in sorted(genres)[:12]:  # 12 ta janr
        emoji = get_emoji(genre)
        row.append(InlineKeyboardButton(f"{emoji} {genre}", callback_data=f"genre_{genre}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def get_catalog_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """Kino katalogi - Sahifalash"""
    movies = get_movies()
    movie_list = list(movies.items())
    per_page = 10
    total_pages = (len(movie_list) + per_page - 1) // per_page
    
    start = page * per_page
    end = start + per_page
    current_movies = movie_list[start:end]
    
    buttons = []
    
    # Kino tugmalari
    for code, data in current_movies:
        name = data.get('name', code)
        views = data.get('views', 0)
        # Qisqa nom
        short_name = name[:18] + "..." if len(name) > 18 else name
        text = f"🎬 {short_name} ({code}) 👁{views}"
        buttons.append([InlineKeyboardButton(text, callback_data=f"movie_{code}")])
    
    # Navigatsiya tugmalari
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"catalog_{page-1}"))
    
    # Sahifa raqami
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="catalog_page"))
    
    if end < len(movie_list):
        nav_buttons.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"catalog_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Majburiy obuna - Chiroyli"""
    channels = get_channels()
    buttons = []
    
    if not channels:
        buttons.append([InlineKeyboardButton("📭 Kanallar mavjud emas", callback_data="no_channels")])
    else:
        for i, (channel_id, info) in enumerate(channels.items(), 1):
            name = info.get("name", f"Kanal {i}")
            url = info.get("invite_link", "")
            
            # URL ni aniqlash
            if not url:
                if channel_id.startswith("@"):
                    url = f"https://t.me/{channel_id[1:]}"
                elif channel_id.startswith("-100"):
                    # Kanal ID dan username olish mumkin emas, shunchaki link
                    url = f"https://t.me/c/{channel_id.replace('-100', '')}"
            
            buttons.append([InlineKeyboardButton(f"📢 {name}", url=url if url else "https://t.me")])
    
    buttons.append([InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

def get_channels_keyboard() -> InlineKeyboardMarkup:
    """Kanallar boshqaruvi"""
    channels = get_channels()
    buttons = []
    
    if not channels:
        buttons.append([InlineKeyboardButton("📭 Kanallar yo'q", callback_data="no_action")])
    else:
        for ch_id, info in channels.items():
            name = info.get('name', 'Noma\'lum kanal')[:25]
            buttons.append([InlineKeyboardButton(f"❌ {name}", callback_data=f"rem_channel_{ch_id}")])
    
    buttons.append([InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_channel")])
    buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)
