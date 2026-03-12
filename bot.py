import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Config import - xato bo'lsa ham davom etamiz
try:
    from config import BOT_TOKEN, BOT_USERNAME, ADMIN_IDS
except Exception as e:
    print(f"Config import xato: {e}")
    BOT_TOKEN = ""
    BOT_USERNAME = "UzbekFilmTV_bot"
    ADMIN_IDS = []

# Qolgan importlar
try:
    from database import get_users, get_movies
    from users import (
        get_or_create_user, is_admin, is_banned, is_super_admin,
        check_limit, decrease_limit, add_referral, add_to_history,
        toggle_favorite, add_limit, ban_user, unban_user
    )
    from movies import (
        get_random_movie, get_trending_movies, search_movies,
        get_movies_by_genre, increment_movie_views, delete_movie
    )
    from subscription import check_subscription
    from utils import (
        get_main_keyboard, get_movie_keyboard, get_admin_keyboard,
        get_genres_keyboard, get_catalog_keyboard, get_subscription_keyboard,
        get_channels_keyboard
    )
    from admin import (
        show_admin_panel, start_add_movie, process_add_movie,
        start_delete_movie, delete_movie as admin_delete_movie,
        show_stats, start_broadcast, process_broadcast,
        manage_channels, start_add_channel, process_add_channel,
        remove_channel_handler, start_add_limit, process_add_limit,
        start_ban_user, process_ban_user, start_unban_user,
        unban_user_handler, create_backup, export_data,
        start_add_admin, process_add_admin, start_remove_admin,
        remove_admin_handler
    )
except Exception as e:
    print(f"Modul import xato: {e}")
    raise

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== HANDLERLAR ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = str(user.id)
        
        # Referal tekshiruvi
        if context.args and len(context.args) > 0 and context.args[0].startswith("ref"):
            referrer_id = context.args[0].replace("ref", "")
            users = get_users()
            if referrer_id in users and referrer_id != user_id and user_id not in users:
                add_referral(referrer_id)
        
        # Foydalanuvchi yaratish
        get_or_create_user(user_id, user.username, user.first_name)
        
        # Ban tekshiruvi
        if is_banned(user_id):
            await update.message.reply_text("Siz botdan bloklangansiz.")
            return
        
        # Majburiy obuna tekshiruvi
        if not await check_subscription(user.id, context):
            await update.message.reply_text(
                "Xush kelibsiz! Botdan foydalanish uchun kanallarga obuna bo'ling:",
                reply_markup=get_subscription_keyboard()
            )
            return
        
        # Xush kelibsiz xabari
        if is_admin(user_id):
            text = f"Salom {user.first_name}! Siz admin sifatidasiz. Limit cheksiz."
        else:
            text = f"Salom {user.first_name}! Limit: 5 ta kino. Kino kodini yuboring."
        
        await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id))
        
    except Exception as e:
        logger.error(f"Start error: {e}")
        await update.message.reply_text("Xatolik yuz berdi.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = str(user.id)
        text = update.message.text
        
        if is_banned(user_id):
            return
        
        if not await check_subscription(user.id, context):
            await update.message.reply_text(
                "Avval kanallarga obuna bo'ling!",
                reply_markup=get_subscription_keyboard()
            )
            return
        
        # Admin jarayonlari
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
        
        # Kino kodi tekshiruvi
        movies = get_movies()
        if text in movies:
            await send_movie(update, context, text)
            return
        
        # Qidiruv
        results = search_movies(text)
        if results:
            if len(results) == 1:
                await send_movie(update, context, results[0][0])
            else:
                msg = "Topilgan kinolar:\n\n"
                keyboard = []
                for code, data in results[:10]:
                    msg += f"{data.get('name', code)} - {code}\n"
                    keyboard.append([InlineKeyboardButton(data.get('name', code), callback_data=f"movie_{code}")])
                keyboard.append([InlineKeyboardButton("Asosiy menyu", callback_data="main_menu")])
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            # Tavsiya
            import random
            similar = random.sample(list(movies.items()), min(5, len(movies))) if movies else []
            msg = "Kino topilmadi. Balki quyidagilardan:\n\n"
            keyboard = []
            for code, data in similar:
                msg += f"{data.get('name', code)} - {code}\n"
                keyboard.append([InlineKeyboardButton(data.get('name', code), callback_data=f"movie_{code}")])
            keyboard.append([InlineKeyboardButton("Asosiy menyu", callback_data="main_menu")])
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
            
    except Exception as e:
        logger.error(f"Message error: {e}")
        await update.message.reply_text("Xatolik yuz berdi.")

async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, movie_code: str, query=None):
    try:
        from telegram import InlineKeyboardMarkup
        user_id = str(update.effective_user.id)
        
        if not is_admin(user_id) and not check_limit(user_id):
            ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
            text = f"Limit tugadi! Do'stlaringizni taklif qiling: {ref_link}"
            if query:
                await query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
            return
        
        movies = get_movies()
        if movie_code not in movies:
            return
        
        movie = movies[movie_code]
        
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
            caption = f"{movie.get('name', movie_code)} yuborildi! (Admin)"
        else:
            remaining = get_users()[user_id]["limit"]
            caption = f"{movie.get('name', movie_code)} yuborildi! Limit: {remaining}"
        
        if query:
            await query.message.reply_text(caption, reply_markup=get_movie_keyboard(movie_code, user_id))
        else:
            await update.message.reply_text(caption, reply_markup=get_movie_keyboard(movie_code, user_id))
            
    except Exception as e:
        logger.error(f"Send movie error: {e}")
        if query:
            await query.answer("Xatolik!", show_alert=True)
        else:
            await update.message.reply_text("Xatolik yuz berdi.")

# ==================== CALLBACKS ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from telegram import InlineKeyboardMarkup
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = query.data
        
        if is_banned(user_id) and not data.startswith("unban"):
            await query.edit_message_text("Siz bloklangansiz.")
            return
        
        if not await check_subscription(update.effective_user.id, context) and data != "check_sub":
            await query.edit_message_text(
                "Avval kanallarga obuna bo'ling!",
                reply_markup=get_subscription_keyboard()
            )
            return
        
        # Asosiy menyu
        if data == "main_menu":
            await show_main_menu(query, user_id)
        elif data == "check_sub":
            if await check_subscription(update.effective_user.id, context):
                await show_main_menu(query, user_id)
            else:
                await query.answer("Hali obuna bo'lmagansiz!", show_alert=True)
        
        # Foydalanuvchi funksiyalari
        elif data == "my_limit":
            await show_limit(query, user_id)
        elif data == "random_movie":
            await send_random_movie_by_query(query, context, user_id)
        elif data == "trending":
            await show_trending_list(query)
        elif data == "catalog":
            await query.edit_message_text("Kino katalogi:", reply_markup=get_catalog_keyboard(0))
        elif data.startswith("catalog_"):
            page = int(data.split("_")[1])
            await query.edit_message_text("Kino katalogi:", reply_markup=get_catalog_keyboard(page))
        elif data == "referral":
            await show_referral_info(query, user_id)
        elif data == "new_movies":
            await show_new_movies_list(query)
        elif data == "popular":
            await show_trending_list(query)
        elif data == "genres":
            await query.edit_message_text("Janr tanlang:", reply_markup=get_genres_keyboard())
        elif data.startswith("genre_"):
            await show_movies_by_genre_list(query, data.replace("genre_", ""))
        elif data == "favorites":
            await show_favorites_list(query, user_id)
        elif data == "my_stats":
            await show_user_stats(query, user_id)
        
        # Kino tugmalari
        elif data.startswith("movie_"):
            await send_movie_by_query_handler(query, context, data.replace("movie_", ""), user_id)
        elif data.startswith("fav_"):
            await toggle_favorite_handler(query, user_id, data.replace("fav_", ""))
        elif data.startswith("share_"):
            await share_movie_handler(query, data.replace("share_", ""))
        
        # Admin panel
        elif data == "admin_panel":
            await show_admin_panel(query, user_id)
        elif data == "add_movie":
            await start_add_movie(query, context)
        elif data == "delete_movie":
            await start_delete_movie(query)
        elif data.startswith("del_movie_"):
            await admin_delete_movie(query, data.replace("del_movie_", ""))
        elif data == "stats":
            await show_stats(query)
        elif data == "top_movies":
            await show_trending_list(query)
        elif data == "broadcast":
            await start_broadcast(query, context)
        elif data == "manage_channels":
            await manage_channels(query)
        elif data == "add_channel":
            await start_add_channel(query, context)
        elif data.startswith("rem_channel_"):
            await remove_channel_handler(query, data.replace("rem_channel_", ""))
        elif data == "add_limit":
            await start_add_limit(query, context)
        elif data == "ban_user":
            await start_ban_user(query, context)
        elif data == "unban_user":
            await start_unban_user(query)
        elif data.startswith("unban_user_"):
            await unban_user_handler(query, data.replace("unban_user_", ""))
        elif data == "backup":
            await create_backup(query)
        elif data == "export_data":
            await export_data(query)
        elif data == "add_admin":
            await start_add_admin(query, context)
        elif data == "remove_admin":
            await start_remove_admin(query)
        elif data.startswith("rem_admin_"):
            await remove_admin_handler(query, data.replace("rem_admin_", ""))
            
    except Exception as e:
        logger.error(f"Callback error: {e}")
        try:
            await query.answer("Xatolik!", show_alert=True)
        except:
            pass

# ==================== YORDAMCHI FUNKSIYALAR ====================

async def show_main_menu(query, user_id: str):
    text = (
        "Asosiy menyu\n\n"
        "Mening limitim - Qolgan limit\n"
        "Random film - Tasodifiy kino\n"
        "Trend filmlar - Top kinolar\n"
        "Kino katalog - Barcha kinolar\n"
        "Do'st taklif qilish - Referal\n"
        "Yangi filmlar - Songi qoshilgan\n"
        "Mashhur filmlar - Top reyting\n"
        "Janrlar - Janr boyicha\n"
        "Sevimlilar - Saqlanganlar\n"
        "Statistikam - Shaxsiy stat"
    )
    await query.edit_message_text(text, reply_markup=get_main_keyboard(user_id))

async def show_limit(query, user_id: str):
    users = get_users()
    user = users.get(user_id, {})
    
    if is_admin(user_id):
        text = "Limit: Cheksiz (Admin)"
    else:
        limit = user.get("limit", 0)
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
        text = f"Limit: {limit} ta kino\n\nReferal link: {ref_link}"
    
    await query.edit_message_text(text, reply_markup=get_main_keyboard(user_id))

async def send_random_movie_by_query(query, context, user_id: str):
    movie = get_random_movie()
    if not movie:
        await query.answer("Kinolar mavjud emas!", show_alert=True)
        return
    await send_movie_by_query_handler(query, context, movie[0], user_id)

async def send_movie_by_query_handler(query, context, movie_code: str, user_id: str):
    if not is_admin(user_id) and not check_limit(user_id):
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
        await query.edit_message_text(f"Limit tugadi! {ref_link}")
        return
    
    movies = get_movies()
    if movie_code not in movies:
        await query.answer("Kino topilmadi!", show_alert=True)
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
            caption = f"{movie.get('name', movie_code)} yuborildi! (Admin)"
        else:
            remaining = get_users()[user_id]["limit"]
            caption = f"{movie.get('name', movie_code)} yuborildi! Limit: {remaining}"
        
        await query.message.reply_text(caption, reply_markup=get_movie_keyboard(movie_code, user_id))
        
    except Exception as e:
        logger.error(f"Send error: {e}")
        await query.answer("Xatolik!", show_alert=True)

async def show_trending_list(query):
    trending = get_trending_movies(10)
    if not trending:
        await query.answer("Kinolar mavjud emas!", show_alert=True)
        return
    
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    text = "Top 10 kinolar:\n\n"
    keyboard = []
    for i, (code, data) in enumerate(trending, 1):
        text += f"{i}. {data.get('name', code)} - {data.get('views', 0)} marta\n"
        keyboard.append([InlineKeyboardButton(f"{i}. {data.get('name', code)}", callback_data=f"movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("Asosiy menyu", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_referral_info(query, user_id: str):
    users = get_users()
    ref_count = users.get(user_id, {}).get("referrals", 0)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    
    text = f"Referallar: {ref_count}\nHar bir referal: +5 limit\n\nLink: {ref_link}"
    
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    share_url = f"https://t.me/share/url?url={ref_link}&text=Zor kino bot!"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Ulashish", url=share_url)],
        [InlineKeyboardButton("Asosiy menyu", callback_data="main_menu")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def show_new_movies_list(query):
    movies = get_movies()
    sorted_movies = sorted(movies.items(), key=lambda x: x[1].get("added_at", ""), reverse=True)[:10]
    
    if not sorted_movies:
        await query.answer("Kinolar mavjud emas!", show_alert=True)
        return
    
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    text = "Songi qoshilgan:\n\n"
    keyboard = []
    for code, data in sorted_movies:
        text += f"{data.get('name', code)} - {code}\n"
        keyboard.append([InlineKeyboardButton(data.get('name', code), callback_data=f"movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("Asosiy menyu", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_movies_by_genre_list(query, genre: str):
    movies = get_movies_by_genre(genre)
    if not movies:
        await query.answer("Bu janrda kino yoq!", show_alert=True)
        return
    
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    text = f"{genre} janri:\n\n"
    keyboard = []
    for code, data in movies[:20]:
        text += f"{data.get('name', code)} - {code}\n"
        keyboard.append([InlineKeyboardButton(data.get('name', code), callback_data=f"movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("Orqaga", callback_data="genres")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_favorites_list(query, user_id: str):
    users = get_users()
    favorites = users.get(user_id, {}).get("favorites", [])
    movies = get_movies()
    
    if not favorites:
        await query.edit_message_text("Sevimlilar bo'sh!", reply_markup=get_main_keyboard(user_id))
        return
    
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    text = "Sevimlilar:\n\n"
    keyboard = []
    for code in favorites[:20]:
        if code in movies:
            data = movies[code]
            text += f"{data.get('name', code)} - {code}\n"
            keyboard.append([InlineKeyboardButton(data.get('name', code), callback_data=f"movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("Asosiy menyu", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_user_stats(query, user_id: str):
    users = get_users()
    user = users.get(user_id, {})
    
    watched = len(user.get("history", []))
    favs = len(user.get("favorites", []))
    refs = user.get("referrals", 0)
    joined = user.get("joined_at", "Nomlum")[:10]
    
    if is_admin(user_id):
        role = "Admin"
        limit_text = "Cheksiz"
    else:
        role = "User"
        limit_text = str(user.get("limit", 0))
    
    text = (
        f"Statistika:\n\n"
        f"Korilgan: {watched}\n"
        f"Sevimlilar: {favs}\n"
        f"Referallar: {refs}\n"
        f"Limit: {limit_text}\n"
        f"Status: {role}\n"
        f"Qoshilgan: {joined}"
    )
    
    await query.edit_message_text(text, reply_markup=get_main_keyboard(user_id))

async def toggle_favorite_handler(query, user_id: str, movie_code: str):
    is_added = toggle_favorite(user_id, movie_code)
    action = "qoshildi" if is_added else "olib tashlandi"
    await query.answer(f"Sevimlilarga {action}!", show_alert=True)
    await query.edit_message_reply_markup(reply_markup=get_movie_keyboard(movie_code, user_id))

async def share_movie_handler(query, movie_code: str):
    movies = get_movies()
    if movie_code not in movies:
        await query.answer("Kino topilmadi!", show_alert=True)
        return
    
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    movie = movies[movie_code]
    text = f"{movie.get('name', movie_code)}\n@{BOT_USERNAME}\nKod: {movie_code}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Dostlarga", url=f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}&text={text}")],
        [InlineKeyboardButton("Orqaga", callback_data=f"movie_{movie_code}")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Bekor qilindi!", reply_markup=get_main_keyboard(str(update.effective_user.id)))

# ==================== MAIN ====================

def main():
    import os
    import sys
    
    # Environment variables ni qayta o'qish
    env_token = os.environ.get("BOT_TOKEN", "")
    if env_token:
        global BOT_TOKEN
        BOT_TOKEN = env_token
        print(f"Token env dan o'qildi: {len(BOT_TOKEN)} ta belgi")
    
    if not BOT_TOKEN or len(BOT_TOKEN) < 20:
        print("ERROR: BOT_TOKEN noto'g'ri!")
        print(f"Mavjud env vars: {[k for k in os.environ.keys() if not k.startswith('_')]}")
        sys.exit(1)
    
    print(f"Bot: @{BOT_USERNAME}")
    print(f"Admins: {ADMIN_IDS}")
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("cancel", cancel))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        print("Bot ishga tushdi...")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"Bot xato: {e}")
        raise

if __name__ == "__main__":
    main()
