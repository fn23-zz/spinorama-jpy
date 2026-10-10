#!/bin/bash
# Weekly deploy helper: regenerate nothing, just publish dist/ to Cloudflare Pages.
# ASCII-only on purpose (cron runs reject commands containing confusable/non-ASCII text).
set -uo pipefail

PROJECT_DIR="/home/nari/scripts/spinorama_JPY"
cd "$PROJECT_DIR" || exit 1

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] && [ -f "$HOME/.bashrc" ]; then
  eval "$(grep -m1 '^export CLOUDFLARE_API_TOKEN=' "$HOME/.bashrc")"
fi

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "ERROR: CLOUDFLARE_API_TOKEN not available (checked env and ~/.bashrc)" >&2
  exit 2
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "ERROR: npx not found; cannot run wrangler" >&2
  exit 3
fi

npx --yes wrangler pages deploy dist --project-name=spinorama-jpy --commit-dirty=true
rc=$?
if [ $rc -eq 0 ]; then
  echo "DEPLOY_OK"
else
  echo "DEPLOY_FAILED rc=$rc" >&2
fi
exit $rc
