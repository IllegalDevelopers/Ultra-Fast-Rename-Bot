import os
from pyrogram import Client, filters
from pyrogram.types import Message
from config import *
from database import *

app = Client(
    "rename_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Start Command
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "👋 Welcome to Super Fast Rename Bot!\n\n"
        "Send me a file to rename.\n"
        "Use:\n"
        "/setthumb - Reply photo to set thumbnail\n"
        "/setcaption - Set custom caption"
    )

# Set Thumbnail
@app.on_message(filters.command("setthumb") & filters.reply)
async def set_thumb(client, message):
    if message.reply_to_message.photo:
        file_id = message.reply_to_message.photo.file_id
        await set_thumbnail(message.from_user.id, file_id)
        await message.reply_text("✅ Custom thumbnail saved!")
    else:
        await message.reply_text("❌ Reply to a photo.")

# Set Caption
@app.on_message(filters.command("setcaption"))
async def set_cap(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /setcaption Your Caption Here")
    
    caption = message.text.split(" ", 1)[1]
    await set_caption(message.from_user.id, caption)
    await message.reply_text("✅ Custom caption saved!")

# Rename File
@app.on_message(filters.document | filters.video | filters.audio)
async def rename_file(client, message: Message):
    user_id = message.from_user.id
    
    file = message.document or message.video or message.audio
    file_name = file.file_name
    new_name = file_name.replace(" ", "_")

    thumb_id = await get_thumbnail(user_id)
    caption = await get_caption(user_id)

    msg = await message.reply_text("⚡ Downloading...")

    file_path = await message.download()
    os.rename(file_path, new_name)

    thumb_path = None

    # 🔥 FIXED THUMBNAIL SYSTEM
    if thumb_id:
        try:
            thumb_path = await client.download_media(thumb_id)
        except:
            thumb_path = None

    await msg.edit("⚡ Uploading...")

    await client.send_document(
        chat_id=message.chat.id,
        document=new_name,
        caption=caption if caption else new_name,
        thumb=thumb_path
    )

    os.remove(new_name)

    if thumb_path:
        os.remove(thumb_path)

    await msg.delete()
