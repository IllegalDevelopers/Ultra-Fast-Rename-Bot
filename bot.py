import os
import time
import asyncio
import humanize
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, BOT_TOKEN
from database import set_thumbnail, get_thumbnail, set_caption, get_caption
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

app = Client(
    "UltraRenameBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=32
)

pending_files = {}
last_percentage = {}

# ---------------- SAFE PROGRESS ---------------- #

async def progress(current, total, message, start_time, text):

    percentage = int(current * 100 / total)
    message_id = message.id

    if message_id in last_percentage:
        if percentage - last_percentage[message_id] < 5:
            return

    last_percentage[message_id] = percentage

    diff = time.time() - start_time
    if diff == 0:
        return

    speed = current / diff
    total_size = humanize.naturalsize(total)
    current_size = humanize.naturalsize(current)
    speed_text = humanize.naturalsize(speed) + "/s"

    progress_bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))

    try:
        await message.edit_text(
            f"{text}\n\n"
            f"[{progress_bar}] {percentage}%\n\n"
            f"⚡ Speed: {speed_text}\n"
            f"📦 {current_size} / {total_size}"
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except:
        pass


# ---------------- VIDEO DURATION ---------------- #

def get_video_duration(file_path):
    try:
        parser = createParser(file_path)
        metadata = extractMetadata(parser)
        return int(metadata.get('duration').seconds)
    except:
        return 0


# ---------------- THUMBNAIL OPTIMIZER ---------------- #

def process_thumbnail(input_path, user_id):
    try:
        img = Image.open(input_path)
        img = img.convert("RGB")

        width, height = img.size

        # Resize only if larger than Telegram limit
        if width > 320 or height > 320:
            img.thumbnail((320, 320), Image.LANCZOS)

        output_path = f"thumb_{user_id}.jpg"
        img.save(output_path, "JPEG", quality=95)

        return output_path

    except Exception:
        return None


# ---------------- START ---------------- #

@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    await message.reply_text(
        "🚀 Ultra Fast Rename Bot Ready!\n\n"
        "1️⃣ Send File\n"
        "2️⃣ Use /rename newname.ext\n\n"
        "Caption Variables:\n"
        "{filename}\n"
        "{filesize}"
    )


# ---------------- SETTINGS ---------------- #

@app.on_message(filters.command("setthumb") & filters.reply)
async def set_thumb(client, message: Message):
    if not message.reply_to_message.photo:
        return await message.reply_text("Reply to a photo.")

    file_id = message.reply_to_message.photo.file_id

    # Download immediately to avoid file_reference issue
    temp_path = await client.download_media(file_id)

    final_thumb = process_thumbnail(temp_path, message.from_user.id)

    os.remove(temp_path)

    if final_thumb:
        await set_thumbnail(message.from_user.id, final_thumb)
        await message.reply_text("✅ High Quality Thumbnail Saved!")
    else:
        await message.reply_text("❌ Thumbnail processing failed.")


@app.on_message(filters.command("setcaption"))
async def set_caption_handler(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage:\n/setcaption Your Caption")
    await set_caption(message.from_user.id, message.text.split(" ",1)[1])
    await message.reply_text("✅ Caption Saved!")


# ---------------- STORE FILE ---------------- #

@app.on_message(filters.document | filters.video | filters.audio)
async def store_file(client, message: Message):
    pending_files[message.from_user.id] = message
    await message.reply_text("📁 File Received!\nUse:\n/rename newname.ext")


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

        thumb_path = await get_thumbnail(user_id)
        caption_template = await get_caption(user_id)

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
                thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
                duration=duration,
                progress=progress,
                progress_args=(status, start_time, "⬆️ Uploading...")
            )

        elif original_message.audio:
            await client.send_audio(
                chat_id=message.chat.id,
                audio=new_name,
                caption=final_caption,
                thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
                progress=progress,
                progress_args=(status, start_time, "⬆️ Uploading...")
            )

        else:
            await client.send_document(
                chat_id=message.chat.id,
                document=new_name,
                caption=final_caption,
                thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
                progress=progress,
                progress_args=(status, start_time, "⬆️ Uploading...")
            )

        os.remove(new_name)
        del pending_files[user_id]
        last_percentage.pop(status.id, None)

        await status.edit_text("✅ Completed Successfully!")

    except Exception as e:
        await status.edit_text(f"❌ Error:\n{e}")


# ---------------- RUN ---------------- #

print("🚀 Ultra Rename Bot Running Smoothly...")
app.run()
