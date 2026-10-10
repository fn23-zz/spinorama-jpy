#!/usr/bin/env python3
"""週次検証ジョブ用: 参考CPI上位の「未検証」候補を選定してJSONで出力する。

選定条件:
  - japan_market.verification_status が 'unverified' または NULL (未検証のみ)
  - japan_market.availability が 'not_available' / 'discontinued' 以外 (調査余地あり)
  - is_manual_override = 1 の行は除外 (人間が既に判断済み)
  - is_manual_override でない 'verified' も除外
並び順: COALESCE(cp_tone, cp_tone_est) DESC
"""
import argparse
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "data", "spinorama_jpy.db")

SQL = """
SELECT s.id, s.brand, s.model, s.price_usd, s.amount_type, s.shape, s.energy_type,
       s.score_tone, s.score_tone_sub, s.score_tone_eq, s.score_tone_sub_eq,
       j.price_jpy, j.price_type, j.availability, j.verification_status,
       j.confidence_level, j.source_name, j.source_url, j.search_keyword,
       j.is_manual_override,
       cp.cp_tone, cp.cp_tone_est
FROM speakers s
LEFT JOIN japan_market j      ON j.speaker_id  = s.id
LEFT JOIN cost_performance cp ON cp.speaker_id = s.id
WHERE COALESCE(j.is_manual_override, 0) = 0
  AND (j.verification_status IS NULL OR j.verification_status = 'unverified')
  AND COALESCE(j.availability, 'unknown') NOT IN ('not_available', 'discontinued')
  AND COALESCE(cp.cp_tone_est, cp.cp_tone) IS NOT NULL
ORDER BY COALESCE(cp.cp_tone, cp.cp_tone_est) DESC
LIMIT ?
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--out", default=os.path.join(ROOT, "reports", "weekly_targets.json"))
    ap.add_argument("--json", action="store_true", help="JSONのみ出力")
    args = ap.parse_args()

    if not os.path.exists(DB):
        print(f"DB not found: {DB}", file=sys.stderr)
        return 1

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(SQL, (args.limit,))]
    con.close()

    payload = {"generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
               "limit": args.limit, "count": len(rows), "items": rows}

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"# 週次検証ターゲット {payload['generated_at']} / {len(rows)}件 (参考CPI降順)")
    print(f"# 保存先: {args.out}")
    for i, r in enumerate(rows, 1):
        cpi = r["cp_tone"] if r["cp_tone"] is not None else r["cp_tone_est"]
        tag = "" if r["cp_tone"] is None else "(確定CPI) "
        print(f"{i:2d}. id={r['id']} {r['brand']} {r['model']} | Tone={r['score_tone']} "
              f"| 参考CPI={cpi:.2f} {tag}| USD={r['price_usd']} | 現DB価格={r['price_jpy']} "
              f"| {r['availability']}/{r['verification_status']} "
              f"| amount_type={r['amount_type']} | keyword={r['search_keyword']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
