import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN
from database import set_thumbnail, get_thumbnail, set_caption, get_caption

app = Client(
    "SuperFastRenameBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ---------------- START COMMAND ---------------- #

@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    await message.reply_text(
        "👋 **Welcome to Super Fast Rename Bot!**\n\n"
        "📌 Send me any file to auto rename.\n\n"
        "Available Commands:\n"
        "• /setthumb - Reply to a photo to set custom thumbnail\n"
        "• /delthumb - Delete saved thumbnail\n"
        "• /setcaption Your Caption - Set custom caption\n"
        "• /delcaption - Delete custom caption\n"
    )

# ---------------- SET THUMBNAIL ---------------- #

@app.on_message(filters.command("setthumb") & filters.reply)
async def set_thumb(client, message: Message):
    if not message.reply_to_message.photo:
        return await message.reply_text("❌ Reply to a photo to set thumbnail.")

    file_id = message.reply_to_message.photo.file_id
    await set_thumbnail(message.from_user.id, file_id)

    await message.reply_text("✅ Custom thumbnail saved successfully!")

# ---------------- DELETE THUMBNAIL ---------------- #

@app.on_message(filters.command("delthumb"))
async def delete_thumb(client, message: Message):
    await set_thumbnail(message.from_user.id, None)
    await message.reply_text("🗑 Custom thumbnail deleted!")

# ---------------- SET CAPTION ---------------- #

@app.on_message(filters.command("setcaption"))
async def set_cap(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Usage:\n/setcaption Your Caption Here"
        )

    caption = message.text.split(" ", 1)[1]
    await set_caption(message.from_user.id, caption)

    await message.reply_text("✅ Custom caption saved successfully!")

# ---------------- DELETE CAPTION ---------------- #

@app.on_message(filters.command("delcaption"))
async def delete_cap(client, message: Message):
    await set_caption(message.from_user.id, None)
    await message.reply_text("🗑 Custom caption deleted!")

# ---------------- RENAME FILE HANDLER ---------------- #

@app.on_message(filters.document | filters.video | filters.audio)
async def rename_file(client, message: Message):

    user_id = message.from_user.id
    file = message.document or message.video or message.audio

    if not file.file_name:
        return await message.reply_text("❌ File name not found!")

    original_name = file.file_name
    new_name = original_name.replace(" ", "_")

    status = await message.reply_text("⚡ Downloading...")

    try:
        # Download File
        file_path = await message.download()
        os.rename(file_path, new_name)

        # Get user settings
        thumb_id = await get_thumbnail(user_id)
        caption = await get_caption(user_id)

        thumb_path = None

        # 🔥 FIXED THUMB SYSTEM (download file_id first)
        if thumb_id:
            try:
                thumb_path = await client.download_media(thumb_id)
            except Exception:
                thumb_path = None

        await status.edit("⚡ Uploading...")

        await client.send_document(
            chat_id=message.chat.id,
            document=new_name,
            caption=caption if caption else new_name,
            thumb=thumb_path
        )

        # Cleanup
        os.remove(new_name)

        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)

        await status.delete()

    except Exception as e:
        await status.edit(f"❌ Error:\n`{e}`")

# ---------------- RUN BOT ---------------- #

print("🚀 Super Fast Rename Bot Started...")
app.run()
