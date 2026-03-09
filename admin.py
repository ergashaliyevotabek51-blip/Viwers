from database import load_json,save_json
from config import SETTINGS_FILE,DEFAULT_ADMINS

def get_admins():

    settings=load_json(SETTINGS_FILE,{"admins":DEFAULT_ADMINS})

    if "admins" not in settings:
        settings["admins"]=DEFAULT_ADMINS

    return settings["admins"]

def is_admin(uid):

    return uid in get_admins()
