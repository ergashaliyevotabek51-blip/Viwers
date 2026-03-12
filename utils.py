from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from users import is_admin, is_super_admin
from database import get_users, get_movies, get_channels

def get_main_keyboard(user_id: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("Mening limitim", callback_data="my_limit"),
         InlineKeyboardButton("Random film", callback_data="random_movie")],
        [InlineKeyboardButton("Trend filmlar", callback_data="trending"),
         InlineKeyboardButton("Kino katalog", callback_data="catalog")],
        [InlineKeyboardButton("Do'st taklif qilish", callback_data="referral")],
    ]
    
    if is_admin(user_id):
        buttons.append([InlineKeyboardButton("Admin panel", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(buttons)

def get_admin_keyboard(user_id: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("Kino qo'shish", callback_data="add_movie"),
         InlineKeyboardButton("Kino o'chirish", callback_data="delete_movie")],
        [InlineKeyboardButton("Statistika", callback_data="stats"),
         InlineKeyboardButton("Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("Asosiy menyu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(buttons)
