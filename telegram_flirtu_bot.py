import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler, ConversationHandler

import os
from dotenv import load_dotenv

from keep_alive import keep_alive


# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Data stores
user_profiles = {}  # user_id: {age, gender, preference, location}
waiting_users = []
active_chats = {}  # user_id: partner_id

# States for ConversationHandler
AGE, GENDER, PREFERENCE, LOCATION = range(4)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("👋 Welcome to FlirtBot! Let's create your profile.\nHow old are you?")
    return AGE

async def get_age(update: Update, context: CallbackContext):
    context.user_data['age'] = update.message.text
    await update.message.reply_text("What is your gender? (e.g., male, female, non-binary)")
    return GENDER

async def get_gender(update: Update, context: CallbackContext):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("Who are you interested in chatting with? (e.g., male, female, anyone)")
    return PREFERENCE

async def get_preference(update: Update, context: CallbackContext):
    context.user_data['preference'] = update.message.text
    await update.message.reply_text("What city or country are you in?")
    return LOCATION

async def get_location(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_profiles[user_id] = {
        'age': context.user_data['age'],
        'gender': context.user_data['gender'],
        'preference': context.user_data['preference'],
        'location': update.message.text
    }
    await update.message.reply_text("✅ Profile created! Type /find to meet someone.")
    return ConversationHandler.END

async def find(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in user_profiles:
        await update.message.reply_text("Please set up your profile first by typing /start")
        return
    if user_id in active_chats:
        await update.message.reply_text("You're already in a chat. Type /stop to end it.")
        return
    for partner_id in waiting_users:
        if partner_id != user_id and match(user_profiles[user_id], user_profiles[partner_id]):
            waiting_users.remove(partner_id)
            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id
            await context.bot.send_message(chat_id=user_id, text="✅ Connected. Say hi!")
            await context.bot.send_message(chat_id=partner_id, text="✅ Connected. Say hi!")
            return
    if user_id not in waiting_users:
        waiting_users.append(user_id)
        await update.message.reply_text("⏳ Waiting for a partner...")

async def stop(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await context.bot.send_message(chat_id=partner_id, text="❌ Your partner has left the chat.")
        await update.message.reply_text("❌ You left the chat.")
    else:
        if user_id in waiting_users:
            waiting_users.remove(user_id)
        await update.message.reply_text("You're not in a chat.")

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)
    else:
        await update.message.reply_text("❗ You're not in a chat. Use /find to get started.")

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text("Commands:\n/start - Set up your profile\n/find - Find a partner\n/stop - End chat\n/help - Show help")

def match(user1, user2):
    # Basic match logic by preference
    return (
        user1['preference'].lower() in [user2['gender'].lower(), 'anyone'] and
        user2['preference'].lower() in [user1['gender'].lower(), 'anyone']
    )

def main():

    keep_alive() 
    
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            PREFERENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_preference)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_location)],
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
