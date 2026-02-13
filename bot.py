import os
import re
import html
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
DEST_CHANNEL = os.environ["DEST_CHANNEL"]
FEED_URL = os.environ["FEED_URL"]
FOLLOW_LINE = "📢 Follow @topgkguru"
LAST_FILE = "last.txt"

def tg(method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    r = requests.post(url, json=payload)
    r.raise_for_status()

def read_last():
    if os.path.exists(LAST_FILE):
        return open(LAST_FILE).read().strip()
    return ""

def write_last(val):
    open(LAST_FILE, "w").write(val)

def clean_html(text):
    text = html.unescape(text)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<.*?>", "", text)
    return text.strip()

def get_latest():
    xml = requests.get(FEED_URL).text
    item = re.search(r"<item>(.*?)</item>", xml, re.S)
    if not item:
        return None
    item = item.group(1)

    def get(tag):
        m = re.search(f"<{tag}>(.*?)</{tag}>", item, re.S)
        return m.group(1).strip() if m else ""

    title = clean_html(get("title"))
    desc_raw = get("description")
    guid = get("guid") or get("link")

    img_match = re.search(r'<img[^>]+src="([^"]+)"', desc_raw)
    img = img_match.group(1) if img_match else None

    desc = clean_html(desc_raw)

    return {
        "guid": guid,
        "title": title,
        "desc": desc,
        "img": img
    }

def main():
    last = read_last()
    post = get_latest()

    if not post:
        print("No post found")
        return

    if post["guid"] == last:
        print("No new post")
        return

    caption = f"🔥 New Update\n\n{post['title']}\n\n{post['desc']}\n\n━━━━━━━━━━━━━━\n{FOLLOW_LINE}"
    caption = caption[:1000]

    if post["img"]:
        tg("sendPhoto", {
            "chat_id": DEST_CHANNEL,
            "photo": post["img"],
            "caption": caption
        })
    else:
        tg("sendMessage", {
            "chat_id": DEST_CHANNEL,
            "text": caption,
            "disable_web_page_preview": False
        })

    write_last(post["guid"])
    print("Posted successfully")

if __name__ == "__main__":
    main()
