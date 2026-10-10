#!/usr/bin/env python3
"""
AI Agent Verification Helper CLI
Allows autonomous AI agents to easily inspect unverified speakers,
run targeted market research, and reliably save verified findings into the database.
"""

import os
import sys
import json
import argparse
import sqlite3
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.append(CURRENT_DIR)

from db import get_db_connection
from cost_perf_engine import update_cost_performance

def generate_search_keywords(brand: str, model: str):
    return [
        f"{brand} {model} 価格",
        f"{brand} {model} ペア 価格",
        f"{brand} {model} サウンドハウス",
        f"{brand} {model} 価格.com",
        f"{brand} {model} Amazon 日本"
    ]

def get_unverified_speakers(limit=10, priority="cpi_desc", brand=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    order_sql = "cp.cp_tone DESC NULLS LAST, s.score_tone DESC NULLS LAST"
    if priority == "score_desc":
        order_sql = "s.score_tone DESC NULLS LAST"
    elif priority == "brand_asc":
        order_sql = "s.brand ASC, s.model ASC"

    where_clauses = ["(j.verification_status = 'unverified' OR j.verification_status IS NULL OR j.verification_status = 'needs_review')"]
    params = []

    if brand:
        where_clauses.append("s.brand = ?")
        params.append(brand)

    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT 
            s.id,
            s.brand,
            s.model,
            s.shape,
            s.energy_type,
            s.price_usd,
            s.amount_type,
            s.score_tone,
            s.score_tone_sub,
            s.score_tone_eq,
            s.score_tone_sub_eq,
            j.price_jpy,
            j.price_type,
            j.price_each,
            COALESCE(j.availability, 'unconfirmed') as availability,
            COALESCE(j.verification_status, 'unverified') as verification_status,
            j.source_name,
            j.source_url,
            j.notes,
            cp.cp_tone
        FROM speakers s
        LEFT JOIN japan_market j ON s.id = j.speaker_id
        LEFT JOIN cost_performance cp ON s.id = cp.speaker_id
        WHERE {where_sql}
        ORDER BY {order_sql}
        LIMIT ?
    """
    cursor.execute(query, params + [limit])
    rows = cursor.fetchall()

    items = []
    for r in rows:
        item = dict(r)
        item["search_queries"] = generate_search_keywords(item["brand"], item["model"])
        items.append(item)

    conn.close()
    return items

def get_single_speaker(speaker_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            s.id,
            s.brand,
            s.model,
            s.shape,
            s.energy_type,
            s.price_usd,
            s.amount_type,
            s.score_tone,
            s.score_tone_sub,
            s.score_tone_eq,
            s.score_tone_sub_eq,
            j.price_jpy,
            j.price_type,
            j.price_each,
            COALESCE(j.availability, 'unconfirmed') as availability,
            COALESCE(j.verification_status, 'unverified') as verification_status,
            j.source_name,
            j.source_url,
            j.notes,
            cp.cp_tone
        FROM speakers s
        LEFT JOIN japan_market j ON s.id = j.speaker_id
        LEFT JOIN cost_performance cp ON s.id = cp.speaker_id
        WHERE s.id = ?
    """
    cursor.execute(query, (speaker_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    item = dict(row)
    item["search_queries"] = generate_search_keywords(item["brand"], item["model"])
    return item

def save_verified_result(data: dict):
    speaker_id = data.get("speaker_id")
    if not speaker_id:
        raise ValueError("speaker_id is required")

    availability = data.get("availability", "domestic_in_stock")
    verification_status = data.get("verification_status", "verified")
    is_unavailable = verification_status == "unavailable" or availability == "not_available"

    if is_unavailable:
        price_jpy = None
        price_each = None
        availability = "not_available"
        verification_status = "unavailable"
    else:
        price_jpy = data.get("price_jpy")
        price_each = data.get("price_each")

        if price_jpy is not None:
            price_jpy = int(price_jpy)
        if price_each is not None:
            price_each = int(price_each)

        # Auto-compute if one is missing and price_type is given
        price_type = data.get("price_type", "pair")
        if price_jpy is None and price_each is not None:
            price_jpy = price_each * 2
        elif price_each is None and price_jpy is not None:
            price_each = round(price_jpy / 2)

    price_type = data.get("price_type", "pair")
    source_name = data.get("source_name", "AIエージェント調査").strip()
    source_url = data.get("source_url", "").strip()
    search_keyword = data.get("search_keyword", "").strip()
    confidence_level = data.get("confidence_level", "high" if is_unavailable or price_jpy else "medium")
    notes = data.get("notes", "").strip()
    is_manual = 1

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

    # Recalculate cost performance models
    update_cost_performance()

    # Return updated speaker
    updated = get_single_speaker(speaker_id)
    return updated

def main():
    parser = argparse.ArgumentParser(description="Agent Verifier CLI for Spinorama JPY")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command: list
    list_p = subparsers.add_parser("list", help="List unverified speakers")
    list_p.add_argument("--limit", type=int, default=5, help="Number of speakers to fetch")
    list_p.add_argument("--priority", choices=["cpi_desc", "score_desc", "brand_asc"], default="cpi_desc")
    list_p.add_argument("--brand", type=str, default=None, help="Filter by brand")

    # Command: get
    get_p = subparsers.add_parser("get", help="Get single speaker details by ID")
    get_p.add_argument("speaker_id", type=int, help="Speaker ID")

    # Command: save
    save_p = subparsers.add_parser("save", help="Save verification result")
    save_p.add_argument("--json", type=str, help="JSON string or path to JSON file containing findings")

    args = parser.parse_args()

    if args.command == "list":
        items = get_unverified_speakers(limit=args.limit, priority=args.priority, brand=args.brand)
        print(json.dumps({"count": len(items), "speakers": items}, ensure_ascii=False, indent=2))

    elif args.command == "get":
        item = get_single_speaker(args.speaker_id)
        if not item:
            print(json.dumps({"error": f"Speaker ID {args.speaker_id} not found"}, ensure_ascii=False))
            sys.exit(1)
        print(json.dumps(item, ensure_ascii=False, indent=2))

    elif args.command == "save":
        if not args.json:
            # Try reading from stdin
            raw_input = sys.stdin.read().strip()
        else:
            if os.path.exists(args.json):
                with open(args.json, "r", encoding="utf-8") as f:
                    raw_input = f.read().strip()
            else:
                raw_input = args.json.strip()

        try:
            data = json.loads(raw_input)
        except Exception as e:
            print(json.dumps({"error": f"Invalid JSON: {e}"}, ensure_ascii=False))
            sys.exit(1)

        try:
            res = save_verified_result(data)
            print(json.dumps({"status": "success", "result": res}, ensure_ascii=False, indent=2))
        except Exception as e:
            print(json.dumps({"error": f"Failed to save: {e}"}, ensure_ascii=False))
            sys.exit(1)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
