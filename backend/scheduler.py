import time
import os
import sys
import json
import threading
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db import get_db_connection
from spinorama_sync import fetch_spinorama_data
from jp_market_updater import run_market_update

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"weekly_update_interval_days": 7}

def get_last_update_time():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT finished_at FROM update_logs WHERE status = 'success' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row and row["finished_at"]:
        try:
            return datetime.fromisoformat(row["finished_at"])
        except Exception:
            pass
    return None

def should_update():
    last_time = get_last_update_time()
    if not last_time:
        return True
    cfg = load_config()
    interval_days = cfg.get("weekly_update_interval_days", 7)
    return datetime.now() - last_time >= timedelta(days=interval_days)

def perform_full_update():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Executing scheduled full weekly update...")
    try:
        fetch_spinorama_data()
        run_market_update()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduled full update completed successfully.")
        return True
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error during scheduled update: {e}")
        return False

def scheduler_loop(interval_check_seconds=3600):
    print("Background weekly update scheduler started.")
    while True:
        if should_update():
            perform_full_update()
        time.sleep(interval_check_seconds)

def start_scheduler_background():
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()
    return t

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        perform_full_update()
    else:
        print("Running scheduler in foreground. Press Ctrl+C to stop.")
        scheduler_loop()
