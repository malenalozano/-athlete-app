#!/usr/bin/env python3
"""
Script de prueba SIMPLE para sincronización de Garmin.
Utiliza el código mejorado con logging detallado.
"""

import sys
import logging
from getpass import getpass
from pathlib import Path

# Añadir la carpeta actual al path para poder importar módulos locales
sys.path.insert(0, str(Path(__file__).parent))

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(name)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('garmin_sync_test.log')  # También guardar en archivo
    ]
)

from garmin_sync import sincronizar_biometricos_garmin

def main():
    print("\n" + "="*80)
    print("TEST DE SINCRONIZACIÓN DE DATOS BIOMÉTRICOS GARMIN".center(80))
    print("="*80 + "\n")
    
    # Solicitar credenciales
    email = input("📧 Email Garmin: ").strip()
    password = getpass("🔐 Contraseña Garmin: ")
    
    if not email or not password:
        print("\n❌ Email o contraseña no proporcionados")
        sys.exit(1)
    
    usuario_id = input("👤 ID de usuario (default=1): ").strip() or "1"
    try:
        usuario_id = int(usuario_id)
    except ValueError:
        print("❌ ID de usuario inválido")
        sys.exit(1)
    
    dias = input("📅 Número de días a sincronizar (default=7): ").strip() or "7"
    try:
        dias = int(dias)
    except ValueError:
        print("❌ Número de días inválido")
        sys.exit(1)
    
    print(f"\n{'='*80}")
    print(f"Iniciando sincronización...")
    print(f"  Email: {email}")
    print(f"  Usuario ID: {usuario_id}")
    print(f"  Días: {dias}")
    print(f"{'='*80}\n")
    
    try:
        resultado = sincronizar_biometricos_garmin(email, password, usuario_id, dias=dias)
        print(f"\n{'='*80}")
        print(f"✅ SINCRONIZACIÓN EXITOSA: {resultado} días importados")
        print(f"{'='*80}")
        print(f"\n📝 Detalles disponibles en: garmin_sync_test.log")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ ERROR DURANTE LA SINCRONIZACIÓN: {e}")
        print(f"{'='*80}")
        print(f"\n📝 Revisa garmin_sync_test.log para más detalles")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Cancelado por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
