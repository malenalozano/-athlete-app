#!/usr/bin/env python3
"""
Verificador periódico de tokens Garmin.
Ejecutar regularmente (ej: cron job) para validar y refrescar tokens expirados.

Uso:
    python scripts/check_garmin_tokens.py           # Verifica ambos usuarios
    python scripts/check_garmin_tokens.py --usuario 1  # Solo usuario 1
    python scripts/check_garmin_tokens.py --fix      # Auto-regenera tokens inválidos
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

_BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend-fastapi")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

GARTH_HOME = os.path.expanduser("~/.garth_athlete")


def get_db():
    """Obtiene conexión a la BD del backend."""
    from database import get_db as db_get
    return db_get()


def check_token_validity(usuario_id: int) -> dict:
    """Verifica si un token es válido sin hacer cambios.
    
    Devuelve dict con:
        - valid: bool
        - name: str (nombre del usuario si es válido)
        - error: str (si no es válido)
        - token_age_days: int (aproximado)
    """
    try:
        from garminconnect import Garmin
    except ImportError:
        return {"valid": False, "error": "garminconnect no instalado"}

    try:
        conn = get_db()
        row = conn.execute(
            "SELECT nombre, garmin_tokens, email_garmin FROM usuarios WHERE id = ?",
            (usuario_id,)
        ).fetchone()
        conn.close()

        if not row or not row[1]:  # row[1] es garmin_tokens
            return {
                "valid": False,
                "error": "No hay tokens guardados",
                "name": row[0] if row else "N/A"
            }

        name = row[0]
        email = row[2]

        # Intentar cargar cliente desde tokens
        gc = Garmin()
        if hasattr(gc, "garth") and gc.garth is not None:
            store = gc.garth
        elif hasattr(gc, "client") and gc.client is not None:
            store = gc.client
        else:
            return {"valid": False, "error": "Versión desconocida de garminconnect", "name": name}

        store.loads(row[1])
        
        # Probar con get_full_name (no gasta cuota, solo valida token)
        try:
            full_name = gc.get_full_name()
            return {
                "valid": True,
                "name": name,
                "email": email,
                "display_name": full_name
            }
        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "Authentication failed" in err_str:
                return {
                    "valid": False,
                    "error": "Token expirado (401)",
                    "name": name,
                    "email": email
                }
            elif "Display name" in err_str:
                # Este es un warning, no error crítico
                return {
                    "valid": True,
                    "name": name,
                    "email": email,
                    "warning": "Perfil incompleto en Garmin (sin display name)"
                }
            else:
                raise e

    except Exception as e:
        return {
            "valid": False,
            "error": f"{type(e).__name__}: {str(e)[:100]}",
            "name": name if 'name' in locals() else "N/A"
        }


def regenerate_token(usuario_id: int) -> bool:
    """Regenera token ejecutando el script de login.
    
    Devuelve True si éxito, False si fallo.
    """
    login_script = Path(__file__).parent / "garmin_login_once.py"
    if not login_script.exists():
        logger.error(f"Script de login no encontrado: {login_script}")
        return False

    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, str(login_script), "--usuario", str(usuario_id), "--force"],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            logger.info(f"Token regenerado exitosamente para usuario {usuario_id}")
            return True
        else:
            logger.error(f"Fallo regenerar token usuario {usuario_id}: {result.stderr[:200]}")
            return False
    except Exception as e:
        logger.error(f"Error ejecutando script de login: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Verificador de tokens Garmin")
    parser.add_argument("--usuario", type=int, default=None, help="ID de usuario (si no especifica, revisa ambos)")
    parser.add_argument("--fix", action="store_true", help="Auto-regenera tokens inválidos")
    args = parser.parse_args()

    usuarios = [args.usuario] if args.usuario else [1, 2]

    all_valid = True
    results = []

    for uid in usuarios:
        print(f"\n{'='*60}")
        print(f"Verificando usuario {uid}...")
        print('='*60)

        result = check_token_validity(uid)
        results.append((uid, result))

        if result["valid"]:
            print(f"✅ Token válido")
            print(f"   Nombre: {result.get('display_name', 'N/A')}")
            print(f"   Email: {result.get('email', 'N/A')}")
            if result.get("warning"):
                print(f"   ⚠️  {result['warning']}")
        else:
            print(f"❌ Token inválido")
            print(f"   Error: {result.get('error', 'Desconocido')}")
            print(f"   Usuario: {result.get('name', 'N/A')}")
            all_valid = False

            if args.fix:
                print(f"\n🔄 Intentando regenerar token...")
                if regenerate_token(uid):
                    print(f"✅ Token regenerado. Verificando...")
                    result2 = check_token_validity(uid)
                    if result2["valid"]:
                        print(f"✅ Verificación exitosa después de regenerar")
                    else:
                        print(f"❌ Token sigue inválido: {result2.get('error')}")
                else:
                    print(f"❌ No se pudo regenerar token")

    print(f"\n{'='*60}")
    print("RESUMEN")
    print('='*60)

    for uid, result in results:
        status = "✅" if result["valid"] else "❌"
        print(f"{status} Usuario {uid}: {result.get('display_name', result.get('name', 'N/A'))}")

    if all_valid:
        print("\n✅ Todos los tokens son válidos")
        return 0
    else:
        print("\n❌ Algunos tokens necesitan atención")
        return 1


if __name__ == "__main__":
    sys.exit(main())
