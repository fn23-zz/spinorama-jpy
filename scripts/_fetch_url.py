#!/usr/bin/env python3
"""Single URL fetch with charset detection; prints title + body size + marker hits.

Usage: python3 scripts/_fetch_url.py <url> [cachekey]
"""
import re
import sys

sys.path.insert(0, "/home/nari/scripts/spinorama_JPY/scripts")
from _market_probe import fetch, strip  # noqa: E402

url = sys.argv[1]
key = sys.argv[2] if len(sys.argv) > 2 else re.sub(r"\W+", "_", url)[:80]
html = fetch(url, key, force=True)
print("KEY", key, "LEN", len(html))
print("HEAD", html[:200].replace("\n", " "))
for pat in [r"<title>(.*?)</title>", r"Emotiva", r"Airmotiv", r"XB2", r"取扱", r"在庫"]:
    hits = re.findall(pat, html, re.S)[:5]
    hits = [strip(h)[:100] if "<" in str(h) else str(h)[:100] for h in hits]
    print(repr(pat), "->", hits)
