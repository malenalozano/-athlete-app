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
import json
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

GARTH_HOME = os.path.expanduser("~/.garth_athlete")
BLOCKADE_FILE = os.path.expanduser("~/.garth_athlete/.blockade.json")


def _safe_email_slug(email: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "_", str(email or "").strip().lower())


def _token_home_for_email(email: str) -> str:
    return os.path.join(GARTH_HOME, _safe_email_slug(email))


def _check_blockade():
    """Verifica si hay un bloqueo 429 activo y cuánto tiempo queda."""
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
        print(f"⚠️  Error verificando bloqueo: {e}")
        return None


def _save_blockade(hours=48):
    """Guarda información de bloqueo por N horas."""
    blocked_until = datetime.now() + timedelta(hours=hours)
    os.makedirs(GARTH_HOME, exist_ok=True)
    
    try:
        with open(BLOCKADE_FILE, 'w') as f:
            json.dump({
                'blocked_until': blocked_until.isoformat(),
                'reason': '429 Too Many Requests from Garmin',
                'created_at': datetime.now().isoformat()
            }, f)
        print(f"📌 Bloqueo registrado hasta: {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"⚠️  No se pudo guardar bloqueo: {e}")


def _clear_blockade():
    """Limpia el registro de bloqueo."""
    if os.path.exists(BLOCKADE_FILE):
        try:
            os.remove(BLOCKADE_FILE)
        except Exception:
            pass


def main():
    print("=== Login único Garmin ===")
    print(f"Directorio base de tokens: {GARTH_HOME}\n")

    # Verificar si hay bloqueo activo
    blockade = _check_blockade()
    if blockade and blockade['blocked']:
        hours = int(blockade['remaining_hours'])
        minutes = int((blockade['remaining_hours'] % 1) * 60)
        print("❌ CUENTA BLOQUEADA POR GARMIN (error 429)")
        print(f"\n⏳ Tiempo restante de bloqueo:")
        print(f"   {hours}h {minutes}m (hasta {blockade['blocked_until']})\n")
        print("📍 Acciones permitidas:")
        print("   • Esperar el tiempo indicado arriba")
        print("   • NO intentar login de nuevo (alargaría el bloqueo)")
        print("   • Puedes usar la app en Cloud mientras tienes tokens guardados\n")
        print("🔄 Cuando haya pasado el tiempo, vuelve a ejecutar este script:")
        print("   python scripts/garmin_login_once.py")
        return

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
            gc.garth.load(token_home)
            name = gc.get_full_name()
            print(f"✓ Tokens válidos. Sesión activa como: {name}")
            print("No es necesario volver a hacer login.")
            _clear_blockade()  # Si llegamos aquí, el bloqueo ha pasado
            return
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                print("⚠️  Los tokens guardados tampoco funcionan (Garmin sigue bloqueado).")
                print("Garmin está bloqueando TODAS las peticiones desde esta IP.")
                hours = 24
                print(f"\n⏳ Se requiere esperar al menos {hours} horas más...")
                _save_blockade(hours=hours)
                return
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
            _clear_blockade()  # Éxito: limpiar bloqueo si lo había
        except Exception as e:
            print(f"\n⚠️  No se pudo guardar en BD: {e}")
            print("   (Los tokens se guardaron en disco, pero no en Cloud)")
            
    except Exception as e:
        msg = str(e)
        if "429" in msg or "Too Many Requests" in msg:
            print("❌ ERROR: Garmin bloqueó el intento (429 Too Many Requests).")
            print("\n🚫 Garmin ha detectado múltiples intentos fallidos.")
            print("   Esto ocurre cuando:")
            print("   • Se intenta login demasiadas veces en poco tiempo")
            print("   • Hay múltiples aplicaciones con la misma cuenta")
            print("   • La IP está siendo bloqueada (especialmente en Cloud)")
            
            # Guardar bloqueo por 48 horas por defecto
            _save_blockade(hours=48)
            
            print("\n📍 QUÉ HACER:")
            print("   1. NO intentes ejecutar este script de nuevo aún")
            print("   2. Espera 48 horas completas")
            print("   3. Vuelve a ejecutar (después del tiempo):")
            print("      python scripts/garmin_login_once.py")
            print("\n💡 Nota: Si usas la app de Garmin oficial o conectas desde otro lado,")
            print("   puede afectar este bloqueo. Cierra sesiones extras si es posible.")
        elif "Authentication" in msg or "auth" in msg.lower():
            print(f"❌ ERROR de autenticación: {msg}")
            print("   Comprueba que el email y password sean correctos.")
        else:
            print(f"❌ ERROR inesperado: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
