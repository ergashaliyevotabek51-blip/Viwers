import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, Any

# PostgreSQL sozlamalari
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "telegram_bot")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

# JSON fallback uchun (agar PostgreSQL ishlamasa)
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
MOVIES_FILE = os.path.join(DATA_DIR, "movies.json")
CHANNELS_FILE = os.path.join(DATA_DIR, "channels.json")
ADMINS_FILE = os.path.join(DATA_DIR, "admins.json")
REQUESTS_FILE = os.path.join(DATA_DIR, "requests.json")

_connection = None

def get_connection():
    """PostgreSQL ulanishini olish"""
    global _connection
    if _connection is None or _connection.closed:
        _connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    return _connection

def init_database():
    """Jadvallarni yaratish"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR(50) PRIMARY KEY,
                first_name VARCHAR(255),
                username VARCHAR(255),
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                limit_count INTEGER DEFAULT 0,
                favorites TEXT DEFAULT '[]',
                banned BOOLEAN DEFAULT FALSE,
                referrals INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                code VARCHAR(50) PRIMARY KEY,
                name VARCHAR(500),
                genre VARCHAR(255),
                channel_id VARCHAR(100),
                message_id VARCHAR(50),
                added_by VARCHAR(50),
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                views INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id VARCHAR(100) PRIMARY KEY,
                name VARCHAR(255),
                invite_link TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id VARCHAR(50) PRIMARY KEY,
                role VARCHAR(50) DEFAULT 'admin',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                added_by VARCHAR(50),
                source VARCHAR(50) DEFAULT 'manual'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                request_id SERIAL PRIMARY KEY,
                user_id VARCHAR(50),
                movie_name VARCHAR(500),
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cursor.close()
        print("✅ PostgreSQL jadvallari yaratildi!")
        
        # JSON'dan ma'lumotlarni ko'chirish
        migrate_from_json()
        
    except Exception as e:
        print(f"❌ Database xatosi: {e}")
        print("⚠️ JSON rejimida ishlanmoqda...")

def migrate_from_json():
    """Eski JSON ma'lumotlarni PostgreSQL'ga ko'chirish"""
    try:
        # Users
        if os.path.exists(USERS_FILE):
            users = load_json(USERS_FILE)
            for uid, data in users.items():
                add_user(uid, data.get('first_name'), data.get('username'))
            print(f"✅ {len(users)} ta user ko'chirildi")
        
        # Movies
        if os.path.exists(MOVIES_FILE):
            movies = load_json(MOVIES_FILE)
            for code, data in movies.items():
                add_movie(
                    code, 
                    data.get('name'), 
                    data.get('genre'), 
                    data.get('channel_id'), 
                    data.get('message_id'), 
                    data.get('added_by')
                )
            print(f"✅ {len(movies)} ta movie ko'chirildi")
        
        # Channels
        if os.path.exists(CHANNELS_FILE):
            channels = load_json(CHANNELS_FILE)
            for cid, data in channels.items():
                add_channel(cid, data.get('name'), data.get('invite_link'))
            print(f"✅ {len(channels)} ta channel ko'chirildi")
        
        # Admins
        if os.path.exists(ADMINS_FILE):
            admins = load_json(ADMINS_FILE)
            for aid, data in admins.items():
                add_admin(aid, data.get('role', 'admin'), data.get('added_by'), data.get('source', 'manual'))
            print(f"✅ {len(admins)} ta admin ko'chirildi")
            
    except Exception as e:
        print(f"Migration xatosi: {e}")

# ============ JSON HELPER ============
def load_json(filename: str) -> dict:
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return {}
    return {}

def save_json(filename: str, data: dict):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

# ============ USERS ============
def get_users() -> dict:
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        cursor.close()
        
        users = {}
        for row in rows:
            uid = str(row['user_id'])
            users[uid] = dict(row)
            if isinstance(users[uid].get('favorites'), str):
                users[uid]['favorites'] = json.loads(users[uid]['favorites'])
        return users
    except:
        return load_json(USERS_FILE)

def save_users(users: dict):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        for uid, data in users.items():
            fav = json.dumps(data.get('favorites', [])) if isinstance(data.get('favorites'), list) else data.get('favorites', '[]')
            cursor.execute("""
                INSERT INTO users (user_id, first_name, username, limit_count, favorites, banned, referrals)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    username = EXCLUDED.username,
                    limit_count = EXCLUDED.limit_count,
                    favorites = EXCLUDED.favorites,
                    banned = EXCLUDED.banned,
                    referrals = EXCLUDED.referrals
            """, (uid, data.get('first_name'), data.get('username'), 
                  data.get('limit_count', 0), fav, data.get('banned', False), 
                  data.get('referrals', 0)))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Error saving users: {e}")
        save_json(USERS_FILE, users)

def add_user(user_id: str, first_name: str = None, username: str = None):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, first_name, username, joined_at, last_active)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                first_name = EXCLUDED.first_name,
                username = EXCLUDED.username,
                last_active = CURRENT_TIMESTAMP
        """, (user_id, first_name, username, datetime.now(), datetime.now()))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Error adding user: {e}")

# ============ MOVIES ============
def get_movies() -> dict:
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM movies")
        rows = cursor.fetchall()
        cursor.close()
        
        movies = {}
        for row in rows:
            code = str(row['code'])
            movies[code] = dict(row)
        return movies
    except:
        return load_json(MOVIES_FILE)

def save_movies(movies: dict):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        for code, data in movies.items():
            cursor.execute("""
                INSERT INTO movies (code, name, genre, channel_id, message_id, added_by, added_at, views)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    genre = EXCLUDED.genre,
                    channel_id = EXCLUDED.channel_id,
                    message_id = EXCLUDED.message_id,
                    views = EXCLUDED.views
            """, (code, data.get('name'), data.get('genre'), str(data.get('channel_id')),
                  str(data.get('message_id')), data.get('added_by'), 
                  data.get('added_at', datetime.now()), data.get('views', 0)))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Error saving movies: {e}")
        save_json(MOVIES_FILE, movies)

def add_movie(code: str, name: str, genre: str, channel_id: str, message_id: str, added_by: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO movies (code, name, genre, channel_id, message_id, added_by, added_at, views)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (code, name, genre, str(channel_id), str(message_id), added_by, datetime.now(), 0))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error adding movie: {e}")
        return False

def delete_movie(code: str) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movies WHERE code = %s", (code,))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error deleting movie: {e}")
        return False

# ============ CHANNELS ============
def get_channels() -> dict:
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM channels")
        rows = cursor.fetchall()
        cursor.close()
        
        channels = {}
        for row in rows:
            cid = str(row['channel_id'])
            channels[cid] = dict(row)
        return channels
    except:
        return load_json(CHANNELS_FILE)

def save_channels(channels: dict):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        for cid, data in channels.items():
            cursor.execute("""
                INSERT INTO channels (channel_id, name, invite_link)
                VALUES (%s, %s, %s)
                ON CONFLICT (channel_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    invite_link = EXCLUDED.invite_link
            """, (cid, data.get('name'), data.get('invite_link')))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Error saving channels: {e}")
        save_json(CHANNELS_FILE, channels)

def add_channel(channel_id: str, name: str, invite_link: str = ""):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO channels (channel_id, name, invite_link)
            VALUES (%s, %s, %s)
            ON CONFLICT (channel_id) DO UPDATE SET
                name = EXCLUDED.name,
                invite_link = EXCLUDED.invite_link
        """, (channel_id, name, invite_link))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error adding channel: {e}")
        return False

def remove_channel(channel_id: str) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM channels WHERE channel_id = %s", (channel_id,))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error removing channel: {e}")
        return False

# ============ ADMINS ============
def get_admins() -> dict:
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM admins")
        rows = cursor.fetchall()
        cursor.close()
        
        admins = {}
        for row in rows:
            uid = str(row['user_id'])
            admins[uid] = dict(row)
        return admins
    except:
        return load_json(ADMINS_FILE)

def save_admins(admins: dict):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        for uid, data in admins.items():
            cursor.execute("""
                INSERT INTO admins (user_id, role, added_at, added_by, source)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    role = EXCLUDED.role,
                    added_by = EXCLUDED.added_by,
                    source = EXCLUDED.source
            """, (uid, data.get('role', 'admin'), data.get('added_at', datetime.now()),
                  data.get('added_by'), data.get('source', 'manual')))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Error saving admins: {e}")
        save_json(ADMINS_FILE, admins)

def add_admin(user_id: str, role: str = "admin", added_by: str = None, source: str = "manual"):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO admins (user_id, role, added_at, added_by, source)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                role = EXCLUDED.role,
                added_by = EXCLUDED.added_by,
                source = EXCLUDED.source
        """, (user_id, role, datetime.now(), added_by, source))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error adding admin: {e}")
        return False

def remove_admin(user_id: str) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admins WHERE user_id = %s", (user_id,))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error removing admin: {e}")
        return False

def is_admin_db(user_id: str) -> bool:
    """Database'dan admin tekshirish"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM admins WHERE user_id = %s", (str(user_id),))
        result = cursor.fetchone()
        cursor.close()
        return result is not None
    except:
        return False

def is_super_admin_db(user_id: str) -> bool:
    """Database'dan super admin tekshirish"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM admins WHERE user_id = %s", (str(user_id),))
        result = cursor.fetchone()
        cursor.close()
        return result is not None and result[0] == 'super_admin'
    except:
        return False

# ============ REQUESTS ============
def get_requests() -> dict:
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM requests ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        
        requests = {}
        for row in rows:
            rid = str(row['request_id'])
            requests[rid] = dict(row)
        return requests
    except:
        return load_json(REQUESTS_FILE)

def save_requests(requests: dict):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        for rid, data in requests.items():
            cursor.execute("""
                INSERT INTO requests (request_id, user_id, movie_name, status, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (request_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    movie_name = EXCLUDED.movie_name,
                    status = EXCLUDED.status,
                    created_at = EXCLUDED.created_at
            """, (rid, data.get('user_id'), data.get('movie_name'), 
                  data.get('status', 'pending'), data.get('created_at', datetime.now())))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Error saving requests: {e}")
        save_json(REQUESTS_FILE, requests)

# Initialize
if __name__ == "__main__":
    init_database()

def is_admin_db(user_id: str) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM admins WHERE user_id = %s", (str(user_id),))
        result = cursor.fetchone()
        cursor.close()
        return result is not None
    except:
        return False

def is_super_admin_db(user_id: str) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM admins WHERE user_id = %s", (str(user_id),))
        result = cursor.fetchone()
        cursor.close()
        return result is not None and result[0] == 'super_admin'
    except:
        return False

