#!/usr/bin/env python3
"""Amazon.co.jp search fetcher that solves the Akamai bm-verify interstitial.

Usage: python3 scripts/_amazon_fetch.py <input.json> [id ...]
input.json: [{"id": 597, "keyword": "Kanto YU6"}, ...]
Caches to /tmp/probe_cache/<id>_amazon.html
"""
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
CACHE = "/tmp/probe_cache"
os.makedirs(CACHE, exist_ok=True)

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def get(url, referer=None):
    h = {"User-Agent": UA, "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8",
         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    with opener.open(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def solve(html, base):
    m = re.search(r'var i\s*=\s*(\d+);\s*var j\s*=\s*i\s*\+\s*Number\("(\d+)"\s*\+\s*"(\d+)"\)', html)
    if not m:
        return False
    i, a, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
    j = i + int(a + b)
    tok = re.search(r"bm-verify=(AAQ[^'\"&]+)", html) or re.search(r'"bm-verify"\s*:\s*"([^"]+)"', html)
    if not tok:
        return False
    token = urllib.parse.unquote(tok.group(1))
    body = json.dumps({"bm-verify": token, "pow": j}).encode()
    req = urllib.request.Request(
        "https://www.amazon.co.jp/_sec/verify?provider=interstitial", data=body,
        headers={"User-Agent": UA, "Content-Type": "application/json",
                 "Accept": "*/*", "Origin": "https://www.amazon.co.jp",
                 "Referer": base, "X-Requested-With": "XMLHttpRequest"})
    try:
        with opener.open(req, timeout=30) as r:
            resp = r.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        print("   verify POST error:", repr(e))
        return False
    print("   verify resp:", resp[:200])
    return '"reload":true' in resp.replace(" ", "") or "location" in resp


def search(kw, cid, tries=3):
    url = "https://www.amazon.co.jp/s?k=" + urllib.parse.quote(kw)
    html = ""
    for attempt in range(tries):
        try:
            html = get(url)
        except Exception as e:  # noqa: BLE001
            print("   GET error:", repr(e))
            time.sleep(5)
            continue
        if 'data-component-type="s-search-result"' in html:
            return html, url
        print("   challenge on attempt %d (len=%d)" % (attempt + 1, len(html)))
        if solve(html, url):
            time.sleep(3)
            continue
        time.sleep(8)
    return html, url


def parse(html):
    out = []
    blocks = re.split(r'<div[^>]*data-asin="([A-Z0-9]{10})"', html)
    for k in range(1, len(blocks) - 1, 2):
        asin, body = blocks[k], blocks[k + 1]
        if "s-search-result" not in body[:600]:
            continue
        t = re.search(r"<h2[^>]*>(.*?)</h2>", body, re.S)
        pr = re.search(r'a-price-whole">([\d,]+)', body)
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t.group(1))).strip() if t else ""
        out.append({"asin": asin, "title": title[:95], "price": pr.group(1) if pr else None})
        if len(out) >= 12:
            break
    return out


def main():
    inp = json.load(open(sys.argv[1], encoding="utf-8"))
    wanted = set(sys.argv[2:])
    for c in inp:
        if wanted and str(c["id"]) not in wanted:
            continue
        cid = str(c["id"])
        print("=== ID %s | %s" % (cid, c["keyword"]))
        html, url = search(c["keyword"], cid)
        if 'data-component-type="s-search-result"' not in html:
            print("   STILL BLOCKED len=%d" % len(html))
            continue
        with open(os.path.join(CACHE, "%s_amazon.html" % cid), "w", encoding="utf-8") as f:
            f.write(html)
        items = parse(html)
        print("   ok len=%d items=%d" % (len(html), len(items)))
        for it in items:
            print("   -", json.dumps(it, ensure_ascii=False))
        sys.stdout.flush()
        time.sleep(6)


if __name__ == "__main__":
    main()
