import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate("bot/database/firebase-key.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# Collection names
USERS_COLLECTION = "users"
MESSAGES_COLLECTION = "messages"

def add_user(user_id, username, first_name, last_name):
    user_data = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "has_received_welcome": False
    }
    db.collection(USERS_COLLECTION).document(str(user_id)).set(user_data)

def get_user(user_id):
    user_ref = db.collection(USERS_COLLECTION).document(str(user_id))
    user = user_ref.get()
    if user.exists:
        return user.to_dict()
    return None

def update_user(user_id, data):
    db.collection(USERS_COLLECTION).document(str(user_id)).update(data)

def is_new_user(user_id):
    user = get_user(user_id)
    return user is None

def get_all_users():
    users = db.collection(USERS_COLLECTION).stream()
    return [user.to_dict() for user in users]

def get_dm_message():
    message_ref = db.collection(MESSAGES_COLLECTION).document("welcome_message")
    message = message_ref.get()
    if message.exists:
        return message.to_dict().get("text")
    return None

def set_dm_message(new_message):
    db.collection(MESSAGES_COLLECTION).document("welcome_message").set({"text": new_message})