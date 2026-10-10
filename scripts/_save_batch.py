#!/usr/bin/env python3
"""Save a batch of verification JSON objects via agent_verifier.save.

Usage: python3 scripts/_save_batch.py /tmp/spinorama_batch.json
Also writes each item to /tmp/spinorama_<id>.json for the record.
"""
import json
import os
import sys

sys.path.insert(0, "/home/nari/scripts/spinorama_JPY/backend")
from agent_verifier import save_verified_result  # noqa: E402

items = json.load(open(sys.argv[1], encoding="utf-8"))
for it in items:
    sid = it["speaker_id"]
    with open("/tmp/spinorama_%d.json" % sid, "w", encoding="utf-8") as f:
        json.dump(it, f, ensure_ascii=False, indent=2)
    try:
        res = save_verified_result(it)
        print(json.dumps({
            "id": sid, "model": "%s %s" % (res.get("brand"), res.get("model")),
            "price_jpy": res.get("price_jpy"), "price_each": res.get("price_each"),
            "availability": res.get("availability"),
            "verification_status": res.get("verification_status"),
            "confidence": res.get("confidence_level"),
            "cp_tone": res.get("cp_tone"),
        }, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"id": sid, "error": repr(e)}, ensure_ascii=False))
