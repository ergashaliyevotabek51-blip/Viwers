import shutil
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_users, save_users, get_movies, save_movies, get_channels, save_channels, get_admins, save_admins, USERS_FILE, MOVIES_FILE, CHANNELS_FILE
from config import ADMIN_IDS

def is_admin(user_id: str) -> bool:
    return user_id in ADMIN_IDS

def is_super_admin(user_id: str) -> bool:
    return ADMIN_IDS and user_id == ADMIN_IDS[0]

async def show_admin_panel(query, user_id: str):
    if not is_admin(user_id):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    total_users = len(get_users())
    total_movies = len(get_movies())
    
    role = "👑 Super Admin" if is_super_admin(user_id) else "👮 Admin"
    
    text = (
        f"🛠 <b>Admin panel</b>\n"
        f"🎭 <b>Status:</b> {role}\n\n"
        f"👥 <b>Foydalanuvchilar:</b> <code>{total_users}</code>\n"
        f"🎬 <b>Kinolar:</b> <code>{total_movies}</code>\n"
        f"📢 <b>Majburiy kanallar:</b> <code>{len(get_channels())}</code>"
    )
    
    from utils import get_admin_keyboard
    await query.edit_message_text(text, reply_markup=get_admin_keyboard(user_id), parse_mode='HTML')

async def start_add_movie(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["adding_movie"] = {"step": "forward"}
    await query.edit_message_text(
        "➕ <b>Kino qo'shish</b>\n\n"
        "1️⃣ Kanaldan film/video forward qiling\n"
        "2️⃣ Kod kiriting (masalan: <code>uzb001</code>)\n"
        "3️⃣ Film nomini to'liq yozing\n"
        "4️⃣ Janr kiriting (ixtiyoriy)\n\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_add_movie(update, context):
    from movies import add_movie
    user_data = context.user_data.get("adding_movie", {})
    step = user_data.get("step")
    
    if update.message.forward_from_chat:
        user_data["channel_id"] = update.message.forward_from_chat.id
        user_data["message_id"] = update.message.forward_from_message_id
        user_data["step"] = "code"
        await update.message.reply_text("✅ <b>Saqlandi!</b> Endi kod kiriting:", parse_mode='HTML')
    
    elif step == "code":
        code = update.message.text.strip().lower()
        movies = get_movies()
        if code in movies:
            await update.message.reply_text("❌ <b>Bu kod allaqachon mavjud!</b>\nBoshqa kod kiriting:", parse_mode='HTML')
            return
        user_data["code"] = code
        user_data["step"] = "name"
        await update.message.reply_text("✅ <b>Kod saqlandi!</b>\nFilm nomini yozing:", parse_mode='HTML')
    
    elif step == "name":
        user_data["name"] = update.message.text.strip()
        user_data["step"] = "genre"
        await update.message.reply_text("✅ <b>Nom saqlandi!</b>\nJanr kiriting (yo'q bo'lsa <code>skip</code>):", parse_mode='HTML')
    
    elif step == "genre":
        genre = update.message.text.strip()
        if genre.lower() == "skip":
            genre = ""
        
        add_movie(
            user_data["code"],
            user_data["name"],
            genre,
            user_data["channel_id"],
            user_data["message_id"],
            str(update.effective_user.id)
        )
        
        del context.user_data["adding_movie"]
        
        genre_display = genre if genre else "🎬 Belgilanmagan"
        
        from utils import get_admin_keyboard
        await update.message.reply_text(
            f"✅ <b>Kino muvaffaqiyatli qo'shildi!</b>\n\n"
            f"🎬 <b>Kod:</b> <code>{user_data['code']}</code>\n"
            f"📝 <b>Nomi:</b> {user_data['name']}\n"
            f"🎭 <b>Janr:</b> {genre_display}",
            reply_markup=get_admin_keyboard(str(update.effective_user.id)),
            parse_mode='HTML'
        )

async def start_delete_movie(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    movies = get_movies()
    if not movies:
        from utils import get_admin_keyboard
        await query.edit_message_text("🎬 <b>Kinolar mavjud emas!</b>", reply_markup=get_admin_keyboard(str(query.from_user.id)), parse_mode='HTML')
        return
    
    keyboard = []
    for code, data in list(movies.items())[:20]:
        keyboard.append([InlineKeyboardButton(f"🎬 {data.get('name', code)[:30]} ({code})", callback_data=f"del_movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    await query.edit_message_text("➖ <b>O'chirish uchun kinoni tanlang:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def delete_movie(query, movie_code: str):
    from movies import delete_movie as remove_movie
    if remove_movie(movie_code):
        await query.answer("✅ Kino o'chirildi!", show_alert=True)
    else:
        await query.answer("❌ Kino o'chirishda xatolik!", show_alert=True)
    await start_delete_movie(query)

async def show_stats(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    users = get_users()
    movies = get_movies()
    
    total_users = len(users)
    total_movies = len(movies)
    banned = sum(1 for u in users.values() if u.get("banned"))
    views = sum(m.get("views", 0) for m in movies.values())
    
    text = (
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> <code>{total_users}</code>\n"
        f"🎬 <b>Jami kinolar:</b> <code>{total_movies}</code>\n"
        f"👁 <b>Jami ko'rishlar:</b> <code>{views}</code>\n"
        f"🚫 <b>Bloklangan:</b> <code>{banned}</code>\n"
        f"📢 <b>Kanallar:</b> <code>{len(get_channels())}</code>\n"
        f"👮 <b>Adminlar:</b> <code>{len(get_admins())}</code>"
    )
    
    from utils import get_admin_keyboard
    await query.edit_message_text(text, reply_markup=get_admin_keyboard(str(query.from_user.id)), parse_mode='HTML')

async def start_broadcast(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["broadcasting"] = True
    await query.edit_message_text(
        "📢 <b>Broadcast xabar</b>\n\n"
        "Yuboriladigan xabarni kiriting:\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_broadcast(update, context):
    if not context.user_data.get("broadcasting"):
        return
    
    del context.user_data["broadcasting"]
    
    users = get_users()
    sent = 0
    failed = 0
    
    status = await update.message.reply_text("📤 <b>Yuborilmoqda...</b>", parse_mode='HTML')
    
    for user_id in users:
        try:
            await update.message.copy(chat_id=int(user_id))
            sent += 1
        except:
            failed += 1
    
    await status.edit_text(
        f"✅ <b>Broadcast yakunlandi!</b>\n\n"
        f"✓ <b>Muvaffaqiyatli:</b> <code>{sent}</code>\n"
        f"✗ <b>Xatolik:</b> <code>{failed}</code>",
        parse_mode='HTML'
    )

async def manage_channels(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    from utils import get_channels_keyboard
    await query.edit_message_text("🔒 <b>Majburiy obuna kanallari</b>", reply_markup=get_channels_keyboard(), parse_mode='HTML')

async def start_add_channel(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["adding_channel"] = True
    await query.edit_message_text(
        "➕ <b>Kanal qo'shish</b>\n\n"
        "Quyidagi variantlardan birini yuboring:\n"
        "• <b>Username:</b> <code>@channelname</code>\n"
        "• <b>Link:</b> <code>https://t.me/channelname</code>\n"
        "• <b>ID:</b> <code>-1001234567890</code> (kamroq tavsiya etiladi)\n\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_add_channel(update, context):
    if not context.user_data.get("adding_channel"):
        return
    
    text = update.message.text.strip()
    
    try:
        if text.startswith('https://t.me/'):
            username = '@' + text.split('/')[-1].split('?')[0]
            chat = await context.bot.get_chat(username)
        elif text.startswith('@'):
            chat = await context.bot.get_chat(text)
        else:
            chat = await context.bot.get_chat(int(text))
        
        from subscription import add_channel
        invite_link = chat.invite_link
        if not invite_link and chat.username:
            invite_link = f"https://t.me/{chat.username}"
        
        add_channel(
            str(chat.id),
            chat.title,
            invite_link
        )
        del context.user_data["adding_channel"]
        
        await update.message.reply_text(
            f"✅ <b>Kanal qo'shildi!</b>\n\n"
            f"📢 <b>Nomi:</b> {chat.title}\n"
            f"🆔 <b>ID:</b> <code>{chat.id}</code>\n"
            f"🔗 <b>Link:</b> {invite_link or 'Mavjud emas'}",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>Xatolik:</b> Kanal topilmadi yoki bot kanalda admin emas!\n\n"
            f"<code>{e}</code>\n\n"
            f"ℹ️ Botni kanalga admin qiling va qayta urinib ko'ring.",
            parse_mode='HTML'
        )

async def remove_channel_handler(query, channel_id: str):
    from subscription import remove_channel
    if remove_channel(channel_id):
        await query.answer("✅ Kanal o'chirildi!", show_alert=True)
    await manage_channels(query)

async def start_add_limit(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["adding_limit"] = {"step": "user"}
    await query.edit_message_text(
        "💠 <b>Limit qo'shish</b>\n\n"
        "Foydalanuvchi ID sini kiriting:\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_add_limit(update, context):
    from users import add_limit
    user_data = context.user_data.get("adding_limit", {})
    step = user_data.get("step")
    
    if step == "user":
        user_id = update.message.text.strip()
        if user_id not in get_users():
            await update.message.reply_text("❌ <b>Foydalanuvchi topilmadi!</b>", parse_mode='HTML')
            return
        context.user_data["adding_limit"]["target_user"] = user_id
        context.user_data["adding_limit"]["step"] = "amount"
        await update.message.reply_text("✅ <b>Endi limit miqdorini kiriting:</b>", parse_mode='HTML')
    
    elif step == "amount":
        try:
            amount = int(update.message.text.strip())
            target = context.user_data["adding_limit"]["target_user"]
            add_limit(target, amount)
            del context.user_data["adding_limit"]
            await update.message.reply_text(f"✅ <b>{target}</b> ga <code>{amount}</code> limit qo'shildi!", parse_mode='HTML')
        except ValueError:
            await update.message.reply_text("❌ <b>Raqam kiriting!</b>", parse_mode='HTML')

async def start_ban_user(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["banning_user"] = True
    await query.edit_message_text(
        "👤 <b>User ban qilish</b>\n\n"
        "Foydalanuvchi ID sini kiriting:\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_ban_user(update, context):
    from users import ban_user
    if not context.user_data.get("banning_user"):
        return
    
    user_id = update.message.text.strip()
    
    if is_admin(user_id):
        await update.message.reply_text("❌ <b>Adminni ban qilish mumkin emas!</b>", parse_mode='HTML')
        del context.user_data["banning_user"]
        return
    
    ban_user(user_id)
    del context.user_data["banning_user"]
    await update.message.reply_text(f"🚫 <b>{user_id}</b> bloklandi!", parse_mode='HTML')

async def start_unban_user(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    users = get_users()
    banned = [(uid, u) for uid, u in users.items() if u.get("banned")]
    
    if not banned:
        from utils import get_admin_keyboard
        await query.edit_message_text("✅ <b>Bloklangan foydalanuvchilar yo'q!</b>", reply_markup=get_admin_keyboard(str(query.from_user.id)), parse_mode='HTML')
        return
    
    keyboard = []
    for uid, u in banned[:20]:
        name = u.get("first_name", "Nomlum")
        keyboard.append([InlineKeyboardButton(f"♻️ {name[:20]} ({uid})", callback_data=f"unban_user_{uid}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    await query.edit_message_text("♻️ <b>Blokdan ochish uchun tanlang:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def unban_user_handler(query, user_id: str):
    from users import unban_user
    unban_user(user_id)
    await query.answer("✅ Foydalanuvchi blokdan chiqarildi!", show_alert=True)
    await start_unban_user(query)

async def create_backup(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    try:
        backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copytree("data", backup_dir)
        from utils import get_admin_keyboard
        await query.edit_message_text(
            f"✅ <b>Backup yaratildi!</b>\n\n"
            f"📁 <b>Papka:</b> <code>{backup_dir}</code>",
            reply_markup=get_admin_keyboard(str(query.from_user.id)),
            parse_mode='HTML'
        )
    except Exception as e:
        from utils import get_admin_keyboard
        await query.edit_message_text(
            f"❌ <b>Backup xatosi:</b>\n<code>{e}</code>",
            reply_markup=get_admin_keyboard(str(query.from_user.id)),
            parse_mode='HTML'
        )

async def export_data(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    import os
    sent = 0
    for filename in [USERS_FILE, MOVIES_FILE, CHANNELS_FILE]:
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                await query.message.reply_document(f, caption=f"📁 {os.path.basename(filename)}")
                sent += 1
    
    from utils import get_admin_keyboard
    await query.edit_message_text(
        f"✅ <b>Export yakunlandi!</b>\n\n"
        f"📤 <b>Yuborilgan fayllar:</b> {sent} ta",
        reply_markup=get_admin_keyboard(str(query.from_user.id)),
        parse_mode='HTML'
    )

async def start_add_admin(query, context):
    if not is_super_admin(str(query.from_user.id)):
        await query.answer("🚫 Faqat super admin!", show_alert=True)
        return
    
    context.user_data["adding_admin"] = True
    await query.edit_message_text(
        "👮 <b>Admin qo'shish</b>\n\n"
        "Yangi admin ID sini kiriting:\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_add_admin(update, context):
    if not context.user_data.get("adding_admin"):
        return
    
    new_id = update.message.text.strip()
    
    if new_id == str(update.effective_user.id):
        await update.message.reply_text("❌ <b>O'zingizni emas!</b>", parse_mode='HTML')
        del context.user_data["adding_admin"]
        return
    
    admins = get_admins()
    if new_id in admins:
        await update.message.reply_text("❌ <b>Allaqachon admin!</b>", parse_mode='HTML')
        del context.user_data["adding_admin"]
        return
    
    admins[new_id] = {
        "role": "admin",
        "added_at": datetime.now().isoformat(),
        "added_by": str(update.effective_user.id),
        "source": "manual"
    }
    save_admins(admins)
    del context.user_data["adding_admin"]
    await update.message.reply_text(f"✅ <b>{new_id}</b> admin qilindi!", parse_mode='HTML')

async def start_remove_admin(query):
    if not is_super_admin(str(query.from_user.id)):
        await query.answer("🚫 Faqat super admin!", show_alert=True)
        return
    
    admins = get_admins()
    removable = [(aid, a) for aid, a in admins.items() 
                 if a.get("source") == "manual" and aid != str(query.from_user.id)]
    
    if not removable:
        from utils import get_admin_keyboard
        await query.edit_message_text("✅ <b>O'chiriladigan admin yo'q!</b>", reply_markup=get_admin_keyboard(str(query.from_user.id)), parse_mode='HTML')
        return
    
    keyboard = []
    for aid, a in removable:
        keyboard.append([InlineKeyboardButton(f"❌ {aid}", callback_data=f"rem_admin_{aid}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    await query.edit_message_text("❌ <b>O'chirish uchun tanlang:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def remove_admin_handler(query, admin_id: str):
    admins = get_admins()
    if admin_id in admins and admins[admin_id].get("source") == "manual":
        del admins[admin_id]
        save_admins(admins)
        await query.answer("✅ Admin o'chirildi!", show_alert=True)
    await start_remove    movies = get_movies()
    
    total_users = len(users)
    total_movies = len(movies)
    banned = sum(1 for u in users.values() if u.get("banned"))
    views = sum(m.get("views", 0) for m in movies.values())
    
    text = (
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> <code>{total_users}</code>\n"
        f"🎬 <b>Jami kinolar:</b> <code>{total_movies}</code>\n"
        f"👁 <b>Jami ko'rishlar:</b> <code>{views}</code>\n"
        f"🚫 <b>Bloklangan:</b> <code>{banned}</code>\n"
        f"📢 <b>Kanallar:</b> <code>{len(get_channels())}</code>\n"
        f"👮 <b>Adminlar:</b> <code>{len(get_admins())}</code>"
    )
    
    from utils import get_admin_keyboard
    await query.edit_message_text(text, reply_markup=get_admin_keyboard(str(query.from_user.id)), parse_mode='HTML')

async def start_broadcast(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["broadcasting"] = True
    await query.edit_message_text(
        "📢 <b>Broadcast xabar</b>\n\n"
        "Yuboriladigan xabarni kiriting:\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_broadcast(update, context):
    if not context.user_data.get("broadcasting"):
        return
    
    del context.user_data["broadcasting"]
    
    users = get_users()
    sent = 0
    failed = 0
    
    status = await update.message.reply_text("📤 <b>Yuborilmoqda...</b>", parse_mode='HTML')
    
    for user_id in users:
        try:
            await update.message.copy(chat_id=int(user_id))
            sent += 1
        except:
            failed += 1
    
    await status.edit_text(
        f"✅ <b>Broadcast yakunlandi!</b>\n\n"
        f"✓ <b>Muvaffaqiyatli:</b> <code>{sent}</code>\n"
        f"✗ <b>Xatolik:</b> <code>{failed}</code>",
        parse_mode='HTML'
    )

async def manage_channels(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    from utils import get_channels_keyboard
    await query.edit_message_text("🔒 <b>Majburiy obuna kanallari</b>", reply_markup=get_channels_keyboard(), parse_mode='HTML')

async def start_add_channel(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["adding_channel"] = True
    await query.edit_message_text(
        "➕ <b>Kanal qo'shish</b>\n\n"
        "Quyidagi variantlardan birini yuboring:\n"
        "• <b>Username:</b> <code>@channelname</code>\n"
        "• <b>Link:</b> <code>https://t.me/channelname</code>\n"
        "• <b>ID:</b> <code>-1001234567890</code> (kamroq tavsiya etiladi)\n\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_add_channel(update, context):
    if not context.user_data.get("adding_channel"):
        return
    
    text = update.message.text.strip()
    
    try:
        if text.startswith('https://t.me/'):
            username = '@' + text.split('/')[-1].split('?')[0]
            chat = await context.bot.get_chat(username)
        elif text.startswith('@'):
            chat = await context.bot.get_chat(text)
        else:
            chat = await context.bot.get_chat(int(text))
        
        from subscription import add_channel
        invite_link = chat.invite_link
        if not invite_link and chat.username:
            invite_link = f"https://t.me/{chat.username}"
        
        add_channel(
            str(chat.id),
            chat.title,
            invite_link
        )
        del context.user_data["adding_channel"]
        
        await update.message.reply_text(
            f"✅ <b>Kanal qo'shildi!</b>\n\n"
            f"📢 <b>Nomi:</b> {chat.title}\n"
            f"🆔 <b>ID:</b> <code>{chat.id}</code>\n"
            f"🔗 <b>Link:</b> {invite_link or 'Mavjud emas'}",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>Xatolik:</b> Kanal topilmadi yoki bot kanalda admin emas!\n\n"
            f"<code>{e}</code>\n\n"
            f"ℹ️ Botni kanalga admin qiling va qayta urinib ko'ring.",
            parse_mode='HTML'
        )

async def remove_channel_handler(query, channel_id: str):
    from subscription import remove_channel
    if remove_channel(channel_id):
        await query.answer("✅ Kanal o'chirildi!", show_alert=True)
    await manage_channels(query)

async def start_add_limit(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["adding_limit"] = {"step": "user"}
    await query.edit_message_text(
        "💠 <b>Limit qo'shish</b>\n\n"
        "Foydalanuvchi ID sini kiriting:\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_add_limit(update, context):
    from users import add_limit
    user_data = context.user_data.get("adding_limit", {})
    step = user_data.get("step")
    
    if step == "user":
        user_id = update.message.text.strip()
        if user_id not in get_users():
            await update.message.reply_text("❌ <b>Foydalanuvchi topilmadi!</b>", parse_mode='HTML')
            return
        context.user_data["adding_limit"]["target_user"] = user_id
        context.user_data["adding_limit"]["step"] = "amount"
        await update.message.reply_text("✅ <b>Endi limit miqdorini kiriting:</b>", parse_mode='HTML')
    
    elif step == "amount":
        try:
            amount = int(update.message.text.strip())
            target = context.user_data["adding_limit"]["target_user"]
            add_limit(target, amount)
            del context.user_data["adding_limit"]
            await update.message.reply_text(f"✅ <b>{target}</b> ga <code>{amount}</code> limit qo'shildi!", parse_mode='HTML')
        except ValueError:
            await update.message.reply_text("❌ <b>Raqam kiriting!</b>", parse_mode='HTML')

async def start_ban_user(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["banning_user"] = True
    await query.edit_message_text(
        "👤 <b>User ban qilish</b>\n\n"
        "Foydalanuvchi ID sini kiriting:\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_ban_user(update, context):
    from users import ban_user
    if not context.user_data.get("banning_user"):
        return
    
    user_id = update.message.text.strip()
    
    if is_admin(user_id):
        await update.message.reply_text("❌ <b>Adminni ban qilish mumkin emas!</b>", parse_mode='HTML')
        del context.user_data["banning_user"]
        return
    
    ban_user(user_id)
    del context.user_data["banning_user"]
    await update.message.reply_text(f"🚫 <b>{user_id}</b> bloklandi!", parse_mode='HTML')

async def start_unban_user(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    users = get_users()
    banned = [(uid, u) for uid, u in users.items() if u.get("banned")]
    
    if not banned:
        from utils import get_admin_keyboard
        await query.edit_message_text("✅ <b>Bloklangan foydalanuvchilar yo'q!</b>", reply_markup=get_admin_keyboard(str(query.from_user.id)), parse_mode='HTML')
        return
    
    keyboard = []
    for uid, u in banned[:20]:
        name = u.get("first_name", "Nomlum")
        keyboard.append([InlineKeyboardButton(f"♻️ {name[:20]} ({uid})", callback_data=f"unban_user_{uid}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    await query.edit_message_text("♻️ <b>Blokdan ochish uchun tanlang:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def unban_user_handler(query, user_id: str):
    from users import unban_user
    unban_user(user_id)
    await query.answer("✅ Foydalanuvchi blokdan chiqarildi!", show_alert=True)
    await start_unban_user(query)

async def create_backup(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    try:
        backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copytree("data", backup_dir)
        from utils import get_admin_keyboard
        await query.edit_message_text(
            f"✅ <b>Backup yaratildi!</b>\n\n"
            f"📁 <b>Papka:</b> <code>{backup_dir}</code>",
            reply_markup=get_admin_keyboard(str(query.from_user.id)),
            parse_mode='HTML'
        )
    except Exception as e:
        from utils import get_admin_keyboard
        await query.edit_message_text(
            f"❌ <b>Backup xatosi:</b>\n<code>{e}</code>",
            reply_markup=get_admin_keyboard(str(query.from_user.id)),
            parse_mode='HTML'
        )

async def export_data(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    import os
    sent = 0
    for filename in [USERS_FILE, MOVIES_FILE, CHANNELS_FILE]:
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                await query.message.reply_document(f, caption=f"📁 {os.path.basename(filename)}")
                sent += 1
    
    from utils import get_admin_keyboard
    await query.edit_message_text(
        f"✅ <b>Export yakunlandi!</b>\n\n"
        f"📤 <b>Yuborilgan fayllar:</b> {sent} ta",
        reply_markup=get_admin_keyboard(str(query.from_user.id)),
        parse_mode='HTML'
    )

async def start_add_admin(query, context):
    if not is_super_admin(str(query.from_user.id)):
        await query.answer("🚫 Faqat super admin!", show_alert=True)
        return
    
    context.user_data["adding_admin"] = True
    await query.edit_message_text(
        "👮 <b>Admin qo'shish</b>\n\n"
        "Yangi admin ID sini kiriting:\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_add_admin(update, context):
    if not context.user_data.get("adding_admin"):
        return
    
    new_id = update.message.text.strip()
    
    if new_id == str(update.effective_user.id):
        await update.message.reply_text("❌ <b>O'zingizni emas!</b>", parse_mode='HTML')
        del context.user_data["adding_admin"]
        return
    
    admins = get_admins()
    if new_id in admins:
        await update.message.reply_text("❌ <b>Allaqachon admin!</b>", parse_mode='HTML')
        del context.user_data["adding_admin"]
        return
    
    admins[new_id] = {
        "role": "admin",
        "added_at": datetime.now().isoformat(),
        "added_by": str(update.effective_user.id),
        "source": "manual"
    }
    save_admins(admins)
    del context.user_data["adding_admin"]
    await update.message.reply_text(f"✅ <b>{new_id}</b> admin qilindi!", parse_mode='HTML')

async def start_remove_admin(query):
    if not is_super_admin(str(query.from_user.id)):
        await query.answer("🚫 Faqat super admin!", show_alert=True)
        return
    
    admins = get_admins()
    removable = [(aid, a) for aid, a in admins.items() 
                 if a.get("source") == "manual" and aid != str(query.from_user.id)]
    
    if not removable:
        from utils import get_admin_keyboard
        await query.edit_message_text("✅ <b>O'chiriladigan admin yo'q!</b>", reply_markup=get_admin_keyboard(str(query.from_user.id)), parse_mode='HTML')
        return
    
    keyboard = []
    for aid, a in removable:
        keyboard.append([InlineKeyboardButton(f"❌ {aid}", callback_data=f"rem_admin_{aid}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    await query.edit_message_text("❌ <b>O'chirish uchun tanlang:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def remove_admin_handler(query, admin_id: str):
    admins = get_admins()
    if admin_id in admins and admins[admin_id].get("source") == "manual":
        del admins[admin_id]
        save_admins(admins)
        await query.answer("✅ Admin o'chirildi!", show_alert=True)
    await start_remove_admin(query)
