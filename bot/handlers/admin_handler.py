# bot/handlers/admin_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from bot.database.db_operations import update_welcome_message

def change_welcome_message(update: Update, context: CallbackContext):
    new_message = ' '.join(context.args)
    if new_message:
        update_welcome_message(new_message)
        update.message.reply_text(f"Welcome message changed to: {new_message}")
    else:
        update.message.reply_text("Please provide a new welcome message.")