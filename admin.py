from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from users import is_admin, is_super_admin
from database import get_users, get_movies, get_channels

async def show_admin_panel(query, user_id: str):
    if not is_admin(user_id):
        await query.answer("Ruxsat yoq!", show_alert=True)
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
    
    # Keyboard qaytarish
    from utils import get_admin_keyboard
    await query.edit_message_text(text, reply_markup=get_admin_keyboard(user_id))
