from database import load_json, save_json
from config import SETTINGS_FILE, DEFAULT_ADMINS


def get_settings():

    return load_json(SETTINGS_FILE, {
        "admins": DEFAULT_ADMINS,
        "channels": []
    })


def save_settings(data):

    save_json(SETTINGS_FILE, data)


def get_admins():

    settings = get_settings()

    if "admins" not in settings:
        settings["admins"] = DEFAULT_ADMINS
        save_settings(settings)

    return settings["admins"]


def is_admin(uid):

    return uid in get_admins()


def add_admin(uid):

    settings = get_settings()

    if uid not in settings["admins"]:
        settings["admins"].append(uid)
        save_settings(settings)

        return True

    return False


def remove_admin(uid):

    settings = get_settings()

    if uid in settings["admins"]:

        settings["admins"].remove(uid)
        save_settings(settings)

        return True

    return False
