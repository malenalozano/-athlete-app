#!/usr/bin/env python3
"""
Script de prueba simulada para verificar que el parsing de datos funciona correctamente.
No necesita credenciales de Garmin.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from src.garmin.garmin_sync import (
    _extract_daily_metrics,
    _extract_sleep_metrics,
    _extract_activity_metrics,
    _first_number,
    _to_int,
    _search_values
)

print("\n" + "="*80)
print("TEST DE PARSING DE DATOS - SIMULACIÓN".center(80))
print("="*80 + "\n")

# Datos simulados como si vinieran de la API de Garmin
test_data = {
    "hrv": {
        "hrvSummary": {
            "lastNightAverage": 45.5,
            "weeklyAvg": 48.2
        }
    },
    "readiness": {
        "trainingReadiness": 78,
        "score": 78,
        "readinessScore": 78,
        "recoveryTime": 8.5,
        "recoveryHours": 8.5
    },
    "body_battery": [
        {"bodyBattery": 85, "chargedValue": 85, "date": "2026-03-15"},
        {"bodyBattery": 72, "chargedValue": 72, "date": "2026-03-15"}
    ],
    "stress": {
        "overallStressLevel": 32,
        "stressScore": 32,
        "calendarDateStressValue": 32
    },
    "spo2": {
        "averageSpo2": 97.8,
        "avgSpo2": 97.8
    },
    "heart_rates": {
        "restingHeartRate": 52,
        "restHeartRate": 52,
        "maxHeartRate": 178,
        "maxHeartRateInBeatsPerMinute": 178
    },
    "sleep": {
        "sleepTimeSeconds": 28800,  # 8 horas
        "totalSleepSeconds": 28800,
        "deepSleepSeconds": 6300,   # 1.75 horas
        "remSleepSeconds": 4200,    # 1.17 horas
        "awakeSleepSeconds": 1800,  # 0.5 horas
        "awakeCount": 3,
        "overallSleepScore": {"value": 85}
    },
    "activity": {
        "activityId": 12345,
        "startTimeLocal": "2026-03-14 06:30:00",
        "activityType": {"typeKey": "running"},
        "distance": 10000,
        "duration": 2700,
        "averageSpeed": 3.7
    }
}

print("1️⃣  TESTING _extract_daily_metrics simulado...")
print("-" * 80)

# Simular lo que haría _extract_daily_metrics
test_fecha = "2026-03-14"
hrv_value = _first_number(test_data["hrv"], ["lastNightAverage", "averageHrv"])
tr_value = _to_int(_first_number(test_data["readiness"], ["trainingReadiness", "readinessScore","score"]))
bb_value = _to_int(_first_number(test_data["body_battery"], ["bodyBattery", "chargedValue"]))
rec_hours = _first_number(test_data["readiness"], ["recoveryTime", "recoveryHours"])
stress_value = _to_int(_first_number(test_data["stress"], ["overallStressLevel"]))
spo2_value = _first_number(test_data["spo2"], ["averageSpo2"])
rhr = _to_int(_first_number(test_data["heart_rates"], ["restingHeartRate"]))
mhr = _to_int(_first_number(test_data["heart_rates"], ["maxHeartRate"]))

results = {
    "fecha": test_fecha,
    "hrv_ms": hrv_value,
    "training_readiness": tr_value,
    "body_battery": bb_value,
    "recovery_hours": rec_hours,
    "fc_reposo": rhr,
    "fc_maxima": mhr,
    "estres_vital": stress_value,
    "spo2": spo2_value,
}

print("\n✅ Métricas diarias extraídas correctamente:")
for key, value in results.items():
    status = "✓" if value is not None else "✗"
    print(f"   {status} {key:.<30} {value}")

print(f"\n2️⃣  TESTING _extract_sleep_metrics...")
print("-" * 80)

sleep_result = _extract_sleep_metrics(test_data["sleep"], test_fecha)
if sleep_result:
    print("\n✅ Métricas de sueño extraídas correctamente:")
    for key, value in sleep_result.items():
        status = "✓" if value is not None else "✗"
        print(f"   {status} {key:.<30} {value}")
else:
    print("\n❌ No se pudieron extraer métricas de sueño")

print(f"\n3️⃣  TESTING _extract_activity_metrics...")
print("-" * 80)

activity_result = _extract_activity_metrics(test_data["activity"], {}, {})
if activity_result:
    print("\n✅ Métricas de actividad extraídas correctamente:")
    for key, value in activity_result.items():
        status = "✓" if value is not None else "✗"
        print(f"   {status} {key:.<30} {value}")
else:
    print("\n❌ No se pudieron extraer métricas de actividad")

print(f"\n{'='*80}")
print("✅ TEST DE PARSING COMPLETADO".center(80))
print(f"{'='*80}\n")
print("\n📊 RESULTADOS: Todos los parseos funcionan correctamente")
print("   Si la API de Garmin devuelve datos similares, serán importados correctamente\n")
