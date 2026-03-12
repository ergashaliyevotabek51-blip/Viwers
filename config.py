import os

# Railway Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "UzbekFilmTV_bot")
ADMIN_ID = os.environ.get("ADMIN_ID", "")

# ADMIN_IDS ro'yxati
ADMIN_IDS = []
if ADMIN_ID:
    ADMIN_IDS = [aid.strip() for aid in ADMIN_ID.split(",") if aid.strip()]

# Tekshiruv - faqat print, raise emas
if not BOT_TOKEN:
    print("WARNING: BOT_TOKEN topilmadi! Railway Variables ga qo'shing.")
    print(f"Mavjud variablelar: {list(os.environ.keys())}")
    # Default token (bo'sh) - main() da tekshiramiz
    BOT_TOKEN = ""

print(f"Config yuklandi: @{BOT_USERNAME}")
print(f"Token uzunligi: {len(BOT_TOKEN)}")
print(f"Admins: {ADMIN_IDS}")
