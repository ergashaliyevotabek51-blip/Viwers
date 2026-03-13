# config.py - YANGILANGAN VERSIYA (PostgreSQL + .env qo'llab-quvvatlash)

from dotenv import load_dotenv
import os

# .env faylni o'qish (agar mavjud bo'lsa)
load_dotenv()

# ============ BOT SOZLAMALARI ============
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME") or os.environ.get("BOT_USERNAME", "UzbekFilmTV_bot")
ADMIN_ID = os.getenv("ADMIN_ID") or os.environ.get("ADMIN_ID", "")

ADMIN_IDS = []
if ADMIN_ID:
    ADMIN_IDS = [aid.strip() for aid in ADMIN_ID.split(",") if aid.strip()]

if not BOT_TOKEN:
    print("⚠️ WARNING: BOT_TOKEN topilmadi!")
    BOT_TOKEN = ""

# ============ POSTGRESQL SOZLAMALARI ============
DB_HOST = os.getenv("DB_HOST") or os.environ.get("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT") or os.environ.get("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME") or os.environ.get("DB_NAME", "telegram_bot")
DB_USER = os.getenv("DB_USER") or os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD") or os.environ.get("DB_PASSWORD", "")

# DATABASE_URL (Railway/Render uchun)
DATABASE_URL = os.getenv("DATABASE_URL") or os.environ.get("DATABASE_URL", "")

print(f"✅ Config: @{BOT_USERNAME}")
print(f"✅ Admins: {ADMIN_IDS}")
print(f"✅ Database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
