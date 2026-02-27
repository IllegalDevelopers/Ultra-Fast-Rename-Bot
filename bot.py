import os
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton
)
from pyrogram.enums import ParseMode
from motor.motor_asyncio import AsyncIOMotorClient
from config import *

# ---------------- APP INIT ---------------- #

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
last_edit_time = {}

# ---------------- ADMIN CHECK ---------------- #

def is_admin(user_id):
    return user_id in ADMINS


# ---------------- PROGRESS BAR ---------------- #

def progress_bar(current, total, start_time, task_type):
    now = time.time()
    diff = now - start_time

    if diff == 0:
        return None

    percentage = current * 100 / total
    speed = current / diff
    speed_mb = speed / (1024 * 1024)
    eta = round((total - current) / speed) if speed > 0 else 0

    bar_length = 20
    filled = int(bar_length * current // total)
    bar = "█" * filled + "░" * (bar_length - filled)

    return (
        f"🔄 <b>{task_type}...</b>\n\n"
        f"<code>[{bar}]</code>\n\n"
        f"📦 {round(current/(1024*1024),2)} MB / {round(total/(1024*1024),2)} MB\n"
        f"⚡ Speed: {round(speed_mb,2)} MB/s\n"
        f"⏳ ETA: {eta} sec\n"
        f"📊 {round(percentage,2)} %"
    )


async def safe_edit(msg, text):
    now = time.time()
    msg_id = msg.id

    if msg_id in last_edit_time:
        if now - last_edit_time[msg_id] < 1.5:   # 1.5 sec delay (anti flood)
            return

    last_edit_time[msg_id] = now
    try:
        await msg.edit(text, parse_mode=ParseMode.HTML)
    except:
        pass


# ---------------- DATABASE ---------------- #

async def set_thumbnail(user_id, file_path):
    await users.update_one(
        {"_id": user_id},
        {"$set": {"thumbnail": file_path}},
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


# ---------------- START ---------------- #

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):

    if not is_admin(message.from_user.id):

        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📞 Contact Admin", url="https://t.me/yourusername")]]
        )

        return await message.reply_text(
            "🚫 <b>You are not allowed to use this bot.</b>\n\nContact admin for access.",
            reply_markup=buttons,
            parse_mode=ParseMode.HTML
        )

    await message.reply_text(
        "🔥 <b>Super Fast Rename Bot Ready!</b>\n\nSend any file to rename.",
        parse_mode=ParseMode.HTML
    )


# ---------------- SET THUMB ---------------- #

@app.on_message(filters.command("setthumb") & filters.private)
async def thumb_info(client, message):
    if not is_admin(message.from_user.id):
        return
    await message.reply_text("Send a photo to set as thumbnail.")


@app.on_message(filters.photo & filters.private)
async def save_thumb(client, message):
    if not is_admin(message.from_user.id):
        return

    path = await message.download()
    await set_thumbnail(message.from_user.id, path)

    await message.reply_text("✅ Thumbnail Saved Successfully (No Quality Loss)")


# ---------------- SET CAPTION ---------------- #

@app.on_message(filters.command("setcaption") & filters.private)
async def set_caption_cmd(client, message):

    if not is_admin(message.from_user.id):
        return

    text = message.text.split(" ", 1)

    if len(text) < 2:
        return await message.reply_text(
            "📝 <b>Usage:</b>\n\n"
            "<code>/setcaption Your Caption Here</code>\n\n"
            "<b>Variables:</b>\n"
            "• <code>{filename}</code>\n"
            "• <code>{filesize}</code>\n"
            "• <code>{extension}</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/setcaption 📂 {filename}\n💾 Size: {filesize}</code>",
            parse_mode=ParseMode.HTML
        )

    await set_caption(message.from_user.id, text[1])
    await message.reply_text("✅ Caption Format Saved!")


# ---------------- RECEIVE FILE ---------------- #

@app.on_message((filters.document | filters.video | filters.audio) & filters.private)
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
        f"📝 <b>Send New File Name</b>\n\nCurrent Name:\n<code>{file.file_name}</code>",
        parse_mode=ParseMode.HTML
    )


# ---------------- RENAME PROCESS ---------------- #

@app.on_message(filters.text & filters.private)
async def rename_process(client, message):

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    if user_id not in pending_files:
        return

    data = pending_files[user_id]
    new_name = message.text.strip()

    progress_msg = await message.reply_text("⚡ Preparing...")

    start_time = time.time()

    # -------- DOWNLOAD -------- #

    file_path = await client.download_media(
        data["file_id"],
        file_name=new_name,
        progress=lambda current, total: asyncio.create_task(
            safe_edit(
                progress_msg,
                progress_bar(current, total, start_time, "Downloading")
            )
        )
    )

    await safe_edit(progress_msg, "🚀 <b>Uploading...</b>")

    start_time = time.time()

    thumb_path = await get_thumbnail(user_id)
    caption_template = await get_caption(user_id)

    file_size_mb = round(data["file_size"] / (1024 * 1024), 2)
    extension = os.path.splitext(new_name)[1]

    if caption_template:
        caption = caption_template.replace("{filename}", new_name)\
                                  .replace("{filesize}", f"{file_size_mb} MB")\
                                  .replace("{extension}", extension)
    else:
        caption = new_name

    # -------- UPLOAD -------- #

    await client.send_document(
        chat_id=message.chat.id,
        document=file_path,
        thumb=thumb_path if thumb_path else None,
        caption=caption,
        parse_mode=ParseMode.HTML,
        progress=lambda current, total: asyncio.create_task(
            safe_edit(
                progress_msg,
                progress_bar(current, total, start_time, "Uploading")
            )
        )
    )

    os.remove(file_path)
    await progress_msg.delete()
    del pending_files[user_id]


print("🚀 Super Fast Rename Bot Running...")
app.run()
