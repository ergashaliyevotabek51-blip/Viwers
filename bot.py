import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Assalomu alaykum, {update.effective_user.first_name}!\n"
        "Bot ishlayapti. Kod yuboring."
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot polling boshladi...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
