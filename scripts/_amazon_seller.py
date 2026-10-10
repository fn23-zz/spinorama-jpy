#!/usr/bin/env python3
"""Fetch Amazon product pages and print the seller (sellerProfileTriggerId) + title.

Usage: python3 scripts/_amazon_seller.py ASIN1 ASIN2 ...
"""
import re
import sys
import time

sys.path.insert(0, "/home/nari/scripts/spinorama_JPY/scripts")
import _amazon_fetch as af  # noqa: E402


def strip(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


for asin in sys.argv[1:]:
    url = "https://www.amazon.co.jp/dp/%s" % asin
    html = af.get(url)
    if 'data-component-type="s-search-result"' in html or len(html) < 5000:
        if af.solve(html, url):
            time.sleep(3)
            html = af.get(url)
    print("==", asin, "len", len(html))
    t = re.search(r"<title>(.*?)</title>", html, re.S)
    print("   title:", strip(t.group(1))[:120] if t else None)
    for pat in [r"id=['\"]sellerProfileTriggerId['\"][^>]*>(.*?)<",
                r'"merchantName"\s*:\s*"([^"]+)"',
                r"Ships from</span>.*?<span[^>]*>(.*?)</span>",
                r"Sold by</span>.*?<span[^>]*>(.*?)</span>",
                r"この商品は(.{0,60}?)が出品",
                r"a-price-whole\">([\d,]+)"]:
        hits = [strip(x)[:80] for x in re.findall(pat, html, re.S)[:3]]
        if hits:
            print("   ", pat[:30], "->", hits)
    time.sleep(4)
