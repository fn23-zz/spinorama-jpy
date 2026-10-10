#!/usr/bin/env python3
"""Verify saved rows in DB + exported dist JSON for a list of ids."""
import json
import os
import sys

sys.path.insert(0, "/home/nari/scripts/spinorama_JPY/backend")
from db import get_db_connection  # noqa: E402

ids = [int(x) for x in sys.argv[1:]]
conn = get_db_connection()
cur = conn.cursor()
cur.execute(
    "SELECT speaker_id, price_jpy, price_each, price_type, availability, verification_status,"
    " confidence_level, is_manual_override, substr(notes,1,60) FROM japan_market"
    " WHERE speaker_id IN (%s) ORDER BY speaker_id" % ",".join("?" * len(ids)), ids)
print("--- DB rows ---")
for r in cur.fetchall():
    print(json.dumps(dict(r), ensure_ascii=False))
conn.close()

path = "/home/nari/scripts/spinorama_JPY/dist/data/speakers.json"
d = json.load(open(path, encoding="utf-8"))
items = d.get("items", d if isinstance(d, list) else [])
print("--- dist/data/speakers.json total=%s items=%d ---" % (d.get("total"), len(items)))
byid = {i["id"]: i for i in items if "id" in i}
for i in ids:
    it = byid.get(i)
    if not it:
        print(i, "MISSING")
        continue
    print(i, it.get("brand"), it.get("model"), "| jpy=", it.get("price_jpy"),
          "| each=", it.get("price_each"), "|", it.get("availability"),
          "|", it.get("verification_status"), "| cp_tone=", it.get("cp_tone"))
print("file mtime", os.path.getmtime(path))
