#!/usr/bin/env python3
"""Inspect probe caches for specific pages (Japanese terms hardcoded)."""
import re
import os

CACHE = "/tmp/probe_cache"


def load(p):
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def plain(t):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


TARGETS = [
    ("275_kakaku_search.html", ["見つかりません", "該当", "Debut"]),
    ("877_kakaku_search.html", ["見つかりません", "該当", "RCF", "Ayra"]),
    ("850_kakaku_search.html", ["見つかりません", "該当", "QSC"]),
    ("545_yahoo.html", ["見つかりませんでした", "該当する", "Q350"]),
    ("275_yahoo.html", ["見つかりませんでした", "該当する"]),
]

for fn, terms in TARGETS:
    p = os.path.join(CACHE, fn)
    t = load(p)
    print("=" * 66)
    print(fn, "len", len(t))
    if not t:
        continue
    pl = plain(t)
    for term in terms:
        hits = []
        for m in re.finditer(re.escape(term), pl, re.I):
            hits.append(pl[max(0, m.start() - 110):m.end() + 110])
            if len(hits) >= 2:
                break
        print("  --", term, len(hits))
        for h in hits:
            print("     ...", h.strip()[:210])
    links = sorted(set(re.findall(r"/item/(K\d+)/", t)))
    print("  item_links:", links[:12])

# kakaku item pages: shop count context
for fn in ("1051_kakaku_item_K0000818790.html", "1051_kakaku_item_K0000818791.html",
           "545_kakaku_item_K0000964229.html"):
    t = load(os.path.join(CACHE, fn))
    print("=" * 66)
    print(fn, "len", len(t))
    if not t:
        continue
    pl = plain(t)
    for term in ["店舗", "販売終了", "在庫", "登録がありません", "最安値"]:
        hits = []
        for m in re.finditer(re.escape(term), pl):
            hits.append(pl[max(0, m.start() - 90):m.end() + 90])
            if len(hits) >= 3:
                break
        print("  --", term, len(hits))
        for h in hits:
            print("     ...", h.strip()[:190])
    for pat in (r'data-jsread-lowprice="(\d+)"', r'"shopCount":(\d+)',
                r'data-shopcount="(\d+)"', r'(\d+)店舗'):
        print("  pat", pat, "->", re.findall(pat, t)[:6])
