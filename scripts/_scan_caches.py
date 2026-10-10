#!/usr/bin/env python3
"""Scan probe caches for bot-block / empty-result markers."""
import glob
import os
import re

MARK = {
    "captcha": r"captcha|Captcha|CAPTCHA|ロボットではありません|Enter the characters",
    "amazon_empty": r"did not match any products|に一致する商品はありません",
    "amazon_block": r"api-services-support@amazon|To discuss automated access",
    "yahoo_empty": r"見つかりませんでした|該当する商品はありません",
    "kakaku_noinfo": r"価格情報の登録がありません|取扱店舗なし",
}
for p in sorted(glob.glob("/tmp/probe_cache/*")):
    t = open(p, encoding="utf-8", errors="replace").read()
    if t.startswith("FETCH_ERROR"):
        print("%-52s FETCH_ERROR" % os.path.basename(p))
        continue
    flags = [k for k, pat in MARK.items() if re.search(pat, t)]
    extra = ""
    if "amazon" in p:
        extra = " n_blocks=%d" % len(re.findall(r'data-asin="', t))
    print("%-52s len=%-8d %s%s" % (os.path.basename(p), len(t), ",".join(flags), extra))
