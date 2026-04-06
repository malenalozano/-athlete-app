"""
migrate_via_http.py
Migra datos del SQLite local a Turso usando la API HTTP de Turso.
No requiere libsql. Ejecutar: python scripts/migrate_via_http.py
"""
import sqlite3
import sys
import os
import urllib.request
import urllib.error
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

LOCAL_DB = "atleta.db"

# Leer credenciales de secrets.toml
try:
    import tomllib
    with open(".streamlit/secrets.toml", "rb") as f:
        secrets = tomllib.load(f)
except Exception:
    try:
        import toml
        secrets = toml.load(".streamlit/secrets.toml")
    except Exception:
        secrets = {}

TURSO_URL = os.getenv("TURSO_DATABASE_URL") or secrets.get("TURSO_DATABASE_URL", "")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN") or secrets.get("TURSO_AUTH_TOKEN", "")

if not TURSO_URL or not TURSO_TOKEN:
    print("ERROR: TURSO_DATABASE_URL o TURSO_AUTH_TOKEN no encontrados.")
    sys.exit(1)

# Convertir URL libsql:// a https://
http_url = TURSO_URL.replace("libsql://", "https://")
api_url = f"{http_url}/v2/pipeline"

print(f"Turso endpoint: {http_url[:60]}...")


def turso_execute_batch(statements: list[str]) -> dict:
    """Ejecuta un batch de statements SQL via HTTP API de Turso."""
    payload = {
        "requests": [
            {"type": "execute", "stmt": {"sql": sql}}
            for sql in statements
        ] + [{"type": "close"}]
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=data,
        headers={
            "Authorization": f"Bearer {TURSO_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP {e.code}: {body[:200]}")
        return {}


def escape(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"


TABLES = [
    "usuarios",
    "actividades_garmin",
    "diario_fisiologia",
    "plan_entrenamiento",
    "sesiones_fuerza",
    "ejercicios_fuerza",
    "datos_biometricos_premium",
    "historial_lesiones",
    "datos_sueno",
    "ejercicios_biblioteca",
    "historial_ejercicio",
    "ejercicios_por_defecto",
    "lesiones",
]

BATCH_SIZE = 20  # statements per HTTP request


def migrate():
    local = sqlite3.connect(LOCAL_DB)
    local.row_factory = sqlite3.Row

    total = 0
    for table in TABLES:
        exists = local.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            continue

        rows = local.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  SKIP {table} (vacía)")
            continue

        cols = [d[0] for d in local.execute(f"SELECT * FROM {table} LIMIT 0").description]
        col_list = ", ".join(cols)

        statements = []
        for row in rows:
            vals = ", ".join(escape(row[c]) for c in cols)
            statements.append(
                f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({vals})"
            )

        # Send in batches
        errors = 0
        inserted = 0
        for i in range(0, len(statements), BATCH_SIZE):
            batch = statements[i : i + BATCH_SIZE]
            result = turso_execute_batch(batch)
            results = result.get("results", [])
            for r in results:
                if r.get("type") == "error":
                    errors += 1
                    if errors <= 2:
                        print(f"    ERROR en {table}: {r.get('error', {}).get('message', '?')[:100]}")
                else:
                    inserted += 1

        status = f"  {'OK' if not errors else 'WARN'} {table}: {inserted}/{len(rows)} migradas"
        if errors:
            status += f" ({errors} errores)"
        print(status)
        total += inserted

    local.close()
    print(f"\n{'='*50}")
    print(f"Migración completada: {total} inserts enviados a Turso")


if __name__ == "__main__":
    migrate()
