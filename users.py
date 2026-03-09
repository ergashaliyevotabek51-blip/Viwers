from database import load_json,save_json
from config import USERS_FILE,FREE_LIMIT,REF_LIMIT
from datetime import datetime

def load_users():
    return load_json(USERS_FILE,{})

def save_users(data):
    save_json(USERS_FILE,data)

def get_user(users,uid):

    uid=str(uid)

    if uid not in users:

        users[uid]={
            "used":0,
            "referrals":0,
            "joined":datetime.utcnow().isoformat()
        }

    return users[uid]

def max_limit(user):

    return FREE_LIMIT + user["referrals"]*REF_LIMIT
