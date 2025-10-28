import os
import re
import tempfile
import logging
import asyncio
from yt_dlp import YoutubeDL
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required")

TIKTOK_RE = re.compile(
    r"(https?://)?(www\.)?(vm\.)?tiktok\.com/[^\s]+|https?://m\.tiktok\.com/[^\s]+",
    re.IGNORECASE
)

YTDLP_OPTS = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'merge_output_format': 'mp4',
    'quiet': True,
    'no_warnings': True,
}

def download_tiktok(url: str, dest_dir: str) -> str:
    opts = {**YTDLP_OPTS, 'outtmpl': os.path.join(dest_dir, '%(id)s.%(ext)s')}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.effective_message.text or update.effective_message.caption or ""
    if not text:
        return

    match = TIKTOK_RE.search(text)
    if not match:
        return

    url = match.group(0)
    chat_id = update.effective_chat.id
    logger.info(f"TikTok URL: {url}")
    await context.bot.send_message(chat_id=chat_id, text="Downloading...")

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            filepath = await asyncio.to_thread(download_tiktok, url, tmpdir)
            file_size = os.path.getsize(filepath)
            if file_size > 50 * 1024 * 1024:
                await context.bot.send_message(chat_id=chat_id, text="File too large (max 50MB)")
                return

            with open(filepath, 'rb') as f:
                await context.bot.send_video(chat_id=chat_id, video=f)

            logger.info("Video sent successfully")

        except Exception as e:
            logger.error(f"Error: {e}")
            await context.bot.send_message(chat_id=chat_id, text="Failed to download video")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Error:", exc_info=context.error)

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, handle_message))
    application.add_error_handler(error_handler)
    logger.info("Bot started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
