import argparse
from datetime import datetime

from db_manager import get_db_connection
from garmin_sync import sincronizar_actividades_inteligente, sincronizar_biometricos_garmin
from seguridad import desencriptar_password


def _usuarios_con_credenciales(user_id=None):
    conn = get_db_connection()
    try:
        if user_id is None:
            rows = conn.execute(
                """
                SELECT id, nombre, email_garmin, password_garmin_enc
                FROM usuarios
                WHERE email_garmin IS NOT NULL
                  AND email_garmin != ''
                  AND password_garmin_enc IS NOT NULL
                  AND password_garmin_enc != ''
                ORDER BY id
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, nombre, email_garmin, password_garmin_enc
                FROM usuarios
                WHERE id = ?
                  AND email_garmin IS NOT NULL
                  AND email_garmin != ''
                  AND password_garmin_enc IS NOT NULL
                  AND password_garmin_enc != ''
                """,
                (int(user_id),),
            ).fetchall()
    finally:
        conn.close()

    users = []
    for row in rows:
        users.append(
            {
                "id": int(row[0]),
                "nombre": row[1] or f"usuario_{row[0]}",
                "email": row[2],
                "password_enc": row[3],
            }
        )
    return users


def ejecutar_worker(user_id=None, dias=7, num_actividades=20):
    inicio = datetime.now()
    users = _usuarios_con_credenciales(user_id=user_id)
    if not users:
        print("No hay usuarios con credenciales Garmin configuradas.")
        return 0

    print(f"[{inicio:%Y-%m-%d %H:%M:%S}] Iniciando sync Garmin para {len(users)} usuario(s)...")
    errores = 0

    for user in users:
        uid = user["id"]
        nombre = user["nombre"]
        try:
            password = desencriptar_password(user["password_enc"])
        except Exception as exc:
            errores += 1
            print(f"- Usuario {uid} ({nombre}): no se pudo desencriptar la clave ({exc}).")
            continue

        try:
            n_act = sincronizar_actividades_inteligente(
                user["email"],
                password,
                uid,
                num_actividades=num_actividades,
            )
            n_bio = sincronizar_biometricos_garmin(
                user["email"],
                password,
                uid,
                dias=dias,
            )
            print(f"- Usuario {uid} ({nombre}): OK -> actividades={n_act}, biometria_dias={n_bio}")
        except Exception as exc:
            errores += 1
            print(f"- Usuario {uid} ({nombre}): ERROR -> {exc}")

    fin = datetime.now()
    duracion = (fin - inicio).total_seconds()
    print(f"[{fin:%Y-%m-%d %H:%M:%S}] Sync finalizada en {duracion:.1f}s. Errores: {errores}")
    return errores


def main():
    parser = argparse.ArgumentParser(description="Worker de sincronizacion Garmin desacoplado de Streamlit")
    parser.add_argument("--user-id", type=int, default=None, help="Sincroniza solo este usuario")
    parser.add_argument("--dias", type=int, default=7, help="Dias de biometria a sincronizar")
    parser.add_argument("--actividades", type=int, default=20, help="Numero de actividades recientes")
    args = parser.parse_args()

    errores = ejecutar_worker(
        user_id=args.user_id,
        dias=max(1, int(args.dias)),
        num_actividades=max(1, int(args.actividades)),
    )
    raise SystemExit(1 if errores else 0)


if __name__ == "__main__":
    main()
