#!/bin/bash
# Verify the latest Cloudflare Pages deployment for spinorama-jpy (non-interactive).
# ASCII-only on purpose: cron commands with non-ASCII text get held for approval.
set -uo pipefail

PROJECT_DIR="/home/nari/scripts/spinorama_JPY"
cd "$PROJECT_DIR" || exit 1

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] && [ -f "$HOME/.bashrc" ]; then
  eval "$(grep -m1 '^export CLOUDFLARE_API_TOKEN=' "$HOME/.bashrc")"
fi

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "ERROR: CLOUDFLARE_API_TOKEN not available" >&2
  exit 2
fi

npx --yes wrangler pages deployment list --project-name=spinorama-jpy 2>&1 | head -10
