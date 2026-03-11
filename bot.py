import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "YOUR_TOKEN_HERE"  # O'zgartiring

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Start from user: {update.effective_user.id}")
    await update.message.reply_text("✅ Bot ishlayapti!")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    logger.info("Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
