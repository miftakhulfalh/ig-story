import os
import json
import instaloader
import requests
from io import BytesIO
from telegram import Bot

# Set your Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')  # Pastikan di Vercel Environment Variables
bot = Bot(token=BOT_TOKEN)

def handler(event, context):
    body = json.loads(event["body"])

    # Handle Telegram webhook
    if "message" in body:
        chat_id = body["message"]["chat"]["id"]
        text = body["message"].get("text", "")

        if text.startswith("/story"):
            username = text.split(maxsplit=1)[1] if len(text.split()) > 1 else None

            if not username:
                bot.send_message(chat_id=chat_id, text="Kirim /story username")
                return {"statusCode": 200}

            # Download story
            try:
                L = instaloader.Instaloader(download_stories_only=True, download_videos=True, save_metadata=False, download_video_thumbnails=False)

                # (Optional) login supaya bisa ambil story private (jika perlu)
                # L.login('your_username', 'your_password')

                profile = instaloader.Profile.from_username(L.context, username)

                found = False

                for story in L.get_stories(userids=[profile.userid]):
                    for item in story.get_items():
                        # Download media ke memory
                        url = item.video_url if item.is_video else item.url
                        response = requests.get(url)
                        file_bytes = BytesIO(response.content)
                        file_bytes.name = "story.mp4" if item.is_video else "story.jpg"

                        if item.is_video:
                            bot.send_video(chat_id=chat_id, video=file_bytes)
                        else:
                            bot.send_photo(chat_id=chat_id, photo=file_bytes)

                        found = True

                if not found:
                    bot.send_message(chat_id=chat_id, text="Tidak ada story aktif.")

            except Exception as e:
                bot.send_message(chat_id=chat_id, text=f"Error: {str(e)}")

    return {"statusCode": 200, "body": "ok"}
