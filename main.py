import os
import subprocess
from io import BytesIO
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from googleapiclient.discovery import build
from keep_alive import keep_alive  # Import the keep_alive function

# Get YouTube API key and Telegram Bot token from environment variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not YOUTUBE_API_KEY or not BOT_TOKEN:
    print("Error: API keys or Bot token not found in environment variables.")
    exit()

# Thread pool for handling concurrent requests
executor = ThreadPoolExecutor(max_workers=5)

# Function to get YouTube video details using YouTube Data API v3
def get_video_details(video_url: str) -> dict:
    video_id = video_url.split("v=")[-1]  # Extract video ID from URL
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    request = youtube.videos().list(part="snippet", id=video_id)
    response = request.execute()

    if 'items' in response and len(response['items']) > 0:
        video = response['items'][0]
        video_title = video['snippet']['title']
        return {"url": video_url, "title": video_title}
    return None

# Function to search YouTube using YouTube Data API
def search_youtube(query: str) -> dict:
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    request = youtube.search().list(q=query, part="id,snippet", maxResults=1)
    response = request.execute()

    if 'items' in response:
        video = response['items'][0]
        video_id = video['id']['videoId']
        video_title = video['snippet']['title']
        return {"url": f"https://www.youtube.com/watch?v={video_id}", "title": video_title}
    return None

# Function to download audio from YouTube link
async def download_audio(url: str, update: Update, video_title: str = None) -> None:
    try:
        await update.message.reply_text("Downloading the audio, please wait...")
        if not video_title:
            video_title = "audio"

        # Use yt-dlp to download the audio and send it directly to Telegram
        command = [
            "yt-dlp",
            "-x",
            "--audio-format", "mp3",
            "-o", "-",  # Output to stdout
            url
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        audio_data, error = process.communicate()

        if process.returncode == 0 and audio_data:
            audio_file = BytesIO(audio_data)
            audio_file.name = f"{video_title}.mp3"
            await update.message.reply_audio(audio_file)
        else:
            await update.message.reply_text("Failed to download the audio.")
    except Exception as e:
        print(f"Error while downloading audio: {e}")
        await update.message.reply_text("An error occurred while processing your request.")

# Function to handle /start command
async def start(update: Update, context) -> None:
    await update.message.reply_text("Hi! Send me a YouTube link or a search keyword, and I'll download the audio for you.")

# Function to handle user messages
async def handle_message(update: Update, context) -> None:
    url_or_keyword = update.message.text

    async def process_request():
        if 'youtube.com' in url_or_keyword or 'youtu.be' in url_or_keyword:
            result = get_video_details(url_or_keyword)
            if result:
                await download_audio(result["url"], update, result["title"])
            else:
                await update.message.reply_text("Invalid YouTube link.")
        else:
            result = search_youtube(url_or_keyword)
            if result:
                await download_audio(result["url"], update, result["title"])
            else:
                await update.message.reply_text("No results found for your query.")

    # Handle the request in a new thread
    Thread(target=lambda: context.application.create_task(process_request())).start()

# Main function to start the bot
def main() -> None:
    if not BOT_TOKEN:
        print("Error: Bot token not found in environment variables.")
        return

    # Keep the bot alive
    keep_alive()

    # Initialize the application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
