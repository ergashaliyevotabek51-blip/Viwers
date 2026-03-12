# ==================== KINO QO'SHISH (TO'LIQ TO'G'RILANGAN) ====================

async def start_add_movie(query, context):
    if not is_admin(str(query.from_user.id)):
        await query.answer("🚫 Ruxsat yo'q!", show_alert=True)
        return
    
    # Tozalash
    context.user_data.pop("adding_movie", None)
    context.user_data["adding_movie"] = {"step": "forward"}
    
    text = (
        "➕ <b>YANGI KINO QO'SHISH</b>\n\n"
        "📋 <b>Qo'llanma:</b>\n"
        "1️⃣ Kanalingizga kiring\n"
        "2️⃣ Kino postini <b>forward</b> qiling (shu yerga)\n"
        "3️⃣ Kod, nom va janr kiriting\n\n"
        "⚠️ <i>Bot kanalda admin bo'lishi shart!</i>\n\n"
        "❌ Bekor qilish: /cancel"
    )
    
    await query.edit_message_text(text, parse_mode='HTML')


async def process_add_movie(update, context):
    from movies import add_movie
    
    if "adding_movie" not in context.user_data:
        print("DEBUG: adding_movie yo'q")
        return
    
    user_data = context.user_data["adding_movie"]
    step = user_data.get("step", "forward")
    
    print(f"DEBUG: Step = {step}")
    print(f"DEBUG: Forward = {update.message.forward_from_chat is not None}")
    
    # FORWARD QABUL QILISH
    if step == "forward":
        if not update.message.forward_from_chat:
            await update.message.reply_text(
                "❌ <b>Iltimos, kanaldan kino forward qiling!</b>\n\n"
                "📤 Kanalingizga kiring, kino postini ushlab turib, "
                "shu yerga yuboring (forward).\n\n"
                "❌ Bekor qilish: /cancel",
                parse_mode='HTML'
            )
            return
        
        try:
            channel_id = update.message.forward_from_chat.id
            message_id = update.message.forward_from_message_id
            
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
                # Davom etamiz, lekin ogohlantirish
                await update.message.reply_text(
                    "⚠️ <b>Ogohlantirish:</b> Bot adminligini tekshirib bo'lmadi.\n"
                    "Agar kanalda admin bo'lmasa, kino ishlamaydi!\n\n"
                    "Davom etish uchun <b>ha</b> deb yozing yoki /cancel",
                    parse_mode='HTML'
                )
                # Keyingi bosqichga o'tish
                user_data["channel_id"] = channel_id
                user_data["message_id"] = message_id
                user_data["step"] = "confirm_continue"
                return
            
            # Saqlash va keyingi bosqichga o'tish
            user_data["channel_id"] = channel_id
            user_data["message_id"] = message_id
            user_data["step"] = "code"
            
            await update.message.reply_text(
                "✅ <b>Kino posti qabul qilindi!</b>\n\n"
                f"📢 Kanal: <code>{channel_id}</code>\n"
                f"🆔 Xabar ID: <code>{message_id}</code>\n\n"
                "📝 Endi <b>kod</b> kiriting:\n"
                "<i>Masalan: uzb001, film2024, kino001</i>\n\n"
                "❌ Bekor qilish: /cancel",
                parse_mode='HTML'
            )
            return
            
        except Exception as e:
            print(f"Forward qabul qilish xatosi: {e}")
            await update.message.reply_text(
                f"❌ <b>Xatolik:</b> <code>{e}</code>\n\n"
                "Qayta urinib ko'ring yoki /cancel",
                parse_mode='HTML'
            )
            return
    
    # TASDIQLASH (agar admin tekshiruvi o'tmagan bo'lsa)
    elif step == "confirm_continue":
        if update.message.text.lower() in ['ha', 'yes', 'ok']:
            user_data["step"] = "code"
            await update.message.reply_text(
                "✅ <b>Davom etamiz!</b>\n\n"
                "📝 Endi <b>kod</b> kiriting:\n"
                "<i>Masalan: uzb001, film2024</i>\n\n"
                "❌ Bekor qilish: /cancel",
                parse_mode='HTML'
            )
        else:
            context.user_data.pop("adding_movie", None)
            await update.message.reply_text("❌ Bekor qilindi.", parse_mode='HTML')
        return
    
    # KOD KIRITISH
    elif step == "code":
        code = update.message.text.strip().lower()
        movies = get_movies()
        
        if not code:
            await update.message.reply_text(
                "❌ <b>Kod bo'sh bo'lishi mumkin emas!</b>\n\n"
                "Qayta kiriting:",
                parse_mode='HTML'
            )
            return
        
        if code in movies:
            movie_name = movies[code].get('name', 'Nomalum')
            await update.message.reply_text(
                "❌ <b>Bu kod allaqachon mavjud!</b>\n\n"
                f"🎬 Mavjud film: <b>{movie_name}</b>\n"
                f"📌 Kod: <code>{code}</code>\n\n"
                f"📝 <b>Boshqa kod kiriting:</b>\n"
                "❌ Bekor qilish: /cancel",
                parse_mode='HTML'
            )
            return
        
        user_data["code"] = code
        user_data["step"] = "name"
        
        await update.message.reply_text(
            f"✅ Kod saqlandi: <code>{code}</code>\n\n"
            f"🎬 Endi <b>film nomini</b> to'liq yozing:\n"
            f"<i>Masalan: O'zbek film, Dunyo, Sevgi qissalari</i>\n\n"
            f"❌ Bekor qilish: /cancel",
            parse_mode='HTML'
        )
        return
    
    # NOM KIRITISH
    elif step == "name":
        name = update.message.text.strip()
        
        if not name:
            await update.message.reply_text(
                "❌ <b>Nom bo'sh bo'lishi mumkin emas!</b>\n\n"
                "Qayta kiriting:",
                parse_mode='HTML'
            )
            return
        
        user_data["name"] = name
        user_data["step"] = "genre"
        
        await update.message.reply_text(
            f"✅ Nomi saqlandi: <b>{name}</b>\n\n"
            f"🎭 <b>Janr</b> kiriting (ixtiyoriy):\n"
            f"<i>Masalan: Drama, Komediya, Sarguzasht, Jangari</i>\n\n"
            f"🔄 Yo'q bo'lsa <code>skip</code> deb yozing\n"
            f"❌ Bekor qilish: /cancel",
            parse_mode='HTML'
        )
        return
    
    # JANR KIRITISH
    elif step == "genre":
        genre_text = update.message.text.strip()
        genre = "" if genre_text.lower() == "skip" else genre_text
        
        # Kino saqlash
        try:
            print(f"DEBUG: Saving movie - code={user_data['code']}, name={user_data['name']}")
            
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
                f"🚀 Film endi katalogda!\n"
                f"🎯 Test qilish uchun: <code>{user_data['code']}</code>"
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
                f"Qayta urinib ko'ring yoki /cancel",
                parse_mode='HTML'
            )
            context.user_data.pop("adding_movie", None)
        return
    
    # NOTO'G'RI STEP
    else:
        print(f"DEBUG: Noto'g'ri step: {step}")
        await update.message.reply_text(
            "❌ <b>Jarayon xatosi!</b>\n\n"
            "Iltimos, /cancel yozib qayta boshlang.",
            parse_mode='HTML'
        )
        context.user_data.pop("adding_movie", None)
