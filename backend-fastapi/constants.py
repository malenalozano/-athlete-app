"""Constantes compartidas entre routers. Antes duplicadas por separado en
plan.py, dashboard.py y garmin.py — desincronizarse causaba bugs (p.ej. bici
contando como km de carrera en unos sitios y no en otros)."""

# Tipos de actividad Garmin que cuentan como "carrera" (running/cinta), para
# distinguir del resto de deportes (bici, natación, etc.) al sumar km de plan.
# Debe reflejar Figma/src/app/lib/running.ts::RUNNING_TIPOS — mantener ambos en sync.
RUNNING_TIPOS = {
    "running", "trail_running", "treadmill_running", "track_running",
    "correr", "carrera", "trail", "run", "indoor_running", "treadmill",
    "road_running",
}
RUNNING_TIPOS_SQL = (
    "('running','trail_running','treadmill_running','track_running','correr',"
    "'carrera','trail','run','indoor_running','treadmill','road_running')"
)

STRENGTH_TIPOS = {"strength_training", "strength", "fuerza", "gym", "fitness_equipment"}
STRENGTH_TIPOS_SQL = "('strength_training','strength','fuerza','gym','fitness_equipment')"


def es_actividad_running(tipo_deporte: str | None) -> bool:
    return (tipo_deporte or "").lower() in RUNNING_TIPOS
