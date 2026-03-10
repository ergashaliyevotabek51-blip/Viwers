import os
import json
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder,CommandHandler,CallbackQueryHandler,MessageHandler,ContextTypes,filters

TOKEN=os.getenv("BOT_TOKEN")
BOT_USERNAME="UzbekFilmTV_bot"

USERS_FILE="users.json"
MOVIES_FILE="movies.json"
SETTINGS_FILE="settings.json"

FREE_LIMIT=5
REF_LIMIT=5

ADMINS=[774440841]

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

def save_users(x):
    save_json(USERS_FILE,x)

def load_movies():
    return load_json(MOVIES_FILE,{})

def save_movies(x):
    save_json(MOVIES_FILE,x)

def load_settings():
    return load_json(SETTINGS_FILE,{"channels":[]})

def save_settings(x):
    save_json(SETTINGS_FILE,x)

def is_admin(uid):
    return uid in ADMINS

def get_user(users,uid):
    uid=str(uid)
    if uid not in users:
        users[uid]={
        "used":0,
        "limit":FREE_LIMIT,
        "referrals":0,
        "joined":datetime.utcnow().isoformat()
        }
    return users[uid]

def max_limit(user):
    return user["limit"]+user["referrals"]*REF_LIMIT

def trending(movies):
    return sorted(movies.items(),key=lambda x:x[1].get("views",0),reverse=True)[:10]

def random_movie(movies):
    if not movies:
        return None
    return random.choice(list(movies.keys()))

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id
    name=update.effective_user.first_name

    users=load_users()
    get_user(users,uid)
    save_users(users)

    text=f"Assalomu alaykum {name} 👋\n\nKod yuboring va film oling."

    kb=[
    [InlineKeyboardButton("🎟 Mening limitim",callback_data="limit")],
    [InlineKeyboardButton("🎬 Random film",callback_data="random")],
    [InlineKeyboardButton("🔥 Trend filmlar",callback_data="trend")]
    ]

    if is_admin(uid):
        kb.append([InlineKeyboardButton("🛠 Admin panel",callback_data="admin")])

    await update.message.reply_text(text,reply_markup=InlineKeyboardMarkup(kb))

async def callback(update:Update,context:ContextTypes.DEFAULT_TYPE):

    q=update.callback_query
    await q.answer()

    data=q.data
    uid=q.from_user.id

    users=load_users()
    movies=load_movies()

    user=get_user(users,uid)

    if data=="limit":

        await q.message.reply_text(
        f"🎟 Limit: {user['used']}/{max_limit(user)}"
        )

    elif data=="random":

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

    elif data=="trend":

        top=trending(movies)

        text="🔥 Trend filmlar\n\n"

        for i,(code,m) in enumerate(top,1):
            text+=f"{i}. {m['name']} — {m.get('views',0)} ta\n"

        await q.message.reply_text(text)

    elif data=="admin":

        kb=[
        [InlineKeyboardButton("➕ Kino qo‘shish",callback_data="add")],
        [InlineKeyboardButton("➖ Kino o‘chirish",callback_data="delete")],
        [InlineKeyboardButton("📊 Statistika",callback_data="stats")],
        [InlineKeyboardButton("🔥 Top filmlar",callback_data="top")],
        [InlineKeyboardButton("📢 Broadcast",callback_data="broadcast")],
        [InlineKeyboardButton("🔒 Majburiy obuna",callback_data="sub")],
        [InlineKeyboardButton("💠 Limit qo‘shish",callback_data="limit_add")]
        ]

        await q.message.reply_text("Admin panel",reply_markup=InlineKeyboardMarkup(kb))

    elif data=="stats":

        await q.message.reply_text(
        f"👥 Users: {len(users)}\n🎬 Movies: {len(movies)}"
        )

    elif data=="top":

        top=trending(movies)

        text="🔥 Top filmlar\n\n"

        for i,(code,m) in enumerate(top,1):
            text+=f"{i}. {m['name']} — {m.get('views',0)} ta\n"

        await q.message.reply_text(text)

    elif data=="add":

        context.user_data["mode"]="add_movie"
        await q.message.reply_text("Filmni forward qiling")

    elif data=="delete":

        context.user_data["mode"]="delete_movie"
        await q.message.reply_text("Kod yuboring")

    elif data=="broadcast":

        context.user_data["mode"]="broadcast"
        await q.message.reply_text("Xabar yuboring")

    elif data=="limit_add":

        context.user_data["mode"]="limit_add"
        await q.message.reply_text("user_id limit")

    elif data=="sub":

        context.user_data["mode"]="add_channel"
        await q.message.reply_text("Kanal username yuboring")

async def messages(update:Update,context:ContextTypes.DEFAULT_TYPE):

    users=load_users()
    movies=load_movies()

    text=update.message.text
    mode=context.user_data.get("mode")

    if mode=="add_movie":

        if update.message.video:
            file_id=update.message.video.file_id
        elif update.message.document:
            file_id=update.message.document.file_id
        else:
            await update.message.reply_text("Video yuboring")
            return

        context.user_data["file"]=file_id
        context.user_data["mode"]="movie_code"

        await update.message.reply_text("Film kodi")
        return

    if mode=="movie_code":

        context.user_data["code"]=text
        context.user_data["mode"]="movie_name"

        await update.message.reply_text("Film nomi")
        return

    if mode=="movie_name":

        movies[context.user_data["code"]]={
        "name":text,
        "file_id":context.user_data["file"],
        "views":0
        }

        save_movies(movies)

        await update.message.reply_text("Film qo‘shildi")

        context.user_data.clear()
        return

    if mode=="delete_movie":

        if text in movies:

            del movies[text]
            save_movies(movies)

            await update.message.reply_text("Film o‘chirildi")

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

    if mode=="limit_add":

        try:
            uid,limit=text.split()

            users[uid]["limit"]=int(limit)

            save_users(users)

            await update.message.reply_text("Limit qo‘shildi")

        except:
            await update.message.reply_text("Format: user_id limit")

        context.user_data.clear()
        return

    if mode=="add_channel":

        settings=load_settings()

        settings["channels"].append(text)

        save_settings(settings)

        await update.message.reply_text("Kanal qo‘shildi")

        context.user_data.clear()
        return

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

    app.add_handler(CallbackQueryHandler(callback))

    app.add_handler(MessageHandler(filters.ALL,messages))

    print("Bot ishga tushdi")

    app.run_polling()

if __name__=="__main__":
    main()
