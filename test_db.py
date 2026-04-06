#!/usr/bin/env python3
"""Quick database integrity check"""
import sqlite3
from src.db.db_manager import get_db_connection

# Test connection
conn = get_db_connection()
cursor = conn.cursor()

# Check tables and data
print("\n=== DATABASE STATUS ===\n")

tables_to_check = [
    ("datos_biometricos_premium", ["usuario_id", "fecha", "sleep_score", "fc_reposo", "carga_aguda", "carga_cronica"]),
    ("datos_sueno", ["usuario_id", "fecha", "score", "sleep_profundo_horas"]),
]

for table_name, expected_cols in tables_to_check:
    print(f"\n[{table_name}]")
    try:
        # Check if table exists and columns
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = {row[1]: row[2] for row in cursor.fetchall()}

        missing = [c for c in expected_cols if c not in cols]
        if missing:
            print(f"  ❌ MISSING COLUMNS: {missing}")
        else:
            print(f"  ✅ All expected columns present")

        # Count rows
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  Rows: {count}")

        if count > 0:
            # Show sample
            cols_str = ", ".join(expected_cols[:3])
            cursor.execute(f"SELECT {cols_str} FROM {table_name} LIMIT 1")
            sample = cursor.fetchone()
            print(f"  Sample: {sample}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")

conn.close()
print("\n=== END ===\n")
