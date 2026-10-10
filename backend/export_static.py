import sqlite3
import json
import os
import shutil
import csv
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "spinorama_jpy.db")
DIST_DIR = os.path.join(BASE_DIR, "dist")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

def export_static_site():
    print(f"Starting static site generation into: {DIST_DIR}")
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(os.path.join(DIST_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(DIST_DIR, "css"), exist_ok=True)
    os.makedirs(os.path.join(DIST_DIR, "js"), exist_ok=True)

    # 1. Copy frontend static files
    shutil.copy(os.path.join(FRONTEND_DIR, "index.html"), os.path.join(DIST_DIR, "index.html"))
    shutil.copy(os.path.join(FRONTEND_DIR, "css", "style.css"), os.path.join(DIST_DIR, "css", "style.css"))
    shutil.copy(os.path.join(FRONTEND_DIR, "js", "app.js"), os.path.join(DIST_DIR, "js", "app.js"))
    shutil.copy(os.path.join(FRONTEND_DIR, "js", "chart.js"), os.path.join(DIST_DIR, "js", "chart.js"))
    shutil.copy(os.path.join(FRONTEND_DIR, "js", "editor.js"), os.path.join(DIST_DIR, "js", "editor.js"))
    if os.path.exists(os.path.join(FRONTEND_DIR, "js", "verification.js")):
        shutil.copy(os.path.join(FRONTEND_DIR, "js", "verification.js"), os.path.join(DIST_DIR, "js", "verification.js"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 2. Export Stats
    cursor.execute("SELECT COUNT(*) FROM speakers")
    total_spk = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM japan_market WHERE availability = 'domestic_in_stock'")
    domestic_stock = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM japan_market WHERE is_manual_override = 1")
    manual_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM japan_market WHERE verification_status = 'verified'")
    verified_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM japan_market WHERE verification_status = 'needs_review'")
    needs_review_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM japan_market WHERE verification_status = 'unavailable'")
    unavailable_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM japan_market WHERE verification_status = 'unverified' OR verification_status IS NULL")
    unverified_count = cursor.fetchone()[0]

    cursor.execute("SELECT MAX(updated_at) FROM cost_performance")
    last_upd = cursor.fetchone()[0]

    stats_data = {
        "total_speakers": total_spk,
        "domestic_in_stock": domestic_stock,
        "manual_overrides": manual_count,
        "verified_count": verified_count,
        "needs_review_count": needs_review_count,
        "unavailable_count": unavailable_count,
        "unverified_count": unverified_count,
        "verification_progress": round(((verified_count + unavailable_count) / total_spk * 100), 1) if total_spk > 0 else 0,
        "last_updated": last_upd or datetime.now().isoformat(),
        "mode": "static_pages"
    }

    with open(os.path.join(DIST_DIR, "data", "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats_data, f, ensure_ascii=False, indent=2)

    # 3. Export Brands
    cursor.execute("SELECT DISTINCT brand FROM speakers ORDER BY brand ASC")
    brands = [r[0] for r in cursor.fetchall() if r[0]]
    with open(os.path.join(DIST_DIR, "data", "brands.json"), "w", encoding="utf-8") as f:
        json.dump({"brands": brands}, f, ensure_ascii=False, indent=2)

    # 4. Export All Speakers (Full Dataset)
    cursor.execute("""
        SELECT 
            s.id,
            s.speaker_key,
            s.speaker_name,
            s.brand,
            s.model,
            s.shape,
            s.energy_type,
            s.price_usd,
            s.amount_type,
            s.default_measurement,
            s.measurement_quality,
            s.f3,
            s.f6,
            s.flatness,
            s.score_tone,
            s.score_tone_sub,
            s.score_tone_eq,
            s.score_tone_sub_eq,
            s.reviews_json,
            j.price_jpy,
            j.price_type as jpy_price_type,
            j.price_each,
            j.availability,
            j.source_name,
            j.source_url,
            j.is_manual_override,
            j.notes,
            COALESCE(j.verification_status, 'unverified') as verification_status,
            COALESCE(j.confidence_level, 'low') as confidence_level,
            j.search_keyword,
            j.verified_at,
            j.last_checked,
            cp.cp_tone,
            cp.cp_tone_sub,
            cp.cp_tone_eq,
            cp.cp_tone_sub_eq,
            cp.cp_tone_ratio,
            cp.cp_tone_sub_ratio,
            cp.cp_tone_eq_ratio,
            cp.cp_tone_sub_eq_ratio,
            cp.cp_tone_est,
            cp.cp_tone_sub_est,
            cp.cp_tone_eq_est,
            cp.cp_tone_sub_eq_est
        FROM speakers s
        LEFT JOIN japan_market j ON s.id = j.speaker_id
        LEFT JOIN cost_performance cp ON s.id = cp.speaker_id
        ORDER BY s.brand ASC, s.model ASC
    """)
    rows = cursor.fetchall()

    speakers_list = []
    for r in rows:
        item = dict(r)
        if item.get("reviews_json"):
            try:
                item["reviews"] = json.loads(item["reviews_json"])
            except Exception:
                item["reviews"] = []
        else:
            item["reviews"] = []
        speakers_list.append(item)

    with open(os.path.join(DIST_DIR, "data", "speakers.json"), "w", encoding="utf-8") as f:
        json.dump({"total": len(speakers_list), "items": speakers_list}, f, ensure_ascii=False)

    # 5. Export Full CSV
    csv_path = os.path.join(DIST_DIR, "data", "spinorama_jpy.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Brand", "Model", "Shape", "Type", "USD", "JPY Price (Pair)", "Availability", 
            "Source", "Tone", "Tone w/Sub", "Tone w/EQ", "Tone w/Both",
            "CP Tone (CPI)", "CP w/Sub (CPI)", "CP w/EQ (CPI)", "CP w/Both (CPI)",
            "-3dB (Hz)", "-6dB (Hz)", "Flatness (dB)", "Source URL", "Notes", "Last Checked"
        ])
        for s in speakers_list:
            writer.writerow([
                s.get("brand", ""),
                s.get("model", ""),
                s.get("shape", ""),
                s.get("energy_type", ""),
                s.get("price_usd", ""),
                s.get("price_jpy", ""),
                s.get("availability", ""),
                s.get("source_name", ""),
                s.get("score_tone", ""),
                s.get("score_tone_sub", ""),
                s.get("score_tone_eq", ""),
                s.get("score_tone_sub_eq", ""),
                s.get("cp_tone", ""),
                s.get("cp_tone_sub", ""),
                s.get("cp_tone_eq", ""),
                s.get("cp_tone_sub_eq", ""),
                s.get("f3", ""),
                s.get("f6", ""),
                s.get("flatness", ""),
                s.get("source_url", ""),
                s.get("notes", ""),
                s.get("last_checked", "")
            ])

    conn.close()

    # Calculate file size
    json_size = os.path.getsize(os.path.join(DIST_DIR, "data", "speakers.json")) / 1024
    csv_size = os.path.getsize(csv_path) / 1024
    print(f"Static site export completed successfully!")
    print(f"  - Total Speakers: {len(speakers_list)}")
    print(f"  - speakers.json: {json_size:.1f} KB")
    print(f"  - spinorama_jpy.csv: {csv_size:.1f} KB")
    print(f"  - Output Directory: {DIST_DIR}")

if __name__ == '__main__':
    export_static_site()
