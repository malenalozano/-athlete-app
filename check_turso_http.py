#!/usr/bin/env python3
"""Query Turso via HTTP directly to check if data was migrated"""

import os
import json
import base64
import sqlite3
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("TURSO_DATABASE_URL")
TOKEN = os.getenv("TURSO_AUTH_TOKEN")

print("=" * 70)
print("TURSO DATA CHECK VIA HTTP")
print("=" * 70)

if not URL or not TOKEN:
    print("❌ TURSO_DATABASE_URL or TURSO_AUTH_TOKEN not set")
    exit(1)

try:
    import httpx
    
    # Normalize URL
    turso_url = URL
    if turso_url.startswith("libsql://"):
        turso_url = "https://" + turso_url[len("libsql://"):]
    
    print(f"🔗 Turso URL: {turso_url}")
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }
    
    # Query: Get usuario count
    queries = [
        ("SELECT COUNT(*) as cnt FROM usuarios", "Total usuarios"),
        ("SELECT COUNT(*) as cnt FROM actividades_garmin", "Total actividades"),
        ("SELECT COUNT(*) as cnt FROM actividades_garmin WHERE usuario_id=1", "Actividades usuario_id=1"),
        ("SELECT COUNT(*) as cnt FROM actividades_garmin WHERE usuario_id=2", "Actividades usuario_id=2"),
        ("SELECT COUNT(*) as cnt FROM datos_biometricos_premium", "Total datos biométricos"),
        ("SELECT COUNT(*) as cnt FROM datos_biometricos_premium WHERE usuario_id=1", "Biométricos usuario_id=1"),
        ("SELECT COUNT(*) as cnt FROM datos_biometricos_premium WHERE usuario_id=2", "Biométricos usuario_id=2"),
    ]
    
    for sql, label in queries:
        payload = {
            "statements": [
                {
                    "q": {
                        "sql": sql
                    }
                }
            ]
        }
        
        try:
            response = httpx.post(
                f"{turso_url}/v2/pipeline",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("results") and len(data["results"]) > 0:
                    rows = data["results"][0].get("response", {}).get("result", {}).get("rows", [])
                    if rows:
                        count = rows[0][0] if rows[0] else 0
                        print(f"  ✓ {label}: {count}")
                    else:
                        print(f"  ✗ {label}: No rows")
                else:
                    print(f"  ✗ {label}: No results")
            else:
                print(f"  ✗ {label}: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ✗ {label}: {e}")
    
except ImportError:
    print("❌ httpx not available, trying with requests...")
    
    try:
        import requests
        
        turso_url = URL
        if turso_url.startswith("libsql://"):
            turso_url = "https://" + turso_url[len("libsql://"):]
        
        print(f"🔗 Turso URL: {turso_url}")
        
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        }
        
        sql_query = "SELECT COUNT(*) FROM usuarios"
        payload = {
            "statements": [{"q": {"sql": sql_query}}]
        }
        
        response = requests.post(
            f"{turso_url}/v2/pipeline",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"❌ Error with requests: {e}")

# Compare with local
print("\n" + "=" * 70)
print("LOCAL DB DATA:")
print("=" * 70)

try:
    conn = sqlite3.connect("atleta.db")
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM usuarios")
    print(f"  ✓ Usuarios en local: {c.fetchone()[0]}")
    
    c.execute("SELECT COUNT(*) FROM actividades_garmin")
    print(f"  ✓ Actividades en local: {c.fetchone()[0]}")
    
    c.execute("SELECT COUNT(*) FROM actividades_garmin WHERE usuario_id=1")
    print(f"  ✓ Actividades usuario_id=1 (local): {c.fetchone()[0]}")
    
    c.execute("SELECT COUNT(*) FROM actividades_garmin WHERE usuario_id=2")
    print(f"  ✓ Actividades usuario_id=2 (local): {c.fetchone()[0]}")
    
    conn.close()
except Exception as e:
    print(f"❌ Error checking local DB: {e}")
