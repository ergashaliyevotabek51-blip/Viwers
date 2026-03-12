import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config import BOT_TOKEN, BOT_USERNAME, ADMIN_IDS
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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== START - CHIROYLI ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = str(user.id)
        first_name = user.first_name or "Do'stim"
        
        # Referal
        if context.args and len(context.args) > 0 and context.args[0].startswith("ref"):
            referrer_id = context.args[0].replace("ref", "")
            users = get_users()
            if referrer_id in users and referrer_id != user_id and user_id not in users:
                add_referral(referrer_id)
        
        get_or_create_user(user_id, user.username, first_name)
        
        if is_banned(user_id):
            await update.message.reply_text(
                "🚫 <b>Siz botdan bloklangansiz!</b>\n\n"
                "Admin bilan bog'laning: @admin",
                parse_mode='HTML'
            )
            return
        
        # Majburiy obuna
        if not await check_subscription(user.id, context):
            text = (
                f"👋 <b>Assalomu alaykum, {first_name}!</b>\n\n"
                f"🎬 <b>{BOT_USERNAME}</b> — eng sara o'zbek filmlari!\n\n"
                f"❗️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>"
            )
            await update.message.reply_text(text, reply_markup=get_subscription_keyboard(), parse_mode='HTML')
            return
        
        # Asosiy xush kelibsiz
        user_data = get_users().get(user_id, {})
        limit = "♾️ Cheksiz" if is_admin(user_id) else f"🎟 {user_data.get('limit', 5)} ta"
        
        welcome_text = (
            f"👋 <b>Assalomu alaykum, {first_name}!</b>\n\n"
            f"🎬 <b>{BOT_USERNAME}</b> — eng sara o'zbek filmlari va seriallari!\n\n"
            f"📝 <b>Kod yuboring</b> → film darhol keladi\n"
            f"• <b>Bepul:</b> 5 ta\n"
            f"• <b>Do'st uchun:</b> +5 ta\n\n"
            f"🎟 <b>Sizning limitingiz:</b> {limit}\n\n"
            f"🚀 <i>Kod yozing yoki do'stlaringizni taklif qiling!</i>"
        )
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_keyboard(user_id),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Start error: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

# ==================== MESSAGE HANDLER ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = str(user.id)
        text = update.message.text
        
        if is_banned(user_id):
            return
        
        if not await check_subscription(user.id, context):
            await update.message.reply_text(
                "❗️ <b>Avval kanallarga obuna bo'ling!</b>",
                reply_markup=get_subscription_keyboard(),
                parse_mode='HTML'
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
        
        # Kino kodi
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
                msg = "🔍 <b>Topilgan kinolar:</b>\n\n"
                keyboard = []
                for code, data in results[:10]:
                    msg += f"🎬 <code>{code}</code> — {data.get('name', code)}\n"
                    keyboard.append([InlineKeyboardButton(f"🎬 {data.get('name', code)[:30]}", callback_data=f"movie_{code}")])
                keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        else:
            # Tavsiya
            import random
            similar = random.sample(list(movies.items()), min(5, len(movies))) if movies else []
            msg = (
                "❌ <b>Kino topilmadi</b>\n\n"
                "🤔 <i>Balki quyidagilardan birini izlagandirsiz:</i>\n\n"
            )
            keyboard = []
            for code, data in similar:
                msg += f"🎬 <code>{code}</code> — {data.get('name', code)}\n"
                keyboard.append([InlineKeyboardButton(f"🎬 {data.get('name', code)[:30]}", callback_data=f"movie_{code}")])
            keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            
    except Exception as e:
        logger.error(f"Message error: {e}")
        await update.message.reply_text("❌ <b>Xatolik yuz berdi!</b>", parse_mode='HTML')

async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, movie_code: str, query=None):
    try:
        user_id = str(update.effective_user.id)
        
        if not is_admin(user_id) and not check_limit(user_id):
            ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
            text = (
                "🚫 <b>Limitingiz tugadi!</b>\n\n"
                f"👥 <b>Do'stlaringizni taklif qiling va +5 limit oling:</b>\n"
                f"🔗 <code>{ref_link}</code>"
            )
            if query:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Ulashish", url=f"https://t.me/share/url?url={ref_link}&text=🎬%20Zo'r%20kino%20bot!")],
                    [InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")]
                ]), parse_mode='HTML')
            else:
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Ulashish", url=f"https://t.me/share/url?url={ref_link}&text=🎬%20Zo'r%20kino%20bot!")],
                    [InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")]
                ]), parse_mode='HTML')
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
        
        remaining = "♾️" if is_admin(user_id) else get_users()[user_id]["limit"]
        caption = (
            f"✅ <b>{movie.get('name', movie_code)}</b> yuborildi!\n\n"
            f"🎟 <b>Qolgan limit:</b> <code>{remaining}</code>\n\n"
            f"📌 <b>Kod:</b> <code>{movie_code}</code>"
        )
        
        if query:
            await query.message.reply_text(caption, reply_markup=get_movie_keyboard(movie_code, user_id), parse_mode='HTML')
        else:
            await update.message.reply_text(caption, reply_markup=get_movie_keyboard(movie_code, user_id), parse_mode='HTML')
            
    except Exception as e:
        logger.error(f"Send movie error: {e}")
        error_msg = "❌ <b>Kino yuborishda xatolik!</b>\nIltimos, keyinroq urinib ko'ring."
        if query:
            await query.answer("❌ Xatolik!", show_alert=True)
        else:
            await update.message.reply_text(error_msg, parse_mode='HTML')

# ==================== CALLBACKS ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = query.data
        
        if is_banned(user_id) and not data.startswith("unban"):
            await query.edit_message_text("🚫 <b>Siz bloklangansiz!</b>", parse_mode='HTML')
            return
        
        if not await check_subscription(update.effective_user.id, context) and data != "check_sub":
            await query.edit_message_text(
                "❗️ <b>Avval kanallarga obuna bo'ling!</b>",
                reply_markup=get_subscription_keyboard(),
                parse_mode='HTML'
            )
            return
        
        # Asosiy menyu
        if data == "main_menu":
            await show_main_menu(query, user_id)
        elif data == "check_sub":
            if await check_subscription(update.effective_user.id, context):
                await show_main_menu(query, user_id)
            else:
                await query.answer("❌ Hali obuna bo'lmagansiz!", show_alert=True)
        
        # Foydalanuvchi funksiyalari
        elif data == "my_limit":
            await show_limit(query, user_id)
        elif data == "random_movie":
            await send_random_movie_by_query(query, context, user_id)
        elif data == "trending":
            await show_trending_list(query)
        elif data == "catalog":
            await query.edit_message_text("🎥 <b>Kino katalogi</b>", reply_markup=get_catalog_keyboard(0), parse_mode='HTML')
        elif data.startswith("catalog_"):
            page = int(data.split("_")[1])
            await query.edit_message_text("🎥 <b>Kino katalogi</b>", reply_markup=get_catalog_keyboard(page), parse_mode='HTML')
        elif data == "referral":
            await show_referral_info(query, user_id)
        elif data == "new_movies":
            await show_new_movies_list(query)
        elif data == "popular":
            await show_trending_list(query)
        elif data == "genres":
            await query.edit_message_text("🎭 <b>Janrni tanlang</b>", reply_markup=get_genres_keyboard(), parse_mode='HTML')
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
            await query.answer("❌ Xatolik!", show_alert=True)
        except:
            pass

# ==================== YORDAMCHI FUNKSIYALAR ====================

async def show_main_menu(query, user_id: str):
    user_data = get_users().get(user_id, {})
    limit = "♾️ Cheksiz" if is_admin(user_id) else f"🎟 {user_data.get('limit', 5)} ta"
    
    text = (
        f"🎬 <b>Asosiy menyu</b>\n\n"
        f"🎟 <b>Limit:</b> <code>{limit}</code>\n\n"
        f"📋 <b>Quyidagilardan tanlang:</b>\n"
        f"• 🎟 Mening limitim — Qolgan limit\n"
        f"• 🎬 Random film — Tasodifiy kino\n"
        f"• 🔥 Trend filmlar — Top 10\n"
        f"• 🎥 Kino katalog — Barcha kinolar\n"
        f"• 👥 Do'stlarni taklif qilish — Referal\n"
        f"• 🆕 Yangi filmlar — Songi qo'shilgan\n"
        f"• ⭐ Mashhur filmlar — Top reyting\n"
        f"• 🎭 Janrlar — Janr bo'yicha\n"
        f"• ❤️ Sevimlilar — Saqlanganlar\n"
        f"• 📊 Mening statistikam — Shaxsiy stat"
    )
    await query.edit_message_text(text, reply_markup=get_main_keyboard(user_id), parse_mode='HTML')

async def show_limit(query, user_id: str):
    users = get_users()
    user = users.get(user_id, {})
    
    if is_admin(user_id):
        text = (
            f"🎟 <b>Sizning limitingiz:</b> ♾️ <b>Cheksiz</b>\n\n"
            f"👮 <b>Siz admin sifatidasiz!</b>\n"
            f"Limit cheklanmagan."
        )
    else:
        limit = user.get("limit", 0)
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
        refs = user.get("referrals", 0)
        
        text = (
            f"🎟 <b>Sizning limitingiz:</b> <code>{limit}</code> ta kino\n\n"
            f"👥 <b>Referallaringiz:</b> <code>{refs}</code> ta\n"
            f"🎁 <b>Har bir referal uchun:</b> +5 limit\n\n"
            f"🔗 <b>Sizning linkingiz:</b>\n<code>{ref_link}</code>"
        )
    
    await query.edit_message_text(text, reply_markup=get_main_keyboard(user_id), parse_mode='HTML')

async def send_random_movie_by_query(query, context, user_id: str):
    movie = get_random_movie()
    if not movie:
        await query.answer("🎬 Hozircha kinolar mavjud emas!", show_alert=True)
        return
    await send_movie_by_query_handler(query, context, movie[0], user_id)

async def send_movie_by_query_handler(query, context, movie_code: str, user_id: str):
    if not is_admin(user_id) and not check_limit(user_id):
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
        text = (
            f"🚫 <b>Limitingiz tugadi!</b>\n\n"
            f"👥 <b>Do'stlaringizni taklif qiling:</b>\n<code>{ref_link}</code>"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Ulashish", url=f"https://t.me/share/url?url={ref_link}&text=🎬%20Zo'r%20kino%20bot!")],
            [InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")]
        ]), parse_mode='HTML')
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
        
        remaining = "♾️" if is_admin(user_id) else get_users()[user_id]["limit"]
        caption = (
            f"✅ <b>{movie.get('name', movie_code)}</b> yuborildi!\n\n"
            f"🎟 <b>Qolgan limit:</b> <code>{remaining}</code>\n"
            f"📌 <b>Kod:</b> <code>{movie_code}</code>"
        )
        
        await query.message.reply_text(caption, reply_markup=get_movie_keyboard(movie_code, user_id), parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Send error: {e}")
        await query.answer("❌ Xatolik!", show_alert=True)

async def show_trending_list(query):
    trending = get_trending_movies(10)
    if not trending:
        await query.answer("🎬 Hozircha kinolar mavjud emas!", show_alert=True)
        return
    
    text = "🔥 <b>Top 10 eng ko'p ko'rilgan filmlar:</b>\n\n"
    keyboard = []
    for i, (code, data) in enumerate(trending, 1):
        views = data.get("views", 0)
        text += f"{i}. 🎬 <b>{data.get('name', code)}</b> — 👁 <code>{views}</code>\n"
        keyboard.append([InlineKeyboardButton(f"{i}. {data.get('name', code)[:35]}", callback_data=f"movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_referral_info(query, user_id: str):
    users = get_users()
    ref_count = users.get(user_id, {}).get("referrals", 0)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    
    text = (
        f"👥 <b>Do'stlaringizni taklif qiling!</b>\n\n"
        f"📊 <b>Sizning referallaringiz:</b> <code>{ref_count}</code> ta\n"
        f"🎁 <b>Har bir referal uchun:</b> +5 limit\n\n"
        f"🔗 <b>Sizning linkingiz:</b>\n<code>{ref_link}</code>"
    )
    
    share_url = f"https://t.me/share/url?url={ref_link}&text=🎬%20Zo'r%20kino%20bot!%20Eng%20sara%20o'zbek%20filmlari!"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Do'stlarga yuborish", url=share_url)],
        [InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')

async def show_new_movies_list(query):
    movies = get_movies()
    sorted_movies = sorted(movies.items(), key=lambda x: x[1].get("added_at", ""), reverse=True)[:10]
    
    if not sorted_movies:
        await query.answer("🎬 Hozircha yangi kinolar mavjud emas!", show_alert=True)
        return
    
    text = "🆕 <b>So'nggi qo'shilgan filmlar:</b>\n\n"
    keyboard = []
    for code, data in sorted_movies:
        added = data.get("added_at", "")[:10]
        text += f"🎬 <b>{data.get('name', code)}</b> — <code>{code}</code>\n"
        keyboard.append([InlineKeyboardButton(f"🎬 {data.get('name', code)[:35]}", callback_data=f"movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_movies_by_genre_list(query, genre: str):
    movies = get_movies_by_genre(genre)
    if not movies:
        await query.answer(f"🎭 {genre} janrida kino yo'q!", show_alert=True)
        return
    
    emoji = "🎭" if "drama" in genre.lower() else "😂" if "komed" in genre.lower() else "💕" if "romant" in genre.lower() else "🔥" if "action" in genre.lower() else "🎬"
    
    text = f"{emoji} <b>{genre}</b> janridagi filmlar:\n\n"
    keyboard = []
    for code, data in movies[:20]:
        text += f"🎬 <b>{data.get('name', code)}</b> — <code>{code}</code>\n"
        keyboard.append([InlineKeyboardButton(f"🎬 {data.get('name', code)[:35]}", callback_data=f"movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="genres")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_favorites_list(query, user_id: str):
    users = get_users()
    favorites = users.get(user_id, {}).get("favorites", [])
    movies = get_movies()
    
    if not favorites:
        await query.edit_message_text(
            "❤️ <b>Sevimli filmlaringiz bo'sh!</b>\n\n"
            "🎬 Kino katalogidan o'zingizga yoqqan filmlarni qo'shing.",
            reply_markup=get_main_keyboard(user_id),
            parse_mode='HTML'
        )
        return
    
    text = "❤️ <b>Sevimli filmlaringiz:</b>\n\n"
    keyboard = []
    for code in favorites[:20]:
        if code in movies:
            data = movies[code]
            text += f"🎬 <b>{data.get('name', code)}</b> — <code>{code}</code>\n"
            keyboard.append([InlineKeyboardButton(f"🎬 {data.get('name', code)[:35]}", callback_data=f"movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_user_stats(query, user_id: str):
    users = get_users()
    user = users.get(user_id, {})
    
    watched = len(user.get("history", []))
    favs = len(user.get("favorites", []))
    refs = user.get("referrals", 0)
    joined = user.get("joined_at", "Nomlum")[:10]
    
    if is_admin(user_id):
        role = "👮 Admin"
        limit_text = "♾️ Cheksiz"
    else:
        role = "👤 Foydalanuvchi"
        limit_text = str(user.get("limit", 0))
    
    text = (
        f"📊 <b>Sizning statistikangiz</b>\n\n"
        f"🎬 <b>Ko'rilgan kinolar:</b> <code>{watched}</code>\n"
        f"❤️ <b>Sevimli filmlar:</b> <code>{favs}</code>\n"
        f"👥 <b>Taklif qilingan do'stlar:</b> <code>{refs}</code>\n"
        f"🎟 <b>Joriy limit:</b> <code>{limit_text}</code>\n"
        f"🎭 <b>Status:</b> {role}\n"
        f"📅 <b>Qo'shilgan sana:</b> <code>{joined}</code>"
    )
    
    await query.edit_message_text(text, reply_markup=get_main_keyboard(user_id), parse_mode='HTML')

async def toggle_favorite_handler(query, user_id: str, movie_code: str):
    is_added = toggle_favorite(user_id, movie_code)
    action = "qo'shildi ❤️" if is_added else "olib tashlandi 💔"
    await query.answer(f"Sevimlilarga {action}!", show_alert=True)
    await query.edit_message_reply_markup(reply_markup=get_movie_keyboard(movie_code, user_id))

async def share_movie_handler(query, movie_code: str):
    movies = get_movies()
    if movie_code not in movies:
        await query.answer("❌ Kino topilmadi!", show_alert=True)
        return
    
    movie = movies[movie_code]
    text = (
        f"🎬 <b>{movie.get('name', movie_code)}</b>\n\n"
        f"🎥 Eng sara o'zbek filmlari — @{BOT_USERNAME}\n"
        f"📌 <b>Kod:</b> <code>{movie_code}</code>"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Do'stlarga yuborish", url=f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}&text=🎬%20{movie.get('name', movie_code)}")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data=f"movie_{movie_code}")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✅ <b>Bekor qilindi!</b>", reply_markup=get_main_keyboard(str(update.effective_user.id)), parse_mode='HTML')

# ==================== MAIN ====================

def main():
    import os
    import sys
    
    env_token = os.environ.get("BOT_TOKEN", "")
    if env_token:
        global BOT_TOKEN
        BOT_TOKEN = env_token
    
    if not BOT_TOKEN or len(BOT_TOKEN) < 20:
        print("ERROR: BOT_TOKEN noto'g'ri!")
        print(f"Env vars: {[k for k in os.environ.keys() if not k.startswith('_')]}")
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
