from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from bot.handlers.welcome_handler import welcome_new_member, register_user
from bot.handlers.broadcast_handler import broadcast_message
import os
import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firebase (if needed)
from bot.database.firebase_operations import init_db
init_db()

# Define command handlers
def start(update: Update, context: CallbackContext):
    register_user(update, context)

def broadcast(update: Update, context: CallbackContext):
    broadcast_message(update, context)

def main():
    # Get the bot token from environment variables
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN must be set in the .env file.")

    # Set up the Updater with the webhook URL
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("broadcast", broadcast))

    # Set up the webhook
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    if WEBHOOK_URL:
        updater.start_webhook(listen="0.0.0.0", port=int(os.getenv("PORT", 8080)), url_path=BOT_TOKEN)
        updater.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")
        logger.info("Webhook set up successfully.")
    else:
        updater.start_polling()
        logger.info("Polling mode activated.")

    updater.idle()

if __name__ == '__main__':
    main()