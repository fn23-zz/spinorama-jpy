#!/usr/bin/env python3
"""Print plain-text context around each ASIN occurrence in a cached Amazon page."""
import re
import sys

path = sys.argv[1]
html = open(path, encoding="utf-8", errors="replace").read()
for asin in sys.argv[2:]:
    print("=" * 40, asin)
    for m in list(re.finditer(re.escape(asin), html))[:2]:
        body = html[m.start():m.start() + 5000]
        plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S)
        plain = re.sub(r"<[^>]+>", " ", plain)
        plain = re.sub(r"\s+", " ", plain)
        print("   ", plain[:700])
