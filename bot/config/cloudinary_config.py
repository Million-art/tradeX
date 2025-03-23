# cloudinary_config.py
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Cloudinary credentials
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')

# Initialize Cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

# Function to upload media to Cloudinary
def upload_media(file_url, resource_type="auto"):
    """
    Uploads a file to Cloudinary and returns the secure URL.
    :param file_url: URL of the file to upload
    :param resource_type: Type of resource (e.g., "image", "video", "auto")
    :return: Secure URL of the uploaded file
    """
    try:
        upload_result = cloudinary.uploader.upload(file_url, resource_type=resource_type)
        return upload_result['secure_url']
    except Exception as e:
        print(f"Failed to upload media to Cloudinary: {e}")
        return None