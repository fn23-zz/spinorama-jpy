#!/usr/bin/env python3
"""Grep patterns in probe cache files."""
import re
import sys

for path in sys.argv[1:]:
    t = open(path, encoding="utf-8", errors="replace").read()
    print("=" * 60)
    print(path, len(t), "chars")
    for pat in sys.argv[0:0]:
        pass
    pats = [r"[^\s<>]{0,25}販売終了[^\s<>]{0,25}", r"[^\s<>]{0,20}取扱店舗[^\s<>]{0,20}",
            r"[^\s<>]{0,20}\d+店舗[^\s<>]{0,20}", r"[^\s<>]{0,15}在庫[^\s<>]{0,15}",
            r"data-jsread-lowprice=\"\d+\"", r"data-jsread-price=\"\d+\"",
            r"[^\s<>]{0,15}登録がありません[^\s<>]{0,15}"]
    for p in pats:
        hits = re.findall(p, t)[:5]
        if hits:
            print("  ", p, "->", hits)
