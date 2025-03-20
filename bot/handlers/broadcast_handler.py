# bot/handlers/broadcast_handler.py
from telethon import events
from bot.database.firebase_operations import get_all_users
import logging

logger = logging.getLogger(__name__)

async def broadcast_message(event):
    message = event.raw_text.split("/broadcast", 1)[1].strip()
    if message:
        users = get_all_users()
        success_count = 0
        fail_count = 0

        for user in users:
            try:
                await event.client.send_message(user["user_id"], message)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send message to {user['user_id']}: {e}")
                fail_count += 1

        await event.reply(f"Broadcast message sent to {success_count} users. Failed for {fail_count} users.")
    else:
        await event.reply("Please provide a message to broadcast.")