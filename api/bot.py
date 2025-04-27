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
    L.context._session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
})
    L = instaloader.Instaloader(
        download_videos=True,
        save_metadata=False,
        download_video_thumbnails=False,
        dirname_pattern=''
    )

    # Cookie yang diperlukan
    cookies = {
        'sessionid': IG_SESSIONID,
        'ds_user_id': os.getenv('IG_DS_USER_ID'),
        'csrftoken': os.getenv('IG_CSRFTOKEN'),
        'rur': os.getenv('IG_RUR')  # Cookie tambahan
    }

    if all(cookies.values()):
        for name, value in cookies.items():
            L.context._session.cookies.set(
                name, value, domain=".instagram.com", path="/"
            )
        # Validasi dengan profil private
        try:
            profile = instaloader.Profile.from_username(L.context, "your_private_username")
            print(f"[INFO] Session valid (Username: {profile.username})")
            return L
        except Exception as e:
            print(f"[ERROR] Session invalid: {e}")
            L.context._session.cookies.clear()  # Hapus cookie yang gagal
    else:
        print("[WARN] Missing cookies. Falling back to username/password.")

    # Jika session gagal, coba login dengan username/password
    if IG_USERNAME and IG_PASSWORD:
        try:
            L.login(IG_USERNAME, IG_PASSWORD)
            print("[INFO] Logged in via username/password")
        except Exception as e:
            raise Exception(f"Login failed: {e}")
    else:
        raise Exception("No valid session or credentials.")

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

            except instaloader.exceptions.LoginRequiredException:
                send_message(chat_id, "Error: Session expired. Update cookies.")
            except instaloader.exceptions.PrivateProfileNotFollowedException:
                send_message(chat_id, "Error: Profile is private and not followed.")
            except Exception as e:
                send_message(chat_id, f'Error: {e}')

        return 'OK', 200

if __name__ == '__main__':
    app.run()
