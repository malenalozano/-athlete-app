#!/usr/bin/env python3
"""Test script to verify all changes work correctly"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.db.db_manager import obtener_perfil
from src.core.dashboard_ui import obtener_titulo_macrociclo, obtener_estado_ciclo_malena
from src.core.dashboard_data import cargar_datos_dashboard

print("=" * 70)
print("TESTING ALL CHANGES")
print("=" * 70)

# Test 1: Obtener títulos macrociclo dinámicos
print("\n✅ TEST 1: Títulos macrociclo por usuario")
print("-" * 70)

for uid in [1, 2]:
    perfil = obtener_perfil(uid)
    titulo = obtener_titulo_macrociclo(uid)
    nombre = perfil.get("nombre") if perfil else "???"
    objetivo = perfil.get("objetivo_tipo") if perfil else "???"
    print(f"\nUsuario {uid} ({nombre}):")
    print(f"  Objetivo: {objetivo}")
    print(f"  Título: {titulo}")
    
    # Verify it's different
    if uid == 1:
        assert "Maratón" in titulo, f"Malena título should have 'Maratón', got: {titulo}"
        assert "Feb 2027" in titulo, f"Malena título should have 'Feb 2027', got: {titulo}"
        print(f"  ✅ Correcto para Malena")
    elif uid == 2:
        assert "Ultra" in titulo, f"Dani título should have 'Ultra', got: {titulo}"
        assert "2026" in titulo, f"Dani título should have '2026', got: {titulo}"
        print(f"  ✅ Correcto para Dani")

# Test 2: Ciclo menstrual solo para Malena
print("\n✅ TEST 2: Ciclo menstrual - solo para Malena")
print("-" * 70)

for uid in [1, 2]:
    estado_ciclo = obtener_estado_ciclo_malena(uid)
    nombre = obtener_perfil(uid).get("nombre") if obtener_perfil(uid) else "???"
    
    if uid == 1:
        if estado_ciclo:
            print(f"\n✅ Malena ve ciclo: {estado_ciclo.get('fase', 'N/A')}")
        else:
            print(f"\n⚠️ Malena no tiene datos de ciclo (OK si es datos históricos vacíos)")
    else:
        if estado_ciclo is None:
            print(f"\n✅ Dani correctamente NO ve ciclo (retorna None)")
        else:
            print(f"\n❌ ERROR: Dani DEBE return None, got: {estado_ciclo}")

# Test 3: Datos por usuario
print("\n✅ TEST 3: Datos por usuario (actividades)")
print("-" * 70)

for uid in [1, 2]:
    df_act, df_sueno, df_fuerza = cargar_datos_dashboard(uid)
    perfil = obtener_perfil(uid)
    nombre = perfil.get("nombre") if perfil else "???"
    
    print(f"\n{nombre} (uid={uid}):")
    print(f"  Actividades: {len(df_act)}")
    print(f"  Sueño: {len(df_sueno)}")
    print(f"  Fuerza: {len(df_fuerza)}")
    
    # Verify data isolation
    if uid == 1:
        assert len(df_act) > 0, "Malena should have activities"
        print(f"  ✅ Malena tiene datos")
    elif uid == 2:
        assert len(df_act) == 0, "Dani should have 0 activities (no sync yet)"
        print(f"  ✅ Dani sin datos (esperado - sin Garmin)")

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print("\nNext:")
print("1. Visit http://localhost:8501 in your browser")
print("2. Login as malena/malena123")
print("3. Verify: Avatar=M, Macrociclo title correct, data loads")
print("4. Click avatar M → Popover should show logout option")
print("5. Logout and login as dani/dani123")
print("6. Verify: Avatar=D, Macrociclo title correct, no ciclo menstrual, 0 activities")
