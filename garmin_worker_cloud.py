"""
garmin_worker_cloud.py — Garmin sync for GitHub Actions.

Uses stored tokens from Turso DB (no password needed).
Run: python garmin_worker_cloud.py [--dias 7] [--usuario 1]
"""
import os
import sys
import argparse
from datetime import datetime

# Allow imports from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.db.db_manager import get_db_connection
from src.garmin.garmin_sync import (
    cargar_sesion_tokens,
    sincronizar_todo_con_sesion,
)


def _usuarios_con_tokens(user_id=None):
    """Return users that have garmin_tokens stored in DB."""
    conn = get_db_connection()
    try:
        if user_id is not None:
            rows = conn.execute(
                "SELECT id, nombre, email_garmin FROM usuarios "
                "WHERE id=? AND garmin_tokens IS NOT NULL AND garmin_tokens != ''",
                (int(user_id),),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, nombre, email_garmin FROM usuarios "
                "WHERE garmin_tokens IS NOT NULL AND garmin_tokens != ''",
            ).fetchall()
    finally:
        conn.close()
    return [{"id": int(r[0]), "nombre": r[1], "email": r[2]} for r in rows]


def run_sync(user_id=None, dias=7):
    inicio = datetime.now()
    users = _usuarios_con_tokens(user_id=user_id)

    if not users:
        print("No hay usuarios con tokens Garmin almacenados en BD.")
        print("Ejecuta el login desde tu máquina local primero:")
        print("  python scripts/garmin_login_once.py")
        return 1

    print(f"[{inicio:%Y-%m-%d %H:%M:%S}] Sincronizando {len(users)} usuario(s) con tokens almacenados...")
    errores = 0

    for user in users:
        uid = user["id"]
        nombre = user["nombre"] or f"usuario_{uid}"
        email = user.get("email")
        print(f"\n→ Usuario {uid} ({nombre})...")

        try:
            gc = cargar_sesion_tokens(email, usuario_id=uid)
            if gc is None:
                print(f"  ✗ No se pudieron cargar los tokens de BD.")
                errores += 1
                continue

            result = sincronizar_todo_con_sesion(gc, uid, dias=dias)
            act = result.get("actividades", 0)
            bio = result.get("dias_bio", 0)
            sueno = result.get("dias_sueno", 0)
            print(f"  ✓ {act} actividades, {bio} días biométricos, {sueno} días sueño")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            errores += 1

    fin = datetime.now()
    duracion = (fin - inicio).total_seconds()
    print(f"\n[{fin:%Y-%m-%d %H:%M:%S}] Completado en {duracion:.1f}s. Errores: {errores}")
    return errores


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Garmin Cloud Sync Worker")
    parser.add_argument("--dias", type=int, default=7, help="Días a sincronizar")
    parser.add_argument("--usuario", type=int, default=None, help="ID de usuario específico")
    args = parser.parse_args()

    exit_code = run_sync(user_id=args.usuario, dias=args.dias)
    sys.exit(0 if exit_code == 0 else 1)
