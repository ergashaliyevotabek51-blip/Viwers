import time

flood = {}
COOLDOWN = 1  # sekundlar bilan cheklash, kerak bo'lsa oshirilishi mumkin


def anti_flood(uid, cooldown=COOLDOWN):
    """
    Tez-tez xabar yuborilishini cheklash.
    Agar foydalanuvchi oxirgi xabardan beri cooldown sekundan kam bo'lsa False qaytaradi.
    """
    now = time.time()
    if uid not in flood:
        flood[uid] = now
        return True
    if now - flood[uid] < cooldown:
        return False
    flood[uid] = now
    return True


def reset_flood(uid):
    """
    Foydalanuvchi uchun flood vaqtini reset qiladi
    """
    if uid in flood:
        del flood[uid]
