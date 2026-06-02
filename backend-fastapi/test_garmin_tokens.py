"""Test rápido de carga de tokens Garmin. Ejecutar: python test_garmin_tokens.py"""
import sys
sys.path.insert(0, '.')
from database import get_db

try:
    from garminconnect import Garmin
except ImportError:
    print("ERROR: garminconnect no instalado")
    sys.exit(1)

conn = get_db()

for uid in [1, 2]:
    print(f"\n=== Usuario {uid} ===")
    row = conn.execute("SELECT garmin_tokens, nombre FROM usuarios WHERE id=?", (uid,)).fetchone()
    if not row:
        print("  No encontrado en BD")
        continue

    nombre, tokens = row[1], row[0]
    print(f"  Nombre: {nombre}")
    print(f"  Tokens len: {len(tokens) if tokens else 0}")

    if not tokens:
        print("  SIN TOKENS")
        continue

    try:
        gc = Garmin()
        has_client = hasattr(gc, "client") and gc.client is not None
        has_garth = hasattr(gc, "garth") and gc.garth is not None
        print(f"  Garmin() attrs: has_client={has_client}, has_garth={has_garth}")

        if has_garth:
            store = gc.garth
            store_name = "garth"
        elif has_client:
            store = gc.client
            store_name = "client"
        else:
            print("  ERROR: ni .client ni .garth disponibles")
            continue

        print(f"  Usando store: {store_name}")
        store.loads(tokens)
        print("  store.loads() OK")

        is_auth = getattr(store, "is_authenticated", "N/A")
        print(f"  is_authenticated: {is_auth}")

        if is_auth is False:
            print("  --> TOKENS EXPIRADOS o inválidos")
            continue

        print("  Probando get_activities(0, 3)...")
        try:
            acts = gc.get_activities(0, 3)
            print(f"  get_activities OK: {len(acts)} actividades")
            for a in acts[:3]:
                fecha = a.get("startTimeLocal", "?")[:10]
                tipo = (a.get("activityType") or {}).get("typeKey", "?")
                print(f"    - {fecha} | {tipo}")
        except Exception as e:
            print(f"  get_activities ERROR: {e}")

        print("  Probando get_stats('2026-05-26')...")
        try:
            stats = gc.get_stats("2026-05-26")
            keys = list((stats or {}).keys())[:5]
            print(f"  get_stats OK: keys={keys}")
        except Exception as e:
            print(f"  get_stats ERROR: {e}")

    except Exception as e:
        print(f"  EXCEPCION CARGANDO CLIENT: {e}")

conn.close()
print("\nFin del test.")
