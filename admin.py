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
        await query.answer("Ruxsat yo'q!", show_alert=True)
        return
    
    total_users = len(get_users())
    total_movies = len(get_movies())
    
    role = "Super Admin" if is_super_admin(user_id) else "Admin"
    
    text = (
        f"Admin panel\n"
        f"Status: {role}\n\n"
        f"Foydalanuvchilar: {total_users}\n"
        f"Kinolar: {total_movies}\n"
        f"Kanallar: {len(get_channels())}"
    )
    
    from utils import get_admin_keyboard
    await query.edit_message_text(text, reply_markup=get_admin_keyboard(user_id))

async def start_add_movie(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["adding_movie"] = {"step": "forward"}
    await query.edit_message_text(
        "Kino qo'shish:\n\n"
        "1. Kanaldan film forward qiling\n"
        "2. Kod kiriting (masalan: uzb001)\n"
        "3. Film nomini yozing\n"
        "4. Janr kiriting (ixtiyoriy)\n\n"
        "Bekor qilish: /cancel"
    )

async def process_add_movie(update, context):
    from movies import add_movie
    user_data = context.user_data.get("adding_movie", {})
    step = user_data.get("step")
    
    if update.message.forward_from_chat:
        user_data["channel_id"] = update.message.forward_from_chat.id
        user_data["message_id"] = update.message.forward_from_message_id
        user_data["step"] = "code"
        await update.message.reply_text("Saqlandi! Endi kod kiriting:")
    
    elif step == "code":
        code = update.message.text.strip().lower()
        movies = get_movies()
        if code in movies:
            await update.message.reply_text("Bu kod allaqachon mavjud! Boshqa kod:")
            return
        user_data["code"] = code
        user_data["step"] = "name"
        await update.message.reply_text("Kod saqlandi! Film nomini yozing:")
    
    elif step == "name":
        user_data["name"] = update.message.text.strip()
        user_data["step"] = "genre"
        await update.message.reply_text("Nom saqlandi! Janr kiriting (yo'q bo'lsa 'skip' deb yozing):")
    
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
        await update.message.reply_text(
            f"Kino qo'shildi!\n\nKod: {user_data['code']}\nNomi: {user_data['name']}",
            reply_markup=get_admin_keyboard(str(update.effective_user.id))
        )

async def start_delete_movie(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    movies = get_movies()
    if not movies:
        from utils import get_admin_keyboard
        await query.edit_message_text("Kinolar mavjud emas!", reply_markup=get_admin_keyboard(str(query.from_user.id)))
        return
    
    keyboard = []
    for code, data in list(movies.items())[:20]:
        keyboard.append([InlineKeyboardButton(f"{data.get('name', code)} ({code})", callback_data=f"del_movie_{code}")])
    
    keyboard.append([InlineKeyboardButton("Orqaga", callback_data="admin_panel")])
    await query.edit_message_text("O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_movie(query, movie_code: str):
    from movies import delete_movie as remove_movie
    if remove_movie(movie_code):
        await query.answer("Kino o'chirildi!", show_alert=True)
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
        f"Statistika:\n\n"
        f"Foydalanuvchilar: {total_users}\n"
        f"Kinolar: {total_movies}\n"
        f"Ko'rishlar: {views}\n"
        f"Bloklangan: {banned}"
    )
    
    from utils import get_admin_keyboard
    await query.edit_message_text(text, reply_markup=get_admin_keyboard(str(query.from_user.id)))

async def start_broadcast(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["broadcasting"] = True
    await query.edit_message_text("Broadcast xabarini kiriting:\nBekor qilish: /cancel")

async def process_broadcast(update, context):
    if not context.user_data.get("broadcasting"):
        return
    
    del context.user_data["broadcasting"]
    
    users = get_users()
    sent = 0
    failed = 0
    
    status = await update.message.reply_text("Yuborilmoqda...")
    
    for user_id in users:
        try:
            await update.message.copy(chat_id=int(user_id))
            sent += 1
        except:
            failed += 1
    
    await status.edit_text(f"Yakunlandi! Muvaffaqiyatli: {sent}, Xatolik: {failed}")

async def manage_channels(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    from utils import get_channels_keyboard
    await query.edit_message_text("Kanallar:", reply_markup=get_channels_keyboard())

async def start_add_channel(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["adding_channel"] = True
    await query.edit_message_text("Kanal ID sini yuboring (masalan: -1001234567890):\nBekor: /cancel")

async def process_add_channel(update, context):
    if not context.user_data.get("adding_channel"):
        return
    
    channel_id = update.message.text.strip()
    
    try:
        chat = await context.bot.get_chat(channel_id)
        from subscription import add_channel
        add_channel(
            str(chat.id),
            chat.title,
            chat.invite_link or (f"https://t.me/{chat.username}" if chat.username else "")
        )
        del context.user_data["adding_channel"]
        await update.message.reply_text(f"Kanal qo'shildi: {chat.title}")
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")

async def remove_channel_handler(query, channel_id: str):
    from subscription import remove_channel
    if remove_channel(channel_id):
        await query.answer("Kanal o'chirildi!", show_alert=True)
    await manage_channels(query)

async def start_add_limit(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["adding_limit"] = {"step": "user"}
    await query.edit_message_text("Foydalanuvchi ID sini kiriting:\nBekor: /cancel")

async def process_add_limit(update, context):
    from users import add_limit
    user_data = context.user_data.get("adding_limit", {})
    step = user_data.get("step")
    
    if step == "user":
        user_id = update.message.text.strip()
        if user_id not in get_users():
            await update.message.reply_text("Foydalanuvchi topilmadi!")
            return
        context.user_data["adding_limit"]["target_user"] = user_id
        context.user_data["adding_limit"]["step"] = "amount"
        await update.message.reply_text("Limit miqdorini kiriting:")
    
    elif step == "amount":
        try:
            amount = int(update.message.text.strip())
            target = context.user_data["adding_limit"]["target_user"]
            add_limit(target, amount)
            del context.user_data["adding_limit"]
            await update.message.reply_text(f"{target} ga {amount} limit qo'shildi!")
        except ValueError:
            await update.message.reply_text("Raqam kiriting!")

async def start_ban_user(query, context):
    if not is_admin(str(query.from_user.id)):
        return
    
    context.user_data["banning_user"] = True
    await query.edit_message_text("Foydalanuvchi ID sini kiriting:\nBekor: /cancel")

async def process_ban_user(update, context):
    from users import ban_user
    if not context.user_data.get("banning_user"):
        return
    
    user_id = update.message.text.strip()
    
    if is_admin(user_id):
        await update.message.reply_text("Adminni ban qilish mumkin emas!")
        del context.user_data["banning_user"]
        return
    
    ban_user(user_id)
    del context.user_data["banning_user"]
    await update.message.reply_text(f"{user_id} bloklandi!")

async def start_unban_user(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    users = get_users()
    banned = [(uid, u) for uid, u in users.items() if u.get("banned")]
    
    if not banned:
        from utils import get_admin_keyboard
        await query.edit_message_text("Bloklanganlar yo'q!", reply_markup=get_admin_keyboard(str(query.from_user.id)))
        return
    
    keyboard = []
    for uid, u in banned[:20]:
        name = u.get("first_name", "Nomlum")
        keyboard.append([InlineKeyboardButton(f"Ochirish {name} ({uid})", callback_data=f"unban_user_{uid}")])
    
    keyboard.append([InlineKeyboardButton("Orqaga", callback_data="admin_panel")])
    await query.edit_message_text("Tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

async def unban_user_handler(query, user_id: str):
    from users import unban_user
    unban_user(user_id)
    await query.answer("Blokdan chiqarildi!", show_alert=True)
    await start_unban_user(query)

async def create_backup(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    try:
        backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copytree("data", backup_dir)
        await query.answer(f"Backup: {backup_dir}", show_alert=True)
    except Exception as e:
        await query.answer("Xatolik!", show_alert=True)

async def export_data(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    import os
    for filename in [USERS_FILE, MOVIES_FILE, CHANNELS_FILE]:
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                await query.message.reply_document(f)

async def start_add_admin(query, context):
    if not is_super_admin(str(query.from_user.id)):
        await query.answer("Faqat super admin!", show_alert=True)
        return
    
    context.user_data["adding_admin"] = True
    await query.edit_message_text("Yangi admin ID:\nBekor: /cancel")

async def process_add_admin(update, context):
    if not context.user_data.get("adding_admin"):
        return
    
    new_id = update.message.text.strip()
    
    if new_id == str(update.effective_user.id):
        await update.message.reply_text("O'zingizni emas!")
        del context.user_data["adding_admin"]
        return
    
    admins = get_admins()
    if new_id in admins:
        await update.message.reply_text("Allaqachon admin!")
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
    await update.message.reply_text(f"{new_id} admin qilindi!")

async def start_remove_admin(query):
    if not is_super_admin(str(query.from_user.id)):
        await query.answer("Faqat super admin!", show_alert=True)
        return
    
    admins = get_admins()
    removable = [(aid, a) for aid, a in admins.items() 
                 if a.get("source") == "manual" and aid != str(query.from_user.id)]
    
    if not removable:
        from utils import get_admin_keyboard
        await query.edit_message_text("O'chiriladigan admin yo'q!", reply_markup=get_admin_keyboard(str(query.from_user.id)))
        return
    
    keyboard = []
    for aid, a in removable:
        keyboard.append([InlineKeyboardButton(f"O'chirish {aid}", callback_data=f"rem_admin_{aid}")])
    
    keyboard.append([InlineKeyboardButton("Orqaga", callback_data="admin_panel")])
    await query.edit_message_text("Tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

async def remove_admin_handler(query, admin_id: str):
    admins = get_admins()
    if admin_id in admins and admins[admin_id].get("source") == "manual":
        del admins[admin_id]
        save_admins(admins)
        await query.answer("Admin o'chirildi!", show_alert=True)
    await start_remove_admin(query)
