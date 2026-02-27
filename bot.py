import os
import humanize
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN
from database import set_thumbnail, get_thumbnail, set_caption, get_caption
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

app = Client(
    "SuperFastRenameBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

pending_files = {}

# ---------------- VIDEO DURATION FUNCTION ---------------- #

def get_video_duration(file_path):
    try:
        parser = createParser(file_path)
        metadata = extractMetadata(parser)
        return int(metadata.get('duration').seconds)
    except:
        return 0

# ---------------- START ---------------- #

@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    await message.reply_text(
        "👋 **Super Fast Rename Bot Ready!**\n\n"
        "1️⃣ Send File\n"
        "2️⃣ Use `/rename newname.ext`\n\n"
        "Commands:\n"
        "• /setthumb (reply photo)\n"
        "• /delthumb\n"
        "• /setcaption Your Caption\n"
        "• /delcaption\n\n"
        "Caption Variables:\n"
        "`{filename}`\n"
        "`{filesize}`"
    )

# ---------------- THUMBNAIL ---------------- #

@app.on_message(filters.command("setthumb") & filters.reply)
async def set_thumb(client, message: Message):
    if not message.reply_to_message.photo:
        return await message.reply_text("❌ Reply to a photo.")

    await set_thumbnail(message.from_user.id, message.reply_to_message.photo.file_id)
    await message.reply_text("✅ Thumbnail Saved!")

@app.on_message(filters.command("delthumb"))
async def del_thumb(client, message: Message):
    await set_thumbnail(message.from_user.id, None)
    await message.reply_text("🗑 Thumbnail Deleted!")

# ---------------- CAPTION ---------------- #

@app.on_message(filters.command("setcaption"))
async def set_cap(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage:\n/setcaption Your Caption")

    caption = message.text.split(" ", 1)[1]
    await set_caption(message.from_user.id, caption)
    await message.reply_text("✅ Caption Saved!")

@app.on_message(filters.command("delcaption"))
async def del_cap(client, message: Message):
    await set_caption(message.from_user.id, None)
    await message.reply_text("🗑 Caption Deleted!")

# ---------------- STORE FILE ---------------- #

@app.on_message(filters.document | filters.video | filters.audio)
async def store_file(client, message: Message):
    pending_files[message.from_user.id] = message
    await message.reply_text("📁 File Received!\nNow send:\n`/rename newname.ext`")

# ---------------- RENAME ---------------- #

@app.on_message(filters.command("rename"))
async def rename_file(client, message: Message):

    user_id = message.from_user.id

    if user_id not in pending_files:
        return await message.reply_text("❌ Send file first.")

    if len(message.command) < 2:
        return await message.reply_text("Usage:\n/rename newname.ext")

    new_name = message.text.split(" ", 1)[1]
    original_message = pending_files[user_id]
    file = original_message.document or original_message.video or original_message.audio

    status = await message.reply_text("⚡ Downloading...")

    try:
        file_path = await original_message.download()
        os.rename(file_path, new_name)

        thumb_id = await get_thumbnail(user_id)
        caption_template = await get_caption(user_id)

        thumb_path = None
        if thumb_id:
            try:
                thumb_path = await client.download_media(thumb_id)
            except:
                thumb_path = None

        file_size = humanize.naturalsize(os.path.getsize(new_name))

        if caption_template:
            final_caption = caption_template.replace("{filename}", new_name)
            final_caption = final_caption.replace("{filesize}", file_size)
        else:
            final_caption = new_name

        await status.edit("⚡ Uploading...")

        # Upload Correct Media Type
        if original_message.video:
            duration = get_video_duration(new_name)

            await client.send_video(
                chat_id=message.chat.id,
                video=new_name,
                caption=final_caption,
                thumb=thumb_path,
                duration=duration
            )

        elif original_message.audio:
            await client.send_audio(
                chat_id=message.chat.id,
                audio=new_name,
                caption=final_caption,
                thumb=thumb_path
            )

        else:
            await client.send_document(
                chat_id=message.chat.id,
                document=new_name,
                caption=final_caption,
                thumb=thumb_path
            )

        # Cleanup
        os.remove(new_name)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)

        del pending_files[user_id]
        await status.delete()

    except Exception as e:
        await status.edit(f"❌ Error:\n`{e}`")

# ---------------- RUN ---------------- #

print("🚀 Super Fast Rename Bot Running...")
app.run()
