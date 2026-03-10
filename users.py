from database import load_json, save_json
from config import USERS_FILE, FREE_LIMIT, REF_LIMIT
from datetime import datetime


def load_users():
    return load_json(USERS_FILE, {})


def save_users(data):
    save_json(USERS_FILE, data)


def get_user(users, uid):
    """
    Userni olish yoki yaratish
    """
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "used": 0,
            "referrals": 0,
            "joined": datetime.utcnow().isoformat(),
            "refed": None  # referral uchun
        }
        save_users(users)
    return users[uid]


def max_limit(user):
    """
    Maksimal limitni hisoblash
    """
    return FREE_LIMIT + user.get("referrals", 0) * REF_LIMIT


def add_referral(users, user_id, ref_id):
    """
    Referral qo‘shish: agar user biror referral orqali kirgan bo‘lsa
    """
    user_id = str(user_id)
    ref_id = str(ref_id)
    user = get_user(users, user_id)
    if user.get("refed") is None and ref_id != user_id:
        ref_user = get_user(users, ref_id)
        ref_user["referrals"] += 1
        user["refed"] = ref_id
        save_users(users)
        return True
    return False


def increment_used(users, user_id):
    """
    User limitini ishlatish
    """
    user = get_user(users, user_id)
    user["used"] += 1
    save_users(users)
    return user["used"], max_limit(user)


def user_stats(users, user_id):
    """
    Foydalanuvchi statistikasi
    """
    user = get_user(users, user_id)
    return {
        "used": user["used"],
        "max": max_limit(user),
        "referrals": user["referrals"],
        "joined": user["joined"]
    }
