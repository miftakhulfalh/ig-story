import os
import json
import instaloader
import requests
from io import BytesIO
from flask import Flask, request

app = Flask(__name__)

# Environment Variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
IG_USERNAME = os.getenv('IG_USERNAME')  # optional
IG_PASSWORD = os.getenv('IG_PASSWORD')  # optional
IG_SESSIONID = os.getenv('IG_SESSIONID')

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Helper Functions
def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
        'chat_id': chat_id,
        'text': text
    })

def send_photo(chat_id, photo):
    requests.post(f"{TELEGRAM_API_URL}/sendPhoto", files={'photo': photo}, data={'chat_id': chat_id})

def send_video(chat_id, video):
    requests.post(f"{TELEGRAM_API_URL}/sendVideo", files={'video': video}, data={'chat_id': chat_id})

def setup_instaloader():
    L = instaloader.Instaloader(
        download_videos=True,
        save_metadata=False,
        download_video_thumbnails=False,
        dirname_pattern=''
    )

def setup_instaloader():
    L = instaloader.Instaloader(
        download_videos=True,
        save_metadata=False,
        download_video_thumbnails=False,
        dirname_pattern=''
    )

    if IG_SESSIONID:
        # Sertakan semua cookie yang diperlukan
        cookies = {
            'sessionid': IG_SESSIONID,
            'ds_user_id': os.getenv('IG_DS_USER_ID'),
            'csrftoken': os.getenv('IG_CSRFTOKEN')
        }
        for name, value in cookies.items():
            if value:
                L.context._session.cookies.set(
                    name, value, domain=".instagram.com", path="/"
                )
        # Validasi dengan profil sendiri (misalnya)
        try:
            profile = instaloader.Profile.from_username(L.context, "ker_anii")
            print("[INFO] SessionID valid, logged in.")
            return L
        except Exception as e:
            print(f"[WARN] Session invalid: {e}")
            L.context._session.cookies.clear()
            # Lanjut ke login username/password jika ada
    # ... (sisanya tetap)

    # If no sessionid or invalid, try login
    if IG_USERNAME and IG_PASSWORD:
        try:
            L.login(IG_USERNAME, IG_PASSWORD)
            print("[INFO] Logged in with username+password")
        except Exception as e:
            raise Exception(f"Login gagal: {e}")
    else:
        raise Exception("No valid sessionid or login credentials available.")

    return L

# Webhook endpoint
@app.route('/api/bot', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return 'Bot is running', 200
    elif request.method == 'POST':
        data = request.get_json()

        if not data or 'message' not in data:
            return 'No message found', 200

        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')

        if text.startswith('/story'):
            args = text.split(maxsplit=1)
            if len(args) < 2 or not args[1].strip():
                send_message(chat_id, 'Usage: /story <username>')
                return 'OK', 200

            username = args[1].strip()

            try:
                send_message(chat_id, f'Mengambil story {username}...')

                # Setup Instaloader
                L = setup_instaloader()

                # Fetch profile
                profile = instaloader.Profile.from_username(L.context, username)
                found = False

                for story in L.get_stories(userids=[profile.userid]):
                    for item in story.get_items():
                        url = item.video_url if item.is_video else item.url
                        resp = requests.get(url)
                        bio = BytesIO(resp.content)
                        bio.name = 'story.mp4' if item.is_video else 'story.jpg'

                        if item.is_video:
                            send_video(chat_id, bio)
                        else:
                            send_photo(chat_id, bio)

                        found = True

                if not found:
                    send_message(chat_id, 'User has no active stories.')

            except Exception as e:
                send_message(chat_id, f'Error: {e}')

        return 'OK', 200

if __name__ == '__main__':
    app.run()
