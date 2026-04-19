"""
src/garmin/workout_builder.py
Construye y sube workouts estructurados a Garmin Connect.
Usa gc.upload_workout(dict) → POST /workout-service/workout
"""

from datetime import datetime

FCMAX = 200  # Malena, 21 años (220 - 21)

ZONA_HR = {
    "Z1": (0.50, 0.60),
    "Z2": (0.60, 0.70),
    "Z3": (0.70, 0.80),
    "Z4": (0.80, 0.90),
    "Z5": (0.90, 1.00),
}

_SPORT = {"sportTypeId": 1, "sportTypeKey": "running"}

_STEP_TYPE_WARMUP   = {"stepTypeId": 1, "stepTypeKey": "warmup"}
_STEP_TYPE_INTERVAL = {"stepTypeId": 3, "stepTypeKey": "interval"}
_STEP_TYPE_COOLDOWN = {"stepTypeId": 2, "stepTypeKey": "cooldown"}
_STEP_TYPE_RECOVERY = {"stepTypeId": 4, "stepTypeKey": "recovery"}

_DUR_TIME = {"durationTypeId": 2, "durationTypeKey": "time"}
_TGT_HR   = {"workoutTargetTypeId": 4, "workoutTargetTypeKey": "heart.rate.zone"}
_TGT_NONE = {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"}


def _step(order: int, zona: str, duracion_min: float, tipo: str = "interval") -> dict:
    lo, hi = ZONA_HR.get(zona, (0.60, 0.70))
    step_types = {
        "warmup": _STEP_TYPE_WARMUP,
        "interval": _STEP_TYPE_INTERVAL,
        "cooldown": _STEP_TYPE_COOLDOWN,
        "recovery": _STEP_TYPE_RECOVERY,
    }
    return {
        "stepOrder": order,
        "stepType": step_types.get(tipo, _STEP_TYPE_INTERVAL),
        "durationType": _DUR_TIME,
        "durationValue": int(duracion_min * 60),
        "targetType": _TGT_HR,
        "targetValueOne": int(FCMAX * lo),
        "targetValueTwo": int(FCMAX * hi),
    }


def sesion_a_bloques(sesion_motor: dict) -> list:
    """
    Convierte el output de generar_plan_semana a lista de bloques con zona.
    Retorna: [{"zona": "Z2", "duracion_min": 30, "tipo": "interval"}, ...]
    """
    tipo = sesion_motor.get("tipo", "")
    duracion = float(sesion_motor.get("duracion_min") or 40)
    km = float(sesion_motor.get("km") or 0)
    dur_principal = max(duracion - 20, 10)  # descontar calentamiento/vuelta calma

    if "Tirada Larga" in tipo or "tirada_larga" in tipo:
        return [
            {"zona": "Z1", "duracion_min": 10,           "tipo": "warmup"},
            {"zona": "Z2", "duracion_min": dur_principal, "tipo": "interval"},
            {"zona": "Z1", "duracion_min": 10,            "tipo": "cooldown"},
        ]
    if "Progresiva" in tipo or "progresiva" in tipo:
        bloque = max(dur_principal / 4, 5)
        return [
            {"zona": "Z1", "duracion_min": 10,     "tipo": "warmup"},
            {"zona": "Z2", "duracion_min": bloque,  "tipo": "interval"},
            {"zona": "Z3", "duracion_min": bloque,  "tipo": "interval"},
            {"zona": "Z4", "duracion_min": bloque,  "tipo": "interval"},
            {"zona": "Z1", "duracion_min": 5,       "tipo": "cooldown"},
        ]
    if "Tempo" in tipo or "tempo" in tipo:
        return [
            {"zona": "Z1", "duracion_min": 10,           "tipo": "warmup"},
            {"zona": "Z4", "duracion_min": dur_principal, "tipo": "interval"},
            {"zona": "Z1", "duracion_min": 10,            "tipo": "cooldown"},
        ]
    if "Fartlek" in tipo or "fartlek" in tipo:
        n_series = max(int(dur_principal / 6), 2)
        bloques = [{"zona": "Z1", "duracion_min": 10, "tipo": "warmup"}]
        for _ in range(n_series):
            bloques.append({"zona": "Z4", "duracion_min": 3, "tipo": "interval"})
            bloques.append({"zona": "Z2", "duracion_min": 3, "tipo": "recovery"})
        bloques.append({"zona": "Z1", "duracion_min": 5, "tipo": "cooldown"})
        return bloques
    if "Intervalos" in tipo or "vo2max" in tipo:
        return [
            {"zona": "Z1", "duracion_min": 10, "tipo": "warmup"},
            {"zona": "Z5", "duracion_min": 4,  "tipo": "interval"},
            {"zona": "Z1", "duracion_min": 2,  "tipo": "recovery"},
            {"zona": "Z5", "duracion_min": 4,  "tipo": "interval"},
            {"zona": "Z1", "duracion_min": 2,  "tipo": "recovery"},
            {"zona": "Z5", "duracion_min": 4,  "tipo": "interval"},
            {"zona": "Z1", "duracion_min": 10, "tipo": "cooldown"},
        ]
    # Regenerativo / Carrera Z2 / fallback
    return [
        {"zona": "Z1", "duracion_min": 5,            "tipo": "warmup"},
        {"zona": "Z2", "duracion_min": dur_principal, "tipo": "interval"},
        {"zona": "Z1", "duracion_min": 5,             "tipo": "cooldown"},
    ]


def crear_workout_garmin(sesion: dict, gc) -> str:
    """
    Sube el workout a Garmin Connect via gc.upload_workout(dict).
    Retorna workout_id (str) del workout creado.
    Lanza excepción con mensaje claro si falla.
    """
    fecha_str = sesion.get("fecha", datetime.now().strftime("%Y-%m-%d"))
    nombre = f"{sesion.get('tipo', 'Entrenamiento')} — {fecha_str}"
    bloques = sesion_a_bloques(sesion)

    steps = []
    for i, bloque in enumerate(bloques, start=1):
        steps.append(_step(i, bloque["zona"], bloque["duracion_min"], bloque["tipo"]))

    workout_json = {
        "workoutName": nombre,
        "sportType": _SPORT,
        "estimatedDurationInSecs": int(sum(b["duracion_min"] for b in bloques) * 60),
        "workoutSegments": [{
            "segmentOrder": 1,
            "sportType": _SPORT,
            "workoutSteps": steps,
        }],
    }

    try:
        resp = gc.upload_workout(workout_json)
        workout_id = str(resp.get("workoutId") or resp.get("id") or "OK")
        return workout_id
    except Exception as e:
        raise RuntimeError(f"Error subiendo workout a Garmin: {e}") from e


def programar_workout_garmin(gc, workout_id: str, fecha: str) -> bool:
    """
    Asigna el workout al calendario Garmin en la fecha indicada.
    fecha formato: "2026-04-01"
    Usa POST /workout-service/schedule/{workoutId} con {"date": fecha}.
    Retorna True si éxito, False si falla (no lanza excepción).
    """
    try:
        gc.client.post(
            "connectapi",
            f"/workout-service/schedule/{int(workout_id)}",
            json={"date": fecha},
            api=True,
        )
        return True
    except Exception:
        return False
