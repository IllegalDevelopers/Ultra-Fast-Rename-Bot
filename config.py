import os

API_ID = int(os.environ.get("API_ID", "21655449"))
API_HASH = os.environ.get("API_HASH", "112be9974e163f6dbd645ce4b94f4e6a")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7812581699:AAE914UAENlDmOWpKjpqSOj65avld8Pxww8")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://kailash:pass@cluster0.sqtztxm.mongodb.net/?retryWrites=true&w=majority")
# 👇 Multiple admins support
ADMIN_IDS = [1229852181]  # apna Telegram user ID daalo
