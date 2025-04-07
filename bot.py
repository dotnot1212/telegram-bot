from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler
import asyncio
from pymongo import MongoClient
import os

# توکن رباتت
TOKEN = "8083629204:AAEDIDO-WNXyo8CDlEwx8LBFnJPK3suJhaQ"

# اتصال به MongoDB (رشته اتصال بعداً از متغیر محیطی میاد)
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://<username>:<password>@cluster0.xxx.mongodb.net/telegram_bot_db?retryWrites=true&w=majority")
client = MongoClient(MONGO_URI)
db = client["telegram_bot_db"]  # اسم دیتابیس
users_collection = db["users"]  # کالکشن برای ذخیره کاربرها

# ذخیره آیدی کاربرها
def save_user(chat_id):
    users_collection.update_one({"chat_id": chat_id}, {"$set": {"chat_id": chat_id}}, upsert=True)

# حذف کاربر از لیست
def remove_user(chat_id):
    result = users_collection.delete_one({"chat_id": chat_id})
    return result.deleted_count > 0

# لود کردن لیست کاربرها
def load_users():
    return {doc["chat_id"] for doc in users_collection.find()}

# منوی اصلی
async def start(update, context):
    chat_id = update.effective_chat.id
    save_user(chat_id)  # ذخیره آیدی کاربر
    keyboard = [
        [InlineKeyboardButton("اعضای تیم‌ها", callback_data='team_members')],
        [InlineKeyboardButton("داورها", callback_data='judges')],
        [InlineKeyboardButton("سرورها", callback_data='servers')],
        [InlineKeyboardButton("اخبار", callback_data='news')],
        [InlineKeyboardButton("لایوها", callback_data='live')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await update.message.reply_text("به ربات خوش اومدی! یه گزینه انتخاب کن:\nبرای لغو اشتراک: /stop", reply_markup=reply_markup)
    context.job_queue.run_once(delete_message, 60, context=(context.bot, message.chat_id, message.message_id))

# دستور لغو اشتراک
async def stop(update, context):
    chat_id = update.effective_chat.id
    if remove_user(chat_id):
        await update.message.reply_text("اشتراکت لغو شد. برای اشتراک دوباره: /start")
    else:
        await update.message.reply_text("شما تو لیست نبودید! برای اشتراک: /start")

# حذف پیام
def delete_message(context):
    bot, chat_id, message_id = context.job_context
    bot.delete_message(chat_id=chat_id, message_id=message_id)

# مدیریت گزینه‌ها
async def button(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == 'team_members':
        keyboard = [
            [InlineKeyboardButton("تیم 1", callback_data='team_1')],
            [InlineKeyboardButton("تیم 2", callback_data='team_2')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = await query.edit_message_text(text="یه تیم انتخاب کن:", reply_markup=reply_markup)
    
    elif query.data == 'judges':
        message = await query.edit_message_text(text="آیدی داورها:\nداور 1: @Judge1 - IG: judge1_insta\nداور 2: @Judge2 - IG: judge2_insta")
    
    elif query.data == 'servers':
        message = await query.edit_message_text(text="سرورها:\nIP: 192.168.1.1\nTS: ts.example.com")
    
    elif query.data == 'news':
        message = await query.edit_message_text(text="آخرین اخبار:\nخبر 1: فلان\nخبر 2: بیسار")
    
    elif query.data == 'live':
        message = await query.edit_message_text(text="لایوها:\nلینک لایو 1: t.me/live1")
    
    elif query.data == 'team_1':
        message = await query.edit_message_text(text="اعضای تیم 1:\n- علی\n- رضا\n- محمد")
    
    elif query.data == 'team_2':
        message = await query.edit_message_text(text="اعضای تیم 2:\n- حسین\n- مهدی\n- سعید")

    context.job_queue.run_once(delete_message, 60, context=(context.bot, chat_id, message.message_id))

# فیلتر برای پست‌های کانال
def is_channel_post(update):
    return update.channel_post and update.channel_post.chat.type == Chat.CHANNEL

# هندل کردن پست‌های کانال
async def channel_post(update, context):
    message = update.channel_post
    channel_id = message.chat_id

    # چک کردن وجود #خبر
    if message.text and "#خبر" in message.text:
        users = load_users()
        for user_id in users:
            try:
                await context.bot.forward_message(chat_id=user_id, from_chat_id=channel_id, message_id=message.message_id)
            except Exception as e:
                print(f"خطا در ارسال به {user_id}: {e}")

# راه‌اندازی ربات
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(is_channel_post, channel_post))
    application.run_polling()

if __name__ == '__main__':
    main()