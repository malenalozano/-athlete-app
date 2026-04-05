"""
src/garmin/sync.py
Punto de entrada canónico para el módulo de sincronización Garmin.
Re-exporta todas las funciones públicas de garmin_sync para que el resto
de la app las importe desde aquí.
"""

from src.garmin.garmin_sync import (
    sincronizar_actividades,
    sincronizar_actividades_inteligente,
    obtener_datos_sueno,
    guardar_sueno_db,
    iniciar_sesion_garmin,
    sincronizar_biometricos_garmin,
    guardar_metricas_premium_db,
)

__all__ = [
    "sincronizar_actividades",
    "sincronizar_actividades_inteligente",
    "obtener_datos_sueno",
    "guardar_sueno_db",
    "iniciar_sesion_garmin",
    "sincronizar_biometricos_garmin",
    "guardar_metricas_premium_db",
]
