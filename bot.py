import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from motor.motor_asyncio import AsyncIOMotorClient
from config import *

app = Client(
    "rename-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

mongo = AsyncIOMotorClient(MONGO_URI)
db = mongo.rename_bot
users = db.users

# ---------------- DATABASE ---------------- #

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


# ---------------- COMMANDS ---------------- #

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("🔥 Super Fast Rename Bot\n\nSend any file to rename.")

@app.on_message(filters.command("setthumb"))
async def thumb_info(client, message):
    await message.reply_text("Send a photo to set as thumbnail.")

@app.on_message(filters.photo)
async def save_thumb(client, message):
    await set_thumbnail(message.from_user.id, message.photo.file_id)
    await message.reply_text("✅ Thumbnail Saved Successfully!")

@app.on_message(filters.command("setcaption"))
async def set_caption_cmd(client, message):
    text = message.text.split(" ", 1)
    if len(text) < 2:
        return await message.reply_text("Usage:\n/setcaption Your Caption Here")
    
    await set_caption(message.from_user.id, text[1])
    await message.reply_text("✅ Caption Saved Successfully!")


# ---------------- RENAME SYSTEM ---------------- #

@app.on_message(filters.document | filters.video | filters.audio)
async def rename_file(client, message: Message):
    user_id = message.from_user.id
    
    file = message.document or message.video or message.audio
    file_name = file.file_name

    new_name = file_name  # same name (auto)
    
    msg = await message.reply_text("⚡ Downloading...")

    file_path = await message.download(file_name=new_name)

    thumb_id = await get_thumbnail(user_id)
    caption = await get_caption(user_id)

    if not caption:
        caption = new_name

    await msg.edit("🚀 Uploading...")

    await client.send_document(
        chat_id=message.chat.id,
        document=file_path,
        thumb=thumb_id,
        caption=caption
    )

    os.remove(file_path)
    await msg.delete()


print("Bot Running...")
app.run()
