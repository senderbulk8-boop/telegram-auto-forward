import os, re, html
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
DEST_CHANNEL = os.environ["DEST_CHANNEL"]
FEED_URL = os.environ["FEED_URL"]
FOLLOW_LINE = os.environ.get("FOLLOW_LINE", "📢 Follow @topgkguru")
LAST_FILE = "last.txt"

def tg_json(method: str, payload: dict):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def tg_photo_upload(photo_bytes: bytes, caption: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {"photo": ("image.jpg", photo_bytes)}
    data = {"chat_id": DEST_CHANNEL, "caption": caption}
    r = requests.post(url, data=data, files=files, timeout=120)
    r.raise_for_status()
    return r.json()

def read_last():
    if os.path.exists(LAST_FILE):
        return open(LAST_FILE, "r", encoding="utf-8").read().strip()
    return ""

def write_last(val: str):
    open(LAST_FILE, "w", encoding="utf-8").write(val)

def strip_tags(s: str) -> str:
    s = html.unescape(s)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<.*?>", "", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s

def parse_first_item(xml: str):
    m_item = re.search(r"<item>(.*?)</item>", xml, flags=re.S)
    if not m_item:
        return None
    item = m_item.group(1)

    def pick(tag):
        m = re.search(rf"<{tag}>(.*?)</{tag}>", item, flags=re.S)
        return (m.group(1).strip() if m else "")

    title_raw = re.sub(r"<!\[CDATA\[|\]\]>", "", pick("title"))
    link = pick("link").strip()
    guid = (pick("guid").strip() or link)

    desc_raw = re.sub(r"<!\[CDATA\[|\]\]>", "", pick("description"))

    # IMPORTANT: decode HTML entities first (because your feed contains &lt;img ...&gt;)
    desc_html = html.unescape(desc_raw)

    # Prefer full image from <a href="...jpg/png">
    img = None
    m_href = re.search(r'<a[^>]+href="([^"]+\.(?:jpg|jpeg|png|webp))"', desc_html, flags=re.I)
    if m_href:
        img = m_href.group(1)
    else:
        # fallback: <img src="...">
        m_img = re.search(r'<img[^>]+src="([^"]+)"', desc_html, flags=re.I)
        if m_img:
            img = m_img.group(1)

    title = strip_tags(title_raw)
    desc = strip_tags(desc_html)

    # remove useless “[Photo]” text if present
    desc = re.sub(r"^\[Photo\]\s*", "", desc).strip()

    return {"guid": guid, "title": title, "desc": desc, "img": img}

def main():
    last = read_last()
    xml = requests.get(FEED_URL, timeout=60).text
    item = parse_first_item(xml)

    if not item:
        print("No items found")
        return
    if item["guid"] == last:
        print("No new post")
        return

    caption = f"🔥 New Update\n\n{item['title']}\n\n{item['desc']}\n\n━━━━━━━━━━━━━━\n{FOLLOW_LINE}"
    caption = caption[:900]  # safe for photo caption

    if item["img"]:
        # download image and upload to Telegram
        img_resp = requests.get(item["img"], timeout=120)
        img_resp.raise_for_status()
        tg_photo_upload(img_resp.content, caption)
    else:
        # text only
        tg_json("sendMessage", {
            "chat_id": DEST_CHANNEL,
            "text": caption[:3900],
            "disable_web_page_preview": True
        })

    write_last(item["guid"])
    print("Posted:", item["guid"])

if __name__ == "__main__":
    main()
