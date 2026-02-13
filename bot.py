import os
import re
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
DEST_CHANNEL = os.environ["DEST_CHANNEL"]   # @topgkguru
FEED_URL = os.environ["FEED_URL"]           # https://tg.i-c-a.su/rss/testSourcechannelA

FOLLOW_LINE = os.environ.get("FOLLOW_LINE", "📢 Follow @topgkguru")
LAST_FILE = "last.txt"

def tg(method: str, payload: dict):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def read_last():
    if os.path.exists(LAST_FILE):
        return open(LAST_FILE, "r", encoding="utf-8").read().strip()
    return ""

def write_last(val: str):
    open(LAST_FILE, "w", encoding="utf-8").write(val)

def parse_first_item(xml: str):
    m_item = re.search(r"<item>(.*?)</item>", xml, flags=re.S)
    if not m_item:
        return None
    item = m_item.group(1)

    def pick(tag):
        m = re.search(rf"<{tag}>(.*?)</{tag}>", item, flags=re.S)
        return (m.group(1).strip() if m else "")

    title = re.sub(r"<!\[CDATA\[|\]\]>", "", pick("title")).strip()
    link = pick("link").strip()
    guid = pick("guid").strip() or link

    desc = re.sub(r"<!\[CDATA\[|\]\]>", "", pick("description"))
    desc = re.sub(r"<br\s*/?>", "\n", desc)
    desc = re.sub(r"<.*?>", "", desc).strip()

    return {"guid": guid, "title": title, "desc": desc}

def main():
    last = read_last()
    xml = requests.get(FEED_URL, timeout=30).text
    item = parse_first_item(xml)

    if not item:
        print("No items found")
        return
    if item["guid"] == last:
        print("No new post")
        return

    text = f"🔥 New Update\n\n{item['title']}\n\n{item['desc']}\n\n━━━━━━━━━━━━━━\n{FOLLOW_LINE}"
    tg("sendMessage", {
        "chat_id": DEST_CHANNEL,
        "text": text[:3900],
        "disable_web_page_preview": True
    })

    write_last(item["guid"])
    print("Posted:", item["guid"])

if __name__ == "__main__":
    main()
