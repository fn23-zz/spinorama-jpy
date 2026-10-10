#!/bin/bash
# Weekly data pipeline for spinorama_JPY (price crawl -> CPI -> static export -> Cloudflare deploy).
# ASCII-only on purpose: cron commands with confusable/non-ASCII text get held for approval.
set -uo pipefail

PROJECT=/home/nari/scripts/spinorama_JPY
cd "$PROJECT" || exit 1

echo "[1/4] spinorama sync + JP market crawl"
timeout 1800 python3 backend/scheduler.py --now 2>&1 | tail -5
echo "[2/4] cost performance recompute"
python3 backend/cost_perf_engine.py 2>&1 | tail -3
echo "[3/4] static export"
python3 backend/export_static.py 2>&1 | tail -4
echo "[4/4] deploy to Cloudflare Pages"
bash scripts/weekly_deploy.sh 2>&1 | tail -4

echo "PIPELINE_DONE"
