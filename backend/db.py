import sqlite3
import os
import json
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "spinorama_jpy.db")

def get_db_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS speakers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        speaker_key TEXT UNIQUE,
        speaker_name TEXT,
        brand TEXT NOT NULL,
        model TEXT NOT NULL,
        shape TEXT,
        energy_type TEXT,
        price_usd REAL,
        amount_type TEXT,
        default_measurement TEXT,
        measurement_quality TEXT,
        f3 REAL,
        f6 REAL,
        flatness REAL,
        score_tone REAL,
        score_tone_sub REAL,
        score_tone_eq REAL,
        score_tone_sub_eq REAL,
        reviews_json TEXT,
        raw_json TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS japan_market (
        speaker_id INTEGER PRIMARY KEY REFERENCES speakers(id) ON DELETE CASCADE,
        price_jpy INTEGER,
        price_type TEXT DEFAULT 'pair',
        availability TEXT DEFAULT 'unconfirmed',
        source_name TEXT,
        source_url TEXT,
        is_manual_override INTEGER DEFAULT 0,
        notes TEXT,
        verification_status TEXT DEFAULT 'unverified',
        confidence_level TEXT DEFAULT 'low',
        search_keyword TEXT,
        price_each INTEGER,
        verified_at TIMESTAMP,
        last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cost_performance (
        speaker_id INTEGER PRIMARY KEY REFERENCES speakers(id) ON DELETE CASCADE,
        cp_tone REAL,
        cp_tone_sub REAL,
        cp_tone_eq REAL,
        cp_tone_sub_eq REAL,
        cp_tone_ratio REAL,
        cp_tone_sub_ratio REAL,
        cp_tone_eq_ratio REAL,
        cp_tone_sub_eq_ratio REAL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        speaker_id INTEGER REFERENCES speakers(id) ON DELETE CASCADE,
        price_jpy INTEGER,
        availability TEXT,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS update_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_type TEXT,
        status TEXT,
        message TEXT,
        items_processed INTEGER,
        started_at TIMESTAMP,
        finished_at TIMESTAMP
    );
    """)

    # Run safe migrations for existing tables
    migrate_japan_market_columns(cursor)

    conn.commit()
    conn.close()
    print(f"Database initialized and verified at {DB_PATH}")

def migrate_japan_market_columns(cursor):
    cursor.execute("PRAGMA table_info(japan_market);")
    existing_cols = {row[1] for row in cursor.fetchall()}
    
    new_cols = [
        ("verification_status", "TEXT DEFAULT 'unverified'"),
        ("confidence_level", "TEXT DEFAULT 'low'"),
        ("search_keyword", "TEXT"),
        ("price_each", "INTEGER"),
        ("verified_at", "TIMESTAMP")
    ]
    
    for col_name, col_def in new_cols:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE japan_market ADD COLUMN {col_name} {col_def};")
            print(f"Added column {col_name} to japan_market.")
    
    # Existing manual overrides should default to verified status
    cursor.execute("""
        UPDATE japan_market 
        SET verification_status = 'verified', 
            confidence_level = 'high',
            verified_at = CURRENT_TIMESTAMP
        WHERE is_manual_override = 1 
          AND (verification_status IS NULL OR verification_status = 'unverified')
    """)
    
    # Items with availability not_available can default to unavailable status
    cursor.execute("""
        UPDATE japan_market 
        SET verification_status = 'unavailable'
        WHERE availability = 'not_available' 
          AND (verification_status IS NULL OR verification_status = 'unverified')
    """)

if __name__ == "__main__":
    init_db()
