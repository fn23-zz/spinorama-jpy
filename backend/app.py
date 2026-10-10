import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import sqlite3
import csv
import io
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db import get_db_connection
from cost_perf_engine import update_cost_performance
from scheduler import start_scheduler_background, perform_full_update

PORT = 8000
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"usd_to_jpy_rate": 155.0, "server_port": 8000}

def generate_search_keywords(brand, model):
    b = (brand or "").strip()
    m = (model or "").strip()
    return [
        f"{b} {m} 実売 価格",
        f"{b} {m} ペア 価格",
        f"{b} {m} サウンドハウス",
        f"{b} {m} 価格.com",
        f"{b} {m} Amazon",
        f"{b} {m} 国内定価"
    ]

class SpinoramaAPIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/speakers":
            self.handle_get_speakers(query)
        elif path == "/api/stats":
            self.handle_get_stats()
        elif path == "/api/export_csv":
            self.handle_export_csv(query)
        elif path == "/api/brands":
            self.handle_get_brands()
        elif path == "/api/verification/speakers":
            self.handle_get_verification_speakers(query)
        elif path == "/api/verification/stats":
            self.handle_get_verification_stats()
        else:
            # Fallback to static frontend files
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/speakers/update_market":
            self.handle_update_market()
        elif path == "/api/verification/save":
            self.handle_save_verification()
        elif path == "/api/trigger_update":
            self.handle_trigger_update()
        else:
            self.send_error(404, "Endpoint not found")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def handle_get_brands(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT brand FROM speakers WHERE brand IS NOT NULL ORDER BY brand ASC")
        brands = [r[0] for r in cursor.fetchall()]
        conn.close()
        self.send_json({"brands": brands})

    def handle_get_stats(self):
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM speakers")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM speakers WHERE score_tone IS NOT NULL")
        scored = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM japan_market WHERE availability = 'domestic_in_stock'")
        domestic_stock = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM japan_market WHERE is_manual_override = 1")
        manual_edits = cursor.fetchone()[0]

        cursor.execute("SELECT finished_at FROM update_logs WHERE status = 'success' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        last_updated = row[0] if row else None

        cfg = load_config()
        conn.close()

        self.send_json({
            "total_speakers": total,
            "scored_speakers": scored,
            "domestic_in_stock": domestic_stock,
            "manual_overrides": manual_edits,
            "usd_to_jpy_rate": cfg.get("usd_to_jpy_rate", 155.0),
            "last_updated": last_updated
        })

    def handle_get_speakers(self, query):
        conn = get_db_connection()
        cursor = conn.cursor()

        search = query.get("search", [""])[0].strip()
        brand = query.get("brand", [""])[0].strip()
        shape = query.get("shape", [""])[0].strip()
        energy = query.get("energy", [""])[0].strip()
        quality = query.get("quality", [""])[0].strip()
        availability = query.get("availability", [""])[0].strip()

        min_price = query.get("min_price", [""])[0].strip()
        max_price = query.get("max_price", [""])[0].strip()

        sort_key = query.get("sort", ["score"])[0].strip()
        sort_order = query.get("order", ["desc"])[0].strip().upper()
        if sort_order not in ("ASC", "DESC"):
            sort_order = "DESC"

        page = int(query.get("page", ["1"])[0])
        limit = int(query.get("limit", ["50"])[0])
        offset = (page - 1) * limit

        where_clauses = ["1=1"]
        params = []

        if search:
            where_clauses.append("(s.brand LIKE ? OR s.model LIKE ? OR s.speaker_name LIKE ?)")
            pat = f"%{search}%"
            params.extend([pat, pat, pat])

        if brand:
            where_clauses.append("s.brand = ?")
            params.append(brand)

        if shape:
            where_clauses.append("s.shape = ?")
            params.append(shape)

        if energy:
            where_clauses.append("s.energy_type = ?")
            params.append(energy)

        if quality:
            where_clauses.append("s.measurement_quality = ?")
            params.append(quality)

        if availability:
            if availability == "domestic_only":
                where_clauses.append("j.availability IN ('domestic_in_stock', 'domestic_backorder')")
            elif availability == "available":
                where_clauses.append("j.availability IN ('domestic_in_stock', 'domestic_backorder', 'import_only')")
            elif availability == "discontinued":
                where_clauses.append("j.availability = 'discontinued'")
            elif availability == "all":
                pass  # include all including DIY and not_available
            else:
                where_clauses.append("j.availability = ?")
                params.append(availability)
        else:
            # Default: Show purchasable products (exclude unbuyable DIY kits and not_available)
            where_clauses.append("j.availability IN ('domestic_in_stock', 'domestic_backorder', 'import_only')")

        price_expr = """(CASE 
            WHEN j.availability = 'not_available' OR j.verification_status = 'unavailable' THEN NULL 
            ELSE COALESCE(j.price_jpy, CAST(ROUND(s.price_usd * 155.0) AS INTEGER)) 
        END)"""
        if min_price:
            try:
                where_clauses.append(f"{price_expr} >= ?")
                params.append(int(min_price))
            except ValueError:
                pass

        if max_price:
            try:
                where_clauses.append(f"{price_expr} <= ?")
                params.append(int(max_price))
            except ValueError:
                pass

        # Sort mapping
        sort_col_map = {
            "brand": "s.brand",
            "model": "s.model",
            "price_usd": "s.price_usd",
            "price_jpy": price_expr,
            "f3": "s.f3",
            "flatness": "s.flatness",
            # Tone scores
            "score": "s.score_tone",
            "score_tone": "s.score_tone",
            "score_sub": "s.score_tone_sub",
            "score_tone_sub": "s.score_tone_sub",
            "score_eq": "s.score_tone_eq",
            "score_tone_eq": "s.score_tone_eq",
            "score_both": "s.score_tone_sub_eq",
            "score_tone_sub_eq": "s.score_tone_sub_eq",
            # Residual Cost-Performance scores
            "cp_tone": "cp.cp_tone",
            "cp_tone_sub": "cp.cp_tone_sub",
            "cp_tone_eq": "cp.cp_tone_eq",
            "cp_tone_sub_eq": "cp.cp_tone_sub_eq",
            # Ratio CP
            "cp_tone_ratio": "cp.cp_tone_ratio",
            "cp_tone_sub_ratio": "cp.cp_tone_sub_ratio"
        }

        sort_col = sort_col_map.get(sort_key, "s.score_tone")

        where_sql = " AND ".join(where_clauses)

        # Count total
        count_sql = f"""
            SELECT COUNT(*)
            FROM speakers s
            LEFT JOIN japan_market j ON s.id = j.speaker_id
            LEFT JOIN cost_performance cp ON s.id = cp.speaker_id
            WHERE {where_sql}
        """
        cursor.execute(count_sql, params)
        total_items = cursor.fetchone()[0]

        # Select data
        query_sql = f"""
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
                s.measurement_quality,
                s.default_measurement,
                s.f3,
                s.f6,
                s.flatness,
                s.score_tone,
                s.score_tone_sub,
                s.score_tone_eq,
                s.score_tone_sub_eq,
                s.reviews_json,
                s.raw_json,
                CASE 
                    WHEN j.availability = 'not_available' OR j.verification_status = 'unavailable' THEN NULL
                    ELSE COALESCE(j.price_jpy, CAST(ROUND(s.price_usd * 155.0) AS INTEGER))
                END as effective_price_jpy,
                CASE 
                    WHEN j.availability = 'not_available' OR j.verification_status = 'unavailable' THEN NULL
                    ELSE j.price_jpy
                END as price_jpy,
                j.price_type,
                COALESCE(j.availability, 'unconfirmed') as availability,
                j.source_name,
                j.source_url,
                j.is_manual_override,
                j.notes,
                COALESCE(j.verification_status, 'unverified') as verification_status,
                COALESCE(j.confidence_level, 'low') as confidence_level,
                j.search_keyword,
                j.price_each,
                j.verified_at,
                j.last_checked,
                cp.cp_tone,
                cp.cp_tone_sub,
                cp.cp_tone_eq,
                cp.cp_tone_sub_eq,
                cp.cp_tone_ratio,
                cp.cp_tone_sub_ratio,
                cp.cp_tone_est,
                cp.cp_tone_sub_est,
                cp.cp_tone_eq_est,
                cp.cp_tone_sub_eq_est
            FROM speakers s
            LEFT JOIN japan_market j ON s.id = j.speaker_id
            LEFT JOIN cost_performance cp ON s.id = cp.speaker_id
            WHERE {where_sql}
            ORDER BY {sort_col} IS NULL, {sort_col} {sort_order}, s.brand ASC
            LIMIT ? OFFSET ?
        """
        cursor.execute(query_sql, params + [limit, offset])
        rows = cursor.fetchall()

        items = []
        for r in rows:
            item = dict(r)
            try:
                item["reviews"] = json.loads(item["reviews_json"]) if item["reviews_json"] else []
            except Exception:
                item["reviews"] = []
            try:
                item["raw_data"] = json.loads(item["raw_json"]) if item["raw_json"] else {}
            except Exception:
                item["raw_data"] = {}
            del item["reviews_json"]
            del item["raw_json"]
            items.append(item)

        conn.close()

        self.send_json({
            "total": total_items,
            "page": page,
            "limit": limit,
            "items": items
        })

    def handle_update_market(self):
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len)
        try:
            payload = json.loads(post_body.decode("utf-8"))
        except Exception:
            self.send_error(400, "Invalid JSON payload")
            return

        speaker_id = payload.get("speaker_id")
        if not speaker_id:
            self.send_error(400, "speaker_id is required")
            return

        price_jpy = payload.get("price_jpy")
        price_type = payload.get("price_type", "pair")
        availability = payload.get("availability", "domestic_in_stock")
        verification_status = "unavailable" if availability == "not_available" else "verified"
        if availability == "not_available":
            price_jpy = None
        source_name = payload.get("source_name", "手動入力")
        source_url = payload.get("source_url", "")
        notes = payload.get("notes", "")
        is_manual = 1 if payload.get("is_manual_override", True) else 0

        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO japan_market (
                speaker_id, price_jpy, price_type, availability, source_name, source_url,
                is_manual_override, notes, verification_status, confidence_level, verified_at, last_checked
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'high', ?, ?)
            ON CONFLICT(speaker_id) DO UPDATE SET
                price_jpy = excluded.price_jpy,
                price_type = excluded.price_type,
                availability = excluded.availability,
                source_name = excluded.source_name,
                source_url = excluded.source_url,
                is_manual_override = excluded.is_manual_override,
                notes = excluded.notes,
                verification_status = excluded.verification_status,
                confidence_level = 'high',
                verified_at = excluded.verified_at,
                last_checked = excluded.last_checked
        """, (speaker_id, price_jpy, price_type, availability, source_name, source_url, is_manual, notes, verification_status, now, now))

        conn.commit()
        conn.close()

        # Re-compute cost performance
        update_cost_performance()

        self.send_json({"status": "success", "message": "Market data updated successfully"})

    def handle_get_verification_stats(self):
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM speakers")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM japan_market WHERE verification_status = 'verified'")
        verified = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM japan_market WHERE verification_status = 'needs_review'")
        needs_review = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM japan_market WHERE verification_status = 'unavailable'")
        unavailable = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM japan_market WHERE verification_status = 'unverified' OR verification_status IS NULL")
        unverified = cursor.fetchone()[0]

        conn.close()

        verified_rate = round(((verified + unavailable) / total * 100), 1) if total > 0 else 0

        self.send_json({
            "total": total,
            "verified": verified,
            "needs_review": needs_review,
            "unavailable": unavailable,
            "unverified": unverified,
            "progress_percent": verified_rate
        })

    def handle_get_verification_speakers(self, query):
        conn = get_db_connection()
        cursor = conn.cursor()

        status = query.get("status", ["all"])[0].strip()
        priority = query.get("priority", ["cpi_desc"])[0].strip()
        brand = query.get("brand", [""])[0].strip()
        search = query.get("search", [""])[0].strip()
        limit = int(query.get("limit", ["100"])[0])
        page = int(query.get("page", ["1"])[0])
        offset = (page - 1) * limit

        where_clauses = ["1=1"]
        params = []

        if status == "unverified":
            where_clauses.append("(j.verification_status = 'unverified' OR j.verification_status IS NULL)")
        elif status == "verified":
            where_clauses.append("j.verification_status = 'verified'")
        elif status == "needs_review":
            where_clauses.append("j.verification_status = 'needs_review'")
        elif status == "unavailable":
            where_clauses.append("j.verification_status = 'unavailable'")

        if brand:
            where_clauses.append("s.brand = ?")
            params.append(brand)

        if search:
            where_clauses.append("(s.brand LIKE ? OR s.model LIKE ? OR s.speaker_name LIKE ?)")
            term = f"%{search}%"
            params.extend([term, term, term])

        # 未確定機種は cp_tone が NULL になるため、検証キューでは為替換算の参考CPI(cp_tone_est)で優先度を付ける
        order_by_sql = "COALESCE(cp.cp_tone, cp.cp_tone_est) DESC NULLS LAST, s.score_tone DESC NULLS LAST"
        if priority == "score_desc":
            order_by_sql = "s.score_tone DESC NULLS LAST, COALESCE(cp.cp_tone, cp.cp_tone_est) DESC NULLS LAST"
        elif priority == "brand_asc":
            order_by_sql = "s.brand ASC, s.model ASC"
        elif priority == "cpi_desc":
            order_by_sql = "COALESCE(cp.cp_tone, cp.cp_tone_est) DESC NULLS LAST, s.score_tone DESC NULLS LAST"

        where_sql = " AND ".join(where_clauses)

        count_sql = f"""
            SELECT COUNT(*)
            FROM speakers s
            LEFT JOIN japan_market j ON s.id = j.speaker_id
            LEFT JOIN cost_performance cp ON s.id = cp.speaker_id
            WHERE {where_sql}
        """
        cursor.execute(count_sql, params)
        total_items = cursor.fetchone()[0]

        query_sql = f"""
            SELECT 
                s.id,
                s.brand,
                s.model,
                s.shape,
                s.energy_type,
                s.price_usd,
                s.amount_type,
                s.f3,
                s.flatness,
                s.score_tone,
                s.score_tone_sub,
                s.score_tone_eq,
                s.score_tone_sub_eq,
                CASE 
                    WHEN j.availability = 'not_available' OR j.verification_status = 'unavailable' THEN NULL
                    ELSE COALESCE(j.price_jpy, CAST(ROUND(s.price_usd * 155.0) AS INTEGER))
                END as effective_price_jpy,
                CASE 
                    WHEN j.availability = 'not_available' OR j.verification_status = 'unavailable' THEN NULL
                    ELSE j.price_jpy
                END as price_jpy,
                j.price_type,
                CASE 
                    WHEN j.availability = 'not_available' OR j.verification_status = 'unavailable' THEN NULL
                    ELSE j.price_each
                END as price_each,
                COALESCE(j.availability, 'unconfirmed') as availability,
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
                cp.cp_tone_est,
                cp.cp_tone_sub_est,
                cp.cp_tone_eq_est,
                cp.cp_tone_sub_eq_est
            FROM speakers s
            LEFT JOIN japan_market j ON s.id = j.speaker_id
            LEFT JOIN cost_performance cp ON s.id = cp.speaker_id
            WHERE {where_sql}
            ORDER BY {order_by_sql}
            LIMIT ? OFFSET ?
        """
        cursor.execute(query_sql, params + [limit, offset])
        rows = cursor.fetchall()

        items = []
        for r in rows:
            item = dict(r)
            item["suggested_keywords"] = generate_search_keywords(item["brand"], item["model"])
            items.append(item)

        conn.close()

        self.send_json({
            "total": total_items,
            "page": page,
            "limit": limit,
            "items": items
        })

    def handle_save_verification(self):
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len)
        try:
            payload = json.loads(post_body.decode("utf-8"))
        except Exception:
            self.send_error(400, "Invalid JSON payload")
            return

        speaker_id = payload.get("speaker_id")
        if not speaker_id:
            self.send_error(400, "speaker_id is required")
            return

        price_jpy = payload.get("price_jpy")
        if price_jpy is not None:
            try:
                price_jpy = int(price_jpy)
            except (ValueError, TypeError):
                price_jpy = None

        price_each = payload.get("price_each")
        if price_each is not None:
            try:
                price_each = int(price_each)
            except (ValueError, TypeError):
                price_each = None

        price_type = payload.get("price_type", "pair")
        availability = payload.get("availability", "domestic_in_stock")
        source_name = payload.get("source_name", "").strip() or "手動確認"
        source_url = payload.get("source_url", "").strip()
        search_keyword = payload.get("search_keyword", "").strip()
        verification_status = payload.get("verification_status", "verified")
        confidence_level = payload.get("confidence_level", "high")
        notes = payload.get("notes", "").strip()
        is_manual = 1

        # If domestic availability is unavailable or discontinued without pricing, clear prices
        if verification_status == "unavailable" or availability == "not_available":
            price_jpy = None
            price_each = None
            verification_status = "unavailable"
            availability = "not_available"

        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO japan_market (
                speaker_id, price_jpy, price_type, price_each, availability, source_name, source_url,
                search_keyword, verification_status, confidence_level, is_manual_override, notes,
                verified_at, last_checked
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(speaker_id) DO UPDATE SET
                price_jpy = excluded.price_jpy,
                price_type = excluded.price_type,
                price_each = excluded.price_each,
                availability = excluded.availability,
                source_name = excluded.source_name,
                source_url = excluded.source_url,
                search_keyword = excluded.search_keyword,
                verification_status = excluded.verification_status,
                confidence_level = excluded.confidence_level,
                is_manual_override = excluded.is_manual_override,
                notes = excluded.notes,
                verified_at = excluded.verified_at,
                last_checked = excluded.last_checked
        """, (
            speaker_id, price_jpy, price_type, price_each, availability, source_name, source_url,
            search_keyword, verification_status, confidence_level, is_manual, notes,
            now, now
        ))

        conn.commit()
        conn.close()

        # Re-compute cost performance
        update_cost_performance()

        # Fetch updated CP for immediate UI display
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT cp_tone FROM cost_performance WHERE speaker_id = ?", (speaker_id,))
        cp_row = cursor.fetchone()
        cp_tone = cp_row["cp_tone"] if cp_row else None
        conn.close()

        self.send_json({
            "status": "success",
            "message": "Verification saved successfully",
            "speaker_id": speaker_id,
            "cp_tone": cp_tone
        })

    def handle_trigger_update(self):
        success = perform_full_update()
        if success:
            self.send_json({"status": "success", "message": "Weekly update executed successfully"})
        else:
            self.send_json({"status": "error", "message": "Update encountered errors"}, 500)

    def handle_export_csv(self, query):
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                s.brand,
                s.model,
                s.shape,
                s.energy_type,
                s.price_usd,
                COALESCE(j.price_jpy, CAST(ROUND(s.price_usd * 155.0) AS INTEGER)) as price_jpy,
                j.availability,
                j.notes,
                s.f3,
                s.flatness,
                s.score_tone,
                s.score_tone_sub,
                s.score_tone_eq,
                s.score_tone_sub_eq,
                cp.cp_tone,
                cp.cp_tone_sub,
                cp.cp_tone_eq,
                cp.cp_tone_sub_eq
            FROM speakers s
            LEFT JOIN japan_market j ON s.id = j.speaker_id
            LEFT JOIN cost_performance cp ON s.id = cp.speaker_id
            ORDER BY s.score_tone DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Brand", "Model", "Shape", "Type", "Price (USD)", "Price (JPY)",
            "Availability", "Notes", "F3 (Hz)", "Flatness (dB)",
            "Tone", "Tone w/Sub", "Tone w/EQ", "Tone w/Both",
            "CP Tone", "CP w/Sub", "CP w/EQ", "CP w/Both"
        ])
        for r in rows:
            writer.writerow(list(r))

        csv_bytes = output.getvalue().encode("utf-8-sig")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="spinorama_jpy_export.csv"')
        self.send_header("Content-Length", str(len(csv_bytes)))
        self.end_headers()
        self.wfile.write(csv_bytes)

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def run_server():
    cfg = load_config()
    preferred_port = int(cfg.get("server_port", 8550))
    start_scheduler_background()
    
    port = preferred_port
    max_tries = 10
    httpd = None
    for i in range(max_tries):
        try:
            httpd = ReusableTCPServer(("", port), SpinoramaAPIHandler)
            break
        except OSError:
            print(f"Port {port} in use, trying next port...")
            port += 1

    if not httpd:
        print(f"Error: Could not bind to any port between {preferred_port} and {preferred_port + max_tries}")
        sys.exit(1)

    import socket
    hostname = socket.gethostname()
    print(f"============================================================")
    print(f"  Spinorama JPY Server running on: http://{hostname}:{port}")
    print(f"============================================================")
    with open(os.path.join(os.path.dirname(CONFIG_PATH), "data", "active_port.txt"), "w") as f:
        f.write(str(port))
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
