#!/usr/bin/env python3
"""Toneコスパ（CPI）順位の表示。週次ジョブの前後比較用。

順位対象: japan_market.verification_status='verified' かつ price_jpy が存在する機種のみ
（参考CPIしか持たない未検証機種は順位から除外）。
"""
import argparse
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(os.path.dirname(HERE), "data", "spinorama_jpy.db")

RANK_SQL = """
SELECT s.id, s.brand, s.model, j.price_jpy, j.availability,
       cp.cp_tone, cp.cp_tone_sub, cp.cp_tone_eq, cp.cp_tone_sub_eq
FROM cost_performance cp
JOIN speakers s      ON s.id = cp.speaker_id
JOIN japan_market j  ON j.speaker_id = s.id
WHERE cp.cp_tone IS NOT NULL AND j.price_jpy IS NOT NULL
ORDER BY cp.cp_tone DESC
LIMIT ?
"""

COUNT_SQL = """
SELECT COUNT(*) FROM cost_performance cp
JOIN japan_market j ON j.speaker_id = cp.speaker_id
WHERE cp.cp_tone IS NOT NULL AND j.price_jpy IS NOT NULL
"""

SUMMARY_SQL = """
SELECT
  (SELECT COUNT(*) FROM speakers) AS speakers,
  (SELECT COUNT(*) FROM japan_market WHERE verification_status = 'verified') AS verified_rows,
  (SELECT COUNT(*) FROM japan_market WHERE verification_status = 'unverified') AS unverified_rows,
  (SELECT COUNT(*) FROM japan_market WHERE verification_status = 'unavailable') AS unavailable_rows,
  (SELECT COUNT(*) FROM japan_market WHERE availability = 'discontinued') AS discontinued_rows
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--csv", action="store_true", help="CSV出力（id,brand,model,price_jpy,cp_tone）")
    args = ap.parse_args()

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(RANK_SQL, (args.limit,))]
    ranked = con.execute(COUNT_SQL).fetchone()[0]
    summary = dict(con.execute(SUMMARY_SQL).fetchone())
    con.close()

    if args.csv:
        for i, r in enumerate(rows, 1):
            print(f"{i},{r['id']},{r['brand']} {r['model']},{r['price_jpy']},{r['cp_tone']:.4f}")
    else:
        print(f"Tone CPI ranking (verified-jpy only) / ranked={ranked}")
        for i, r in enumerate(rows, 1):
            print(f"{i:2d}. {r['cp_tone']:.2f}  id={r['id']:<5} {r['brand']} {r['model']}  "
                  f"JPY {r['price_jpy']:,}  ({r['availability']})")
        print(f"summary: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
