"""
migrate_local_to_turso.py
Migra todos los datos del SQLite local (atleta.db) a Turso Cloud.
Usa INSERT OR REPLACE para no perder datos existentes en Turso.
Ejecutar: python scripts/migrate_local_to_turso.py
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Cargar variables de entorno / secrets
from dotenv import load_dotenv
load_dotenv()

try:
    import libsql as libsql_sqlite3
except ImportError:
    print("ERROR: libsql no instalado. Ejecuta: pip install libsql")
    sys.exit(1)

LOCAL_DB = "atleta.db"
TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# Intentar también desde secrets.toml si dotenv no lo encuentra
if not TURSO_URL:
    try:
        import toml
        secrets = toml.load(".streamlit/secrets.toml")
        TURSO_URL = secrets.get("TURSO_DATABASE_URL")
        TURSO_TOKEN = secrets.get("TURSO_AUTH_TOKEN")
    except Exception:
        pass

if not TURSO_URL or not TURSO_TOKEN:
    print("ERROR: TURSO_DATABASE_URL o TURSO_AUTH_TOKEN no encontrados.")
    print("Asegúrate de que .streamlit/secrets.toml está configurado.")
    sys.exit(1)

print(f"Conectando a: {TURSO_URL[:50]}...")

# --- Tablas y sus columnas (en el orden correcto para INSERT OR REPLACE) ---
# Para tablas con UNIQUE(usuario_id, fecha) usamos INSERT OR REPLACE
# Para usuarios usamos INSERT OR REPLACE también (incluye credenciales Garmin)

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


def get_columns(conn, table):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r[1] for r in rows]


def table_exists_turso(turso, table):
    try:
        turso.execute(f"SELECT 1 FROM {table} LIMIT 1")
        return True
    except Exception:
        return False


def migrate():
    local = sqlite3.connect(LOCAL_DB)
    local.row_factory = sqlite3.Row
    turso = libsql_sqlite3.connect(TURSO_URL, auth_token=TURSO_TOKEN)

    total_migrated = 0

    for table in TABLES:
        # Verificar que la tabla existe en local
        exists_local = local.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists_local:
            print(f"  SKIP {table} (no existe en local)")
            continue

        # Verificar que la tabla existe en Turso
        if not table_exists_turso(turso, table):
            print(f"  SKIP {table} (no existe en Turso — ejecuta la app primero para crear tablas)")
            continue

        rows = local.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  SKIP {table} (vacía)")
            continue

        cols_local = get_columns(local, table)

        # Obtener columnas que existen en Turso también
        try:
            cols_turso_rows = turso.execute(f"PRAGMA table_info({table})").fetchall()
            cols_turso = [r[1] for r in cols_turso_rows]
        except Exception as e:
            print(f"  ERROR obteniendo columnas de {table} en Turso: {e}")
            continue

        # Usar solo columnas presentes en ambas
        common_cols = [c for c in cols_local if c in cols_turso]
        col_indices = [cols_local.index(c) for c in common_cols]

        placeholders = ", ".join(["?" for _ in common_cols])
        col_list = ", ".join(common_cols)
        sql = f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})"

        inserted = 0
        errors = 0
        for row in rows:
            values = tuple(row[i] for i in col_indices)
            try:
                turso.execute(sql, values)
                inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"    WARN fila en {table}: {e}")

        try:
            turso.commit()
        except Exception as e:
            print(f"  WARN commit {table}: {e}")

        status = f"✅ {table}: {inserted} filas migradas"
        if errors:
            status += f" ({errors} errores)"
        print(status)
        total_migrated += inserted

    local.close()
    print(f"\n{'='*50}")
    print(f"Migración completada: {total_migrated} filas en total")


if __name__ == "__main__":
    migrate()
