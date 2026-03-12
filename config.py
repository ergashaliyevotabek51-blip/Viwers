# config.py - TO'G'RI VERSIYA

import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "UzbekFilmTV_bot")
ADMIN_ID = os.environ.get("ADMIN_ID", "")

ADMIN_IDS = []
if ADMIN_ID:
    ADMIN_IDS = [aid.strip() for aid in ADMIN_ID.split(",") if aid.strip()]

if not BOT_TOKEN:
    print("WARNING: BOT_TOKEN topilmadi!")
    BOT_TOKEN = ""

print(f"Config: @{BOT_USERNAME}")
print(f"Admins: {ADMIN_IDS}")
