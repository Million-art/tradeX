from http.server import BaseHTTPRequestHandler
import os
import json
import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

# Load environment variables
load_dotenv()
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID'))

# Initialize Firebase
try:
    firebase_config = json.loads(os.environ.get('FIREBASE_SERVICE_ACCOUNT'))
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    logging.error(f"Failed to initialize Firebase: {e}")
    raise

# Initialize bot
bot = AsyncTeleBot(BOT_TOKEN)

# Collection names
USERS_COLLECTION = "users"
MESSAGES_COLLECTION = "messages"

# Default welcome message
DEFAULT_WELCOME_MESSAGE = """
Welcome! Here are the group policies:
1. Be respectful.
2. No spam.
3. Follow the rules.
"""

# Session management
USER_SESSIONS = {}

# Function to get the DM message from Firebase
def get_dm_message():
    try:
        message_ref = db.collection(MESSAGES_COLLECTION).document("welcome_message")
        message = message_ref.get()
        if message.exists:
            return message.to_dict()
        return {"text": DEFAULT_WELCOME_MESSAGE}
    except Exception as e:
        logging.error(f"Failed to get DM message: {e}")
        return {"text": DEFAULT_WELCOME_MESSAGE}

# Function to set the DM message in Firebase
def set_dm_message(new_message, media_file_id=None, media_type=None):
    try:
        message_data = {"text": new_message}
        if media_file_id:
            message_data["media_file_id"] = media_file_id
            message_data["media_type"] = media_type
        db.collection(MESSAGES_COLLECTION).document("welcome_message").set(message_data)
    except Exception as e:
        logging.error(f"Failed to set DM message: {e}")

# Function to add a user to Firebase
def add_user(user_id, username, first_name, last_name):
    try:
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "has_received_welcome": False
        }
        db.collection(USERS_COLLECTION).document(str(user_id)).set(user_data)
    except Exception as e:
        logging.error(f"Failed to add user {user_id}: {e}")

# Function to check if a user is new
def is_new_user(user_id):
    try:
        user_ref = db.collection(USERS_COLLECTION).document(str(user_id))
        user = user_ref.get()
        return not user.exists
    except Exception as e:
        logging.error(f"Failed to check if user {user_id} is new: {e}")
        return True

# Handle join requests
@bot.chat_join_request_handler()
async def handle_join_request(message: types.ChatJoinRequest):
    user = message.from_user
    user_id = user.id
    username = user.username or user.first_name
    first_name = user.first_name
    last_name = user.last_name or ""

    # Add user to Firebase if they are new
    if is_new_user(user_id):
        add_user(user_id, username, first_name, last_name)

    # Get the DM message
    message_data = get_dm_message()
    dm_message = message_data.get("text", DEFAULT_WELCOME_MESSAGE)
    media_file_id = message_data.get("media_file_id")
    media_type = message_data.get("media_type")

    try:
        if media_file_id:
            if media_type == "photo":
                await bot.send_photo(
                    chat_id=user_id,
                    photo=media_file_id,
                    caption=dm_message
                )
            elif media_type == "video":
                await bot.send_video(
                    chat_id=user_id,
                    video=media_file_id,
                    caption=dm_message
                )
            elif media_type == "animation":  # Handle GIFs
                await bot.send_animation(
                    chat_id=user_id,
                    animation=media_file_id,
                    caption=dm_message
                )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=dm_message
            )
        logging.info(f"DM sent to {username} (ID: {user_id})")
    except Exception as e:
        logging.error(f"Failed to send DM to {username}: {e}")

    # Approve the join request
    await bot.approve_chat_join_request(message.chat.id, user_id)
    logging.info(f"Join request approved for {username} (ID: {user_id})")

# Command to start setting the welcome message
@bot.message_handler(commands=['set_welcome'])
async def start_set_welcome(message: types.Message):
    user_id = message.from_user.id

    # Check if the user is the admin
    if user_id != ADMIN_USER_ID:
        await bot.reply_to(message, "You are not authorized to use this command.")
        return

    # Clear any existing session for this user
    USER_SESSIONS.pop(user_id, None)

    # Ask the user to provide the welcome message
    await bot.reply_to(message, "Please provide a new welcome message.")
    USER_SESSIONS[user_id] = {"command": "set_welcome", "state": "awaiting_welcome_message"}
    logging.info(f"User {user_id} started setting welcome message.")

# Handle the user's response for the welcome message
@bot.message_handler(func=lambda message: USER_SESSIONS.get(message.from_user.id, {}).get("command") == "set_welcome" and USER_SESSIONS.get(message.from_user.id, {}).get("state") == "awaiting_welcome_message")
async def handle_welcome_message(message: types.Message):
    user_id = message.from_user.id

    # Store the welcome message text
    welcome_message = message.text

    # Ask the user to provide the media (photo, video, or GIF) or click /empty
    await bot.reply_to(message, "Please upload a photo, video, or GIF for the welcome message or click /empty to skip media.")
    USER_SESSIONS[user_id] = {"command": "set_welcome", "state": "awaiting_media_or_empty", "welcome_message": welcome_message}
    logging.info(f"User {user_id} provided welcome message. State: awaiting_media_or_empty")

# Handle the user's media upload or /empty command for set_welcome
@bot.message_handler(func=lambda message: USER_SESSIONS.get(message.from_user.id, {}).get("command") == "set_welcome" and USER_SESSIONS.get(message.from_user.id, {}).get("state") == "awaiting_media_or_empty")
async def handle_set_welcome_media_or_empty(message: types.Message):
    user_id = message.from_user.id

    # Get the welcome message from the session
    welcome_message = USER_SESSIONS[user_id].get("welcome_message")
    media_file_id = None
    media_type = None

    if message.text and message.text.strip().lower() == "/empty":
        # User chose to skip media
        logging.info(f"User {user_id} chose to skip media.")
    elif message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = "photo"
        logging.info(f"User {user_id} uploaded a photo. File ID: {media_file_id}")
    elif message.video:
        media_file_id = message.video.file_id
        media_type = "video"
        logging.info(f"User {user_id} uploaded a video. File ID: {media_file_id}")
    elif message.document and message.document.mime_type == "video/mp4":  # Handle GIFs
        media_file_id = message.document.file_id
        media_type = "animation"
        logging.info(f"User {user_id} uploaded a GIF. File ID: {media_file_id}")
    elif message.animation:  # Handle GIFs sent as animations
        media_file_id = message.animation.file_id
        media_type = "animation"
        logging.info(f"User {user_id} uploaded a GIF. File ID: {media_file_id}")
    else:
        # Invalid input
        await bot.reply_to(message, "Invalid input. Please upload a photo, video, or GIF, or click /empty to skip media.")
        return

    # Update the DM message in Firebase
    set_dm_message(welcome_message, media_file_id, media_type)
    await bot.reply_to(message, "Welcome message updated successfully!")
    logging.info(f"User {user_id} updated welcome message.")

    # Clear the user's session
    USER_SESSIONS.pop(user_id, None)

# Command to start a broadcast
@bot.message_handler(commands=['broadcast'])
async def start_broadcast(message: types.Message):
    user_id = message.from_user.id

    # Check if the user is the admin
    if user_id != ADMIN_USER_ID:
        await bot.reply_to(message, "You are not authorized to use this command.")
        return

    # Clear any existing session for this user
    USER_SESSIONS.pop(user_id, None)

    # Ask the user to provide the broadcast message
    await bot.reply_to(message, "Please provide the broadcast message.")
    USER_SESSIONS[user_id] = {"command": "broadcast", "state": "awaiting_broadcast_message"}
    logging.info(f"User {user_id} started broadcast. State: awaiting_broadcast_message")

# Handle the user's response for the broadcast message
@bot.message_handler(func=lambda message: USER_SESSIONS.get(message.from_user.id, {}).get("command") == "broadcast" and USER_SESSIONS.get(message.from_user.id, {}).get("state") == "awaiting_broadcast_message")
async def handle_broadcast_message(message: types.Message):
    user_id = message.from_user.id

    # Store the broadcast message text
    broadcast_message = message.text

    # Ask the user to provide the media (photo, video, or GIF) or click /empty
    await bot.reply_to(message, "Please upload a photo, video, or GIF for the broadcast message or click /empty to skip media.")
    USER_SESSIONS[user_id] = {"command": "broadcast", "state": "awaiting_broadcast_media_or_empty", "broadcast_message": broadcast_message}
    logging.info(f"User {user_id} provided broadcast message. State: awaiting_broadcast_media_or_empty")

# Handle the user's media upload or /empty command for broadcast
@bot.message_handler(func=lambda message: USER_SESSIONS.get(message.from_user.id, {}).get("command") == "broadcast" and USER_SESSIONS.get(message.from_user.id, {}).get("state") == "awaiting_broadcast_media_or_empty")
async def handle_broadcast_media_or_empty(message: types.Message):
    user_id = message.from_user.id

    # Get the broadcast message from the session
    broadcast_message = USER_SESSIONS[user_id].get("broadcast_message")
    media_file_id = None
    media_type = None

    if message.text and message.text.strip().lower() == "/empty":
        # User chose to skip media
        logging.info(f"User {user_id} chose to skip media.")
    elif message.photo:
        media_file_id = message.photo[-1].file_id  # Get the highest resolution photo's file_id
        media_type = "photo"
        logging.info(f"User {user_id} uploaded a photo. File ID: {media_file_id}")
    elif message.video:
        media_file_id = message.video.file_id
        media_type = "video"
        logging.info(f"User {user_id} uploaded a video. File ID: {media_file_id}")
    elif message.document and message.document.mime_type == "video/mp4":  # Handle GIFs
        media_file_id = message.document.file_id
        media_type = "animation"
        logging.info(f"User {user_id} uploaded a GIF. File ID: {media_file_id}")
    elif message.animation:  # Handle GIFs sent as animations
        media_file_id = message.animation.file_id
        media_type = "animation"
        logging.info(f"User {user_id} uploaded a GIF. File ID: {media_file_id}")
    else:
        # Invalid input
        await bot.reply_to(message, "Invalid input. Please upload a photo, video, or GIF, or click /empty to skip media.")
        return

    # Send the broadcast message to all users
    users = db.collection(USERS_COLLECTION).stream()
    success_count = 0
    fail_count = 0

    for user in users:
        user_data = user.to_dict()
        try:
            # Check if the user has started a conversation with the bot
            await bot.send_chat_action(user_data["user_id"], "typing")  # Test if the bot can interact with the user
            if media_file_id:
                if media_type == "photo":
                    await bot.send_photo(
                        chat_id=user_data["user_id"],
                        photo=media_file_id,
                        caption=broadcast_message
                    )
                elif media_type == "video":
                    await bot.send_video(
                        chat_id=user_data["user_id"],
                        video=media_file_id,
                        caption=broadcast_message
                    )
                elif media_type == "animation":
                    await bot.send_animation(
                        chat_id=user_data["user_id"],
                        animation=media_file_id,
                        caption=broadcast_message
                    )
            else:
                await bot.send_message(
                    chat_id=user_data["user_id"],
                    text=broadcast_message
                )
            success_count += 1
            logging.info(f"Broadcast message sent to {user_data['first_name']} (ID: {user_data['user_id']})")
        except Exception as e:
            fail_count += 1
            logging.error(f"Failed to send broadcast message to {user_data['first_name']} (ID: {user_data['user_id']}): {e}")

    await bot.reply_to(message, f"Broadcast message sent successfully to {success_count} users. Failed for {fail_count} users.")
    logging.info(f"User {user_id} completed broadcast. Session cleared.")

    # Clear the user's session
    USER_SESSIONS.pop(user_id, None)

# Command to start the bot
@bot.message_handler(commands=['start'])
async def start(message: types.Message):
    await bot.reply_to(message, "Hello! I'm your channel manager bot.")

# HTTP handler for Vercel
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        update_dict = json.loads(post_data.decode('utf-8'))

        asyncio.run(self.process_update(update_dict))

        self.send_response(200)
        self.end_headers()

    async def process_update(self, update_dict):
        update = types.Update.de_json(update_dict)
        await bot.process_new_updates([update])

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write('Hello, BOT is running!'.encode('utf-8'))

# Start the HTTP server
def run_server():
    server_address = ('', 8080)  # Listen on all interfaces, port 8080
    httpd = HTTPServer(server_address, handler)
    logging.info("Starting HTTP server on port 8080...")
    httpd.serve_forever()

# Run the bot
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Start the HTTP server in a separate thread
    import threading
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # Start the bot's event loop
    logging.info("Starting bot...")
    asyncio.run(bot.polling())