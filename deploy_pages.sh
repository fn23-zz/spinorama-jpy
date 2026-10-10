#!/bin/bash
set -e

# スクリプト自身のディレクトリへ自動移動（どこから実行されても安全に動作）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo " SPINORAMA JPY -> Cloudflare Pages (GitHub連動デプロイスクリプト)"
echo " (実行ディレクトリ: $SCRIPT_DIR)"
echo "========================================================"

# オプション: --update が指定されたら価格巡回・計算を実行
if [[ "$1" == "--update" ]]; then
    echo ">>> [1/3] 最新データ巡回とコストパフォーマンス再計算を実行中..."
    python3 backend/scheduler.py --now
else
    echo ">>> [1/3] 既存データベースから静的エクスポートを行います..."
    echo "    (価格巡回も同時に行う場合は: ./deploy_pages.sh --update)"
fi

# 2. 静的サイト生成 (dist/ ディレクトリの構築)
echo ">>> [2/3] 静的ファイル (dist/) を生成中..."
python3 backend/export_static.py

# 3. GitHub (pages ブランチ) へのスマートPush
echo ">>> [3/3] GitHub (pages ブランチ) へ成果物をPush中..."

REMOTE_URL=$(git config --get remote.origin.url || true)
if [ -z "$REMOTE_URL" ]; then
    echo "--------------------------------------------------------"
    echo "【注意】Gitリモート (origin) がまだ設定されていません。"
    echo "GitHub上でリポジトリを作成し、以下のコマンドで設定してください："
    echo "  git remote add origin https://github.com/<ユーザー名>/spinorama-jpy.git"
    echo "  (または git remote add origin git@github.com:<ユーザー名>/spinorama-jpy.git)"
    echo "--------------------------------------------------------"
    echo "静的ファイル (dist/) の生成は正常に完了しています。"
    exit 1
fi

DEPLOY_TIME=$(date '+%Y-%m-%d %H:%M:%S')

(
    cd dist
    rm -rf .git
    git init -b pages > /dev/null
    git config user.name "Spinorama Deployer"
    git config user.email "deploy@spinorama.local"
    git add -A
    git commit -m "Auto-deploy: ${DEPLOY_TIME}" > /dev/null
    echo "    リモート (${REMOTE_URL}) の pages ブランチへ送信中..."
    git push -f "$REMOTE_URL" pages
    rm -rf .git
)

echo "========================================================"
echo " デプロイ用成果物のPushが正常に完了しました！"
echo " Cloudflare Pagesが自動検知し、数秒〜十数秒でエッジに反映されます。"
echo "========================================================"
