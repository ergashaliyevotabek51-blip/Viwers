async def start_add_movie(query, context):
    """Kino qo'shish - Faqat link orqali"""
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    context.user_data.pop("adding_movie", None)
    context.user_data["adding_movie"] = {"step": "link"}
    
    await query.edit_message_text(
        "➕ <b>YANGI KINO QO'SHISH</b>\n\n"
        "🔗 <b>Telegram post linkini yuboring:</b>\n\n"
        "<i>Misollar:</i>\n"
        "<code>https://t.me/c/1234567890/42</code>\n"
        "<code>https://t.me/mychannel/42</code>\n"
        "<code>https://t.me/mychannel/42?single</code>\n\n"
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
        
        # Link formatini tekshirish
        if not text.startswith('https://t.me/'):
            await update.message.reply_text(
                "❌ <b>Noto'g'ri link!</b>\n\n"
                "<i>To'g'ri format:</i>\n"
                "<code>https://t.me/...</code>",
                parse_mode='HTML'
            )
            return
        
        try:
            # Linkdan ID larni ajratish
            # https://t.me/c/1234567890/42?single
            # https://t.me/mychannel/42
            # https://t.me/mychannel/42/comment/123
            
            url_parts = text.replace('https://t.me/', '').split('?')[0]  # ?single ni olib tashlash
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
                    # Public kanal: https://t.me/kanal/42
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
                # Muvaffaqiyatli - test xabarni o'chirish mumkin
            except Exception as e:
                print(f"Tekshirish xatosi: {e}")
                # Ogohlantirish bilan davom etamiz
                await update.message.reply_text(
                    f"⚠️ <b>Eslatma:</b> Xabarni tekshirib bo'lmadi\n"
                    f"<code>{e}</code>\n\n"
                    f"Davom etish uchun <b>ha</b> yozing",
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
                "✅ <b>Link qabul qilindi!</b>\n\n"
                f"📢 Kanal: <code>{channel_id}</code>\n"
                f"🆔 Xabar: <code>{message_id}</code>\n\n"
                "📝 <b>Kod kiriting:</b>\n"
                "<i>Masalan: uzb001</i>",
                parse_mode='HTML'
            )
            return
            
        except Exception as e:
            print(f"Link tahlil xatosi: {e}")
            await update.message.reply_text(
                f"❌ <b>Linkni tushunib bo'lmadi!</b>\n\n"
                f"<code>{e}</code>\n\n"
                f"🔗 <b>To'g'ri link yuboring:</b>\n"
                f"<code>https://t.me/c/1234567890/42</code>",
                parse_mode='HTML'
            )
            return
    
    # ========== TASDIQLASH (agar kerak bo'lsa) ==========
    elif step == "confirm":
        if text.lower() in ['ha', 'yes', 'ok']:
            user_data["channel_id"] = user_data.get("temp_channel_id")
            user_data["message_id"] = user_data.get("temp_message_id")
            user_data["step"] = "code"
            del user_data["temp_channel_id"]
            del user_data["temp_message_id"]
            
            await update.message.reply_text(
                "✅ <b>Davom etamiz!</b>\n\n"
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
                f"❌ <b>Bu kod mavjud!</b>\n\n"
                f"🎬 {movie_name}\n"
                f"📝 Boshqa kod:",
                parse_mode='HTML'
            )
            return
        
        user_data["code"] = code
        user_data["step"] = "name"
        
        await update.message.reply_text(
            f"✅ Kod: <code>{code}</code>\n\n"
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
            f"✅ Nomi: <b>{text}</b>\n\n"
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
                f"✅ <b>KINO QO'SHILDI!</b>\n\n"
                f"🎬 <b>Kod:</b> <code>{user_data['code']}</code>\n"
                f"📝 <b>Nomi:</b> {user_data['name']}\n"
                f"🎭 <b>Janr:</b> {genre or 'Belgilanmagan'}\n"
                f"🔗 <b>Link:</b> {user_data.get('link', 'Nomalum')}\n"
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
