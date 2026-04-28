#!/usr/bin/env python3
"""
Diagnóstico de datos del dashboard.
Muestra qué datos están disponibles en la base de datos para hoy.
"""

from datetime import date, timedelta
from src.db.db_manager import get_db_connection
import pandas as pd
import sqlite3

def diagnosticar_datos_dashboard(usuario_id: int = 1):
    """Verifica qué datos hay en la BD para el dashboard."""
    
    hoy = date.today()
    ayer = hoy - timedelta(days=1)
    hoy_str = hoy.isoformat()
    ayer_str = ayer.isoformat()
    
    print(f"\n{'='*80}")
    print(f"DIAGNÓSTICO DE DATOS DEL DASHBOARD")
    print(f"{'='*80}")
    print(f"Usuario ID: {usuario_id}")
    print(f"Hoy: {hoy_str}")
    print(f"Ayer: {ayer_str}")
    print(f"{'='*80}\n")
    
    # 0. Listar tablas disponibles
    print("0️⃣  TABLAS DISPONIBLES EN LA BD")
    print("-" * 80)
    
    conn = get_db_connection()
    
    try:
        # 1. Datos en datos_biometricos_premium
        print("\n1️⃣  DATOS_BIOMETRICOS_PREMIUM")
        print("-" * 80)
        
        query = """
        SELECT fecha, hrv_ms, fc_reposo, body_battery_max, body_battery_min, 
               estres_medio, estres_vital, sleep_score
        FROM datos_biometricos_premium 
        WHERE usuario_id = ? AND fecha IN (?, ?)
        ORDER BY fecha DESC
        """
        
        df_biom = pd.read_sql_query(query, conn, params=(usuario_id, hoy_str, ayer_str))
        
        if df_biom.empty:
            print("❌ NO hay datos en datos_biometricos_premium para hoy ni ayer")
        else:
            print(f"✅ Encontrados {len(df_biom)} registros:")
            print(df_biom.to_string(index=False))
        
        # 2. Datos en biometricos_garmin (tabla alternativa)
        print("\n\n2️⃣  BIOMETRICOS_GARMIN (tabla alternativa)")
        print("-" * 80)
        
        query = """
        SELECT fecha, tipo, valor 
        FROM biometricos_garmin 
        WHERE usuario_id = ? AND fecha IN (?, ?)
        ORDER BY fecha DESC, tipo
        """
        
        df_garmin = pd.read_sql_query(query, conn, params=(usuario_id, hoy_str, ayer_str))
        
        if df_garmin.empty:
            print("❌ NO hay datos en biometricos_garmin para hoy ni ayer")
        else:
            print(f"✅ Encontrados {len(df_garmin)} registros:")
            print(df_garmin.to_string(index=False))
            
            # Tabla pivote por tipo
            print("\n   📊 RESUMEN POR TIPO:")
            pivot = df_garmin.pivot_table(
                values='valor', 
                index='tipo', 
                columns='fecha',
                aggfunc='first'
            )
            print(pivot.to_string())
        
        # 3. Datos de sueño
        print("\n\n3️⃣  DATOS_SUENO")
        print("-" * 80)
        
        query = """
        SELECT fecha, horas_totales, score, sleep_profundo_horas, sleep_rem_horas, sleep_vigilia_horas
        FROM datos_sueno 
        WHERE usuario_id = ? AND fecha IN (?, ?)
        ORDER BY fecha DESC
        """
        
        df_sueno = pd.read_sql_query(query, conn, params=(usuario_id, hoy_str, ayer_str))
        
        if df_sueno.empty:
            print("❌ NO hay datos de sueño para hoy ni ayer")
        else:
            print(f"✅ Encontrados {len(df_sueno)} registros:")
            print(df_sueno.to_string(index=False))
        
        # 4. Resumen de lo que ve el dashboard
        print("\n\n4️⃣  RESUMEN: ¿Qué ve el dashboard?")
        print("-" * 80)
        
        # Simular lo que ve analisis_hoy()
        bio = None
        if not df_biom.empty:
            bio = df_biom.iloc[0].to_dict()
            print("✅ Dashboard obtiene BIO de datos_biometricos_premium:")
            print(f"   - HRV: {bio.get('hrv_ms')} ms")
            print(f"   - FC Reposo: {bio.get('fc_reposo')} bpm")
            print(f"   - Body Battery Max: {bio.get('body_battery_max')}")
            print(f"   - Body Battery Min: {bio.get('body_battery_min')}")
            print(f"   - Estrés Medio: {bio.get('estres_medio')}")
        else:
            print("❌ Dashboard NO obtiene BIO (no hay en datos_biometricos_premium)")
            print("   Se activarán fallbacks a biometricos_garmin...")
            
            # Mostrar fallbacks disponibles
            if not df_garmin.empty:
                print("   ✅ Fallbacks disponibles en biometricos_garmin:")
                for tipo in df_garmin['tipo'].unique():
                    vals = df_garmin[df_garmin['tipo'] == tipo]['valor'].values
                    print(f"      - {tipo}: {vals[0] if vals.size > 0 else 'N/A'}")
        
        # Sueño
        sueno = None
        if not df_sueno.empty:
            sueno = df_sueno.iloc[0].to_dict()
            print("\n✅ Dashboard obtiene SUEÑO:")
            print(f"   - Horas: {sueno.get('horas_totales')} h")
            print(f"   - Score: {sueno.get('score')}")
        else:
            print("\n❌ Dashboard NO obtiene SUEÑO (no hay en datos_sueno)")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()


if __name__ == "__main__":
    # Puedes cambiar usuario_id si necesario
    diagnosticar_datos_dashboard(usuario_id=1)
    print("\n💡 Si ves muchos '❌', ejecuta: /pages/04_garmin.py para sincronizar Garmin")
