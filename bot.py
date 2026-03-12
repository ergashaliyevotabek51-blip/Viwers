import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Config
from config import BOT_TOKEN, BOT_USERNAME, ADMIN_IDS

# Modullar
from users import get_or_create_user, is_admin, is_banned
from movies import search_movies, get_random_movie
from subscription import check_subscription
from utils import get_main_keyboard, get_subscription_keyboard

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = str(user.id)
        
        # Referal
        if context.args and context.args[0].startswith("ref"):
            # ... referal logikasi
        
        get_or_create_user(user_id, user.username, user.first_name)
        
        if is_banned(user_id):
            await update.message.reply_text("Siz bloklangansiz.")
            return
        
        if not await check_subscription(user.id, context):
            await update.message.reply_text(
                "Kanallarga obuna bo'ling!",
                reply_markup=get_subscription_keyboard()
            )
            return
        
        await update.message.reply_text(
            f"Salom {user.first_name}!",
            reply_markup=get_main_keyboard(user_id)
        )
    except Exception as e:
        logger.error(f"Start error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... xabarlar handleri

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... callback handleri

def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN yo'q!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print(f"Bot ishga tushdi: @{BOT_USERNAME}")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
