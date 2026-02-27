from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI

client = AsyncIOMotorClient(MONGO_URI)
db = client["rename_bot"]
users = db["users"]

async def set_thumbnail(user_id, file_id):
    await users.update_one(
        {"_id": user_id},
        {"$set": {"thumbnail": file_id}},
        upsert=True
    )

async def get_thumbnail(user_id):
    user = await users.find_one({"_id": user_id})
    return user.get("thumbnail") if user else None

async def set_caption(user_id, caption):
    await users.update_one(
        {"_id": user_id},
        {"$set": {"caption": caption}},
        upsert=True
    )

async def get_caption(user_id):
    user = await users.find_one({"_id": user_id})
    return user.get("caption") if user else None
