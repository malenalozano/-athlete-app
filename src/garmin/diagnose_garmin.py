#!/usr/bin/env python3
"""
Verifica que todas las funciones clave de garmin_sync.py se pueden importar correctamente.
Comprueba que el logger está bien configurado.
Revisa que las funciones principales usan el logger para registrar información y errores.
Comprueba que la base de datos tiene las tablas necesarias y muestra si faltan.
"""

import sys
import inspect
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*80)
print("DIAGNÓSTICO DEL CÓDIGO DE SINCRONIZACIÓN GARMIN".center(80))
print("="*80 + "\n")

# Verificar importaciones
print("1️⃣  VERIFICANDO IMPORTACIONES...")
try:
    from garmin_sync import (
        sincronizar_biometricos_garmin,
        _extract_daily_metrics,
        _safe_api_call,
        iniciar_sesion_garmin,
        obtener_datos_sueno,
        guardar_metricas_premium_db,
        _extract_sleep_metrics,
        logger
    )
    print("   ✅ Todas las funciones importadas correctamente")
except ImportError as e:
    print(f"   ❌ Error de importación: {e}")
    sys.exit(1)

# Verificar que logger existe y está configurado
print("\n2️⃣  VERIFICANDO LOGGER...")
try:
    import logging
    if isinstance(logger, logging.Logger):
        print(f"   ✅ Logger configurado correctamente (nivel: {logging.getLevelName(logger.level)})")
    else:
        print(f"   ❌ Logger no es instancia de Logger")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Verificar que las funciones tienen logging
print("\n3️⃣  VERIFICANDO LOGGING EN FUNCIONES...")

def check_function_logging(func, func_name):
    """Verifica que una función contiene llamadas a logger."""
    source = inspect.getsource(func)
    has_logger = "logger." in source
    has_info = "logger.info" in source
    has_error = "logger.error" in source
    
    status = "✅" if (has_logger and (has_info or has_error)) else "⚠️ "
    print(f"   {status} {func_name}: logger={has_logger}, info={has_info}, error={has_error}")
    return has_logger

funcs_to_check = [
    (_safe_api_call, "_safe_api_call"),
    (_extract_daily_metrics, "_extract_daily_metrics"),
    (sincronizar_biometricos_garmin, "sincronizar_biometricos_garmin"),
    (iniciar_sesion_garmin, "iniciar_sesion_garmin"),
    (obtener_datos_sueno, "obtener_datos_sueno"),
]

for func, name in funcs_to_check:
    check_function_logging(func, name)

# Verificar estructura de BD
print("\n4️⃣  VERIFICANDO BASE DE DATOS...")
try:
    from db.db_manager import get_db_connection
    
    conn = get_db_connection()
    
    # Verificar tablas
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = ['datos_biometricos_premium', 'datos_sueno', 'usuarios']
    
    for table in required_tables:
        if table in tables:
            # Contar columnas
            col_cursor = conn.execute(f"PRAGMA table_info({table})")
            cols = col_cursor.fetchall()
            print(f"   ✅ {table} ({len(cols)} columnas)")
        else:
            print(f"   ⚠️  {table} NO EXISTE (se creará al sincronizar)")
    
    conn.close()
except Exception as e:
    print(f"   ❌ Error: {e}")

# Resumen
print("\n" + "="*80)
print("✅ DIAGNÓSTICO COMPLETADO".center(80))
print("="*80)
print("\n📌 PRÓXIMO PASO: Ejecutar sincronización real con credenciales de Garmin")
print("   python test_garmin_simple.py\n")
