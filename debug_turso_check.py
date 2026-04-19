#!/usr/bin/env python3
"""DEBUG: Verificar qué datos hay en Turso vs local DB"""

import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

try:
    import libsql as libsql_sqlite3
except Exception as e:
    print(f"⚠️ libsql error: {e}")
    libsql_sqlite3 = None

try:
    from libsql_client import create_client
except Exception as e:
    print(f"⚠️ libsql_client error: {e}")
    create_client = None

URL = os.getenv("TURSO_DATABASE_URL")
TOKEN = os.getenv("TURSO_AUTH_TOKEN")
LOCAL_DB = "atleta.db"

print("=" * 60)
print("VERIFICACIÓN: Datos en LOCAL DB vs TURSO")
print("=" * 60)

# 1. LOCAL DB
print("\n📁 LOCAL DB (atleta.db):")
print("-" * 60)
try:
    conn_local = sqlite3.connect(LOCAL_DB)
    c = conn_local.cursor()
    
    # Usuarios
    c.execute("SELECT id, nombre, objetivo_tipo FROM usuarios ORDER BY id")
    usuarios = c.fetchall()
    print(f"\n✓ Usuarios (local):")
    for row in usuarios:
        print(f"  ID {row[0]}: {row[1]} | objetivo_tipo={row[2]}")
    
    # Actividades Garmin
    c.execute("SELECT COUNT(*), usuario_id FROM actividades_garmin GROUP BY usuario_id")
    acts = c.fetchall()
    print(f"\n✓ Actividades Garmin (local):")
    for count, uid in acts:
        print(f"  usuario_id={uid}: {count} actividades")
    
    conn_local.close()
except Exception as e:
    print(f"❌ Error leyendo local DB: {e}")

# 2. TURSO DB
print("\n☁️  TURSO DB:")
print("-" * 60)

if URL and TOKEN:
    try:
        # Intentar con libsql primero
        if libsql_sqlite3:
            print("Usando libsql...")
            conn_turso = libsql_sqlite3.connect(URL, auth_token=TOKEN)
        elif create_client:
            print("Usando libsql_client...")
            # Normalizar URL para libsql-client
            turso_url = URL
            if turso_url.startswith("libsql://"):
                turso_url = "https://" + turso_url[len("libsql://"):]
            
            client = create_client(database_url=turso_url, auth_token=TOKEN)
            # libsql_client necesita queries async, vamos a hacer una consulta simple
            try:
                result = client.execute("SELECT id, nombre, objetivo_tipo FROM usuarios ORDER BY id")
                print(f"\n✓ Usuarios (Turso):")
                if hasattr(result, 'rows'):
                    for row in result.rows:
                        print(f"  ID {row[0]}: {row[1]} | objetivo_tipo={row[2]}")
                else:
                    print(f"  {result}")
            except Exception as e:
                print(f"Error querying: {e}")
            exit(0)
        else:
            raise Exception("No libsql libraries available")
        
        # Usuarios
        c = conn_turso.cursor()
        c.execute("SELECT id, nombre, objetivo_tipo FROM usuarios ORDER BY id")
        usuarios = c.fetchall()
        print(f"\n✓ Usuarios (Turso):")
        for row in usuarios:
            print(f"  ID {row[0]}: {row[1]} | objetivo_tipo={row[2]}")
        
        # Actividades
        c.execute("SELECT COUNT(*), usuario_id FROM actividades_garmin GROUP BY usuario_id")
        acts = c.fetchall()
        print(f"\n✓ Actividades Garmin (Turso):")
        for count, uid in acts:
            print(f"  usuario_id={uid}: {count} actividades")
        
        # Datos biométricos
        c.execute("SELECT COUNT(*), usuario_id FROM datos_biometricos_premium GROUP BY usuario_id")
        bios = c.fetchall()
        print(f"\n✓ Datos Biométricos (Turso):")
        for count, uid in bios:
            print(f"  usuario_id={uid}: {count} registros")
        
        conn_turso.close()
    except Exception as e:
        print(f"❌ Error leyendo Turso: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"❌ TURSO URL o TOKEN no configurados")
    print(f"  URL: {URL}")
    print(f"  TOKEN: {'*' * 20 if TOKEN else 'Not set'}")

print("\n" + "=" * 60)
