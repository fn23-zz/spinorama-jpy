#!/usr/bin/env python3
"""Run Yahoo!Shopping search for each keyword listed in a JSON file.

Usage: python3 scripts/_yahoo_probe.py keywords.json
"""
import json
import re
import sys

sys.path.insert(0, "/home/nari/scripts/spinorama_JPY/scripts")
from _market_probe import yahoo  # noqa: E402

kws = json.load(open(sys.argv[1], encoding="utf-8"))
for kw in kws:
    r = yahoo(kw, "yq_" + re.sub(r"\W+", "_", kw)[:40])
    print("==", kw)
    print(json.dumps(r, ensure_ascii=False)[:1600])
