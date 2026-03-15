#!/usr/bin/env python3
"""
Script de prueba detallado para sincronización de datos biométricos de Garmin.
Ayuda a identificar exactamente qué está fallandoen la importación.
"""

import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar librerías locales
from garminconnect import Garmin, GarminConnectConnectionError, GarminConnectAuthenticationError

load_dotenv()

def test_basic_auth(email, password):
    """Prueba 1: Verificar autenticación"""
    logger.info("=" * 80)
    logger.info("PRUEBA 1: AUTENTICACIÓN BÁSICA")
    logger.info("=" * 80)
    
    try:
        client = Garmin(email, password)
        client.login()
        logger.info("✅ AUTENTICACIÓN EXITOSA")
        return client
    except GarminConnectAuthenticationError as e:
        logger.error(f"❌ ERROR DE AUTENTICACIÓN: {e}")
        return None
    except GarminConnectConnectionError as e:
        logger.error(f"❌ ERROR DE CONEXIÓN: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ ERROR INESPERADO: {e}")
        return None

def test_daily_metrics(client, fecha_iso):
    """Prueba 2: Obtener métricas diarias para una fecha específica"""
    logger.info("=" * 80)
    logger.info(f"PRUEBA 2: MÉTRICAS DIARIAS PARA {fecha_iso}")
    logger.info("=" * 80)
    
    results = {}
    
    # HRV
    logger.info(f"Obteniendo HRV para {fecha_iso}...")
    try:
        hrv_data = client.get_hrv_data(fecha_iso)
        logger.info(f"✅ HRV Data: {hrv_data}")
        results["hrv"] = hrv_data
    except Exception as e:
        logger.error(f"❌ Error HRV: {e}")
        results["hrv"] = None
    
    # Training Readiness
    logger.info(f"Obteniendo Training Readiness para {fecha_iso}...")
    try:
        readiness = client.get_training_readiness(fecha_iso)
        logger.info(f"✅ Training Readiness: {readiness}")
        results["readiness"] = readiness
    except Exception as e:
        logger.error(f"❌ Error Training Readiness: {e}")
        results["readiness"] = None
    
    # Morning Training Readiness
    logger.info(f"Obteniendo Morning Training Readiness para {fecha_iso}...")
    try:
        morning_readiness = client.get_morning_training_readiness(fecha_iso)
        logger.info(f"✅ Morning Training Readiness: {morning_readiness}")
        results["morning_readiness"] = morning_readiness
    except Exception as e:
        logger.error(f"❌ Error Morning Training Readiness: {e}")
        results["morning_readiness"] = None
    
    # Body Battery
    logger.info(f"Obteniendo Body Battery para {fecha_iso}...")
    try:
        body_battery = client.get_body_battery(fecha_iso, fecha_iso)
        logger.info(f"✅ Body Battery: {body_battery}")
        results["body_battery"] = body_battery
    except Exception as e:
        logger.error(f"❌ Error Body Battery: {e}")
        results["body_battery"] = None
    
    # Stress Data
    logger.info(f"Obteniendo Stress Data para {fecha_iso}...")
    try:
        stress = client.get_stress_data(fecha_iso)
        logger.info(f"✅ Stress Data: {stress}")
        results["stress"] = stress
    except Exception as e:
        logger.error(f"❌ Error Stress Data: {e}")
        try:
            stress_alt = client.get_all_day_stress(fecha_iso)
            logger.info(f"✅ All Day Stress (fallback): {stress_alt}")
            results["stress"] = stress_alt
        except Exception as e2:
            logger.error(f"❌ Error All Day Stress (fallback): {e2}")
            results["stress"] = None
    
    # SpO2
    logger.info(f"Obteniendo SpO2 para {fecha_iso}...")
    try:
        spo2 = client.get_spo2_data(fecha_iso)
        logger.info(f"✅ SpO2 Data: {spo2}")
        results["spo2"] = spo2
    except Exception as e:
        logger.error(f"❌ Error SpO2: {e}")
        results["spo2"] = None
    
    # Heart Rates
    logger.info(f"Obteniendo Heart Rates para {fecha_iso}...")
    try:
        heart_rates = client.get_heart_rates(fecha_iso)
        logger.info(f"✅ Heart Rates: {heart_rates}")
        results["heart_rates"] = heart_rates
    except Exception as e:
        logger.error(f"❌ Error Heart Rates: {e}")
        results["heart_rates"] = None
    
    return results

def test_sleep_data(client, fecha):
    """Prueba 3: Obtener datos de sueño"""
    logger.info("=" * 80)
    logger.info(f"PRUEBA 3: DATOS DE SUEÑO PARA {fecha}")
    logger.info("=" * 80)
    
    logger.info(f"Obteniendo Sleep Data para {fecha}...")
    try:
        sleep_data = client.get_sleep_data(fecha.strftime("%Y-%m-%d"))
        logger.info(f"✅ Sleep Data: {sleep_data}")
        return sleep_data
    except Exception as e:
        logger.error(f"❌ Error Sleep Data: {e}")
        return None

def test_activities(client):
    """Prueba 4: Obtener actividades recientes"""
    logger.info("=" * 80)
    logger.info("PRUEBA 4: ACTIVIDADES RECIENTES")
    logger.info("=" * 80)
    
    logger.info("Obteniendo últimas 5 actividades...")
    try:
        activities = client.get_activities(0, 5)
        logger.info(f"✅ Actividades encontradas: {len(activities)}")
        
        for i, act in enumerate(activities):
            logger.info(f"  [{i}] {act.get('activityName', 'Sin nombre')} - "
                       f"Tipo: {act.get('activityType', {}).get('typeKey', 'Desconocido')} - "
                       f"Fecha: {act.get('startTimeLocal', 'N/A')}")
            
            # Intentar obtener detalles
            try:
                activity_id = str(act.get('activityId'))
                details = client.get_activity_details(activity_id)
                logger.info(f"     Details keys: {list(details.keys())[:5]}...")  # Mostrar primeras 5 keys
            except Exception as de:
                logger.warning(f"     No se pudieron obtener detalles: {de}")
        
        return activities
    except Exception as e:
        logger.error(f"❌ Error obtener actividades: {e}")
        return None

def main():
    """Función principal para ejecutar todas las pruebas"""
    
    logger.info("INICIO DE PRUEBAS DE SINCRONIZACIÓN GARMIN")
    logger.info("=" * 80)
    
    # Solicitar credenciales
    print("\n*** PRUEBA DE IMPORTACIÓN DE DATOS BIOMÉTRICOS GARMIN ***\n")
    email = input("Email Garmin: ").strip()
    password = input("Contraseña Garmin: ").strip()
    
    if not email or not password:
        logger.error("Email o contraseña vacíos")
        sys.exit(1)
    
    # Prueba 1: Autenticación
    client = test_basic_auth(email, password)
    if not client:
        logger.error("No se pudo autenticar. Abortando.")
        sys.exit(1)
    
    # Prueba 2: Métricas diarias para hoy y últimos 2 días
    hoy = datetime.now()
    for i in range(3):
        fecha = (hoy - timedelta(days=i)).date()
        fecha_iso = fecha.strftime("%Y-%m-%d")
        test_daily_metrics(client, fecha_iso)
        test_sleep_data(client, fecha)
    
    # Prueba 3: Actividades
    test_activities(client)
    
    logger.info("=" * 80)
    logger.info("PRUEBAS COMPLETADAS")
    logger.info("=" * 80)
    logger.info("\nSi todos los datos aparecen arriba (✅), la API de Garmin está funcionando.")
    logger.info("Si hay errores (❌), revisa el mensaje para diagnosticar el problema.")

if __name__ == "__main__":
    main()
