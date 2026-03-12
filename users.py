from datetime import datetime
from database import get_users, save_users
from config import ADMIN_IDS

def is_admin(user_id: str) -> bool:
    return user_id in ADMIN_IDS

def is_super_admin(user_id: str) -> bool:
    return ADMIN_IDS and user_id == ADMIN_IDS[0]

def is_banned(user_id: str) -> bool:
    users = get_users()
    return users.get(user_id, {}).get("banned", False)

def get_or_create_user(user_id: str, username: str = None, first_name: str = None) -> dict:
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
    else:
        users[user_id]["last_activity"] = datetime.now().isoformat()
        if username:
            users[user_id]["username"] = username
        if first_name:
            users[user_id]["first_name"] = first_name
        save_users(users)
    return users[user_id]

def check_limit(user_id: str) -> bool:
    users = get_users()
    user = users.get(user_id, {})
    return user.get("limit", 0) > 0

def decrease_limit(user_id: str):
    users = get_users()
    if user_id in users and users[user_id]["limit"] > 0:
        users[user_id]["limit"] -= 1
        save_users(users)

def add_limit(user_id: str, amount: int):
    users = get_users()
    if user_id in users:
        users[user_id]["limit"] += amount
        save_users(users)

def add_referral(referrer_id: str):
    users = get_users()
    if referrer_id in users:
        users[referrer_id]["referrals"] += 1
        users[referrer_id]["limit"] += 5
        save_users(users)

def add_to_history(user_id: str, movie_code: str):
    users = get_users()
    if user_id in users:
        if movie_code not in users[user_id]["history"]:
            users[user_id]["history"].insert(0, movie_code)
            users[user_id]["history"] = users[user_id]["history"][:20]
            save_users(users)

def toggle_favorite(user_id: str, movie_code: str) -> bool:
    users = get_users()
    if user_id in users:
        if movie_code in users[user_id]["favorites"]:
            users[user_id]["favorites"].remove(movie_code)
            save_users(users)
            return False
        else:
            users[user_id]["favorites"].append(movie_code)
            save_users(users)
            return True

def ban_user(user_id: str):
    users = get_users()
    if user_id in users:
        users[user_id]["banned"] = True
        save_users(users)

def unban_user(user_id: str):
    users = get_users()
    if user_id in users:
        users[user_id]["banned"] = False
        save_users(users)
