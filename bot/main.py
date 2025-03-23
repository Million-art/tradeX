from http.server import BaseHTTPRequestHandler
import os
import json
import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from config.cloudinary_config import upload_media 
from http.server import BaseHTTPRequestHandler, HTTPServer

# Load environment variables
load_dotenv()
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID'))

# Initialize Firebase
firebase_config = json.loads(os.environ.get('FIREBASE_SERVICE_ACCOUNT'))
cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)
db = firestore.client()

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

# Function to get the DM message from Firebase
def get_dm_message():
    message_ref = db.collection(MESSAGES_COLLECTION).document("welcome_message")
    message = message_ref.get()
    if message.exists:
        return message.to_dict()
    return {"text": DEFAULT_WELCOME_MESSAGE}

# Function to set the DM message in Firebase
def set_dm_message(new_message, media_url=None, media_type=None):
    message_data = {"text": new_message}
    if media_url:
        message_data["media_url"] = media_url
        message_data["media_type"] = media_type
    db.collection(MESSAGES_COLLECTION).document("welcome_message").set(message_data)

# Function to add a user to Firebase
def add_user(user_id, username, first_name, last_name):
    user_data = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "has_received_welcome": False
    }
    db.collection(USERS_COLLECTION).document(str(user_id)).set(user_data)

# Function to check if a user is new
def is_new_user(user_id):
    user_ref = db.collection(USERS_COLLECTION).document(str(user_id))
    user = user_ref.get()
    return not user.exists

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
    media_url = message_data.get("media_url")
    media_type = message_data.get("media_type")

    try:
        if media_url:
            if media_type == "photo":
                await bot.send_photo(
                    chat_id=user_id,
                    photo=media_url,
                    caption=dm_message
                )
            elif media_type == "video":
                await bot.send_video(
                    chat_id=user_id,
                    video=media_url,
                    caption=dm_message
                )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=dm_message
            )
        print(f"DM sent to {username} (ID: {user_id})")
    except Exception as e:
        print(f"Failed to send DM to {username}: {e}")

    # Approve the join request
    await bot.approve_chat_join_request(message.chat.id, user_id)
    print(f"Join request approved for {username} (ID: {user_id})")

# Command to change the welcome message
@bot.message_handler(commands=['set_welcome'])
async def set_welcome_message(message: types.Message):
    user_id = message.from_user.id

    # Check if the user is the admin
    if user_id != ADMIN_USER_ID:
        await bot.reply_to(message, "You are not authorized to use this command.")
        return

    # Check if the message contains a photo or video
    media_url = None
    media_type = None
    if message.photo:
        file_info = await bot.get_file(message.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        media_url = upload_media(file_url, resource_type="image")
        media_type = "photo"
    elif message.video:
        file_info = await bot.get_file(message.video.file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        media_url = upload_media(file_url, resource_type="video")
        media_type = "video"

    # Get the new welcome message from the command arguments or caption
    new_message = message.caption if (message.photo or message.video) else " ".join(message.text.split()[1:])
    if not new_message:
        await bot.reply_to(message, "Please provide a new welcome message.")
        return

    # Update the DM message in Firebase
    set_dm_message(new_message, media_url, media_type)
    await bot.reply_to(message, "Welcome message updated successfully!")

# Command to send a broadcast message
@bot.message_handler(commands=['broadcast'])
async def broadcast(message: types.Message):
    user_id = message.from_user.id

    # Check if the user is the admin
    if user_id != ADMIN_USER_ID:
        await bot.reply_to(message, "You are not authorized to use this command.")
        return

    # Check if the message contains a photo or video
    media_url = None
    media_type = None
    if message.photo:
        file_info = await bot.get_file(message.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        media_url = upload_media(file_url, resource_type="image")
        media_type = "photo"
    elif message.video:
        file_info = await bot.get_file(message.video.file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        media_url = upload_media(file_url, resource_type="video")
        media_type = "video"

    # Get the broadcast message from the command arguments or caption
    broadcast_message = message.caption if (message.photo or message.video) else " ".join(message.text.split()[1:])
    if not broadcast_message:
        await bot.reply_to(message, "Please provide a message to broadcast.")
        return

    # Send the broadcast message to all users
    users = db.collection(USERS_COLLECTION).stream()
    for user in users:
        user_data = user.to_dict()
        try:
            if media_url:
                if media_type == "photo":
                    await bot.send_photo(
                        chat_id=user_data["user_id"],
                        photo=media_url,
                        caption=broadcast_message
                    )
                elif media_type == "video":
                    await bot.send_video(
                        chat_id=user_data["user_id"],
                        video=media_url,
                        caption=broadcast_message
                    )
            else:
                await bot.send_message(
                    chat_id=user_data["user_id"],
                    text=broadcast_message
                )
            print(f"Broadcast message sent to {user_data['first_name']} (ID: {user_data['user_id']})")
        except Exception as e:
            print(f"Failed to send broadcast message to {user_data['first_name']}: {e}")

    await bot.reply_to(message, "Broadcast message sent to all users.")

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
    print("Starting HTTP server on port 8080...")
    httpd.serve_forever()

# Run the bot
if __name__ == "__main__":
    # Start the HTTP server in a separate thread
    import threading
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # Start the bot's event loop
    print("Starting bot...")
    asyncio.run(bot.polling())