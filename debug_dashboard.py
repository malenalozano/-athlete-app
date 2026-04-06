#!/usr/bin/env python3
"""Debug dashboard data loading for both users"""

import sqlite3
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.core.dashboard_data import cargar_datos_dashboard, resumen_dashboard
from src.db.db_manager import get_db_connection, obtener_perfil

print("=" * 70)
print("DASHBOARD DATA DEBUG")
print("=" * 70)

# Test para usuario_id=1 (Malena)
print("\n👩 TEST USUARIO_ID=1 (Malena):")
print("-" * 70)

perfil = obtener_perfil(1)
if perfil:
    print(f"✓ Perfil cargado: {perfil.get('nombre')} | objetivo_tipo={perfil.get('objetivo_tipo')}")
else:
    print("✗ Perfil NOT FOUND")

resumen = resumen_dashboard(1)
print(f"✓ Resumen 7 días:")
print(f"  - km_7d: {resumen.get('km_7d')}")
print(f"  - runs_7d: {resumen.get('runs_7d')}")
print(f"  - fuerza_7d: {resumen.get('fuerza_7d')}")
print(f"  - sueno_7d: {resumen.get('sueno_7d')}")

df_act, df_sueno, df_fuerza = cargar_datos_dashboard(1)
print(f"✓ Datos cargados:")
print(f"  - Actividades: {len(df_act)} registros")
if not df_act.empty:
    print(f"    - Primeras 3: ")
    for idx, row in df_act.head(3).iterrows():
        print(f"      {row['fecha']}: {row['distancia_m']/1000:.1f}km")
print(f"  - Sueño: {len(df_sueno)} registros")
print(f"  - Fuerza: {len(df_fuerza)} registros")

# Test para usuario_id=2 (Dani)
print("\n👨 TEST USUARIO_ID=2 (Dani):")
print("-" * 70)

perfil = obtener_perfil(2)
if perfil:
    print(f"✓ Perfil cargado: {perfil.get('nombre')} | objetivo_tipo={perfil.get('objetivo_tipo')}")
else:
    print("✗ Perfil NOT FOUND")

resumen = resumen_dashboard(2)
print(f"✓ Resumen 7 días:")
print(f"  - km_7d: {resumen.get('km_7d')}")
print(f"  - runs_7d: {resumen.get('runs_7d')}")
print(f"  - fuerza_7d: {resumen.get('fuerza_7d')}")
print(f"  - sueno_7d: {resumen.get('sueno_7d')}")

df_act, df_sueno, df_fuerza = cargar_datos_dashboard(2)
print(f"✓ Datos cargados:")
print(f"  - Actividades: {len(df_act)} registros")
print(f"  - Sueño: {len(df_sueno)} registros")
print(f"  - Fuerza: {len(df_fuerza)} registros")

print("\n" + "=" * 70)
print("RAW SQL VERIFY:")
print("=" * 70)

conn = get_db_connection()
c = conn.cursor()

# Count by usuario_id
c.execute("SELECT usuario_id, COUNT(*) FROM actividades_garmin GROUP BY usuario_id")
print("\nActividades por usuario_id:")
for uid, count in c.fetchall():
    print(f"  usuario_id={uid}: {count} actividades")

# Check if table exists
try:
    c.execute("SELECT COUNT(*) FROM actividades_garmin WHERE usuario_id=1")
    count = c.fetchone()[0]
    print(f"\n✓ Query works - Found {count} actividades para usuario_id=1")
except Exception as e:
    print(f"✗ Query error: {e}")

conn.close()
