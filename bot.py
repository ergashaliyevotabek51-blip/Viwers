import os
import json
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
ApplicationBuilder, CommandHandler, CallbackQueryHandler,
MessageHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = "UzbekFilmTV_bot"

USERS_FILE="users.json"
MOVIES_FILE="movies.json"
SETTINGS_FILE="settings.json"

FREE_LIMIT=5
REF_LIMIT=5

DEFAULT_ADMINS=[774440841]
MANDATORY_CHANNELS=[]

def load_json(file,default):
    try:
        with open(file,"r",encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(file,data):
    with open(file,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=4,ensure_ascii=False)

def load_users():
    return load_json(USERS_FILE,{})

def save_users(users):
    save_json(USERS_FILE,users)

def load_movies():
    return load_json(MOVIES_FILE,{})

def save_movies(movies):
    save_json(MOVIES_FILE,movies)

def get_user(users,uid):
    uid=str(uid)
    if uid not in users:
        users[uid]={
            "used":0,
            "referrals":0,
            "limit":FREE_LIMIT,
            "joined":datetime.utcnow().isoformat()
        }
    return users[uid]

def max_limit(user):
    return user.get("limit",FREE_LIMIT)+user["referrals"]*REF_LIMIT

def is_admin(uid):
    return uid in DEFAULT_ADMINS

def trending(movies):
    return sorted(movies.items(),key=lambda x:x[1].get("views",0),reverse=True)[:10]

def random_movie(movies):
    if not movies:
        return None
    return random.choice(list(movies.keys()))

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id
    fname=update.effective_user.first_name

    users=load_users()
    get_user(users,uid)
    save_users(users)

    text=f"Assalomu alaykum {fname} 👋\n\nKod yuboring va filmni oling."

    kb=[
        [InlineKeyboardButton("🎟 Mening limitim",callback_data="my_limit")],
        [InlineKeyboardButton("🎬 Random film",callback_data="rand_movie")],
        [InlineKeyboardButton("🔥 Trend filmlar",callback_data="trend_movie")]
    ]

    if is_admin(uid):
        kb.append([InlineKeyboardButton("🛠 Admin panel",callback_data="admin")])

    await update.message.reply_text(text,reply_markup=InlineKeyboardMarkup(kb))

async def callback_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    q=update.callback_query
    await q.answer()

    uid=q.from_user.id

    users=load_users()
    movies=load_movies()
    user=get_user(users,uid)

    data=q.data

    if data=="my_limit":
        await q.message.reply_text(
        f"🔢 Siz ishlatgan: {user['used']}/{max_limit(user)}\n"
        f"Referal: {user['referrals']}"
        )

    elif data=="rand_movie":

        code=random_movie(movies)

        if not code:
            await q.message.reply_text("Film yo‘q")
            return

        m=movies[code]

        kb=InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Keyingi film",callback_data="next_movie")],
        [InlineKeyboardButton("🎬 Ulashish",url=f"https://t.me/{BOT_USERNAME}")]
        ])

        await context.bot.send_video(
        q.message.chat_id,
        m["file_id"],
        caption=f"🎬 {m['name']}",
        reply_markup=kb
        )

    elif data=="trend_movie":

        top=trending(movies)

        if not top:
            await q.message.reply_text("Trend yo‘q")
            return

        text="🔥 Trend filmlar\n\n"

        for i,(code,m) in enumerate(top,1):
            text+=f"{i}. {m['name']} — {m.get('views',0)} ta\n"

        await q.message.reply_text(text)

    elif data=="admin":

        kb=[
        [InlineKeyboardButton("➕ Kino qo‘shish",callback_data="add_movie")],
        [InlineKeyboardButton("➖ Kino o‘chirish",callback_data="delete_movie")],
        [InlineKeyboardButton("📊 Statistika",callback_data="stats")],
        [InlineKeyboardButton("🔥 Top filmlar",callback_data="top_movies")],
        [InlineKeyboardButton("📢 Broadcast",callback_data="broadcast")],
        [InlineKeyboardButton("🔒 Majburiy obuna",callback_data="subscription")],
        [InlineKeyboardButton("💠 Limit qo‘shish",callback_data="add_limit")]
        ]

        await q.message.reply_text("Admin panel",reply_markup=InlineKeyboardMarkup(kb))

    elif data=="stats":

        await q.message.reply_text(
        f"👥 Users: {len(users)}\n🎬 Movies: {len(movies)}"
        )

    elif data=="top_movies":

        top=trending(movies)

        text="🔥 Top filmlar\n\n"

        for i,(code,m) in enumerate(top,1):
            text+=f"{i}. {m['name']} — {m.get('views',0)}\n"

        await q.message.reply_text(text)

    elif data=="broadcast":

        context.user_data["mode"]="broadcast"
        await q.message.reply_text("Xabar yuboring")

    elif data=="delete_movie":

        context.user_data["mode"]="delete_movie"
        await q.message.reply_text("Film kodini yuboring")

    elif data=="add_limit":

        context.user_data["mode"]="add_limit"
        await q.message.reply_text("user_id limit")

    elif data=="next_movie":

        code=random_movie(movies)

        if not code:
            return

        m=movies[code]

        kb=InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Keyingi film",callback_data="next_movie")],
        [InlineKeyboardButton("🎬 Ulashish",url=f"https://t.me/{BOT_USERNAME}")]
        ])

        await context.bot.send_video(
        q.message.chat_id,
        m["file_id"],
        caption=f"🎬 {m['name']}",
        reply_markup=kb
        )

async def message_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    users=load_users()
    movies=load_movies()

    uid=update.effective_user.id
    text=update.message.text

    user=get_user(users,uid)

    mode=context.user_data.get("mode")

    if mode=="delete_movie":

        if text in movies:

            name=movies[text]["name"]

            del movies[text]

            save_movies(movies)

            await update.message.reply_text(f"{name} o‘chirildi")

        else:
            await update.message.reply_text("Topilmadi")

        context.user_data.clear()
        return

    if mode=="broadcast":

        count=0

        for u in users:

            try:
                await update.message.copy(chat_id=int(u))
                count+=1
            except:
                pass

        await update.message.reply_text(f"{count} ta userga yuborildi")

        context.user_data.clear()
        return

    if mode=="add_limit":

        try:

            uid_new,limit=text.split()

            target=get_user(users,uid_new)

            target["limit"]=int(limit)

            save_users(users)

            await update.message.reply_text("Limit o‘zgardi")

        except:

            await update.message.reply_text("Format: user_id limit")

        context.user_data.clear()
        return

    if text in movies:

        m=movies[text]

        movies[text]["views"]=m.get("views",0)+1

        user["used"]+=1

        save_movies(movies)
        save_users(users)

        kb=InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Keyingi film",callback_data="next_movie")],
        [InlineKeyboardButton("🎬 Ulashish",url=f"https://t.me/{BOT_USERNAME}")]
        ])

        await context.bot.send_video(
        update.effective_chat.id,
        m["file_id"],
        caption=f"🎬 {m['name']}",
        reply_markup=kb
        )

        return

    await update.message.reply_text("Kod topilmadi")

def main():

    app=ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))

    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,message_handler))

    print("Bot ishga tushdi")

    app.run_polling()

if __name__=="__main__":
    main()
