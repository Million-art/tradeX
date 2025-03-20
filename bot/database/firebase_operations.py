# bot/database/firebase_operations.py
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate("bot/database/firebase-key.json") 
firebase_admin.initialize_app(cred)

db = firestore.client()

def add_user(user_id, username, first_name, last_name):
    user_data = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "has_received_welcome": False  
    }
    db.collection("users").document(str(user_id)).set(user_data)

def get_user(user_id):
    user_ref = db.collection("users").document(str(user_id))
    user = user_ref.get()
    if user.exists:
        return user.to_dict()
    return None

def update_user(user_id, data):
    db.collection("users").document(str(user_id)).update(data)

def is_new_user(user_id):
    user = get_user(user_id)
    return user is None
def get_all_users():
    users = db.collection("users").stream()
    return [user.to_dict() for user in users]