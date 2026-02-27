import os
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

# Temporary user file storage
pending_files = {}

# ---------------- START ---------------- #

@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    await message.reply_text(
        "👋 **Welcome to Super Fast Rename Bot!**\n\n"
        "📌 Send a file → then use:\n"
        "`/rename newname.ext`\n\n"
        "Commands:\n"
        "• /setthumb (reply photo)\n"
        "• /delthumb\n"
        "• /setcaption Your Caption\n"
        "• /delcaption"
    )

# ---------------- SET THUMB ---------------- #

@app.on_message(filters.command("setthumb") & filters.reply)
async def set_thumb(client, message: Message):
    if not message.reply_to_message.photo:
        return await message.reply_text("❌ Reply to a photo.")

    file_id = message.reply_to_message.photo.file_id
    await set_thumbnail(message.from_user.id, file_id)
    await message.reply_text("✅ Thumbnail saved!")

# ---------------- DELETE THUMB ---------------- #

@app.on_message(filters.command("delthumb"))
async def del_thumb(client, message: Message):
    await set_thumbnail(message.from_user.id, None)
    await message.reply_text("🗑 Thumbnail deleted!")

# ---------------- SET CAPTION ---------------- #

@app.on_message(filters.command("setcaption"))
async def set_cap(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: /setcaption Your Caption")

    caption = message.text.split(" ", 1)[1]
    await set_caption(message.from_user.id, caption)
    await message.reply_text("✅ Caption saved!")

# ---------------- DELETE CAPTION ---------------- #

@app.on_message(filters.command("delcaption"))
async def del_cap(client, message: Message):
    await set_caption(message.from_user.id, None)
    await message.reply_text("🗑 Caption deleted!")

# ---------------- STORE FILE ---------------- #

@app.on_message(filters.document | filters.video | filters.audio)
async def store_file(client, message: Message):

    pending_files[message.from_user.id] = message

    await message.reply_text(
        "📁 File received!\n\n"
        "Now send new name:\n"
        "`/rename newname.ext`"
    )

# ---------------- RENAME COMMAND ---------------- #

@app.on_message(filters.command("rename"))
async def rename_file(client, message: Message):

    user_id = message.from_user.id

    if user_id not in pending_files:
        return await message.reply_text("❌ Send a file first.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: /rename newname.ext")

    new_name = message.text.split(" ", 1)[1]

    original_message = pending_files[user_id]
    file = original_message.document or original_message.video or original_message.audio

    status = await message.reply_text("⚡ Downloading...")

    try:
        # Download original file
        file_path = await original_message.download()
        os.rename(file_path, new_name)

        # Get user settings
        thumb_id = await get_thumbnail(user_id)
        caption = await get_caption(user_id)
        thumb_path = None

        if thumb_id:
            try:
                thumb_path = await client.download_media(thumb_id)
            except:
                thumb_path = None

        await status.edit("⚡ Uploading...")

        # Send correct media type
        if original_message.video:
            await client.send_video(
                chat_id=message.chat.id,
                video=new_name,
                caption=caption if caption else new_name,
                thumb=thumb_path
            )

        elif original_message.audio:
            await client.send_audio(
                chat_id=message.chat.id,
                audio=new_name,
                caption=caption if caption else new_name,
                thumb=thumb_path
            )

        else:
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
        del pending_files[user_id]

    except Exception as e:
        await status.edit(f"❌ Error:\n`{e}`")

# ---------------- RUN ---------------- #

print("🚀 Super Fast Rename Bot Running...")
app.run()
