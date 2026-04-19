#!/usr/bin/env python3
"""
TEST EXHAUSTIVO: Simula exactamente lo que hace la app cuando
Malena se loguea desde Cloud.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Simular sesión de Streamlit
class FakeSession:
    def __init__(self):
        self.data = {}
    def get(self, key, default=None):
        return self.data.get(key, default)
    def __setitem__(self, key, value):
        self.data[key] = value
    def __getitem__(self, key):
        return self.data[key]

# No podemos usar st.session_state aquí, así que importamos las funciones directas
from src.db.db_manager import (
    get_db_connection, obtener_perfil, obtener_credenciales_garmin
)
from src.core.dashboard_data import (
    cargar_datos_dashboard, resumen_dashboard
)
from src.core.dashboard_ui import (
    obtener_titulo_macrociclo, obtener_estado_ciclo_malena, render_macrociclo
)

print("=" * 80)
print("FULL DIAGNOSTIC TEST - Simulating Cloud App Load")
print("=" * 80)

# TEST 1: Database connection
print("\n[1/7] Testing Database Connection...")
print("-" * 80)
try:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM usuarios")
    usuario_count = c.fetchone()[0]
    print(f"✅ DB Connected. Total usuarios: {usuario_count}")
    
    c.execute("SELECT id, nombre, objetivo_tipo FROM usuarios")
    usuarios = c.fetchall()
    for uid, nombre, obj in usuarios:
        print(f"   - ID={uid}, Nombre={nombre}, Objetivo={obj}")
    conn.close()
except Exception as e:
    print(f"❌ DB Error: {e}")
    sys.exit(1)

# TEST 2: Perfiles de ambos usuarios
print("\n[2/7] Testing Perfil Loading (Malena & Dani)...")
print("-" * 80)
for uid in [1, 2]:
    try:
        perfil = obtener_perfil(uid)
        if perfil:
            print(f"✅ UID={uid}:")
            print(f"   Nombre: {perfil.get('nombre')}")
            print(f"   Objetivo: {perfil.get('objetivo_tipo')}")
            print(f"   Fecha objetivo: {perfil.get('fecha_objetivo')}")
        else:
            print(f"❌ UID={uid}: Perfil NOT found")
    except Exception as e:
        print(f"❌ UID={uid}: Error - {e}")

# TEST 3: Dashboard Data Loading
print("\n[3/7] Testing Dashboard Data Loading (Malena)...")
print("-" * 80)
try:
    df_act, df_sueno, df_fuerza = cargar_datos_dashboard(1)
    print(f"✅ Malena Data Loaded:")
    print(f"   Actividades: {len(df_act)} records")
    if len(df_act) > 0:
        print(f"     - Primeras 3:")
        for idx, row in df_act.head(3).iterrows():
            print(f"       {row.get('fecha', 'N/A')}: {row.get('distancia_m', 0)/1000:.1f}km")
    print(f"   Sueño: {len(df_sueno)} records")
    print(f"   Fuerza: {len(df_fuerza)} records")
except Exception as e:
    print(f"❌ Malena Dashboard Error: {e}")
    import traceback
    traceback.print_exc()

# TEST 4: Macrociclo Titles (CRITICAL)
print("\n[4/7] Testing Macrociclo Titles (DYNAMIC)...")
print("-" * 80)
try:
    for uid in [1, 2]:
        titulo = obtener_titulo_macrociclo(uid)
        perfil = obtener_perfil(uid)
        print(f"✅ UID={uid} ({perfil.get('nombre')}):")
        print(f"   Título: {titulo}")
        
        # Verify correctness
        if uid == 1:
            assert "Maratón" in titulo, f"FAIL: Malena debe tener 'Maratón'"
            assert "Feb 2027" in titulo, f"FAIL: Malena debe tener 'Feb 2027'"
            print(f"   ✅ Título CORRECTO para Malena")
        else:
            assert "Ultra" in titulo, f"FAIL: Dani debe tener 'Ultra'"
            print(f"   ✅ Título CORRECTO para Dani")
except AssertionError as e:
    print(f"❌ ASSERTION FAILED: {e}")
except Exception as e:
    print(f"❌ Macrociclo Error: {e}")
    import traceback
    traceback.print_exc()

# TEST 5: Ciclo Menstrual (CRITICAL)
print("\n[5/7] Testing Ciclo Menstrual (MALENA ONLY)...")
print("-" * 80)
try:
    for uid in [1, 2]:
        estado = obtener_estado_ciclo_malena(uid)
        if uid == 1:
            if estado:
                print(f"✅ Malena VE ciclo: {estado.get('fase')}")
            else:
                print(f"⚠️  Malena NO tiene datos ciclo (podría estar vacío)")
        else:
            if estado is None:
                print(f"✅ Dani NO ve ciclo (returns None) ✓✓✓")
            else:
                print(f"❌ FAIL: Dani DEBE return None, pero devolvió: {estado}")
except Exception as e:
    print(f"❌ Ciclo Menstrual Error: {e}")
    import traceback
    traceback.print_exc()

# TEST 6: Resumen 7 días
print("\n[6/7] Testing Resumen 7 Días...")
print("-" * 80)
try:
    for uid in [1, 2]:
        resumen = resumen_dashboard(uid)
        perfil = obtener_perfil(uid)
        print(f"✅ {perfil.get('nombre')} (UID={uid}):")
        print(f"   KM: {resumen.get('km_7d', 0):.1f}")
        print(f"   Fuerza: {resumen.get('fuerza_7d', 0)}")
        print(f"   Sueño: {resumen.get('sueno_7d', 'N/A')}")
except Exception as e:
    print(f"❌ Resumen Error: {e}")

# TEST 7: Garmin Credentials (INFO)
print("\n[7/7] Testing Garmin Credentials...")
print("-" * 80)
try:
    for uid in [1, 2]:
        cred = obtener_credenciales_garmin(uid)
        perfil = obtener_perfil(uid)
        if cred and cred[0]:
            print(f"✅ {perfil.get('nombre')}: Email={cred[0]}")
        else:
            print(f"⚠️  {perfil.get('nombre')}: Sin credenciales Garmin configuradas")
except Exception as e:
    print(f"❌ Garmin Cred Error: {e}")

print("\n" + "=" * 80)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 80)
print("""
✅ IF ALL TESTS PASSED:
   1. All code working correctly on localhost
   2. Changes should work in Cloud
   3. Issue might be Cloud cache - need explicit reboot
   
⚠️  CLOUD REBOOT PROCEDURE:
    1. Go to https://share.streamlit.io
    2. Find "athlete-performance-tracker" app
    3. Click menu ⋯ (top right)
    4. Click "Reboot app"
    5. Wait for "App is running" message
    6. Use CTRL+F5 or CTRL+SHIFT+DELETE to clear browser cache
    7. Re-access the app URL in a NEW browser tab
    
❌ IF TESTS FAILED:
    See error messages above - need to fix those issues first
""")
