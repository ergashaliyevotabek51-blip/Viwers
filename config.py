import os

# Railway Environment Variables
BOT_TOKEN = os.environ.get("8370792264:AAEFLn2NukQ3E63PHmAln7evLhQPBMxFP6s", "")
BOT_USERNAME = os.environ.get("UzbekFilmTV_bot")
ADMIN_ID = os.environ.get("ADMIN_ID", "")

# ADMIN_IDS ro'yxati
ADMIN_IDS = []
if ADMIN_ID:
    ADMIN_IDS = [aid.strip() for aid in ADMIN_ID.split(",") if aid.strip()]

# Tekshiruv
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Railway Variables ga qo'shing.")
