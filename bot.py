import os, re, html
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
DEST_CHANNEL = os.environ["DEST_CHANNEL"]
FEED_URL = os.environ["FEED_URL"]
FOLLOW_LINE = os.environ.get("FOLLOW_LINE", "📢 Follow @topgkguru")
LAST_FILE = "last.txt"

URL_RE = re.compile(r"""(?ix)
\b(
  https?://\S+ |
  www\.\S+ |
  t\.me/\S+ |
  telegram\.me/\S+
)\b
""")

def tg_photo_upload(photo_bytes: bytes, caption: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {"photo": ("image.jpg", photo_bytes)}
    data = {"chat_id": DEST_CHANNEL, "caption": caption}
    r = requests.post(url, data=data, files=files, timeout=120)
    r.raise_for_status()

def tg_send_text(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": DEST_CHANNEL,
        "text": text[:3900],
        "disable_web_page_preview": True
    }, timeout=60)
    r.raise_for_status()

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
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def remove_links(s: str) -> str:
    # remove urls
    s = URL_RE.sub("", s)
    # remove leftover parentheses/brackets around removed links
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"\[\s*\]", "", s)
    # clean spaces
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def normalize_for_compare(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
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
    desc_html = html.unescape(desc_raw)

    # Try to extract image URL
    img = None
    m_href = re.search(r'<a[^>]+href="([^"]+\.(?:jpg|jpeg|png|webp))"', desc_html, flags=re.I)
    if m_href:
        img = m_href.group(1)
    else:
        m_img = re.search(r'<img[^>]+src="([^"]+)"', desc_html, flags=re.I)
        if m_img:
            img = m_img.group(1)

    title = strip_tags(title_raw)
    desc = strip_tags(desc_html)

    # remove "[Photo]" noise
    desc = re.sub(r"^\[Photo\]\s*", "", desc).strip()

    # Remove links from both
    title = remove_links(title)
    desc = remove_links(desc)

    # ✅ DEDUPE: if desc starts with title (or equal), keep only desc OR only title
    t_norm = normalize_for_compare(title)
    d_norm = normalize_for_compare(desc)

    if t_norm and d_norm:
        if d_norm == t_norm:
            # same text in both
            combined = desc
        elif d_norm.startswith(t_norm):
            # desc already contains title at start -> don't repeat
            combined = desc
        elif t_norm.startswith(d_norm):
            # title contains desc -> use title
            combined = title
        else:
            combined = f"{title}\n\n{desc}"
    else:
        combined = title or desc

    # Final cleanup
    combined = re.sub(r"\n{3,}", "\n\n", combined).strip()

    return {"guid": guid, "text": combined, "img": img}

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

    caption_or_text = f"{item['text']}\n\n━━━━━━━━━━━━━━\n{FOLLOW_LINE}".strip()
    caption_or_text = re.sub(r"\n{3,}", "\n\n", caption_or_text).strip()

    if item["img"]:
        # download & upload image (so image shows properly)
        img_resp = requests.get(item["img"], timeout=120)
        img_resp.raise_for_status()
        # Telegram caption limit ~1024
        cap = caption_or_text[:900]
        tg_photo_upload(img_resp.content, cap)
    else:
        tg_send_text(caption_or_text)

    write_last(item["guid"])
    print("Posted:", item["guid"])

if __name__ == "__main__":
    main()
