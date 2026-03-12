async def unban_user_handler(query, user_id: str):
    from users import unban_user
    unban_user(user_id)
    await query.answer("✅ Foydalanuvchi blokdan chiqarildi!", show_alert=True)
    # Callback javobidan so'ng yangilash
    await start_unban_user(query)
async def create_backup(query):
    if not is_admin(str(query.from_user.id)):
        return
    
    try:
        backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copytree("data", backup_dir)
        # await query.answer() o'rniga edit_message_text
        await query.edit_message_text(
            f"✅ <b>Backup yaratildi!</b>\n\n"
            f"📁 <b>Papka:</b> <code>{backup_dir}</code>",
            reply_markup=get_admin_keyboard(str(query.from_user.id)),
            parse_mode='HTML'
        )
    except Exception as e:
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
    
    # Xabar qaytarish
    await query.edit_message_text(
        f"✅ <b>Export yakunlandi!</b>\n\n"
        f"📤 <b>Yuborilgan fayllar:</b> {sent} ta",
        reply_markup=get_admin_keyboard(str(query.from_user.id)),
        parse_mode='HTML'
    )
async def delete_movie(query, movie_code: str):
    from movies import delete_movie as remove_movie
    if remove_movie(movie_code):
        await query.answer("✅ Kino o'chirildi!", show_alert=True)
    else:
        await query.answer("❌ Kino o'chirishda xatolik!", show_alert=True)
    await start_delete_movie(query)  # Ro'yxatni yangilash
