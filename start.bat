@echo off
chcp 65001 > nul
echo ========================================================
echo   SPINORAMA JPY - スピーカー測定＆日本円コスパ分析システム
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] データベースの存在確認中...
if not exist "data\spinorama_jpy.db" (
    echo 初回起動のため、SPINORAMA公式データおよび日本市場データを同期しています...
    python backend\db.py
    python backend\spinorama_sync.py
    python backend\jp_market_updater.py
)

echo [2/2] ローカルWebサーバーを起動しています (http://localhost:8550)...
start "" http://localhost:8550
python backend\app.py

pause
