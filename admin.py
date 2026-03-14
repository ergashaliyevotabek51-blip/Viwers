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
        f"{crown} <b>{role}</b> {crown}
"
        f"➖➖➖➖➖➖➖➖➖➖
"
        f"📅 <b>Sana:</b> <code>{today}</code>

"
        f"{color} <b>📊 ASOSIY STATISTIKA</b>
"
        f"├ 👥 Foydalanuvchilar: <code>{total_users}</code>
"
        f"├ 🎬 Kinolar: <code>{total_movies}</code>
"
        f"├ 👁 Ko'rishlar: <code>{total_views}</code>
"
        f"├ 📢 Kanallar: <code>{total_channels}</code>
"
        f"├ 👮 Adminlar: <code>{total_admins}</code>
"
        f"└ 🚫 Bloklangan: <code>{banned}</code>

"
        f"⚡️ <i>Quyidagi tugmalardan foydalaning:</i>"
    )

    from utils import get_admin_keyboard
    await query.edit_message_text(text, reply_markup=get_admin_keyboard(user_id), parse_mode='HTML')

# ==================== KINO QO'SHISH - FAQAT LINK ORQALI ====================

async def start_add_movie(query, context):
    """Kino qo'shish - Faqat link orqali"""
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return

    context.user_data.pop("adding_movie", None)
    context.user_data["adding_movie"] = {"step": "link"}

    await query.edit_message_text(
        "➕ <b>YANGI KINO QO'SHISH</b>

"
        "🔗 <b>Telegram post linkini yuboring:</b>

"
        "<i>Misollar:</i>
"
        "<code>https://t.me/c/1234567890/42</code>
"
        "<code>https://t.me/mychannel/42</code>
"
        "<code>https://t.me/mychannel/42?single</code>

"
        "❌ Bekor qilish: /cancel",
        parse_mode='HTML'
    )


async def process_add_movie(update, context):
    """Linkdan avtomatik ID ajratish"""
    try:
        from movies import add_movie as movies_add_movie
    except ImportError:
        await update.message.reply_text("❌ <b>Tizim xatosi!</b>", parse_mode='HTML')
        context.user_data.pop("adding_movie", None)
        return

    if "adding_movie" not in context.user_data:
        return

    user_data = context.user_data["adding_movie"]
    step = user_data.get("step", "link")
    text = update.message.text.strip() if update.message.text else ""

    # ========== LINK QABUL QILISH ==========
    if step == "link":
        if not text:
            await update.message.reply_text("❌ <b>Link yuboring!</b>", parse_mode='HTML')
            return

        if not text.startswith('https://t.me/'):
            await update.message.reply_text(
                "❌ <b>Noto'g'ri link!</b>

"
                "<i>To'g'ri format:</i>
"
                "<code>https://t.me/c/1234567890/42</code>
"
                "<code>https://t.me/kanal_nomi/42</code>",
                parse_mode='HTML'
            )
            return

        try:
            # Linkdan ID larni ajratish
            # https://t.me/c/1234567890/42?single -> c/1234567890/42
            url_parts = text.replace('https://t.me/', '').split('?')[0]
            parts = url_parts.split('/')

            print(f"DEBUG: Link parts = {parts}")

            channel_id = None
            message_id = None

            if len(parts) >= 2:
                if parts[0] == 'c' and len(parts) >= 3:
                    # Private kanal: https://t.me/c/1234567890/42
                    channel_id = int('-100' + parts[1])
                    message_id = int(parts[2]) if len(parts) > 2 else 1
                else:
                    # Public kanal: https://t.me/kanal_nomi/42
                    username = '@' + parts[0]
                    chat = await context.bot.get_chat(username)
                    channel_id = chat.id
                    message_id = int(parts[1]) if len(parts) > 1 else 1

            if not channel_id or not message_id:
                raise ValueError("Kanal ID yoki xabar ID ajratilmadi")

            print(f"DEBUG: channel_id={channel_id}, message_id={message_id}")

            # Tekshirish - xabar mavjudmi?
            try:
                await context.bot.forward_message(
                    chat_id=update.effective_chat.id,
                    from_chat_id=channel_id,
                    message_id=message_id
                )
                # Test muvaffaqiyatli
            except Exception as e:
                print(f"Tekshirish xatosi: {e}")
                # Ogohlantirish bilan davom etamiz
                await update.message.reply_text(
                    f"⚠️ <b>Eslatma:</b> Xabarni tekshirib bo'lmadi
"
                    f"<code>{e}</code>

"
                    f"Davom etish uchun <b>ha</b> yozing yoki /cancel",
                    parse_mode='HTML'
                )
                user_data["temp_channel_id"] = channel_id
                user_data["temp_message_id"] = message_id
                user_data["step"] = "confirm"
                return

            # Saqlash
            user_data["channel_id"] = channel_id
            user_data["message_id"] = message_id
            user_data["link"] = text.split('?')[0]  # Toza link
            user_data["step"] = "code"

            await update.message.reply_text(
                "✅ <b>Link qabul qilindi!</b>

"
                f"📢 Kanal: <code>{channel_id}</code>
"
                f"🆔 Xabar: <code>{message_id}</code>

"
                "📝 <b>Kod kiriting:</b>
"
                "<i>Masalan: uzb001</i>",
                parse_mode='HTML'
            )
            return

        except Exception as e:
            print(f"Link tahlil xatosi: {e}")
            await update.message.reply_text(
                f"❌ <b>Linkni tushunib bo'lmadi!</b>

"
                f"<code>{e}</code>

"
                f"🔗 <b>To'g'ri link yuboring:</b>
"
                f"<code>https://t.me/c/1234567890/42</code>",
                parse_mode='HTML'
            )
            return

    # ========== TASDIQLASH ==========
    elif step == "confirm":
        if text.lower() in ['ha', 'yes', 'ok']:
            user_data["channel_id"] = user_data.get("temp_channel_id")
            user_data["message_id"] = user_data.get("temp_message_id")
            user_data["step"] = "code"
            del user_data["temp_channel_id"]
            del user_data["temp_message_id"]

            await update.message.reply_text(
                "✅ <b>Davom etamiz!</b>

"
                "📝 <b>Kod kiriting:</b>",
                parse_mode='HTML'
            )
        else:
            context.user_data.pop("adding_movie", None)
            await update.message.reply_text("❌ Bekor qilindi.", parse_mode='HTML')
        return

    # ========== KOD ==========
    elif step == "code":
        if not text:
            await update.message.reply_text("❌ <b>Kod kiriting!</b>", parse_mode='HTML')
            return

        code = text.lower()
        movies = get_movies()

        if code in movies:
            movie_name = movies[code].get('name', 'Nomalum')
            await update.message.reply_text(
                f"❌ <b>Bu kod mavjud!</b>

"
                f"🎬 {movie_name}
"
                f"📝 Boshqa kod:",
                parse_mode='HTML'
            )
            return

        user_data["code"] = code
        user_data["step"] = "name"

        await update.message.reply_text(
            f"✅ Kod: <code>{code}</code>

"
            "🎬 <b>Film nomi:</b>",
            parse_mode='HTML'
        )
        return

    # ========== NOM ==========
    elif step == "name":
        if not text:
            await update.message.reply_text("❌ <b>Nom kiriting!</b>", parse_mode='HTML')
            return

        user_data["name"] = text
        user_data["step"] = "genre"

        await update.message.reply_text(
            f"✅ Nomi: <b>{text}</b>

"
            "🎭 <b>Janr</b> (yo'q bo'lsa <code>skip</code>):",
            parse_mode='HTML'
        )
        return

    # ========== JANR ==========
    elif step == "genre":
        genre = "" if text.lower() == "skip" else text

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

            success_text = (
                f"✅ <b>KINO QO'SHILDI!</b>

"
                f"🎬 <b>Kod:</b> <code>{user_data['code']}</code>
"
                f"📝 <b>Nomi:</b> {user_data['name']}
"
                f"🎭 <b>Janr:</b> {genre or 'Belgilanmagan'}
"
                f"🔗 <b>Link:</b> {user_data.get('link', 'Nomalum')}
"
                f"📅 <b>Sana:</b> {datetime.now().strftime('%d.%m.%Y')}"
            )

            from utils import get_admin_keyboard
            await update.message.reply_text(
                success_text,
                reply_markup=get_admin_keyboard(str(update.effective_user.id)),
                parse_mode='HTML',
                disable_web_page_preview=True
            )

        except Exception as e:
            print(f"Saqlash xatosi: {e}")
            await update.message.reply_text(
                f"❌ <b>Xatolik:</b> <code>{e}</code>",
                parse_mode='HTML'
            )
            context.user_data.pop("adding_movie", None)
        return

    else:
        await update.message.reply_text("❌ <b>Xatolik!</b> /cancel", parse_mode='HTML')
        context.user_data.pop("adding_movie", None)

# ==================== KINO O'CHIRISH - PAGINATION BILAN ====================

# Har sahifada ko'rsatiladigan kinolar soni
MOVIES_PER_PAGE = 20

async def start_delete_movie(query, context, page: int = 1):
    """Kino o'chirish paneli - Pagination bilan"""
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

    # Pagination hisoblash
    total_movies = len(movies)
    total_pages = (total_movies + MOVIES_PER_PAGE - 1) // MOVIES_PER_PAGE  # Yuqoriga yaxlitlash

    # Sahifa chegaralarini tekshirish
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    # Joriy sahifadagi kinolarni olish
    start_idx = (page - 1) * MOVIES_PER_PAGE
    end_idx = start_idx + MOVIES_PER_PAGE

    # Kinolarni ro'yxatga olish (sorted qilib)
    movie_items = list(movies.items())
    current_movies = movie_items[start_idx:end_idx]

    # Klaviatura yaratish
    keyboard = []

    # Kino tugmalari
    for code, data in current_movies:
        name = data.get('name', code)
        views = data.get('views', 0)
        # Uzun nomlarni qisqartirish
        display_name = name[:25] + "..." if len(name) > 25 else name

        keyboard.append([InlineKeyboardButton(
            f"🎬 {display_name} ({code}) 👁{views}", 
            callback_data=f"del_movie_{code}_page_{page}"
        )])

    # Pagination tugmalari (bir qatorda)
    nav_buttons = []

    # Oldingi sahifa
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(
            "◀️ Oldingi", 
            callback_data=f"delete_movie_page_{page-1}"
        ))

    # Joriy sahifa / Jami
    nav_buttons.append(InlineKeyboardButton(
        f"📄 {page}/{total_pages}", 
        callback_data="ignore"
    ))

    # Keyingi sahifa
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(
            "Keyingi ▶️", 
            callback_data=f"delete_movie_page_{page+1}"
        ))

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Statistika tugmasi
    keyboard.append([InlineKeyboardButton(
        f"📊 Jami: {total_movies} ta kino", 
        callback_data="ignore"
    )])

    # Orqaga tugmasi
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])

    await query.edit_message_text(
        "➖ <b>KINO O'CHIRISH</b>

"
        f"📄 <b>Sahifa:</b> <code>{page}</code> / <code>{total_pages}</code>
"
        f"📊 <b>Jami kinolar:</b> <code>{total_movies}</code> ta

"
        "🎬 <i>O'chirish uchun kinoni tanlang:</i>",
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='HTML'
    )


async def process_delete_movie_callback(query, context):
    """Kino o'chirish callbacklarini qayta ishlash"""
    data = query.data

    # Sahifa almashish
    if data.startswith("delete_movie_page_"):
        page = int(data.split("_")[-1])
        await start_delete_movie(query, context, page)
        await query.answer(f"📄 Sahifa {page}")
        return

    # Kino o'chirish tasdiqlash
    if data.startswith("del_movie_"):
        # Format: del_movie_{code}_page_{page} yoki del_movie_{code}
        parts = data.split("_")
        movie_code = parts[2]
        page = 1

        # Agar page bo'lsa, uni olish
        if len(parts) >= 5 and parts[3] == "page":
            page = int(parts[4])

        await confirm_delete_movie(query, context, movie_code, page)
        return

    # Tasdiqlashdan keyin o'chirish
    if data.startswith("confirm_delete_"):
        movie_code = data.replace("confirm_delete_", "")
        await final_delete_movie(query, context, movie_code)
        return


async def confirm_delete_movie(query, context, movie_code: str, page: int = 1):
    """Kino o'chirishni tasdiqlash oynasi"""
    movies = get_movies()

    if movie_code not in movies:
        await query.answer("❌ Kino topilmadi!", show_alert=True)
        return

    movie_data = movies[movie_code]
    name = movie_data.get('name', 'Noma'lum')
    views = movie_data.get('views', 0)

    keyboard = [
        [InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"confirm_delete_{movie_code}")],
        [InlineKeyboardButton("❌ Yo'q, bekor qilish", callback_data=f"delete_movie_page_{page}")]
    ]

    await query.edit_message_text(
        f"⚠️ <b>O'CHIRISHNI TASDIQLANG</b>

"
        f"🎬 <b>Kino:</b> {name}
"
        f"📝 <b>Kod:</b> <code>{movie_code}</code>
"
        f"👁 <b>Ko'rishlar:</b> {views}

"
        f"❗ <b>Diqqat:</b> Bu amalni qaytarib bo'lmaydi!

"
        f"Rostdan ham o'chirmoqchimisiz?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    await query.answer()


async def final_delete_movie(query, context, movie_code: str):
    """Kino o'chirishni yakunlash"""
    from movies import delete_movie as remove_movie

    if remove_movie(movie_code):
        await query.answer("✅ Kino o'chirildi!", show_alert=True)
        # O'chirgandan keyin yana o'sha sahifaga qaytish
        # Agar o'sha sahifada kinolar qolmasa, oldingi sahifaga o'tish
        movies = get_movies()
        total_pages = (len(movies) + MOVIES_PER_PAGE - 1) // MOVIES_PER_PAGE

        # Joriy sahifani aniqlash (avvalgi callbackdan)
        # Hozircha 1-sahifaga qaytish
        await start_delete_movie(query, context, page=1)
    else:
        await query.answer("❌ Xatolik yuz berdi!", show_alert=True)

# ==================== STATISTIKA ====================

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
        f"📊 <b>STATISTIKA</b>
"
        f"➖➖➖➖➖➖➖➖➖➖

"
        f"👥 Foydalanuvchilar: <code>{total_users}</code>
"
        f"🎬 Kinolar: <code>{total_movies}</code>
"
        f"👁 Ko'rishlar: <code>{total_views}</code>
"
        f"📢 Kanallar: <code>{len(channels)}</code>
"
        f"👮 Adminlar: <code>{len(admins)}</code>
"
        f"🚫 Bloklangan: <code>{banned}</code>"
    )

    from utils import get_admin_keyboard
    await query.edit_message_text(
        text, 
        reply_markup=get_admin_keyboard(str(query.from_user.id)), 
        parse_mode='HTML'
    )

# ==================== BROADCAST ====================

async def start_broadcast(query, context):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return

    context.user_data["broadcasting"] = True

    await query.edit_message_text(
        "📢 <b>BROADCAST</b>

"
        "Yuboriladigan xabarni kiriting:

"
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
        f"✅ <b>Yakunlandi!</b>

"
        f"✓ Muvaffaqiyatli: <code>{sent}</code>
"
        f"✗ Xatolik: <code>{failed}</code>",
        parse_mode='HTML'
    )

# ==================== KANALLAR ====================

async def manage_channels(query):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return

    channels = get_channels()

    if not channels:
        text = "🔒 <b>MAJBURIY OBUNA</b>

📭 Kanallar yo'q"
    else:
        text = f"🔒 <b>MAJBURIY OBUNA</b>

📢 Jami: <code>{len(channels)}</code> ta"

    from utils import get_channels_keyboard
    await query.edit_message_text(text, reply_markup=get_channels_keyboard(), parse_mode='HTML')

async def start_add_channel(query, context):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return

    context.user_data["adding_channel"] = True

    await query.edit_message_text(
        "➕ <b>KANAL QO'SHISH</b>

"
        "Username yoki link yuboring:
"
        "<i>@channel yoki https://t.me/channel</i>

"
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
            f"✅ <b>Kanal qo'shildi!</b>

"
            f"📢 {chat.title}
"
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

# ==================== LIMIT ====================

async def start_add_limit(query, context):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return

    context.user_data["adding_limit"] = {"step": "user"}

    await query.edit_message_text(
        "💠 <b>LIMIT QO'SHISH</b>

"
        "Foydalanuvchi ID:

"
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

# ==================== BAN/UNBAN ====================

async def start_ban_user(query, context):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return

    context.user_data["banning_user"] = True

    await query.edit_message_text(
        "👤 <b>BAN</b>

"
        "Foydalanuvchi ID:

"
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
        "♻️ <b>UNBAN</b>

"
        f"Jami: <code>{len(banned)}</code>

"
        "Tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='HTML'
    )

async def unban_user_handler(query, user_id: str):
    from users import unban_user

    unban_user(user_id)
    await query.answer("✅ Blokdan chiqarildi!", show_alert=True)
    await start_unban_user(query)

# ==================== BACKUP/EXPORT ====================

async def create_backup(query):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return

    try:
        backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copytree("data", backup_dir)

        from utils import get_admin_keyboard
        await query.edit_message_text(
            f"📦 <b>Backup yaratildi!</b>

"
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
        f"📤 <b>Export yakunlandi!</b>

"
        f"📁 Fayllar: <code>{sent}</code>",
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
        "👑 <b>ADMIN QO'SHISH</b>

"
        "Yangi admin ID:

"
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
        "👑 <b>ADMIN O'CHIRISH</b>

"
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
