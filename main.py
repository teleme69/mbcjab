import os
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from googleapiclient.discovery import build
from io import BytesIO

# Get YouTube API key and Bot token from environment variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8443))

if not YOUTUBE_API_KEY or not BOT_TOKEN:
    raise EnvironmentError("Error: API keys or Bot token not found in environment variables.")

# Function to get YouTube video details using YouTube Data API v3
def get_video_details(video_url: str) -> dict:
    video_id = video_url.split("v=")[-1]  # Extract video ID from URL
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    request = youtube.videos().list(
        part="snippet",
        id=video_id
    )
    response = request.execute()

    if 'items' in response and len(response['items']) > 0:
        video = response['items'][0]
        video_title = video['snippet']['title']
        return {"url": video_url, "title": video_title}
    else:
        return None

# Function to search YouTube using YouTube Data API
def search_youtube(query: str) -> dict:
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    # Perform the search
    request = youtube.search().list(
        q=query,
        part="id,snippet",
        maxResults=1,  # Get the first search result
    )
    response = request.execute()

    # Extract the video ID and title from the response
    if 'items' in response:
        video = response['items'][0]
        video_id = video['id']['videoId']
        video_title = video['snippet']['title']
        return {"url": f"https://www.youtube.com/watch?v={video_id}", "title": video_title}
    else:
        return None

# Function to download audio from YouTube link
async def download_audio(url: str, update: Update, video_title: str = None):
    try:
        await update.message.reply_text("Downloading the audio, please wait...")

        # Default to the video title if not provided
        if not video_title:
            video_title = "audio"

        # Use yt-dlp to download the audio and send it directly to Telegram
        command = [
            "yt-dlp",
            "-x",  # Extract audio
            "--audio-format", "mp3",  # Convert to MP3
            "-o", "-",  # Output to stdout
            url
        ]

        # Run yt-dlp and capture the audio in memory
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        audio_data, error = process.communicate()

        if process.returncode == 0 and audio_data:
            # Send the audio directly to the user
            audio_file = BytesIO(audio_data)
            audio_file.name = f"{video_title}.mp3"
            await update.message.reply_audio(audio_file)
        else:
            await update.message.reply_text("Failed to download the audio.")
    except Exception as e:
        print(f"Error while downloading audio: {e}")
        await update.message.reply_text("An error occurred while processing your request.")

# Function to handle /start command
async def start(update: Update, context):
    await update.message.reply_text("Hi! Send me a YouTube link or a search keyword, and I'll download the audio for you.")

# Function to handle user messages
async def handle_message(update: Update, context):
    url_or_keyword = update.message.text

    # If the message is a YouTube link
    if 'youtube.com' in url_or_keyword or 'youtu.be' in url_or_keyword:
        result = get_video_details(url_or_keyword)

        if result:
            video_url = result["url"]
            video_title = result["title"]
            await download_audio(video_url, update, video_title)
        else:
            await update.message.reply_text("Failed to retrieve video details. Please check the link.")
    else:
        # Otherwise, treat it as a search keyword
        result = search_youtube(url_or_keyword)

        if result:
            video_url = result["url"]
            video_title = result["title"]
            await download_audio(video_url, update, video_title)
        else:
            await update.message.reply_text("No results found. Please try with different keywords.")

# Main function to set up the bot
def main():
    # Initialize the application with the bot token
    app = Application.builder().token(BOT_TOKEN).build()

    # Add command and message handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Set up the webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"https://mbcjab.onrender.com/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
