import os, re, html
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
DEST_CHANNEL = os.environ["DEST_CHANNEL"]
FEED_URL = os.environ["FEED_URL"]
FOLLOW_LINE = os.environ.get("FOLLOW_LINE", "📢 Follow @topgkguru")
LAST_FILE = "last.txt"

# remove any kinds of links
URL_RE = re.compile(r"""(?ix)
\b(
  https?://\S+ |
  www\.\S+ |
  t\.me/\S+ |
  telegram\.me/\S+
)\b
""")

# detect truncated endings like "[...]" or "..." or "…"
TRUNC_END_RE = re.compile(r"""(?ix)
(\s*\[\s*\.\.\.\s*\]\s*$) |
(\s*\[\s*…\s*\]\s*$) |
(\s*…\s*$) |
(\s*\.\.\.\s*$)
""")

def tg_send_text(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": DEST_CHANNEL,
        "text": text[:3900],
        "disable_web_page_preview": True
    }, timeout=60)
    r.raise_for_status()

def tg_send_photo_bytes(photo_bytes: bytes, caption: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {"photo": ("image.jpg", photo_bytes)}
    data = {"chat_id": DEST_CHANNEL, "caption": caption[:900]}
    r = requests.post(url, data=data, files=files, timeout=120)
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
    s = URL_RE.sub("", s)
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"\[\s*\]", "", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def normalize(s: str) -> str:
    s = TRUNC_END_RE.sub("", s).strip()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def remove_prefixes(s: str) -> str:
    # remove [Photo] / [Media] prefix if exists
    s = re.sub(r"^\[(?:Photo|Media)\]\s*", "", s, flags=re.I).strip()
    return s

def parse_first_item(xml: str):
    m_item = re.search(r"<item>(.*?)</item>", xml, flags=re.S)
    if not m_item:
        return None
    item = m_item.group(1)

    def pick(tag):
        m = re.search(rf"<{tag}>(.*?)</{tag}>", item, flags=re.S)
        return (m.group(1).strip() if m else "")

    # basic fields
    title_raw = re.sub(r"<!\[CDATA\[|\]\]>", "", pick("title"))
    desc_raw = re.sub(r"<!\[CDATA\[|\]\]>", "", pick("description"))
    link = pick("link").strip()
    guid = (pick("guid").strip() or link)

    # enclosure (best for photos)
    enc_url = None
    enc_type = None
    m_enc = re.search(r'enclosure[^>]+url="([^"]+)"[^>]+type="([^"]+)"', item, flags=re.I)
    if m_enc:
        enc_url = m_enc.group(1)
        enc_type = m_enc.group(2)

    title = remove_prefixes(strip_tags(title_raw))
    desc = strip_tags(desc_raw)

    # remove "[Photo]" text inside description too
    desc = re.sub(r"^\[Photo\]\s*", "", desc).strip()

    # remove links everywhere
    title = remove_links(title)
    desc = remove_links(desc)

    # --- DEDUPE FIX FOR YOUR FEED ---
    # If title is truncated (ends with [...]/.../…), DO NOT include it at all.
    title_is_truncated = bool(TRUNC_END_RE.search(title_raw)) or bool(TRUNC_END_RE.search(title))
    t_norm = normalize(title)
    d_norm = normalize(desc)

    if title_is_truncated:
        combined = desc
    else:
        # If description already starts with title, drop title
        # (your feed often repeats title inside description)
        # Compare first line too
        first_line = ""
        for ln in desc.splitlines():
            if ln.strip():
                first_line = ln.strip()
                break

        f_norm = normalize(first_line)
        if t_norm and f_norm and (f_norm == t_norm or f_norm.startswith(t_norm) or t_norm.startswith(f_norm)):
            combined = desc
        elif t_norm and d_norm and (d_norm == t_norm or d_norm.startswith(t_norm)):
            combined = desc
        else:
            combined = f"{title}\n\n{desc}".strip() if title and desc else (title or desc)

    combined = re.sub(r"\n{3,}", "\n\n", combined).strip()

    return {
        "guid": guid,
        "text": combined,
        "enclosure_url": enc_url,
        "enclosure_type": enc_type
    }

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

    out = f"{item['text']}\n\n━━━━━━━━━━━━━━\n{FOLLOW_LINE}".strip()
    out = re.sub(r"\n{3,}", "\n\n", out).strip()

    # If image enclosure exists, send as real photo
    if item["enclosure_url"] and item["enclosure_type"] and item["enclosure_type"].lower().startswith("image/"):
        img = requests.get(item["enclosure_url"], timeout=120)
        img.raise_for_status()
        tg_send_photo_bytes(img.content, out)
    else:
        tg_send_text(out)

    write_last(item["guid"])
    print("Posted:", item["guid"])

if __name__ == "__main__":
    main()
