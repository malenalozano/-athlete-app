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
    if os.path.exists(token_home) and os.listdir(token_home):
        print(f"Tokens existentes en {token_home} — verificando...")
        try:
            from garminconnect import Garmin
            gc = Garmin()
            gc.garth.load(token_home)
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
        gc.garth.dump(token_home)
        name = gc.get_full_name()
        print(f"✓ Tokens guardados en {token_home}")
        print(f"✓ Sesión activa como: {name}")
        print("La app ya no necesita hacer login de nuevo.")
    except Exception as e:
        msg = str(e)
        if "429" in msg:
            print("ERROR: Garmin bloqueo el intento (429 Too Many Requests).")
            print("Espera 30-60 minutos sin intentar nada y vuelve a ejecutar este script.")
        elif "Authentication" in msg or "auth" in msg.lower():
            print(f"ERROR de autenticacion: {msg}")
            print("Comprueba que el email y password sean correctos.")
        else:
            print(f"ERROR inesperado: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
