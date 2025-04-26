import os
import json
import instaloader
import requests
import telebot
from telebot.types import Update
from io import BytesIO

# Initialize TeleBot with your Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['story'])
def send_story(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        bot.reply_to(message, 'Usage: /story <username>')
        return

    username = args[1].strip()
    chat_id = message.chat.id

    try:
        # Instantiate Instaloader for stories only
        L = instaloader.Instaloader(
            download_stories_only=True,
            download_videos=True,
            save_metadata=False,
            download_video_thumbnails=False,
            dirname_pattern=''
        )
        # Optional login for private stories
        # L.login('your_username', 'your_password')

        profile = instaloader.Profile.from_username(L.context, username)
        found = False

        for story in L.get_stories(userids=[profile.userid]):
            for item in story.get_items():
                url = item.video_url if item.is_video else item.url
                resp = requests.get(url)
                bio = BytesIO(resp.content)
                bio.name = 'story.mp4' if item.is_video else 'story.jpg'

                if item.is_video:
                    bot.send_video(chat_id, bio)
                else:
                    bot.send_photo(chat_id, bio)

                found = True

        if not found:
            bot.send_message(chat_id, 'User has no active stories.')

    except Exception as e:
        bot.send_message(chat_id, f'Error: {e}')

# Vercel-compatible serverless handler
def handler(event, context):
    # Parse incoming webhook body
    try:
        body = json.loads(event.get('body', '{}') or '{}')
    except Exception:
        body = {}

    # Process Telegram update if present
if 'message' in body:
    update = Update.de_json(body, bot)
    bot.process_new_updates([update])

    # Return HTTP 200 to acknowledge
    return { 'statusCode': 200, 'body': 'OK' }
