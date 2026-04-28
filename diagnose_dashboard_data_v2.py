#!/usr/bin/env python3
"""
Diagnóstico mejorado de datos del dashboard.
"""

from datetime import date, timedelta
from src.db.db_manager import get_db_connection
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
    
    conn = get_db_connection()
    
    try:
        # 0. Listar todas las tablas
        print("0️⃣  TABLAS DISPONIBLES EN LA BD")
        print("-" * 80)
        
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tablas = [row[0] for row in cursor.fetchall()]
        print(f"Encontradas {len(tablas)} tablas:")
        for t in tablas:
            print(f"  - {t}")
        
        # 1. Datos en datos_biometricos_premium
        print("\n\n1️⃣  DATOS_BIOMETRICOS_PREMIUM")
        print("-" * 80)
        
        if "datos_biometricos_premium" in tablas:
            cursor = conn.execute(
                """SELECT fecha, hrv_ms, fc_reposo, body_battery_max, body_battery_min, 
                          estres_medio, estres_vital, sleep_score
                   FROM datos_biometricos_premium 
                   WHERE usuario_id = ? AND fecha IN (?, ?)
                   ORDER BY fecha DESC""",
                (usuario_id, hoy_str, ayer_str)
            )
            cols = [c[0] for c in cursor.description]
            rows = cursor.fetchall()
            
            if rows:
                print(f"✅ Encontrados {len(rows)} registros:")
                for row in rows:
                    d = dict(zip(cols, row))
                    print(f"   Fecha: {d['fecha']}")
                    print(f"     HRV: {d['hrv_ms']} ms")
                    print(f"     FC Reposo: {d['fc_reposo']} bpm")
                    print(f"     Body Battery Max: {d['body_battery_max']}")
                    print(f"     Body Battery Min: {d['body_battery_min']}")
                    print(f"     Estrés Medio: {d['estres_medio']}")
                    print(f"     Estrés Vital: {d['estres_vital']}")
                    print(f"     Sleep Score: {d['sleep_score']}")
            else:
                print("❌ NO hay datos en datos_biometricos_premium para hoy ni ayer")
        else:
            print("❌ Tabla datos_biometricos_premium NO EXISTE")
        
        # 2. Datos en datos_sueno
        print("\n\n2️⃣  DATOS_SUENO")
        print("-" * 80)
        
        if "datos_sueno" in tablas:
            cursor = conn.execute(
                """SELECT fecha, horas_totales, score, sleep_profundo_horas, 
                          sleep_rem_horas, sleep_vigilia_horas
                   FROM datos_sueno 
                   WHERE usuario_id = ? AND fecha IN (?, ?)
                   ORDER BY fecha DESC""",
                (usuario_id, hoy_str, ayer_str)
            )
            cols = [c[0] for c in cursor.description]
            rows = cursor.fetchall()
            
            if rows:
                print(f"✅ Encontrados {len(rows)} registros:")
                for row in rows:
                    d = dict(zip(cols, row))
                    print(f"   Fecha: {d['fecha']}, Horas: {d['horas_totales']}h, Score: {d['score']}")
            else:
                print("❌ NO hay datos de sueño para hoy ni ayer")
        else:
            print("❌ Tabla datos_sueno NO EXISTE")
        
        # 3. Datos en actividades_garmin (últimos 5 días)
        print("\n\n3️⃣  ACTIVIDADES_GARMIN (últimos 5 días)")
        print("-" * 80)
        
        if "actividades_garmin" in tablas:
            cursor = conn.execute(
                """SELECT fecha, tipo_deporte, distancia_m, tiempo_seg, fc_media, cadencia_media
                   FROM actividades_garmin 
                   WHERE usuario_id = ? AND fecha >= ?
                   ORDER BY fecha DESC
                   LIMIT 20""",
                (usuario_id, (hoy - timedelta(days=5)).isoformat())
            )
            cols = [c[0] for c in cursor.description]
            rows = cursor.fetchall()
            
            if rows:
                print(f"✅ Encontradas {len(rows)} actividades:")
                for row in rows:
                    d = dict(zip(cols, row))
                    dist_km = d['distancia_m'] / 1000 if d['distancia_m'] else 0
                    print(f"   {d['fecha']} - {d['tipo_deporte']}: {dist_km:.2f}km, FC media: {d['fc_media']}")
            else:
                print("❌ NO hay actividades recientes")
        else:
            print("❌ Tabla actividades_garmin NO EXISTE")
        
        # 4. Resumen: ¿Qué falta?
        print("\n\n4️⃣  ANÁLISIS: ¿QUÉ ESTÁ PASANDO?")
        print("-" * 80)
        
        # Verificar si datos_biometricos_premium tiene algo para fechas más lejanas
        if "datos_biometricos_premium" in tablas:
            cursor = conn.execute(
                """SELECT COUNT(*), MIN(fecha), MAX(fecha) FROM datos_biometricos_premium 
                   WHERE usuario_id = ?""",
                (usuario_id,)
            )
            count, min_fecha, max_fecha = cursor.fetchone()
            print(f"\nDatos biométricos totales en BD:")
            print(f"  - Total registros: {count}")
            print(f"  - Rango: {min_fecha} a {max_fecha}")
            
            if count == 0:
                print("  ❌ PROBLEMA: No hay datos de Garmin guardados en la BD")
                print("  💡 SOLUCIÓN: Ve a /pages/04_garmin.py y sincroniza tu dispositivo Garmin")
            elif max_fecha and max_fecha < hoy_str:
                print(f"  ⚠️  PROBLEMA: Datos desactualizados (último: {max_fecha})")
                print("  💡 SOLUCIÓN: Sincroniza Garmin para traer datos de hoy")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
    
    print("\n" + "="*80)


if __name__ == "__main__":
    diagnosticar_datos_dashboard(usuario_id=1)
