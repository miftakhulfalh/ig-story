import os
import json
import instaloader
import requests
import telebot
from io import BytesIO

# Initialize TeleBot
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

# Handler for Telegram webhook
@bot.message_handler(commands=['story'])
def send_story(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        bot.reply_to(message, 'Usage: /story <username>')
        return

    username = args[1].strip()
    chat_id = message.chat.id

    try:
        # Initialize Instaloader (in-memory mode)
        L = instaloader.Instaloader(
            download_stories_only=True,
            download_videos=True,
            save_metadata=False,
            download_video_thumbnails=False,
            dirname_pattern=''
        )
        # (Optional) login if you need private stories
        # L.login('your_instagram_username', 'your_instagram_password')

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

# Vercel serverless handler
def handler(event, context):
    body = json.loads(event.get('body', '{}'))
    if 'message' in body:
        bot.process_new_updates([body])
    return {'statusCode': 200, 'body': 'OK'}
