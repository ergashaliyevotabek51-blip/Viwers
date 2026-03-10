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

def load_settings():
    return load_json(SETTINGS_FILE,{"channels":[]})

def save_settings(data):
    save_json(SETTINGS_FILE,data)

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

async def check_subscription(context,user_id):

    settings=load_settings()
    channels=settings.get("channels",[])

    for ch in channels:
        try:
            member=await context.bot.get_chat_member(ch,user_id)
            if member.status not in ["member","administrator","creator"]:
                return False
        except:
            return False

    return True

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id
    fname=update.effective_user.first_name

    users=load_users()
    get_user(users,uid)
    save_users(users)

    if not await check_subscription(context,uid):

        settings=load_settings()
        channels=settings.get("channels",[])

        buttons=[]

        for ch in channels:
            buttons.append([InlineKeyboardButton(ch,url=f"https://t.me/{ch.replace('@','')}")])

        await update.message.reply_text(
        "Botdan foydalanish uchun kanallarga obuna bo‘ling",
        reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

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
        f"🔢 Siz ishlatgan: {user['used']}/{max_limit(user)}"
        )

    elif data=="rand_movie":

        code=random_movie(movies)

        if not code:
            await q.message.reply_text("Film yo‘q")
            return

        m=movies[code]

        await context.bot.send_video(
        q.message.chat_id,
        m["file_id"],
        caption=f"🎬 {m['name']}"
        )

    elif data=="trend_movie":

        top=trending(movies)

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

    elif data=="add_movie":

        context.user_data["mode"]="add_movie"
        await q.message.reply_text("Filmni forward qiling")

    elif data=="subscription":

        context.user_data["mode"]="add_channel"
        await q.message.reply_text("Kanal username yuboring\nMasalan: @kanal")

    elif data=="stats":

        await q.message.reply_text(
        f"👥 Users: {len(users)}\n🎬 Movies: {len(movies)}"
        )

async def message_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    users=load_users()
    movies=load_movies()

    mode=context.user_data.get("mode")

    if mode=="add_movie":

        msg=update.message

        if msg.video:
            file_id=msg.video.file_id
        elif msg.document:
            file_id=msg.document.file_id
        else:
            await msg.reply_text("Video yuboring")
            return

        context.user_data["file"]=file_id
        context.user_data["mode"]="movie_code"

        await msg.reply_text("Film kodi kiriting")
        return

    if mode=="movie_code":

        context.user_data["code"]=update.message.text
        context.user_data["mode"]="movie_name"

        await update.message.reply_text("Film nomini kiriting")
        return

    if mode=="movie_name":

        code=context.user_data["code"]

        movies[code]={
        "name":update.message.text,
        "file_id":context.user_data["file"],
        "views":0
        }

        save_movies(movies)

        await update.message.reply_text("Film qo‘shildi")

        context.user_data.clear()
        return

    if mode=="add_channel":

        ch=update.message.text

        settings=load_settings()

        settings["channels"].append(ch)

        save_settings(settings)

        await update.message.reply_text("Kanal qo‘shildi")

        context.user_data.clear()
        return

    text=update.message.text

    if text in movies:

        m=movies[text]

        await context.bot.send_video(
        update.effective_chat.id,
        m["file_id"],
        caption=m["name"]
        )

def main():

    app=ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))

    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(filters.ALL,message_handler))

    print("Bot ishga tushdi")

    app.run_polling()

if __name__=="__main__":
    main()
