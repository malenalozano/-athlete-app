#!/usr/bin/env python3
"""Test libsql-client connection and verify data in Turso"""

import os
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("TURSO_DATABASE_URL")
TOKEN = os.getenv("TURSO_AUTH_TOKEN")

if not URL or not TOKEN:
    print("❌ TURSO_DATABASE_URL or TURSO_AUTH_TOKEN not set")
    exit(1)

try:
    from libsql_client import create_client
    
    # Normalize URL for libsql_client
    turso_url = URL
    if turso_url.startswith("libsql://"):
        turso_url = "https://" + turso_url[len("libsql://"):]
    
    print(f"🔗 Connecting to Turso: {turso_url[:50]}...")
    
    # Create client with correct parameters
    client = create_client(url=turso_url, auth_token=TOKEN)
    
    print("✅ Connected to Turso!\n")
    
    # Query 1: Usuarios
    print("📋 Usuarios en Turso:")
    result = client.execute("SELECT id, nombre, objetivo_tipo FROM usuarios ORDER BY id")
    if result and hasattr(result, 'rows'):
        for row in result.rows:
            print(f"  ID {row[0]}: {row[1]} | objetivo_tipo={row[2]}")
    else:
        print(f"  {result}")
    
    # Query 2: Actividades por usuario
    print("\n📊 Actividades Garmin por usuario:")
    result = client.execute("SELECT COUNT(*) as cnt, usuario_id FROM actividades_garmin GROUP BY usuario_id ORDER BY usuario_id")
    if result and hasattr(result, 'rows'):
        for row in result.rows:
            print(f"  usuario_id={row[1]}: {row[0]} actividades")
    
    # Query 3: Datos biométricos
    print("\n💪 Datos biométricos por usuario:")
    result = client.execute("SELECT COUNT(*) as cnt, usuario_id FROM datos_biometricos_premium GROUP BY usuario_id ORDER BY usuario_id")
    if result and hasattr(result, 'rows'):
        for row in result.rows:
            print(f"  usuario_id={row[1]}: {row[0]} registros")
    
    # Query 4: Datos de sueño
    print("\n😴 Datos de sueño por usuario:")
    result = client.execute("SELECT COUNT(*) as cnt, usuario_id FROM datos_sueno GROUP BY usuario_id ORDER BY usuario_id")
    if result and hasattr(result, 'rows'):
        for row in result.rows:
            print(f"  usuario_id={row[1]}: {row[0]} registros")
    
    print("\n✅ Query test successful!")
    
except ImportError as e:
    print(f"❌ libsql-client not available: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
