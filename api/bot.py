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

    # Perbaiki urutan: Update headers SETELAH L didefinisikan
    L.context._session.headers.update({
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 200.0.0.28.107 (iPhone13,2; iOS 15_0; en_US; en-US; scale=3.00; 1170x2532; 190542886)",
        "X-IG-App-ID": "1217981644879628"  # <-- Penting untuk API
    })

    # Cookie yang diperlukan
    cookies = {
        'sessionid': IG_SESSIONID,
        'ds_user_id': os.getenv('IG_DS_USER_ID'),
        'csrftoken': os.getenv('IG_CSRFTOKEN'),
        'rur': os.getenv('IG_RUR'),
        'mid': os.getenv('IG_MID'),  # <-- Tambahkan ini
        'ig_did': os.getenv('IG_DID')  # <-- Tambahkan ini
    }

    if all(cookies.values()):
        for name, value in cookies.items():
            L.context._session.cookies.set(
                name, value, domain=".instagram.com", path="/"
            )
        # Di setup_instaloader()
        try:
            # Coba akses story sendiri
            profile = instaloader.Profile.from_username(L.context, "ker_anii")
            stories = L.get_stories(userids=[profile.userid])
            if not stories:
                raise Exception("Validasi session gagal: Tidak bisa akses story")
            print(f"[INFO] Session valid untuk story (Username: {profile.username})")
            return L
        except Exception as e:
            print(f"[ERROR] Validasi story gagal: {e}")

    # Jika session gagal, coba login
    if IG_USERNAME and IG_PASSWORD:
        try:
            L.login(IG_USERNAME, IG_PASSWORD)
            print("[INFO] Logged in via username/password")
            return L  # Return setelah login berhasil
        except Exception as e:
            raise Exception(f"Login failed: {e}")
    else:
        raise Exception("No valid session or credentials.")
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
                send_message(chat_id, f'Mengambil story dari {username}...')

                # Setup Instaloader
                L = setup_instaloader()

                # Fetch profile
                profile = instaloader.Profile.from_username(L.context, username)
                found = False

                # Di dalam handler /story
                for story in L.get_stories(userids=[profile.userid]):
                    for item in story.get_items():
                        # Gunakan instaloader untuk download, bukan requests.get
                        L.download_storyitem(item, filename='story')
                        
                        # Baca file yang baru didownload
                        filename = f"story/{item.date_utc.strftime('%Y%m%d_%H%M%S')}"
                        if item.is_video:
                            filename += ".mp4"
                            with open(filename, 'rb') as f:
                                send_video(chat_id, f)
                        else:
                            filename += ".jpg"
                            with open(filename, 'rb') as f:
                                send_photo(chat_id, f)
                        
                        os.remove(filename)  # Hapus file setelah dikirim
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
