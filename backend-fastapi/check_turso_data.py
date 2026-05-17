"""
Inspecciona el Turso existente para ver qué datos hay.
Uso: Pon TURSO_DATABASE_URL y TURSO_AUTH_TOKEN en .env y ejecuta:
  python check_turso_data.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database import TursoHTTPConnection, get_db
from config import settings

TABLES = [
    "usuarios", "actividades_garmin", "plan_entrenamiento",
    "datos_biometricos_premium", "datos_sueno", "diario_fisiologia",
    "sesiones_fuerza", "ejercicios_biblioteca", "historial_ciclos_menstruales",
]

def check():
    if not settings.turso_database_url or not settings.turso_auth_token:
        print("ERROR: Pon TURSO_DATABASE_URL y TURSO_AUTH_TOKEN en backend-fastapi/.env")
        sys.exit(1)

    turso = TursoHTTPConnection(settings.turso_database_url, settings.turso_auth_token)
    print(f"Conectado a: {settings.turso_database_url}\n")

    for table in TABLES:
        try:
            rows = turso.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            count = rows[0] if rows else 0
            if count > 0:
                sample = turso.execute(f"SELECT * FROM {table} LIMIT 1").fetchone()
                print(f"  {table}: {count} filas  | ejemplo: {sample}")
            else:
                print(f"  {table}: VACÍA")
        except Exception as e:
            print(f"  {table}: NO EXISTE ({e})")

if __name__ == "__main__":
    check()
