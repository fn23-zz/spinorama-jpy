#!/usr/bin/env python3
"""Grep a cached page for terms (case-insensitive), print surrounding text."""
import re
import sys

path = sys.argv[1]
terms = sys.argv[2:]
t = open(path, encoding="utf-8", errors="replace").read()
plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
plain = re.sub(r"<[^>]+>", " ", plain)
plain = re.sub(r"\s+", " ", plain)
for term in terms:
    hits = []
    for m in re.finditer(re.escape(term), plain, re.I):
        hits.append(plain[max(0, m.start() - 90):m.end() + 90])
        if len(hits) >= 4:
            break
    print("==", term, "->", len(hits), "hits")
    for h in hits:
        print("   ...", h.strip()[:220])
