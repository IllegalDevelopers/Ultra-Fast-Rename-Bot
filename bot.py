import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton
)
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

pending_files = {}

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


# ---------------- ADMIN CHECK ---------------- #

def is_admin(user_id):
    return user_id in ADMINS


# ---------------- START ---------------- #

@app.on_message(filters.command("start"))
async def start(client, message):
    if not is_admin(message.from_user.id):
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📢 Contact Admin", url="https://t.me/yourusername")]]
        )
        return await message.reply_text(
            "🚫 You are not allowed to use this bot.\n\nContact Admin for access.",
            reply_markup=buttons
        )

    await message.reply_text("🔥 Super Fast Rename Bot Ready!\n\nSend any file.")


# ---------------- SET THUMB ---------------- #

@app.on_message(filters.command("setthumb"))
async def thumb_info(client, message):
    if not is_admin(message.from_user.id):
        return
    await message.reply_text("Send a photo to set as thumbnail.")

@app.on_message(filters.photo)
async def save_thumb(client, message):
    if not is_admin(message.from_user.id):
        return
    
    # Download to avoid quality loss
    path = await message.download()
    await set_thumbnail(message.from_user.id, path)
    await message.reply_text("✅ Thumbnail Saved (No Quality Loss)")


# ---------------- SET CAPTION ---------------- #

@app.on_message(filters.command("setcaption"))
async def set_caption_cmd(client, message):
    if not is_admin(message.from_user.id):
        return

    text = message.text.split(" ", 1)
    if len(text) < 2:
        return await message.reply_text(
            "📝 Usage:\n\n"
            "/setcaption Your Caption Here\n\n"
            "Available Variables:\n"
            "{filename} → Original File Name\n"
            "{filesize} → File Size\n"
            "{extension} → File Extension\n\n"
            "Example:\n"
            "/setcaption 📂 {filename}\n💾 Size: {filesize}"
        )
    
    await set_caption(message.from_user.id, text[1])
    await message.reply_text("✅ Caption Format Saved!")


# ---------------- RECEIVE FILE ---------------- #

@app.on_message(filters.document | filters.video | filters.audio)
async def ask_new_name(client, message: Message):
    if not is_admin(message.from_user.id):
        return

    file = message.document or message.video or message.audio

    pending_files[message.from_user.id] = {
        "file_id": file.file_id,
        "file_name": file.file_name,
        "file_size": file.file_size
    }

    await message.reply_text(
        f"📝 Send New File Name\n\nCurrent Name:\n`{file.file_name}`",
        parse_mode="markdown"
    )


# ---------------- RENAME PROCESS ---------------- #

@app.on_message(filters.text & ~filters.command(["start","setthumb","setcaption"]))
async def rename_process(client, message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    if user_id not in pending_files:
        return

    data = pending_files[user_id]
    new_name = message.text.strip()

    msg = await message.reply_text("⚡ Downloading...")

    file_path = await client.download_media(data["file_id"], file_name=new_name)

    thumb_path = await get_thumbnail(user_id)
    caption_template = await get_caption(user_id)

    file_size_mb = round(data["file_size"] / (1024*1024), 2)
    extension = os.path.splitext(new_name)[1]

    if caption_template:
        caption = caption_template.replace("{filename}", new_name)\
                                  .replace("{filesize}", f"{file_size_mb} MB")\
                                  .replace("{extension}", extension)
    else:
        caption = new_name

    await msg.edit("🚀 Uploading...")

    await client.send_document(
        chat_id=message.chat.id,
        document=file_path,
        thumb=thumb_path if thumb_path else None,
        caption=caption
    )

    os.remove(file_path)
    await msg.delete()
    del pending_files[user_id]


print("Bot Running...")
app.run()
