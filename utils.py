import time

flood={}

def anti_flood(uid):

    now=time.time()

    if uid not in flood:
        flood[uid]=now
        return True

    if now-flood[uid]<1:
        return False

    flood[uid]=now
    return True
