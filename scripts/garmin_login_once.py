"""
scripts/garmin_login_once.py
Ejecutar UNA SOLA VEZ desde terminal para guardar tokens OAuth de Garmin.
Después la app nunca vuelve a hacer login con credenciales.

Uso:
    cd athlete-performance-tracker
    .venv/Scripts/activate          (Windows)
    python scripts/garmin_login_once.py
"""

import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

GARTH_HOME = os.path.expanduser("~/.garth_athlete")


def _safe_email_slug(email: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "_", str(email or "").strip().lower())


def _token_home_for_email(email: str) -> str:
    return os.path.join(GARTH_HOME, _safe_email_slug(email))


def main():
    print("=== Login único Garmin ===")
    print(f"Directorio base de tokens: {GARTH_HOME}\n")

    # Intentar leer credenciales de BD primero
    try:
        from src.db.db_manager import obtener_credenciales_garmin
        from src.core.seguridad import desencriptar_password
        creds = obtener_credenciales_garmin(1)
        if creds and creds[0] and creds[1]:
            usuario = creds[0]
            password = desencriptar_password(creds[1])
            print(f"Usando credenciales guardadas: {usuario}")
        else:
            usuario = input("Email Garmin: ").strip()
            password = input("Password: ").strip()
    except Exception:
        usuario = input("Email Garmin: ").strip()
        password = input("Password: ").strip()

    print("Conectando con Garmin... (puede tardar 10-30 seg)\n")

    token_home = _token_home_for_email(usuario)

    # Comprobar si ya hay tokens válidos para esta cuenta
    from pathlib import Path
    token_file = Path(token_home) / "garmin_tokens.json"
    if token_file.exists():
        print(f"Tokens existentes en {token_home} — verificando...")
        try:
            from garminconnect import Garmin
            gc = Garmin()
            gc.client.load(token_home)
            if gc.client.is_authenticated:
                name = gc.get_full_name()
                print(f"✓ Tokens válidos. Sesión activa como: {name}")
                print("No es necesario volver a hacer login.")
                return
        except Exception:
            print("Tokens expirados o inválidos — haciendo login fresco...\n")

    try:
        from garminconnect import Garmin
        gc = Garmin(email=usuario, password=password)
        gc.login()
        os.makedirs(token_home, exist_ok=True)
        gc.client.dump(token_home)
        name = gc.get_full_name()
        print(f"✓ Tokens guardados en DISCO: {token_home}")
        print(f"✓ Sesión activa como: {name}")

        # IMPORTANTE: Guardar también en BD para que funcione en Cloud
        try:
            from src.db.db_manager import get_db_connection
            conn = get_db_connection()
            token_json = gc.client.dumps()
            conn.execute(
                "UPDATE usuarios SET garmin_tokens=? WHERE email_garmin=?",
                (token_json, usuario)
            )
            conn.commit()
            conn.close()
            print(f"✓ Tokens guardados en BASE DE DATOS (Turso)")
            print("\n✅ SUCCESS: Tokens guardados en disco Y BD.")
            print("   La app en Cloud podrá usar estos tokens sin volver a hacer login.")
        except Exception as e:
            print(f"\n⚠️  No se pudo guardar en BD: {e}")
            print("   (Los tokens se guardaron en disco, pero no en Cloud)")
            
    except Exception as e:
        msg = str(e)
        if "429" in msg:
            print("❌ ERROR: Garmin bloqueó el intento (429 Too Many Requests).")
            print("⏱️  Espera 30-60 minutos sin intentar nada y vuelve a ejecutar este script.")
        elif "Authentication" in msg or "auth" in msg.lower():
            print(f"❌ ERROR de autenticación: {msg}")
            print("   Comprueba que el email y password sean correctos.")
        else:
            print(f"❌ ERROR inesperado: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
