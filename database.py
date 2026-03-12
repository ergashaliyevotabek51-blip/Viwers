import json
import os
from datetime import datetime

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
MOVIES_FILE = os.path.join(DATA_DIR, "movies.json")
CHANNELS_FILE = os.path.join(DATA_DIR, "channels.json")
ADMINS_FILE = os.path.join(DATA_DIR, "admins.json")
REQUESTS_FILE = os.path.join(DATA_DIR, "requests.json")

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
    return load_json(USERS_FILE)

def save_users(users: dict):
    save_json(USERS_FILE, users)

# ============ MOVIES ============
def get_movies() -> dict:
    return load_json(MOVIES_FILE)

def save_movies(movies: dict):
    save_json(MOVIES_FILE, movies)

# ============ CHANNELS ============
def get_channels() -> dict:
    return load_json(CHANNELS_FILE)

def save_channels(channels: dict):
    save_json(CHANNELS_FILE, channels)

# ============ ADMINS ============
def get_admins() -> dict:
    return load_json(ADMINS_FILE)

def save_admins(admins: dict):
    save_json(ADMINS_FILE, admins)

# ============ REQUESTS ============
def get_requests() -> dict:
    return load_json(REQUESTS_FILE)

def save_requests(requests: dict):
    save_json(REQUESTS_FILE, requests)
