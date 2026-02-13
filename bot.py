import requests
import time

BOT_TOKEN = "8262192667:AAF2DL3Oj_x5YdY1xETCEfMLnFN-cecIpoE"
DEST_CHANNEL = "@topgkguru"
SOURCE = "https://t.me/s/testSourcechannelA"

last_post = None

def get_latest_post():
    r = requests.get(SOURCE)
    posts = r.text.split('tgme_widget_message_wrap')
    if len(posts) > 1:
        return posts[1]
    return None

while True:
    post = get_latest_post()
    if post and post != last_post:
        message = "🔥 New Update\n\nNew post available!\n\n📢 Follow @topgkguru"
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": DEST_CHANNEL, "text": message})
        last_post = post
    time.sleep(300)
