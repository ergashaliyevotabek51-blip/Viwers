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
    total_channels = len(get_channels())
    total_admins = len(get_admins())
    
    # Statistika hisoblash
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

# ==================== KINO QO'SHISH (TO'G'RILANGAN) ====================

async def start_add_movie(query, context):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    # User data tozalash
    context.user_data.pop("adding_movie", None)
    
    context.user_data["adding_movie"] = {"step": "forward"}
    
    text = (
        f"➕ <b>YANGI KINO QO'SHISH</b>\n\n"
        f"📋 <b>Qo'llanma:</b>\n"
        f"1️⃣ Kanalingizga kiring\n"
        f"2️⃣ Kino postini <b>forward</b> qiling (shu yerga)\n"
        f"3️⃣ Kod, nom va janr kiriting\n\n"
        f"⚠️ <i>Bot kanalda admin bo'lishi shart!</i>\n\n"
        f"❌ Bekor qilish: /cancel"
    )
    
    await query.edit_message_text(text, parse_mode='HTML')

async def process_add_movie(update, context):
    from movies import add_movie
    
    if "adding_movie" not in context.user_data:
        return
    
    user_data = context.user_data["adding_movie"]
    step = user_data.get("step", "forward")
    
    # Forward qilish bosqichi
    if step == "forward" and update.message.forward_from_chat:
        try:
            channel_id = update.message.forward_from_chat.id
            message_id = update.message.forward_from_message_id
            
            # Tekshirish - bot kanalda adminmi?
            try:
                chat_member = await context.bot.get_chat_member(channel_id, context.bot.id)
                if chat_member.status not in ['administrator', 'creator']:
                    await update.message.reply_text(
                        "❌ <b>Xatolik!</b>\n\n"
                        "🤖 Bot ushbu kanalda <b>admin</b> emas!\n"
                        "➡️ Avval botni kanalga admin qiling.",
                        parse_mode='HTML'
                    )
                    context.user_data.pop("adding_movie", None)
                    return
            except Exception as e:
                print(f"Admin tekshirish xatosi: {e}")
            
            user_data["channel_id"] = channel_id
            user_data["message_id"] = message_id
            user_data["step"] = "code"
            
            await update.message.reply_text(
                "✅ <b>Kino posti saqlandi!</b>\n\n"
                "📝 Endi <b>kod</b> kiriting:\n"
                "<i>Masalan: uzb001, film2024</i>",
                parse_mode='HTML'
            )
            return
            
        except Exception as e:
            print(f"Forward qabul qilish xatosi: {e}")
            await update.message.reply_text(
                "❌ <b>Forward qabul qilishda xatolik!</b>\n"
                "Qayta urinib ko'ring.",
                parse_mode='HTML'
            )
            return
    
    # Kod kiritish bosqichi
    elif step == "code":
        code = update.message.text.strip().lower()
        movies = get_movies()
        
        if code in movies:
            await update.message.reply_text(
                "❌ <b>Bu kod allaqachon mavjud!</b>\n\n"
                f"Mavjud kod: <code>{code}</code>\n"
                f"Film: {movies[code].get('name', 'Noma\'lum')}\n\n"
                f"📝 <b>Boshqa kod kiriting:</b>",
                parse_mode='HTML'
            )
            return
        
        user_data["code"] = code
        user_data["step"] = "name"
        
        await update.message.reply_text(
            f"✅ Kod: <code>{code}</code>\n\n"
            f"🎬 Endi <b>film nomini</b> to'liq yozing:",
            parse_mode='HTML'
        )
        return
    
    # Nom kiritish bosqichi
    elif step == "name":
        name = update.message.text.strip()
        user_data["name"] = name
        user_data["step"] = "genre"
        
        await update.message.reply_text(
            f"✅ Nomi: <b>{name}</b>\n\n"
            f"🎭 <b>Janr</b> kiriting:\n"
            f"<i>Masalan: Drama, Komediya, Sarguzasht</i>\n"
            f"Yoki <code>skip</code> deb yozing:",
            parse_mode='HTML'
        )
        return
    
    # Janr kiritish bosqichi
    elif step == "genre":
        genre_text = update.message.text.strip()
        genre = "" if genre_text.lower() == "skip" else genre_text
        
        # Kino saqlash
        try:
            add_movie(
                user_data["code"],
                user_data["name"],
                genre,
                user_data["channel_id"],
                user_data["message_id"],
                str(update.effective_user.id)
            )
            
            # Tozalash
            context.user_data.pop("adding_movie", None)
            
            genre_display = f"🎭 {genre}" if genre else "🎬 Belgilanmagan"
            
            success_text = (
                f"✅ <b>KINO MUVAFFAQIYATLI QO'SHILDI!</b>\n\n"
                f"🎬 <b>Kod:</b> <code>{user_data['code']}</code>\n"
                f"📝 <b>Nomi:</b> {user_data['name']}\n"
                f"{genre_display}\n"
                f"📅 <b>Sana:</b> {datetime.now().strftime('%d.%m.%Y')}\n\n"
                f"🚀 Film endi katalogda!"
            )
            
            from utils import get_admin_keyboard
            await update.message.reply_text(
                success_text,
                reply_markup=get_admin_keyboard(str(update.effective_user.id)),
                parse_mode='HTML'
            )
            
        except Exception as e:
            print(f"Kino saqlash xatosi: {e}")
            await update.message.reply_text(
                f"❌ <b>Kino saqlashda xatolik!</b>\n\n"
                f"<code>{e}</code>\n\n"
                f"Qayta urinib ko'ring.",
                parse_mode='HTML'
            )
            context.user_data.pop("adding_movie", None)
        return
    
    # Noto'g'ri xabar
    else:
        await update.message.reply_text(
            "❌ <b>Noto'g'ri amal!</b>\n\n"
            "Iltimos, /cancel yozib qayta boshlang.",
            parse_mode='HTML'
        )

# ==================== BOSHQA FUNKSiyalar ====================

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
            f"🎬 {name[:25]}{'...' if len(name) > 25 else ''} ({code}) 👁{views}", 
            callback_data=f"del_movie_{code}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    
    await query.edit_message_text(
        "➖ <b>KINO O'CHIRISH</b>\n\n"
        "O'chirish uchun kinoni tanlang:\n"
        f"<i>Jami: {len(movies)} ta kino</i>",
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='HTML'
    )

async def delete_movie(query, movie_code: str):
    from movies import delete_movie as remove_movie
    
    if remove_movie(movie_code):
        await query.answer("✅ Kino o'chirildi!", show_alert=True)
    else:
        await query.answer("❌ Xatolik yuz berdi!", show_alert=True)
    
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
    
    # Oxirgi 7 kun statistikasi (agar ma'lumot bo'lsa)
    recent_movies = sorted(
        movies.items(), 
        key=lambda x: x[1].get("added_at", ""), 
        reverse=True
    )[:5]
    
    recent_text = ""
    for code, data in recent_movies:
        date = data.get("added_at", "Noma'lum")[:10]
        recent_text += f"• {data.get('name', code)[:20]} ({date})\n"
    
    text = (
        f"📊 <b>BATAFSIL STATISTIKA</b>\n"
        f"➖➖➖➖➖➖➖➖➖➖\n\n"
        f"👥 <b>Foydalanuvchilar:</b> <code>{total_users}</code>\n"
        f"🎬 <b>Kinolar:</b> <code>{total_movies}</code>\n"
        f"👁 <b>Jami ko'rishlar:</b> <code>{total_views}</code>\n"
        f"📢 <b>Kanallar:</b> <code>{len(channels)}</code>\n"
        f"👮 <b>Adminlar:</b> <code>{len(admins)}</code>\n"
        f"🚫 <b>Bloklangan:</b> <code>{banned}</code>\n\n"
        f"🆕 <b>So'nggi qo'shilgan filmlar:</b>\n"
        f"{recent_text if recent_text else 'Ma\'lumot yo\'q'}"
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
        "📢 <b>MASS XABAR YUBORISH</b>\n\n"
        "📤 Yuboriladigan xabarni kiriting:\n"
        "(Matn, rasm, video yoki boshqa har qanday kontent)\n\n"
        "⚠️ <i>Eslatma: Bu barcha foydalanuvchilarga yuboriladi!</i>\n\n"
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
    blocked = 0
    
    status = await update.message.reply_text(
        f"📤 <b>Yuborilmoqda...</b>\n"
        f"Jami: {len(users)} foydalanuvchi",
        parse_mode='HTML'
    )
    
    for user_id in users:
        try:
            await update.message.copy(chat_id=int(user_id))
            sent += 1
        except Exception as e:
            failed += 1
            if "blocked" in str(e).lower():
                blocked += 1
        
        # Har 50 ta xabardan keyin yangilash
        if (sent + failed) % 50 == 0:
            try:
                await status.edit_text(
                    f"📤 <b>Yuborilmoqda...</b>\n"
                    f"✅ Muvaffaqiyatli: {sent}\n"
                    f"❌ Xatolik: {failed}\n"
                    f"🚫 Bloklangan: {blocked}",
                    parse_mode='HTML'
                )
            except:
                pass
    
    await status.edit_text(
        f"✅ <b>BROADCAST YAKUNLANDI!</b>\n\n"
        f"📊 <b>Natijalar:</b>\n"
        f"├ ✅ Muvaffaqiyatli: <code>{sent}</code>\n"
        f"├ ❌ Xatolik: <code>{failed}</code>\n"
        f"└ 🚫 Bloklangan: <code>{blocked}</code>\n\n"
        f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        parse_mode='HTML'
    )

async def manage_channels(query):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    channels = get_channels()
    
    if not channels:
        text = (
            f"🔒 <b>MAJBURIY OBUNA</b>\n\n"
            f"📭 <i>Hozircha kanallar qo'shilmagan</i>\n\n"
            f"➕ Kanal qo'shish tugmasini bosing"
        )
    else:
        text = (
            f"🔒 <b>MAJBURIY OBUNA KANALLARI</b>\n\n"
            f"📢 <b>Jami:</b> <code>{len(channels)}</code> ta kanal\n\n"
            f"<i>O'chirish uchun kanalni tanlang:</i>"
        )
    
    from utils import get_channels_keyboard
    await query.edit_message_text(text, reply_markup=get_channels_keyboard(), parse_mode='HTML')

async def start_add_channel(query, context):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    context.user_data["adding_channel"] = True
    
    await query.edit_message_text(
        "➕ <b>KANAL QO'SHISH</b>\n\n"
        "Quyidagi variantlardan birini yuboring:\n\n"
        "1️⃣ <b>Username:</b> <code>@channelname</code>\n"
        "2️⃣ <b>Link:</b> <code>https://t.me/channelname</code>\n"
        "3️⃣ <b>ID:</b> <code>-1001234567890</code>\n\n"
        "⚠️ <i>Bot kanalda admin bo'lishi shart!</i>\n\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_add_channel(update, context):
    if not context.user_data.get("adding_channel"):
        return
    
    text = update.message.text.strip()
    
    try:
        # Username yoki linkdan chat olish
        if text.startswith('https://t.me/'):
            username = '@' + text.split('/')[-1].split('?')[0]
            chat = await context.bot.get_chat(username)
        elif text.startswith('@'):
            chat = await context.bot.get_chat(text)
        else:
            chat = await context.bot.get_chat(int(text))
        
        # Bot adminligini tekshirish
        try:
            member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if member.status not in ['administrator', 'creator']:
                await update.message.reply_text(
                    "❌ <b>Xatolik!</b>\n\n"
                    "🤖 Bot ushbu kanalda admin emas!\n"
                    "➡️ Avval botni kanalga admin qiling.",
                    parse_mode='HTML'
                )
                return
        except Exception as e:
            print(f"Admin tekshirish xatosi: {e}")
        
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
            f"✅ <b>KANAL QO'SHILDI!</b>\n\n"
            f"📢 <b>Nomi:</b> {chat.title}\n"
            f"🆔 <b>ID:</b> <code>{chat.id}</code>\n"
            f"🔗 <b>Link:</b> {invite_link or 'Mavjud emas'}\n\n"
            f"🔒 Majburiy obunada qo'shildi.",
            parse_mode='HTML'
        )
        
    except Exception as e:
        print(f"Kanal qo'shish xatosi: {e}")
        await update.message.reply_text(
            f"❌ <b>Kanal qo'shishda xatolik!</b>\n\n"
            f"🔍 Sabab: Bot kanalda admin emas yoki noto'g'ri username/ID\n"
            f"<code>{e}</code>",
            parse_mode='HTML'
        )

async def remove_channel_handler(query, channel_id: str):
    from subscription import remove_channel
    
    if remove_channel(channel_id):
        await query.answer("✅ Kanal o'chirildi!", show_alert=True)
    else:
        await query.answer("❌ Xatolik!", show_alert=True)
    
    await manage_channels(query)

async def start_add_limit(query, context):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    context.user_data["adding_limit"] = {"step": "user"}
    
    await query.edit_message_text(
        "💠 <b>LIMIT QO'SHISH</b>\n\n"
        "Foydalanuvchi ID sini kiriting:\n"
        "<i>Masalan: 123456789</i>\n\n"
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
            await update.message.reply_text(
                "❌ <b>Foydalanuvchi topilmadi!</b>\n\n"
                "ID ni qayta tekshiring:",
                parse_mode='HTML'
            )
            return
        
        context.user_data["adding_limit"]["target_user"] = user_id
        context.user_data["adding_limit"]["step"] = "amount"
        
        await update.message.reply_text(
            f"✅ Foydalanuvchi: <code>{user_id}</code>\n\n"
            f"💠 Endi <b>limit miqdorini</b> kiriting:\n"
            f"<i>Masalan: 10, 50, 100</i>",
            parse_mode='HTML'
        )
    
    elif step == "amount":
        try:
            amount = int(update.message.text.strip())
            target = context.user_data["adding_limit"]["target_user"]
            
            add_limit(target, amount)
            del context.user_data["adding_limit"]
            
            await update.message.reply_text(
                f"✅ <b>Limit qo'shildi!</b>\n\n"
                f"👤 Foydalanuvchi: <code>{target}</code>\n"
                f"💠 Qo'shildi: <code>+{amount}</code>\n"
                f"📅 Sana: {datetime.now().strftime('%d.%m.%Y')}",
                parse_mode='HTML'
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ <b>Faqat raqam kiriting!</b>\n\n"
                "Qayta urinib ko'ring:",
                parse_mode='HTML'
            )

async def start_ban_user(query, context):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    context.user_data["banning_user"] = True
    
    await query.edit_message_text(
        "👤 <b>USER BAN QILISH</b>\n\n"
        "🚫 Bloklash uchun foydalanuvchi ID sini kiriting:\n"
        "<i>Masalan: 123456789</i>\n\n"
        "⚠️ <i>Adminlarni ban qilish mumkin emas!</i>\n\n"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_ban_user(update, context):
    from users import ban_user
    
    if not context.user_data.get("banning_user"):
        return
    
    user_id = update.message.text.strip()
    
    if is_admin(user_id):
        await update.message.reply_text(
            "❌ <b>Adminni ban qilish mumkin emas!</b>",
            parse_mode='HTML'
        )
        del context.user_data["banning_user"]
        return
    
    ban_user(user_id)
    del context.user_data["banning_user"]
    
    await update.message.reply_text(
        f"🚫 <b>FOYDALANUVCHI BLOKLANDI!</b>\n\n"
        f"👤 ID: <code>{user_id}</code>\n"
        f"📅 Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        f"♻️ Blokdan ochish: Admin panel → Unban",
        parse_mode='HTML'
    )

async def start_unban_user(query):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    users = get_users()
    banned = [(uid, u) for uid, u in users.items() if u.get("banned")]
    
    if not banned:
        from utils import get_admin_keyboard
        await query.edit_message_text(
            "✅ <b>Bloklangan foydalanuvchilar yo'q!</b>", 
            reply_markup=get_admin_keyboard(str(query.from_user.id)), 
            parse_mode='HTML'
        )
        return
    
    keyboard = []
    for uid, u in banned[:20]:
        name = u.get("first_name", "Nomlum")
        username = u.get("username", "Noma'lum")
        keyboard.append([InlineKeyboardButton(
            f"♻️ {name[:15]}{'...' if len(name) > 15 else ''} (@{username[:10]}) [{uid}]", 
            callback_data=f"unban_user_{uid}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    
    await query.edit_message_text(
        "♻️ <b>BLOKDAN OCHISH</b>\n\n"
        f"🚫 <b>Jami bloklangan:</b> <code>{len(banned)}</code>\n\n"
        f"<i>Ochish uchun foydalanuvchini tanlang:</i>",
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='HTML'
    )

async def unban_user_handler(query, user_id: str):
    from users import unban_user
    
    unban_user(user_id)
    
    await query.answer(
        f"✅ Foydalanuvchi blokdan chiqarildi!\n\nID: {user_id}", 
        show_alert=True
    )
    
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
            f"📦 <b>BACKUP YARATILDI!</b>\n\n"
            f"📁 Papka: <code>{backup_dir}</code>\n"
            f"📅 Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"✅ Barcha ma'lumotlar nusxalandi.",
            reply_markup=get_admin_keyboard(str(query.from_user.id)),
            parse_mode='HTML'
        )
        
    except Exception as e:
        from utils import get_admin_keyboard
        await query.edit_message_text(
            f"❌ <b>Backup xatosi!</b>\n\n"
            f"<code>{e}</code>",
            reply_markup=get_admin_keyboard(str(query.from_user.id)),
            parse_mode='HTML'
        )

async def export_data(query):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    import os
    
    sent = 0
    files = [USERS_FILE, MOVIES_FILE, CHANNELS_FILE]
    file_names = ["👥 Foydalanuvchilar", "🎬 Kinolar", "📢 Kanallar"]
    
    for filename, name in zip(files, file_names):
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                await query.message.reply_document(
                    f, 
                    caption=f"{name} - {datetime.now().strftime('%d.%m.%Y')}"
                )
                sent += 1
    
    from utils import get_admin_keyboard
    await query.edit_message_text(
        f"📤 <b>EXPORT YAKUNLANDI!</b>\n\n"
        f"📁 Yuborilgan fayllar: <code>{sent}</code> ta\n"
        f"📅 Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        reply_markup=get_admin_keyboard(str(query.from_user.id)),
        parse_mode='HTML'
    )

# ==================== SUPER ADMIN ====================

async def start_add_admin(query, context):
    if not is_super_admin(str(query.from_user.id)):
        await query.answer("🚫 Faqat Super Admin!", show_alert=True)
        return
    
    context.user_data["adding_admin"] = True
    
    await query.edit_message_text(
        f"👑 <b>YANGI ADMIN QO'SHISH</b>\n\n"
        f"🆔 Foydalanuvchi ID sini kiriting:\n"
        f"<i>Masalan: 123456789</i>\n\n"
        f"⚠️ <i>Diqqat: Yangi admin barcha funksiyalarga kirish huquqiga ega bo'ladi!</i>\n\n"
        f"❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )

async def process_add_admin(update, context):
    if not context.user_data.get("adding_admin"):
        return
    
    new_id = update.message.text.strip()
    
    if new_id == str(update.effective_user.id):
        await update.message.reply_text(
            "❌ <b>O'zingizni admin qila olmaysiz!</b>",
            parse_mode='HTML'
        )
        del context.user_data["adding_admin"]
        return
    
    admins = get_admins()
    
    if new_id in admins:
        await update.message.reply_text(
            "❌ <b>Bu foydalanuvchi allaqachon admin!</b>",
            parse_mode='HTML'
        )
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
    
    await update.message.reply_text(
        f"👑 <b>YANGI ADMIN QO'SHILDI!</b>\n\n"
        f"🆔 ID: <code>{new_id}</code>\n"
        f"📅 Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"👤 Qo'shdi: <code>{update.effective_user.id}</code>\n\n"
        f"✅ Endi u admin panelidan foydalanishi mumkin.",
        parse_mode='HTML'
    )

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
            "✅ <b>O'chiriladigan admin yo'q!</b>\n\n"
            "<i>Faqat qo'lda qo'shilgan adminlar o'chirilishi mumkin.</i>", 
            reply_markup=get_admin_keyboard(str(query.from_user.id)), 
            parse_mode='HTML'
        )
        return
    
    keyboard = []
    for aid, a in removable:
        added_at = a.get("added_at", "Noma'lum")[:10]
        keyboard.append([InlineKeyboardButton(
            f"❌ {aid} (qo'shilgan: {added_at})", 
            callback_data=f"rem_admin_{aid}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
    
    await query.edit_message_text(
        "👑 <b>ADMIN O'CHIRISH</b>\n\n"
        f"👮 <b>Jami adminlar:</b> <code>{len(admins)}</code>\n"
        f"❌ <b>O'chirish mumkin:</b> <code>{len(removable)}</code>\n\n"
        f"<i>O'chirish uchun adminni tanlang:</i>",
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='HTML'
    )

async def remove_admin_handler(query, admin_id: str):
    admins = get_admins()
    
    if admin_id in admins and admins[admin_id].get("source") == "manual":
        del admins[admin_id]
        save_admins(admins)
        await query.answer(
            f"✅ Admin o'chirildi!\n\nID: {admin_id}", 
            show_alert=True
        )
    else:
        await query.answer("❌ O'chirish mumkin emas!", show_alert=True)
    
    await start_remove_admin(query)
