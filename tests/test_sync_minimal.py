#!/usr/bin/env python3
"""
Script MINIMALISTA que simula exactamente lo que app.py hace cuando presionas "Sincronizar Biométricos"
"""

import sys
import logging
from pathlib import Path
from getpass import getpass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Setup logging (igual a la app real)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s | %(levelname)-8s | %(message)s'
)

# Importar exactamente lo que usa app.py
from src.garmin.garmin_sync import sincronizar_biometricos_garmin, iniciar_sesion_garmin, obtener_datos_sueno
from src.db.db_manager import obtener_credenciales_garmin
from src.core.seguridad import desencriptar_password
from datetime import datetime, timedelta

def main():
    print("\n" + "="*80)
    print("PRUEBA DE SINCRONIZACIÓN - SIMULANDO app.py".center(80))
    print("="*80 + "\n")
    
    # Opción 1: Usar credenciales guardadas
    print("Opciones:")
    print("  1. Leer credenciales del usuario 1 en BD (si existen)")
    print("  2. Ingresar credenciales nuevas")
    
    opcion = input("\nElige una opción (1 o 2): ").strip() or "2"
    
    if opcion == "1":
        try:
            cred = obtener_credenciales_garmin(1)
            if cred and cred[0]:
                email, p_enc = cred
                print(f"\n✓ Credenciales encontradas para: {email}")
                pw = desencriptar_password(p_enc)
                usuario_id = 1
            else:
                print("✗ No hay credenciales guardadas para usuario 1")
                return
        except Exception as e:
            print(f"✗ Error al leer credenciales: {e}")
            return
    else:
        email = input("\n📧 Email Garmin: ").strip()
        pw = getpass("🔐 Contraseña Garmin: ")
        usuario_id = input("👤 Usuario ID (default=1): ").strip() or "1"
        try:
            usuario_id = int(usuario_id)
        except:
            usuario_id = 1
    
    if not email or not pw:
        print("\n❌ Email o contraseña vacíos")
        sys.exit(1)
    
    # ESTO ES LO QUE HACE app.py (línea 4406)
    print(f"\n{'='*80}")
    print(f"Sincronizando de Garmin para usuario_id={usuario_id}...")
    print(f"{'='*80}\n")
    
    try:
        # Esta es la línea exacta de app.py que falla
        n_bio = sincronizar_biometricos_garmin(email, pw, usuario_id, dias=7)
        
        print(f"\n{'='*80}")
        print(f"✅ ÉXITO: {n_bio} días procesados".center(80))
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ ERROR: {e}".center(80))
        print(f"{'='*80}")
        import traceback
        print("\nDetalles técnicos:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Cancelado por el usuario")
        sys.exit(0)
