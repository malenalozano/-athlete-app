"""
scripts/garmin_login_once.py
Ejecutar UNA SOLA VEZ desde terminal para guardar tokens OAuth de Garmin.
DespuÃ©s la app nunca vuelve a hacer login con credenciales.

Uso:
    cd athlete-performance-tracker
    .venv/Scripts/activate          (Windows)
    python scripts/garmin_login_once.py
"""

import os
import sys
import re
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

GARTH_HOME = os.path.expanduser("~/.garth_athlete")
BLOCKADE_FILE = os.path.expanduser("~/.garth_athlete/.blockade.json")
_BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend-fastapi")
# URL del backend en producciÃ³n (Railway). Puede sobreescribirse con variable de entorno.
_API_URL = os.environ.get("ATHLETE_API_URL", "https://athlete-app-production-78ff.up.railway.app")


def _get_backend_db():
    """Obtiene conexiÃ³n a la BD del backend (Turso o SQLite local)."""
    # Cargar .env de backend-fastapi para obtener credenciales de Turso
    env_file = os.path.join(_BACKEND_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
    if _BACKEND_DIR not in sys.path:
        sys.path.insert(0, _BACKEND_DIR)
    from database import get_db
    return get_db()


def _safe_email_slug(email: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "_", str(email or "").strip().lower())


def _token_home_for_email(email: str) -> str:
    return os.path.join(GARTH_HOME, _safe_email_slug(email))


def _token_store(gc):
    """Compatibilidad entre garminconnect con backend `garth` o `client`."""
    if hasattr(gc, "garth") and getattr(gc, "garth", None) is not None:
        return gc.garth
    if hasattr(gc, "client") and getattr(gc, "client", None) is not None:
        return gc.client
    return None


def _check_blockade():
    """Verifica si hay un bloqueo 429 activo y cuÃ¡nto tiempo queda."""
    if not os.path.exists(BLOCKADE_FILE):
        return None
    
    try:
        with open(BLOCKADE_FILE, 'r') as f:
            data = json.load(f)
        
        blocked_until = data.get('blocked_until')
        if not blocked_until:
            return None
        
        blocked_until_dt = datetime.fromisoformat(blocked_until)
        now = datetime.now()
        
        if now < blocked_until_dt:
            remaining = blocked_until_dt - now
            return {
                'blocked': True,
                'remaining_seconds': remaining.total_seconds(),
                'remaining_hours': remaining.total_seconds() / 3600,
                'blocked_until': blocked_until
            }
        else:
            # Bloqueo ha expirado
            os.remove(BLOCKADE_FILE)
            return None
    except Exception as e:
        print(f"âš ï¸  Error verificando bloqueo: {e}")
        return None


def _save_blockade(hours=48):
    """Guarda informaciÃ³n de bloqueo por N horas."""
    blocked_until = datetime.now() + timedelta(hours=hours)
    os.makedirs(GARTH_HOME, exist_ok=True)
    
    try:
        with open(BLOCKADE_FILE, 'w') as f:
            json.dump({
                'blocked_until': blocked_until.isoformat(),
                'reason': '429 Too Many Requests from Garmin',
                'created_at': datetime.now().isoformat()
            }, f)
        print(f"ðŸ“Œ Bloqueo registrado hasta: {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"âš ï¸  No se pudo guardar bloqueo: {e}")


def _clear_blockade():
    """Limpia el registro de bloqueo."""
    if os.path.exists(BLOCKADE_FILE):
        try:
            os.remove(BLOCKADE_FILE)
        except Exception:
            pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Login Ãºnico Garmin")
    parser.add_argument("--usuario", type=int, default=None, help="ID de usuario (1=Malena, 2=Dani)")
    parser.add_argument("--force", action="store_true", help="Forzar un login fresco aunque existan tokens en disco")
    args = parser.parse_args()

    usuario_id = args.usuario

    print("=== Login Ãºnico Garmin ===")
    print(f"Directorio base de tokens: {GARTH_HOME}\n")

    # Verificar si hay bloqueo activo
    blockade = _check_blockade()
    if blockade and blockade['blocked']:
        hours = int(blockade['remaining_hours'])
        minutes = int((blockade['remaining_hours'] % 1) * 60)
        print("âŒ CUENTA BLOQUEADA POR GARMIN (error 429)")
        print(f"\nâ³ Tiempo restante de bloqueo:")
        print(f"   {hours}h {minutes}m (hasta {blockade['blocked_until']})\n")
        print("ðŸ“ Acciones permitidas:")
        print("   â€¢ Esperar el tiempo indicado arriba")
        print("   â€¢ NO intentar login de nuevo (alargarÃ­a el bloqueo)")
        print("   â€¢ Puedes usar la app en Cloud mientras tienes tokens guardados\n")
        print("ðŸ”„ Cuando haya pasado el tiempo, vuelve a ejecutar este script:")
        print("   python scripts/garmin_login_once.py")
        return

    # Si se especificÃ³ usuario, leer sus credenciales de la BD del backend
    if usuario_id is not None:
        try:
            conn = _get_backend_db()
            row = conn.execute(
                "SELECT email_garmin, password_garmin_enc FROM usuarios WHERE id = ?",
                (usuario_id,)
            ).fetchone()
            conn.close()
            if row and row[0] and row[1]:
                usuario = row[0]
                password = row[1]
                print(f"Usando credenciales de usuario {usuario_id}: {usuario}")
            else:
                print(f"No hay credenciales guardadas para usuario {usuario_id}.")
                usuario = input("Email Garmin: ").strip()
                password = input("Password: ").strip()
        except Exception as e:
            print(f"No se pudo leer BD: {e}")
            usuario = input("Email Garmin: ").strip()
            password = input("Password: ").strip()
    else:
        # Intentar leer credenciales de BD primero (usuario 1 por defecto)
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

    # Comprobar si ya hay tokens vÃ¡lidos para esta cuenta
    from pathlib import Path
    token_file = Path(token_home) / "garmin_tokens.json"
    if token_file.exists() and not args.force:
        print(f"Tokens existentes en {token_home} â€” verificando...")
        try:
            from garminconnect import Garmin
            gc = Garmin()
            store = _token_store(gc)
            if store is None:
                raise RuntimeError("No se encontrÃ³ backend de tokens en Garmin")
            store.load(token_home)
            name = gc.get_full_name()
            print(f"âœ“ Tokens vÃ¡lidos. SesiÃ³n activa como: {name}")
            print("No es necesario volver a hacer login.")
            _clear_blockade()  # Si llegamos aquÃ­, el bloqueo ha pasado
            return
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                print("âš ï¸  Los tokens guardados tampoco funcionan (Garmin sigue bloqueado).")
                print("Garmin estÃ¡ bloqueando TODAS las peticiones desde esta IP.")
                hours = 24
                print(f"\nâ³ Se requiere esperar al menos {hours} horas mÃ¡s...")
                _save_blockade(hours=hours)
                return
            print("Tokens expirados o invÃ¡lidos â€” haciendo login fresco...\n")
    elif args.force:
        print("Forzando login fresco, ignorando tokens existentes en disco...\n")

    def _prompt_mfa():
        print("\nðŸ” Garmin requiere verificaciÃ³n adicional.")
        print("   Si usas la app 'Garmin Connect' en el mÃ³vil:")
        print("   â†’ Abre la app â†’ aprueba la notificaciÃ³n push â†’ pulsa ENTER aquÃ­.")
        print("   Si recibes un cÃ³digo por email/SMS:")
        print("   â†’ EscrÃ­belo aquÃ­ y pulsa ENTER.")
        code = input("   CÃ³digo MFA (o ENTER si aprobaste por app): ").strip()
        return code if code else "0"  # garth necesita un valor no vacÃ­o

    try:
        from garminconnect import Garmin
        gc = Garmin(email=usuario, password=password, prompt_mfa=_prompt_mfa)
        gc.login()
        os.makedirs(token_home, exist_ok=True)
        store = _token_store(gc)
        if store is None:
            raise RuntimeError("No se encontrÃ³ backend de tokens en Garmin")
        store.dump(token_home)
        name = gc.get_full_name()
        print(f"âœ“ Tokens guardados en DISCO: {token_home}")
        print(f"âœ“ SesiÃ³n activa como: {name}")

        # IMPORTANTE: Guardar tokens directamente en la BD (Turso)
        token_json = store.dumps()
        uid = usuario_id if usuario_id is not None else 1
        db_ok = False
        try:
            conn_db = _get_backend_db()
            conn_db.execute(
                "UPDATE usuarios SET garmin_tokens = ? WHERE id = ?",
                (token_json, uid),
            )
            conn_db.commit()
            conn_db.close()
            db_ok = True
            print(f"âœ“ Tokens guardados directamente en BD (usuario {uid})")
            print("\nâœ… SUCCESS: Tokens en disco y en BD. La app Cloud puede sincronizar Garmin.")
            _clear_blockade()
        except Exception as db_err:
            print(f"\nâš ï¸  No se pudo guardar en BD directamente: {db_err}")

        # Intento secundario: subir vÃ­a API HTTP (si hay URL configurada)
        if not db_ok:
            try:
                payload = json.dumps({"tokens_json": token_json}).encode("utf-8")
                req_http = urllib.request.Request(
                    f"{_API_URL}/garmin/{uid}/upload-tokens",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req_http, timeout=15) as resp:
                    json.loads(resp.read())
                print(f"âœ“ Tokens subidos vÃ­a API ({_API_URL})")
                _clear_blockade()
            except Exception as e:
                print(f"âš ï¸  Tampoco se pudieron subir vÃ­a API: {e}")
                print(f"   Configura ATHLETE_API_URL con la URL de tu backend Render.")
            
    except Exception as e:
        msg = str(e)
        if "429" in msg or "Too Many Requests" in msg:
            print("âŒ ERROR: Garmin bloqueÃ³ el intento (429 Too Many Requests).")
            print("\nðŸš« Garmin ha detectado mÃºltiples intentos fallidos.")
            print("   Esto ocurre cuando:")
            print("   â€¢ Se intenta login demasiadas veces en poco tiempo")
            print("   â€¢ Hay mÃºltiples aplicaciones con la misma cuenta")
            print("   â€¢ La IP estÃ¡ siendo bloqueada (especialmente en Cloud)")
            
            # Guardar bloqueo por 48 horas por defecto
            _save_blockade(hours=48)
            
            print("\nðŸ“ QUÃ‰ HACER:")
            print("   1. NO intentes ejecutar este script de nuevo aÃºn")
            print("   2. Espera 48 horas completas")
            print("   3. Vuelve a ejecutar (despuÃ©s del tiempo):")
            print("      python scripts/garmin_login_once.py")
            print("\nðŸ’¡ Nota: Si usas la app de Garmin oficial o conectas desde otro lado,")
            print("   puede afectar este bloqueo. Cierra sesiones extras si es posible.")
        elif "Authentication Application" in msg or "Unexpected title" in msg:
            print(f"âŒ ERROR: Garmin usa autenticaciÃ³n por app push y el cÃ³digo no llegÃ³.")
            print("   Soluciones:")
            print("   1. Vuelve a ejecutar el script y aprueba la notificaciÃ³n push en la app Garmin Connect")
            print("      ANTES de pulsar ENTER cuando pregunte por el cÃ³digo.")
            print("   2. O cambia el mÃ©todo MFA en garmin.com â†’ Cuenta â†’ Seguridad â†’ usa Email/SMS en vez de App.")
        elif "Authentication" in msg or "auth" in msg.lower():
            print(f"âŒ ERROR de autenticaciÃ³n: {msg}")
            print("   Comprueba que el email y password sean correctos.")
        else:
            print(f"âŒ ERROR inesperado: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()

