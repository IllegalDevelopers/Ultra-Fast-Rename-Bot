import os
import time
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

# ---------------- PROGRESS FUNCTION ---------------- #

async def progress(current, total, message, start_time, text):
    now = time.time()
    diff = now - start_time

    if diff == 0:
        return

    percentage = current * 100 / total
    speed = current / diff
    elapsed_time = round(diff)
    total_size = humanize.naturalsize(total)
    current_size = humanize.naturalsize(current)
    speed_text = humanize.naturalsize(speed) + "/s"

    progress_bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))

    await message.edit_text(
        f"{text}\n\n"
        f"[{progress_bar}] {round(percentage, 2)}%\n\n"
        f"⚡ Speed: {speed_text}\n"
        f"📦 {current_size} / {total_size}\n"
        f"⏳ Time: {elapsed_time}s"
    )

# ---------------- VIDEO DURATION ---------------- #

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
        "👋 Super Fast Rename Bot Ready!\n\n"
        "Send file → then use:\n"
        "/rename newname.ext\n\n"
        "Caption Variables:\n"
        "{filename}\n"
        "{filesize}"
    )

# ---------------- SETTINGS ---------------- #

@app.on_message(filters.command("setthumb") & filters.reply)
async def set_thumb(client, message: Message):
    if not message.reply_to_message.photo:
        return await message.reply_text("Reply to a photo.")
    await set_thumbnail(message.from_user.id, message.reply_to_message.photo.file_id)
    await message.reply_text("✅ Thumbnail Saved!")

@app.on_message(filters.command("setcaption"))
async def set_cap(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage:\n/setcaption Your Caption")
    await set_caption(message.from_user.id, message.text.split(" ",1)[1])
    await message.reply_text("✅ Caption Saved!")

# ---------------- STORE FILE ---------------- #

@app.on_message(filters.document | filters.video | filters.audio)
async def store_file(client, message: Message):
    pending_files[message.from_user.id] = message
    await message.reply_text("File received.\nUse:\n/rename newname.ext")

# ---------------- RENAME ---------------- #

@app.on_message(filters.command("rename"))
async def rename_file(client, message: Message):

    user_id = message.from_user.id

    if user_id not in pending_files:
        return await message.reply_text("Send file first.")

    if len(message.command) < 2:
        return await message.reply_text("Usage:\n/rename newname.ext")

    new_name = message.text.split(" ",1)[1]
    original_message = pending_files[user_id]

    status = await message.reply_text("Starting...")

    try:
        # -------- DOWNLOAD -------- #
        start_time = time.time()

        file_path = await original_message.download(
            progress=progress,
            progress_args=(status, start_time, "⬇️ Downloading...")
        )

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

        # -------- UPLOAD -------- #
        start_time = time.time()

        if original_message.video:
            duration = get_video_duration(new_name)

            await client.send_video(
                chat_id=message.chat.id,
                video=new_name,
                caption=final_caption,
                thumb=thumb_path,
                duration=duration,
                progress=progress,
                progress_args=(status, start_time, "⬆️ Uploading...")
            )

        elif original_message.audio:
            await client.send_audio(
                chat_id=message.chat.id,
                audio=new_name,
                caption=final_caption,
                thumb=thumb_path,
                progress=progress,
                progress_args=(status, start_time, "⬆️ Uploading...")
            )

        else:
            await client.send_document(
                chat_id=message.chat.id,
                document=new_name,
                caption=final_caption,
                thumb=thumb_path,
                progress=progress,
                progress_args=(status, start_time, "⬆️ Uploading...")
            )

        os.remove(new_name)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)

        del pending_files[user_id]

        await status.edit_text("✅ Completed Successfully!")

    except Exception as e:
        await status.edit_text(f"Error:\n{e}")

# ---------------- RUN ---------------- #

print("🚀 Rename Bot With Live Progress Running...")
app.run()
