#!/usr/bin/env python3
"""Split a batch JSON into /tmp/spinorama_<id>.json files for agent_verifier CLI."""
import json
import sys

items = json.load(open(sys.argv[1], encoding="utf-8"))
ids = []
for it in items:
    sid = it["speaker_id"]
    with open("/tmp/spinorama_%d.json" % sid, "w", encoding="utf-8") as f:
        json.dump(it, f, ensure_ascii=False, indent=2)
    ids.append(str(sid))
print(" ".join(ids))
