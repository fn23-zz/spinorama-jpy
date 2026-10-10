#!/usr/bin/env python3
"""Fetch a list of kakaku item pages and print title + lowprice + shopcount.

Usage: python3 scripts/_kakaku_items.py K0001407366 K0001407365 ...
"""
import json
import sys

sys.path.insert(0, "/home/nari/scripts/spinorama_JPY/scripts")
from _market_probe import kakaku_item  # noqa: E402

for kid in sys.argv[1:]:
    r = kakaku_item(kid, "batch")
    print(json.dumps(r, ensure_ascii=False))
