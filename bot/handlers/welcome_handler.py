# bot/handlers/welcome_handler.py
from telethon import events
from bot.database.firebase_operations import add_user, get_user, update_user
import logging

logger = logging.getLogger(__name__)

async def welcome_new_member(event):
    for user in event.users:
        user_id = user.id
        username = user.username
        first_name = user.first_name
        last_name = user.last_name

        # Check if the user is new
        if get_user(user_id) is None:
            # Save user to Firebase
            add_user(user_id, username, first_name, last_name)

            # Send a direct welcome message
            welcome_message = (
                f"Hello {first_name}! Welcome to the group. "
                "Please click /start to register and receive updates."
            )
            try:
                await event.client.send_message(user_id, welcome_message)
                logger.info(f"Welcome message sent to user {user_id}.")
            except Exception as e:
                logger.error(f"Failed to send DM to user {user_id}: {e}")

async def register_user(event):
    user_id = event.sender_id
    username = event.sender.username
    first_name = event.sender.first_name
    last_name = event.sender.last_name

    # Check if the user is already registered
    existing_user = get_user(user_id)
    if existing_user:
        await event.reply("You are already registered. Welcome back!")
        return

    # Save user to Firebase
    add_user(user_id, username, first_name, last_name)

    # Send a confirmation message
    await event.reply("You have been registered! Welcome to the bot.")