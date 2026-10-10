#!/bin/bash
# Weekly deploy helper: publish dist/ to Cloudflare Pages via GitHub pages branch.
# ASCII-only on purpose (cron runs reject commands containing confusable/non-ASCII text).
set -uo pipefail

PROJECT_DIR="/home/nari/scripts/spinorama_JPY"
cd "$PROJECT_DIR" || exit 1

REMOTE_URL=$(git config --get remote.origin.url || true)
if [ -z "$REMOTE_URL" ]; then
  echo "ERROR: Git remote 'origin' is not configured" >&2
  exit 2
fi

DEPLOY_TIME=$(date '+%Y-%m-%d %H:%M:%S')

(
  cd dist || exit 1
  rm -rf .git
  git init -b pages > /dev/null
  git config user.name "Spinorama Deployer"
  git config user.email "deploy@spinorama.local"
  git add -A
  git commit -m "Auto-deploy: ${DEPLOY_TIME}" > /dev/null
  git push -f "$REMOTE_URL" pages > /dev/null 2>&1
)

rc=$?
rm -rf dist/.git

if [ $rc -eq 0 ]; then
  echo "DEPLOY_OK"
else
  echo "DEPLOY_FAILED rc=$rc" >&2
fi
exit $rc
