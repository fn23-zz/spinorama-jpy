#!/usr/bin/env python3
"""JP market probe v2: kakaku.com / Yahoo!Shopping / Amazon.co.jp.

Usage: python3 scripts/_market_probe.py <input.json> [id ...]
Writes UTF-8 caches to /tmp/probe_cache/<id>_<channel>.html
"""
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


def _decode(raw):
    m = re.search(rb'charset=["\']?([\w\-]+)', raw[:4000], re.I)
    encs = []
    if m:
        encs.append(m.group(1).decode("ascii", "replace"))
    encs += ["utf-8", "cp932", "euc_jp"]
    for e in encs:
        try:
            return raw.decode(e)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def fetch(url, cache_key, force=False):
    path = os.path.join(CACHE, cache_key + ".html")
    if os.path.exists(path) and not force and os.path.getsize(path) > 300:
        return open(path, encoding="utf-8", errors="replace").read()
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            text = _decode(r.read())
    except Exception as e:  # noqa: BLE001
        text = "FETCH_ERROR: %r" % (e,)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    time.sleep(1.0)
    return text


def strip(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


def kakaku_search(kw, cid):
    url = "https://search.kakaku.com/" + urllib.parse.quote(kw) + "/"
    html = fetch(url, "%s_kakaku_search" % cid)
    out = {"url": url}
    if html.startswith("FETCH_ERROR"):
        out["error"] = html
        return out, []
    ids = []
    for m in re.finditer(r'href="(?:https://kakaku\.com)?/item/(K\d+)/?"[^>]*>(.{0,200}?)</a>', html, re.S):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    names = [strip(m.group(2))[:70] for m in re.finditer(
        r'href="(?:https://kakaku\.com)?/item/(K\d+)/?"[^>]*>(.{0,200}?)</a>', html, re.S)]
    out["ids"] = ids[:8]
    out["names"] = names[:8]
    out["no_hit"] = ("該当する商品が見つかりません" in html) or ("見つかりませんでした" in html)
    return out, ids[:8]


def kakaku_item(kid, cid):
    url = "https://kakaku.com/item/%s/" % kid
    html = fetch(url, "%s_kakaku_item_%s" % (cid, kid))
    out = {"url": url, "kid": kid}
    if html.startswith("FETCH_ERROR"):
        out["error"] = html
        return out
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    out["title"] = strip(m.group(1))[:110] if m else None
    for pat, key in ((r'data-jsread-lowprice="(\d+)"', "lowprice"),
                     (r'"priceLow":"?(\d+)', "priceLow"),
                     (r'itemprop="price"[^>]*content="(\d+)"', "meta_price")):
        v = re.search(pat, html)
        if v:
            out[key] = int(v.group(1))
    sc = re.search(r'"shopCount":(\d+)', html) or re.search(r'data-shopcount="(\d+)"', html)
    if sc:
        out["shopcount"] = int(sc.group(1))
    prices = sorted({int(x) for x in re.findall(r'data-jsread-price="(\d+)"', html)})
    if prices:
        out["prices"] = prices[:6]
    out["shop_labels"] = re.findall(r"(\d+)店舗", html)[:4]
    out["discontinued"] = ("販売終了" in html) or ("取扱店舗なし" in html) or ("登録がありません" in html)
    return out


def kakaku(kw, cid):
    s, ids = kakaku_search(kw, cid)
    items = []
    for kid in ids[:2]:
        try:
            items.append(kakaku_item(kid, cid))
        except Exception as e:  # noqa: BLE001
            items.append({"kid": kid, "error": repr(e)})
    return {"search": s, "items": items}


def yahoo(kw, cid):
    url = "https://shopping.yahoo.co.jp/search?p=" + urllib.parse.quote(kw)
    html = fetch(url, "%s_yahoo" % cid)
    out = {"url": url}
    if html.startswith("FETCH_ERROR"):
        out["error"] = html
        return out
    hits = re.findall(r'"name":"([^"]{0,140}?)","price":(\d+),"actualPrice":(\d+)', html)
    out["hits"] = [{"name": n[:80], "price": int(p), "actual": int(a)} for n, p, a in hits[:8]]
    stores = re.findall(r"storeid:([\w\-]+);", html)
    out["stores"] = stores[:8]
    out["empty_msg"] = ("見つかりませんでした" in html) or ("該当する商品はありません" in html)
    out["title"] = (re.search(r"<title>(.*?)</title>", html, re.S).group(1).strip()[:90]
                    if re.search(r"<title>(.*?)</title>", html, re.S) else None)
    return out


def amazon(kw, cid):
    url = "https://www.amazon.co.jp/s?k=" + urllib.parse.quote(kw)
    html = fetch(url, "%s_amazon" % cid)
    out = {"url": url}
    if html.startswith("FETCH_ERROR"):
        out["error"] = html
        return out
    blocks = re.split(r'<div[^>]*data-asin="([A-Z0-9]{10})"', html)
    items = []
    for i in range(1, len(blocks) - 1, 2):
        asin, body = blocks[i], blocks[i + 1]
        if 's-search-result' not in body[:400]:
            continue
        t = re.search(r'<h2[^>]*>(.*?)</h2>', body, re.S)
        pr = re.search(r'a-price-whole">([\d,]+)', body)
        items.append({"asin": asin, "title": (strip(t.group(1))[:95] if t else ""),
                      "price": pr.group(1) if pr else None})
        if len(items) >= 8:
            break
    out["items"] = items
    out["empty_msg"] = ("did not match any products" in html
                        or "に一致する商品はありません" in html)
    return out


def main():
    inp = json.load(open(sys.argv[1], encoding="utf-8"))
    wanted = set(sys.argv[2:])
    for c in inp:
        if wanted and str(c["id"]) not in wanted:
            continue
        cid = str(c["id"])
        print("=" * 70)
        print("ID %s | %s | %s | kw=%s" % (cid, c.get("brand"), c.get("model"), c.get("keyword")))
        for name, fn in (("KAKAKU", kakaku), ("YAHOO", yahoo), ("AMAZON", amazon)):
            try:
                r = fn(c["keyword"], cid)
            except Exception as e:  # noqa: BLE001
                r = {"error": repr(e)}
            print("-- %s: %s" % (name, json.dumps(r, ensure_ascii=False)))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
