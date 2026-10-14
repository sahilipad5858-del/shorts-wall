"""Daily refresh of the baked-in Shorts pool in index.html (no API key).

Fetches the channel's public /shorts + /videos pages, extracts video IDs,
merges them newest-first with the existing pool (cap 60), and patches
index.html in place. Never empties the pool: if fetching fails or yields
too few IDs, the file is left untouched.
"""
import re
import sys
import urllib.request
from pathlib import Path

CHANNEL_HANDLE = "blvcktorque"
CHANNEL_ID = "UCc3WaSgyMJ4q1orDuTla1BA"
MAX_POOL = 60
MIN_IDS = 5
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def main():
    ids = []
    for tab in ("shorts", "videos"):
        url = f"https://www.youtube.com/@{CHANNEL_HANDLE}/{tab}"
        try:
            html = fetch(url)
        except Exception as e:  # network blocked: keep existing pool
            print(f"warn: {tab} fetch failed: {e}")
            continue
        found = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
        shorts = re.findall(r"/shorts/([A-Za-z0-9_-]{11})", html)
        for v in found + shorts:
            if v not in ids:
                ids.append(v)
        print(f"{tab}: {len(found)} videoIds, {len(shorts)} shorts links")

    print(f"total unique found: {len(ids)}")
    if len(ids) < MIN_IDS:
        print("too few IDs (likely blocked) — keeping existing pool")
        return 0

    p = Path("index.html")
    txt = p.read_text(encoding="utf-8")
    m = re.search(r'"' + CHANNEL_ID + r'": \[(.*?)\]', txt, re.S)
    if not m:
        print("pool pattern not found in index.html")
        return 1
    old = re.findall(r'"([A-Za-z0-9_-]{11})"', m.group(1))
    merged = ids + [v for v in old if v not in ids]
    merged = merged[:MAX_POOL]
    new_block = '"' + CHANNEL_ID + '": [' + ",".join(f'"{v}"' for v in merged) + "]"
    new_txt = txt[: m.start()] + new_block + txt[m.end():]
    if new_txt != txt:
        p.write_text(new_txt, encoding="utf-8")
        print(f"pool updated: {len(old)} -> {len(merged)}")
    else:
        print("pool unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
