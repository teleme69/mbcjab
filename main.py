import os
import subprocess
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from googleapiclient.discovery import build
from io import BytesIO
from keep_alive import keep_alive  # Import the keep_alive function
from concurrent.futures import ThreadPoolExecutor  # For managing threads

# Get YouTube API key from Replit secrets
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
# Get Telegram Bot token from Replit secrets
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not YOUTUBE_API_KEY or not BOT_TOKEN:
    print("Error: API keys or Bot token not found in Replit secrets.")
    exit()

# Thread pool for handling concurrent requests
executor = ThreadPoolExecutor(max_workers=5)  # Allows up to 5 concurrent threads

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

# Function to start the bot
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Hi! Send me a YouTube link or a search keyword, and I'll download the audio for you.")

# Function to handle messages and download audio
def handle_message(update: Update, context: CallbackContext) -> None:
    url_or_keyword = update.message.text

    # Process requests concurrently using ThreadPoolExecutor
    executor.submit(process_request, update, url_or_keyword)

def process_request(update: Update, url_or_keyword: str) -> None:
    # If the message is a YouTube link
    if 'youtube.com' in url_or_keyword or 'youtu.be' in url_or_keyword:
        result = get_video_details(url_or_keyword)

        if result:
            video_url = result["url"]
            video_title = result["title"]
            download_audio(video_url, update, video_title)
    else:
        # Otherwise, treat it as a search keyword
        result = search_youtube(url_or_keyword)

        if result:
            video_url = result["url"]
            video_title = result["title"]
            download_audio(video_url, update, video_title)

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
def download_audio(url: str, update: Update, video_title: str = None) -> None:
    try:
        update.message.reply_text("Downloading the audio, please wait...")

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
            update.message.reply_audio(audio_file)
    except Exception as e:
        # In case of any error, log it (no need to send message)
        print(f"Error while downloading audio: {e}")

# Main function to set up the bot
def main() -> None:
    if not BOT_TOKEN:
        print("Error: Bot token not found in Replit secrets.")
        return

    # Keep the bot alive
    keep_alive()  # Start the keep-alive server

    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Command and message handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
