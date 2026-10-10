import os
import sys
import json
import re
import subprocess
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db import get_db_connection
from cost_perf_engine import update_cost_performance

SPINORAMA_BASE_URL = "https://www.spinorama.org"

def clean_float(val):
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str or val_str in ("-1", "-1.0", "-10", "-10.0", "none", "***", "null"):
        return None
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return None

def fetch_json_via_curl(url):
    """Fetches JSON via curl using IPv4 for fast and reliable network access."""
    cmd = ["curl", "-s", "-4", "--connect-timeout", "15", "--max-time", "60", url]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0 or not res.stdout:
        raise RuntimeError(f"curl failed for {url}: {res.stderr.strip()}")
    return json.loads(res.stdout)

def get_official_chunk_urls():
    """Extracts the active metadata chunks from the official spinorama.org JS bundle."""
    js_url = f"{SPINORAMA_BASE_URL}/js/meta-v5.min.js"
    cmd = ["curl", "-s", "-4", "--connect-timeout", "15", "--max-time", "30", js_url]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    chunks = []
    if res.returncode == 0 and res.stdout:
        m = re.search(r'metadataFilenameChunksValue=\'([^\']+)\'', res.stdout)
        if m:
            try:
                chunks = json.loads(m.group(1))
            except Exception:
                pass

    if not chunks:
        # Fallback to known standard chunks if JS parsing fails
        chunks = [
            "/json/metadata-head.json",
            "/json/metadata-2020.json",
            "/json/metadata-2021.json",
            "/json/metadata-2022.json",
            "/json/metadata-2023.json",
            "/json/metadata-2024.json",
            "/json/metadata-2025.json",
            "/json/metadata-1970.json",
            "/json/metadata-2019.json"
        ]
    else:
        # Ensure metadata-head is included
        if "/json/metadata-head.json" not in chunks:
            chunks.insert(0, "/json/metadata-head.json")

    return chunks

def fetch_spinorama_data():
    print("============================================================")
    print(f"Fetching official SPINORAMA data from {SPINORAMA_BASE_URL}...")
    print("============================================================")

    chunk_paths = get_official_chunk_urls()
    print(f"Discovered {len(chunk_paths)} metadata chunks from official Spinorama site:")
    for cp in chunk_paths:
        print(f"  - {cp}")

    all_speakers_map = {}
    for cp in chunk_paths:
        full_url = f"{SPINORAMA_BASE_URL}{cp}"
        print(f"Downloading {full_url}...")
        try:
            chunk_data = fetch_json_via_curl(full_url)
            all_speakers_map.update(chunk_data)
            print(f"  -> Added {len(chunk_data)} records (Total unique: {len(all_speakers_map)})")
        except Exception as e:
            print(f"  -> Warning: Failed to fetch {full_url}: {e}")

    print(f"\nSuccessfully collected {len(all_speakers_map)} total unique speaker measurements from spinorama.org.")

    # Load config for default rate
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    usd_rate = 155.0
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                usd_rate = float(cfg.get("usd_to_jpy_rate", 155.0))
        except Exception:
            pass

    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    inserted_count = 0
    updated_count = 0

    for name_key, spk in all_speakers_map.items():
        brand = spk.get("brand", "").strip()
        model = spk.get("model", "").strip()
        if not brand and not model:
            continue

        speaker_full = f"{brand} {model}".strip()
        speaker_key = f"{brand}_{model}".lower().replace(" ", "_")

        shape = spk.get("shape", "").strip() or "bookshelves"
        energy = spk.get("type", "").strip() or "passive"
        price_usd = clean_float(spk.get("price"))
        amount = spk.get("amount", "pair").strip() or "pair"

        # Measurement details
        def_m_key = spk.get("default_measurement")
        measurements = spk.get("measurements", {})
        m = measurements.get(def_m_key) if def_m_key else (list(measurements.values())[0] if measurements else {})
        if not m:
            m = {}

        quality = m.get("quality", "").strip() or "medium"
        measurement_name = def_m_key or ""

        # Estimates
        estimates = m.get("estimates", {})
        f3 = clean_float(estimates.get("ref_3dB"))
        f6 = clean_float(estimates.get("ref_6dB"))
        flatness = clean_float(estimates.get("ref_band"))

        # Scores
        pref_rating = m.get("pref_rating", {})
        score_tone = clean_float(pref_rating.get("pref_score"))
        score_tone_sub = clean_float(pref_rating.get("pref_score_wsub"))

        pref_rating_eq = m.get("pref_rating_eq", {})
        score_tone_eq = clean_float(pref_rating_eq.get("pref_score"))
        score_tone_sub_eq = clean_float(pref_rating_eq.get("pref_score_wsub"))

        # Reviews
        reviews = []
        rev_data = m.get("reviews", {})
        if isinstance(rev_data, dict):
            for src, url in rev_data.items():
                label = "AudioScienceReview" if src.lower() == "asr" else ("Erin's Audio Corner" if "erin" in src.lower() else src)
                reviews.append({"source": src.upper(), "label": label, "url": url})
        elif isinstance(rev_data, list):
            for r in rev_data:
                if isinstance(r, dict):
                    reviews.append(r)

        # Raw specs JSON
        specs = m.get("specifications", {})
        raw_json = json.dumps({
            "default_measurement": def_m_key,
            "origin": m.get("origin", ""),
            "format": m.get("format", ""),
            "review_published": m.get("review_published", ""),
            "specifications": specs,
            "computed_sensitivity": m.get("computed_sensitivity", {})
        }, ensure_ascii=False)

        # Check existing in DB
        cursor.execute("SELECT id FROM speakers WHERE speaker_key = ?", (speaker_key,))
        existing = cursor.fetchone()

        if existing:
            speaker_id = existing["id"]
            cursor.execute("""
                UPDATE speakers SET
                    speaker_name = ?,
                    brand = ?,
                    model = ?,
                    shape = ?,
                    energy_type = ?,
                    price_usd = COALESCE(?, price_usd),
                    amount_type = ?,
                    default_measurement = ?,
                    measurement_quality = ?,
                    f3 = ?,
                    f6 = ?,
                    flatness = ?,
                    score_tone = ?,
                    score_tone_sub = ?,
                    score_tone_eq = ?,
                    score_tone_sub_eq = ?,
                    reviews_json = ?,
                    raw_json = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                speaker_full, brand, model, shape, energy, price_usd,
                amount, measurement_name, quality, f3, f6, flatness,
                score_tone, score_tone_sub, score_tone_eq, score_tone_sub_eq,
                json.dumps(reviews), raw_json, now, speaker_id
            ))
            updated_count += 1
        else:
            cursor.execute("""
                INSERT INTO speakers (
                    speaker_key, speaker_name, brand, model, shape, energy_type,
                    price_usd, amount_type, default_measurement, measurement_quality,
                    f3, f6, flatness,
                    score_tone, score_tone_sub, score_tone_eq, score_tone_sub_eq,
                    reviews_json, raw_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                speaker_key, speaker_full, brand, model, shape, energy,
                price_usd, amount, measurement_name, quality,
                f3, f6, flatness,
                score_tone, score_tone_sub, score_tone_eq, score_tone_sub_eq,
                json.dumps(reviews), raw_json, now
            ))
            speaker_id = cursor.lastrowid
            inserted_count += 1

            # Initialize japan_market entry if not exists (never overwrites verified data)
            initial_jpy = int(round(price_usd * usd_rate)) if price_usd else None
            cursor.execute("""
                INSERT OR IGNORE INTO japan_market (
                    speaker_id, price_jpy, price_type, availability, source_name, is_manual_override, notes, last_checked
                ) VALUES (?, ?, 'pair', 'unconfirmed', '為替換算参考値', 0, 'USD価格×為替レート換算', ?)
            """, (speaker_id, initial_jpy, now))

    # Log update
    cursor.execute("""
        INSERT INTO update_logs (task_type, status, message, items_processed, started_at, finished_at)
        VALUES ('spinorama_sync', 'success', 'Synced directly from official spinorama.org metadata JSONs', ?, ?, ?)
    """, (len(all_speakers_map), now, datetime.now().isoformat()))

    conn.commit()

    # Re-compute cost performance regression models and CPIs
    print("\nRecalculating Cost-Performance Index (CPI) with updated official spinorama data...")
    update_cost_performance()

    # Total speakers count
    cursor.execute("SELECT COUNT(*) FROM speakers")
    total_speakers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM speakers WHERE score_tone IS NOT NULL")
    scored_speakers = cursor.fetchone()[0]

    conn.close()
    print(f"\n============================================================")
    print(f"Sync complete! Total speakers in DB: {total_speakers} (with Tone score: {scored_speakers})")
    print(f"  - Updated existing speakers: {updated_count}")
    print(f"  - Inserted newly measured speakers: {inserted_count}")
    print(f"============================================================")

if __name__ == "__main__":
    fetch_spinorama_data()
