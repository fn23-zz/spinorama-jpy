#!/usr/bin/env python3
"""Dump every data-asin block from a cached Amazon search page.

Usage: python3 scripts/_amazon_all.py <cached_html>
"""
import re
import sys

path = sys.argv[1]
html = open(path, encoding="utf-8", errors="replace").read()
print("len", len(html))
m = re.search(r"([\d,]+)\s*件の結果", html)
print("result_count:", m.group(1) if m else None)
seen = {}
for mm in re.finditer(r'data-asin="([A-Z0-9]{10})"', html):
    asin = mm.group(1)
    body = html[mm.start():mm.start() + 6000]
    t = re.search(r"<h2[^>]*>(.*?)</h2>", body, re.S)
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t.group(1))).strip() if t else ""
    if not title:
        t2 = re.search(r'<span class="a-size-base-plus a-color-base a-text-normal">(.*?)</span>', body, re.S)
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t2.group(1))).strip() if t2 else ""
    p1 = re.search(r'a-price-whole">([\d,]+)', body)
    p2 = re.search(r'<span class="a-offscreen">￥([\d,]+)', body)
    price = (p1.group(1) if p1 else (p2.group(1) if p2 else None))
    if asin in seen:
        continue
    seen[asin] = (title[:90], price)
for asin, (title, price) in seen.items():
    print(asin, "|", price, "|", title)
