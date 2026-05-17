"""
Migra la base de datos SQLite local a Turso.
Uso:
  1. Pon TURSO_DATABASE_URL y TURSO_AUTH_TOKEN en tu .env
  2. python migrate_to_turso.py
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

LOCAL_DB = "atleta.db"

TABLES = [
    "usuarios",
    "actividades_garmin",
    "diario_fisiologia",
    "plan_entrenamiento",
    "sesiones_fuerza",
    "ejercicios_fuerza",
    "datos_biometricos_premium",
    "datos_sueno",
    "ejercicios_biblioteca",
    "historial_ejercicio",
    "historial_ciclos_menstruales",
    "lesiones",
]


def val_to_sql(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def migrate():
    from database import TursoHTTPConnection, init_db
    from config import settings

    if not settings.turso_database_url or not settings.turso_auth_token:
        print("ERROR: Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in .env first")
        sys.exit(1)

    local = sqlite3.connect(LOCAL_DB)
    local.row_factory = sqlite3.Row
    turso = TursoHTTPConnection(settings.turso_database_url, settings.turso_auth_token)

    # Init schema on Turso
    print("Initializing Turso schema...")
    init_db()

    for table in TABLES:
        rows = local.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  {table}: empty, skipping")
            continue

        cols = [d[0] for d in local.execute(f"SELECT * FROM {table} LIMIT 0").description]
        cols_str = ", ".join(cols)

        inserted = 0
        errors = 0
        for row in rows:
            vals = ", ".join(val_to_sql(row[c]) for c in cols)
            sql = f"INSERT OR IGNORE INTO {table} ({cols_str}) VALUES ({vals})"
            try:
                turso.execute(sql)
                inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"    ERR: {e}")

        print(f"  {table}: {inserted} rows inserted, {errors} errors")

    local.close()
    print("\nMigration complete!")


if __name__ == "__main__":
    migrate()
