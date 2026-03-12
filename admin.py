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

# ==================== ASOSIY ADMIN PANEL ====================

async def show_admin_panel(query, user_id: str):
    """Admin panelni ko'rsatish"""
    if not is_admin(user_id):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    total_users = len(get_users())
    total_movies = len(get_movies())
    total_channels = len(get_channels())
    total_admins = len(get_admins())
    
    users = get_users()
    movies = get_movies()
    banned = sum(1 for u in users.values() if u.get("banned"))
    total_views = sum(m.get("views", 0) for m in movies.values())
    
    today = datetime.now().strftime("%d.%m.%Y")
    
    if is_super_admin(user_id):
        role = "👑 SUPER ADMIN"
        crown = "👑"
        color = "🟡"
    else:
        role = "👮 ADMIN"
        crown = "👮"
        color = "🔵"
    
    text = (
        f"{crown} <b>{role}</b> {crown}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"📅 <b>Sana:</b> <code>{today}</code>\n\n"
        f"{color} <b>📊 ASOSIY STATISTIKA</b>\n"
        f"├ 👥 Foydalanuvchilar: <code>{total_users}</code>\n"
        f"├ 🎬 Kinolar: <code>{total_movies}</code>\n"
        f"├ 👁 Ko'rishlar: <code>{total_views}</code>\n"
        f"├ 📢 Kanallar: <code>{total_channels}</code>\n"
        f"├ 👮 Adminlar: <code>{total_admins}</code>\n"
        f"└ 🚫 Bloklangan: <code>{banned}</code>\n\n"
        f"⚡️ <i>Quyidagi tugmalardan foydalaning:</i>"
    )
    
    from utils import get_admin_keyboard
    await query.edit_message_text(text, reply_markup=get_admin_keyboard(user_id), parse_mode='HTML')

# ==================== KINO QO'SHISH (ANIQ ISHLAYDIGAN) ====================

async def start_add_movie(query, context):
    """Kino qo'shishni boshlash"""
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    # Tozalash
    if "adding_movie" in context.user_data:
        del context.user_data["adding_movie"]
    
    context.user_data["adding_movie"] = {"step": "forward"}
    
    text = (
        "➕ <b>YANGI KINO QO'SHISH</b>\n\n"
        "📋 <b>Qo'llanma:</b>\n"
        "1️⃣ Kanalingizga kiring\n"
        "2️⃣ Kino postini <b>forward</b> qiling\n"
        "3️⃣ Kod, nom va janr kiriting\n\n"
        "⚠️ <i>Bot kanalda admin bo'lishi shart!</i>\n\n"
        "❌ Bekor qilish: /cancel"
    )
    
    await query.edit_message_text(text, parse_mode='HTML')


async def process_add_movie(update, context):
    """Kino qo'shish jarayoni - TO'G'RI ISHLAYDIGAN"""
    try:
        from movies import add_movie as movies_add_movie
    except ImportError as e:
        print(f"ERROR: movies modulini import qilishda xato: {e}")
        await update.message.reply_text("❌ <b>Tizim xatosi!</b>", parse_mode='HTML')
        context.user_data.pop("adding_movie", None)
        return
    
    # Tekshirish
    if "adding_movie" not in context.user_data:
        print("DEBUG: adding_movie yo'q")
        return
    
    user_data = context.user_data["adding_movie"]
    step = user_data.get("step", "forward")
    
    print(f"DEBUG: Step = {step}")
    print(f"DEBUG: Has forward = {update.message.forward_from_chat is not None}")
    print(f"DEBUG: Has text = {update.message.text is not None}")
    
    # ========== FORWARD QABUL QILISH ==========
    if step == "forward":
        # Forward qilinganmi tekshirish - TEXT emas, FORWARD tekshiriladi!
        if not update.message.forward_from_chat:
            # Bu yerda text bo'lishi mumkin yoki bo'lmasligi mumkin
            # Asosiy forward yo'qligi
            await update.message.reply_text(
                "❌ <b>Iltimos, kanaldan kino forward qiling!</b>\n\n"
                "📤 Kanaldan postni ushlab turib, shu yerga yuboring.\n\n"
                "❌ Bekor qilish: /cancel",
                parse_mode='HTML'
            )
            return
        
        # ✅ FORWARD QABUL QILINDI!
        try:
            channel_id = update.message.forward_from_chat.id
            message_id = update.message.forward_from_message_id
            
            print(f"DEBUG: ✅ Forward qabul qilindi!")
            print(f"DEBUG: Channel ID = {channel_id}, Message ID = {message_id}")
            
            # Bot adminligini tekshirish
            try:
                chat_member = await context.bot.get_chat_member(channel_id, context.bot.id)
                print(f"DEBUG: Bot status = {chat_member.status}")
                
                if chat_member.status not in ['administrator', 'creator']:
                    await update.message.reply_text(
                        "❌ <b>Xatolik!</b>\n\n"
                        "🤖 Bot ushbu kanalda <b>admin</b> emas!\n"
                        "➡️ Avval botni kanalga admin qiling.\n\n"
                        "❌ Bekor qilish: /cancel",
                        parse_mode='HTML'
                    )
                    context.user_data.pop("adding_movie", None)
                    return
            except Exception as e:
                print(f"Admin tekshirish xatosi: {e}")
                # Ogohlantirish bilan davom etamiz
                pass
            
            # Saqlash
            user_data["channel_id"] = channel_id
            user_data["message_id"] = message_id
            user_data["step"] = "code"
            
            # ✅ MUHIM: Xabar yuborish
            await update.message.reply_text(
                "✅ <b>Kino posti qabul qilindi!</b>\n\n"
                f"📢 Kanal ID: <code>{channel_id}</code>\n"
                f"🆔 Xabar ID: <code>{message_id}</code>\n\n"
                "📝 Endi <b>kod</b> kiriting:\n"
                "<i>Masalan: uzb001</i>\n\n"
                "❌ Bekor qilish: /cancel",
                parse_mode='HTML'
            )
            print("DEBUG: ✅ Kod kiritish xabari yuborildi")
            return
            
        except Exception as e:
            print(f"ERROR Forward qabul qilishda: {e}")
            await update.message.reply_text(
                f"❌ <b>Xatolik:</b> <code>{e}</code>\n\n"
                "Qayta urinib ko'ring.",
                parse_mode='HTML'
            )
            return
    
    # ========== KOD KIRITISH ==========
    elif step == "code":
        # ✅ ENDI TEXT TEKSHIRILADI!
        if not update.message.text:
            await update.message.reply_text(
                "❌ <b>Iltimos, matn kiriting!</b>\n\n"
                "📝 <b>Kod</b> yozing:\n"
                "<i>Masalan: uzb001</i>\n\n"
                "❌ Bekor qilish: /cancel",
                parse_mode='HTML'
            )
            return
        
        code = update.message.text.strip().lower()
        
        if not code:
            await update.message.reply_text(
                "❌ <b>Kod bo'sh bo'lishi mumkin emas!</b>\n\n"
                "Qayta kiriting:",
                parse_mode='HTML'
            )
            return
        
        movies = get_movies()
        
        if code in movies:
            movie_name = movies[code].get('name', 'Nomalum')
            await update.message.reply_text(
                "❌ <b>Bu kod allaqachon mavjud!</b>\n\n"
                f"🎬 Film: <b>{movie_name}</b>\n"
                f"📝 <b>Boshqa kod kiriting:</b>",
                parse_mode='HTML'
            )
            return
        
        user_data["code"] = code
        user_data["step"] = "name"
        
        await update.message.reply_text(
            f"✅ Kod: <code>{code}</code>\n\n"
            f"🎬 Endi <b>film nomini</b> yozing:",
            parse_mode='HTML'
        )
        return
    
    # ========== NOM KIRITISH ==========
    elif step == "name":
        if not update.message.text:
            await update.message.reply_text(
                "❌ <b>Iltimos, nom kiriting!</b>",
                parse_mode='HTML'
            )
            return
        
        name = update.message.text.strip()
        
        if not name:
            await update.message.reply_text(
                "❌ <b>Nom bo'sh bo'lishi mumkin emas!</b>",
                parse_mode='HTML'
            )
            return
        
        user_data["name"] = name
        user_data["step"] = "genre"
        
        await update.message.reply_text(
            f"✅ Nomi: <b>{name}</b>\n\n"
            f"🎭 <b>Janr</b> kiriting (yo'q bo'lsa <code>skip</code>):",
            parse_mode='HTML'
        )
        return
    
    # ========== JANR KIRITISH ==========
    elif step == "genre":
        genre_text = update.message.text.strip() if update.message.text else ""
        genre = "" if genre_text.lower() == "skip" else genre_text
        
        try:
            movies_add_movie(
                user_data["code"],
                user_data["name"],
                genre,
                user_data["channel_id"],
                user_data["message_id"],
                str(update.effective_user.id)
            )
            
            context.user_data.pop("adding_movie", None)
            
            genre_display = f"🎭 {genre}" if genre else "🎬 Belgilanmagan"
            
            success_text = (
                f"✅ <b>KINO QO'SHILDI!</b>\n\n"
                f"🎬 <b>Kod:</b> <code>{user_data['code']}</code>\n"
                f"📝 <b>Nomi:</b> {user_data['name']}\n"
                f"{genre_display}\n"
                f"📅 <b>Sana:</b> {datetime.now().strftime('%d.%m.%Y')}"
            )
            
            from utils import get_admin_keyboard
            await update.message.reply_text(
                success_text,
                reply_markup=get_admin_keyboard(str(update.effective_user.id)),
                parse_mode='HTML'
            )
            
        except Exception as e:
            print(f"ERROR Kino saqlashda: {e}")
            await update.message.reply_text(
                f"❌ <b>Xatolik:</b> <code>{e}</code>",
                parse_mode='HTML'
            )
            context.user_data.pop("adding_movie", None)
        return
    
    # ========== NOTO'G'RI STEP ==========
    else:
        print(f"ERROR: Noto'g'ri step: {step}")
        await update.message.reply_text(
            "❌ <b>Xatolik!</b> /cancel yozing.",
            parse_mode='HTML'
        )
        context.user_data.pop("adding_movie", None)



# ==================== QOLGAN FUNKSiyalar ====================

async def start_delete_movie(query):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    movies = get_movies()
    if not movies:
        from utils import get_admin_keyboard
        await query.edit_message_text(
            "🎬 <b>Kinolar mavjud emas!</b>", 
            reply_markup=get_admin_keyboard(str(query.from_user.id)), 
            parse_mode='HTML'
        )
        return
    
    keyboard = []
    for code, data in list(movies.items())[:20]:
        name = data.get('name', code)
        views = data.get('views', 0)
        keyboard.append([InlineKeyboardButton(
            f"🎬 {name[:25]} ({code}) 👁{views}", 
            callback_data=f"del_movie_{code}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    
    await query.edit_message_text(
        "➖ <b>KINO O'CHIRISH</b>\n\n"
        f"<i>Jami: {len(movies)} ta</i>",
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='HTML'
    )

async def delete_movie(query, movie_code: str):
    from movies import delete_movie as remove_movie
    
    if remove_movie(movie_code):
        await query.answer("✅ Kino o'chirildi!", show_alert=True)
    else:
        await query.answer("❌ Xatolik!", show_alert=True)
    
    await start_delete_movie(query)

async def show_stats(query):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    users = get_users()
    movies = get_movies()
    channels = get_channels()
    admins = get_admins()
    
    total_users = len(users)
    total_movies = len(movies)
    total_views = sum(m.get("views", 0) for m in movies.values())
    banned = sum(1 for u in users.values() if u.get("banned"))
    
    text = (
        f"📊 <b>STATISTIKA</b>\n"
        f"➖➖➖➖➖➖➖➖➖➖\n\n"
        f"👥 Foydalanuvchilar: <code>{total_users}</code>\n"
        f"🎬 Kinolar: <code>{total_movies}</code>\n"
        f"👁 Ko'rishlar: <code>{total_views}</code>\n"
        f"📢 Kanallar: <code>{len(channels)}</code>\n"
        f"👮 Adminlar: <code>{len(admins)}</code>\n"
        f"🚫 Bloklangan: <code>{banned}</code>"
    )
    
    from utils import get_admin_keyboard
    await query.edit_message_text(
        text, 
        reply_markup=get_admin_keyboard(str(query.from_user.id)), 
        parse_mode='HTML'
    )

async def start_broadcast(query, context):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    context.user_data["broadcasting"] = True
    
    await query.edit_message_text(
        "📢 <b>BROADCAST</b>\n\n"
        "Yuboriladigan xabarni kiriting:\n\n"
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
    
    status = await update.message.reply_text("📤 Yuborilmoqda...", parse_mode='HTML')
    
    for user_id in users:
        try:
            await update.message.copy(chat_id=int(user_id))
            sent += 1
        except:
            failed += 1
    
    await status.edit_text(
        f"✅ <b>Yakunlandi!</b>\n\n"
        f"✓ Muvaffaqiyatli: <code>{sent}</code>\n"
        f"✗ Xatolik: <code>{failed}</code>",
        parse_mode='HTML'
    )

async def manage_channels(query):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    channels = get_channels()
    
    if not channels:
        text = "🔒 <b>MAJBURIY OBUNA</b>\n\n📭 Kanallar yo'q"
    else:
        text = f"🔒 <b>MAJBURIY OBUNA</b>\n\n📢 Jami: <code>{len(channels)}</code> ta"
    
    from utils import get_channels_keyboard
    await query.edit_message_text(text, reply_markup=get_channels_keyboard(), parse_mode='HTML')

async def start_add_channel(query, context):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    context.user_data["adding_channel"] = True
    
    await query.edit_message_text(
        "➕ <b>KANAL QO'SHISH</b>\n\n"
        "Username yoki link yuboring:\n"
        "<i>@channel yoki https://t.me/channel</i>\n\n"
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
        
        add_channel(str(chat.id), chat.title, invite_link)
        del context.user_data["adding_channel"]
        
        await update.message.reply_text(
            f"✅ <b>Kanal qo'shildi!</b>\n\n"
            f"📢 {chat.title}\n"
            f"🆔 <code>{chat.id}</code>",
            parse_mode='HTML'
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ <b>Xatolik:</b> <code>{e}</code>", parse_mode='HTML')

async def remove_channel_handler(query, channel_id: str):
    from subscription import remove_channel
    
    if remove_channel(channel_id):
        await query.answer("✅ Kanal o'chirildi!", show_alert=True)
    
    await manage_channels(query)

async def start_add_limit(query, context):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    context.user_data["adding_limit"] = {"step": "user"}
    
    await query.edit_message_text(
        "💠 <b>LIMIT QO'SHISH</b>\n\n"
        "Foydalanuvchi ID:\n\n"
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
            await update.message.reply_text("❌ Foydalanuvchi topilmadi!", parse_mode='HTML')
            return
        
        context.user_data["adding_limit"]["target_user"] = user_id
        context.user_data["adding_limit"]["step"] = "amount"
        
        await update.message.reply_text("✅ Limit miqdorini kiriting:", parse_mode='HTML')
    
    elif step == "amount":
        try:
            amount = int(update.message.text.strip())
            target = context.user_data["adding_limit"]["target_user"]
            add_limit(target, amount)
            del context.user_data["adding_limit"]
            
            await update.message.reply_text(
                f"✅ <b>{target}</b> ga <code>+{amount}</code> limit qo'shildi!",
                parse_mode='HTML'
            )
            
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam!", parse_mode='HTML')

async def start_ban_user(query, context):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    context.user_data["banning_user"] = True
    
    await query.edit_message_text(
        "👤 <b>BAN</b>\n\n"
        "Foydalanuvchi ID:\n\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_ban_user(update, context):
    from users import ban_user
    
    if not context.user_data.get("banning_user"):
        return
    
    user_id = update.message.text.strip()
    
    if is_admin(user_id):
        await update.message.reply_text("❌ Adminni ban qilish mumkin emas!", parse_mode='HTML')
        del context.user_data["banning_user"]
        return
    
    ban_user(user_id)
    del context.user_data["banning_user"]
    
    await update.message.reply_text(f"🚫 <b>{user_id}</b> bloklandi!", parse_mode='HTML')

async def start_unban_user(query):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    users = get_users()
    banned = [(uid, u) for uid, u in users.items() if u.get("banned")]
    
    if not banned:
        from utils import get_admin_keyboard
        await query.edit_message_text(
            "✅ Bloklanganlar yo'q!", 
            reply_markup=get_admin_keyboard(str(query.from_user.id)), 
            parse_mode='HTML'
        )
        return
    
    keyboard = []
    for uid, u in banned[:20]:
        name = u.get("first_name", "Nomlum")
        keyboard.append([InlineKeyboardButton(
            f"♻️ {name[:20]} ({uid})", 
            callback_data=f"unban_user_{uid}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    
    await query.edit_message_text(
        "♻️ <b>UNBAN</b>\n\n"
        f"Jami: <code>{len(banned)}</code>\n\n"
        "Tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='HTML'
    )

async def unban_user_handler(query, user_id: str):
    from users import unban_user
    
    unban_user(user_id)
    await query.answer("✅ Blokdan chiqarildi!", show_alert=True)
    await start_unban_user(query)

async def create_backup(query):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    try:
        backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copytree("data", backup_dir)
        
        from utils import get_admin_keyboard
        await query.edit_message_text(
            f"📦 <b>Backup yaratildi!</b>\n\n"
            f"📁 <code>{backup_dir}</code>",
            reply_markup=get_admin_keyboard(str(query.from_user.id)),
            parse_mode='HTML'
        )
        
    except Exception as e:
        from utils import get_admin_keyboard
        await query.edit_message_text(
            f"❌ <b>Xatolik:</b> <code>{e}</code>",
            reply_markup=get_admin_keyboard(str(query.from_user.id)),
            parse_mode='HTML'
        )

async def export_data(query):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    import os
    
    sent = 0
    for filename in [USERS_FILE, MOVIES_FILE, CHANNELS_FILE]:
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                await query.message.reply_document(f)
                sent += 1
    
    from utils import get_admin_keyboard
    await query.edit_message_text(
        f"📤 <b>Export yakunlandi!</b>\n\n"
        f"📁 Fayllar: <code>{sent}</code>",
        reply_markup=get_admin_keyboard(str(query.from_user.id)),
        parse_mode='HTML'
    )

async def start_add_admin(query, context):
    if not is_super_admin(str(query.from_user.id)):
        await query.answer("🚫 Faqat Super Admin!", show_alert=True)
        return
    
    context.user_data["adding_admin"] = True
    
    await query.edit_message_text(
        "👑 <b>ADMIN QO'SHISH</b>\n\n"
        "Yangi admin ID:\n\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_add_admin(update, context):
    if not context.user_data.get("adding_admin"):
        return
    
    new_id = update.message.text.strip()
    
    if new_id == str(update.effective_user.id):
        await update.message.reply_text("❌ O'zingizni emas!", parse_mode='HTML')
        del context.user_data["adding_admin"]
        return
    
    admins = get_admins()
    
    if new_id in admins:
        await update.message.reply_text("❌ Allaqachon admin!", parse_mode='HTML')
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
        await query.answer("🚫 Faqat Super Admin!", show_alert=True)
        return
    
    admins = get_admins()
    removable = [(aid, a) for aid, a in admins.items() 
                 if a.get("source") == "manual" and aid != str(query.from_user.id)]
    
    if not removable:
        from utils import get_admin_keyboard
        await query.edit_message_text(
            "✅ O'chiriladigan admin yo'q!", 
            reply_markup=get_admin_keyboard(str(query.from_user.id)), 
            parse_mode='HTML'
        )
        return
    
    keyboard = []
    for aid, a in removable:
        keyboard.append([InlineKeyboardButton(f"❌ {aid}", callback_data=f"rem_admin_{aid}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    
    await query.edit_message_text(
        "👑 <b>ADMIN O'CHIRISH</b>\n\n"
        "Tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='HTML'
    )

async def remove_admin_handler(query, admin_id: str):
    admins = get_admins()
    
    if admin_id in admins and admins[admin_id].get("source") == "manual":
        del admins[admin_id]
        save_admins(admins)
        await query.answer("✅ Admin o'chirildi!", show_alert=True)
    
    await start_remove_admin(query)
