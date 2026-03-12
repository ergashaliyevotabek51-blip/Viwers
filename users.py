from datetime import datetime
from database import get_users, save_users
from config import ADMIN_IDS

def is_admin(user_id: str) -> bool:
    return user_id in ADMIN_IDS

def is_super_admin(user_id: str) -> bool:
    return ADMIN_IDS and user_id == ADMIN_IDS[0]

def get_or_create_user(user_id: str, username: str = None, first_name: str = None):
    users = get_users()
    if user_id not in users:
        users[user_id] = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "limit": 5,
            "referrals": 0,
            "joined_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "favorites": [],
            "history": [],
            "banned": False
        }
        save_users(users)
    return users[user_id]

# Qolgan funksiyalar...
