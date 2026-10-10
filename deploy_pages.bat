@echo off
chcp 65001 >nul
echo ========================================================
echo  SPINORAMA JPY -^> Cloudflare Pages (GitHub連動デプロイ)
echo ========================================================

if "%1"=="--update" (
    echo ^>^>^> [1/3] 最新データ巡回とコストパフォーマンス再計算を実行中...
    python backend/scheduler.py --now
) else (
    echo ^>^>^> [1/3] 既存データベースから静的エクスポートを行います...
    echo     (価格巡回も同時に行う場合は: deploy_pages.bat --update)
)

echo ^>^>^> [2/3] 静的ファイル (dist/) を生成中...
python backend/export_static.py

echo ^>^>^> [3/3] GitHub (pages ブランチ) へ成果物をPush中...
for /f "tokens=*" %%i in ('git config --get remote.origin.url') do set REMOTE_URL=%%i
if "%REMOTE_URL%"=="" (
    echo --------------------------------------------------------
    echo 【注意】Gitリモート (origin) が設定されていません。
    echo GitHub上でリポジトリを作成し、以下のコマンドで設定してください：
    echo   git remote add origin https://github.com/^<ユーザー名^>/spinorama-jpy.git
    echo --------------------------------------------------------
    pause
    exit /b 1
)

pushd dist
if exist .git rd /s /q .git
git init -b pages >nul
git config user.name "Spinorama Deployer"
git config user.email "deploy@spinorama.local"
git add -A
git commit -m "Auto-deploy via Windows" >nul
echo     リモート (%REMOTE_URL%) の pages ブランチへ送信中...
git push -f "%REMOTE_URL%" pages
if exist .git rd /s /q .git
popd

echo ========================================================
echo  デプロイ用成果物のPushが完了しました！
echo  Cloudflare Pagesが自動検知し、エッジに反映されます。
echo ========================================================
pause
