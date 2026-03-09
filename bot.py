import random
from telegram import *
from telegram.ext import *

from config import *
from users import *
from movies import *
from subscription import *
from utils import *
from admin import *

users=load_users()
movies=load_movies()

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user

    me=get_user(users,user.id)

    save_users(users)

    status=await check_user(context,user.id)

    if False in status.values():

        await update.message.reply_text(
            "Botdan foydalanish uchun kanallarga obuna bo‘ling",
            reply_markup=keyboard(status)
        )
        return

    text=(
        f"Salom {user.first_name}\n\n"
        "Kino kodini yuboring 🎬\n"
        "Yoki film nomini yozib qidirishingiz mumkin."
    )

    kb=InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Mening limitim",callback_data="limit")
        ],
        [
            InlineKeyboardButton("🎲 Random film",callback_data="random")
        ],
        [
            InlineKeyboardButton("🔥 Trend filmlar",callback_data="trend")
        ]
    ])

    await update.message.reply_text(text,reply_markup=kb)


async def check_sub(update,context):

    q=update.callback_query
    await q.answer()

    status=await check_user(context,q.from_user.id)

    if False in status.values():

        await q.edit_message_reply_markup(reply_markup=keyboard(status))

    else:

        await q.edit_message_text(
            "✅ Obuna tasdiqlandi!\nBotdan foydalanishingiz mumkin."
        )


async def callbacks(update,context):

    q=update.callback_query
    await q.answer()

    if q.data=="limit":

        user=get_user(users,q.from_user.id)

        await q.message.reply_text(
            f"Siz ishlatgan: {user['used']}/{max_limit(user)}"
        )

    if q.data=="random":

        code=random_movie(movies)

        await q.message.reply_text(
            f"🎬 Random kino kodi: {code}"
        )

    if q.data=="trend":

        top=trending(movies)

        text="🔥 Eng ko‘p ko‘rilgan filmlar\n\n"

        for i,(code,m) in enumerate(top,1):

            text+=f"{i}. {m['name']} — {m['views']}\n"

        await q.message.reply_text(text)


async def message(update,context):

    text=(update.message.text or "").strip()
    uid=update.message.from_user.id

    if not anti_flood(uid):

        await update.message.reply_text("⏳ Iltimos sekinroq yozing")
        return

    status=await check_user(context,uid)

    if False in status.values():

        await update.message.reply_text(
            "Avval kanallarga obuna bo‘ling",
            reply_markup=keyboard(status)
        )
        return

    user=get_user(users,uid)

    if text in movies:

        if user["used"]>=max_limit(user):

            await update.message.reply_text("❌ Limit tugagan")
            return

        movie=movies[text]

        movie["views"]+=1

        user["used"]+=1

        save_movies(movies)
        save_users(users)

        val=movie["file"]

        p=val.replace("https://t.me/c/","").split("/")

        chat_id=int("-100"+p[0])
        msg_id=int(p[1])

        await context.bot.copy_message(
            chat_id=update.message.chat_id,
            from_chat_id=chat_id,
            message_id=msg_id
        )

        await update.message.reply_text(
            f"🎬 {movie['name']}\n"
            f"📺 {movie['quality']}\n"
            f"⏱ {movie['duration']}\n\n"
            f"Qolgan limit: {user['used']}/{max_limit(user)}"
        )

        return

    found=[]

    for code,m in movies.items():

        if text.lower() in m["name"].lower():

            found.append(f"{code} — {m['name']}")

    if found:

        await update.message.reply_text(
            "Topildi:\n\n"+"\n".join(found[:10])
        )

    else:

        await update.message.reply_text("❌ Bunday kino topilmadi")


def main():

    app=ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))

    app.add_handler(CallbackQueryHandler(check_sub,pattern="check_sub"))

    app.add_handler(CallbackQueryHandler(callbacks))

    app.add_handler(MessageHandler(filters.TEXT,message))

    print("SUPER KINO BOT PRO ISHLADI")

    app.run_polling()


if __name__=="__main__":
    main()
