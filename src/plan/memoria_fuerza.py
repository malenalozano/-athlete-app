"""
src/plan/memoria_fuerza.py
Progresión de ejercicios de fuerza y generación de tabla semanal con pesos sugeridos.
"""

import pandas as pd

# ---------------------------------------------------------------------------
# Esquemas por fase del macrociclo
# ---------------------------------------------------------------------------

_ESQUEMAS = {
    "Acondicionamiento":    {"series": 3, "reps": "12-15", "pct_1rm": 0.67, "nota": "65-70% 1RM, hipertrofia funcional"},
    "Preparación General":  {"series": 4, "reps": "4-6",   "pct_1rm": 0.875,"nota": "85-90% 1RM, fuerza máxima"},
    "Preparación Específica":{"series": 2,"reps": "8",     "pct_1rm": 0.80, "nota": "Mantenimiento de peso"},
    "Pico de Forma":        {"series": 2, "reps": "8-10",  "pct_1rm": 0.75, "nota": "Funcional/movilidad"},
    "Tapering":             {"series": 2, "reps": "10",    "pct_1rm": 0.65, "nota": "Activación mínima"},
}

# Ejercicios organizados por día de fuerza + grupo muscular
_EJERCICIOS_BASE = [
    {"dia_fuerza": "Push", "ejercicio": "Press Banca",        "grupo": "Pecho/Tríceps",        "peso_referencia": 20},
    {"dia_fuerza": "Push", "ejercicio": "Press Militar",      "grupo": "Hombro/Tríceps",      "peso_referencia": 16},
    {"dia_fuerza": "Push", "ejercicio": "Fondos en Paralelas", "grupo": "Pecho/Tríceps",       "peso_referencia": 0},

    {"dia_fuerza": "Pull", "ejercicio": "Dominadas",          "grupo": "Espalda/Bíceps",       "peso_referencia": 0},
    {"dia_fuerza": "Pull", "ejercicio": "Remo con Barra",     "grupo": "Espalda/Bíceps",       "peso_referencia": 35},
    {"dia_fuerza": "Pull", "ejercicio": "Face Pull",          "grupo": "Deltoides post./Trapecio", "peso_referencia": 15},

    {"dia_fuerza": "Tren inferior + glúteo", "ejercicio": "Hip Thrust",         "grupo": "Glúteos",            "peso_referencia": 40},
    {"dia_fuerza": "Tren inferior + glúteo", "ejercicio": "Sentadilla Búlgara", "grupo": "Glúteos/Cuádriceps", "peso_referencia": 14},
    {"dia_fuerza": "Tren inferior + glúteo", "ejercicio": "Peso Muerto Rumano", "grupo": "Isquios/Glúteos",    "peso_referencia": 30},
    {"dia_fuerza": "Tren inferior + glúteo", "ejercicio": "Prensa 45°",         "grupo": "Cuádriceps",         "peso_referencia": 60},
]


def obtener_progresion_ejercicio(usuario_id: int, ejercicio: str, conn) -> dict:
    """
    Lee últimas 4 sesiones del ejercicio desde ejercicios_fuerza.
    Lógica de progresión:
    - Sin historial → peso_referencia del catálogo.
    - Sensaciones vacías o 'técnica perfecta' → +2.5% peso.
    - Corrida semanal subió >10% → mantener pesos (0% incremento).
    - Resto → mantener o +1 rep si se llegó al tope del rango.
    """
    df = pd.read_sql_query(
        """SELECT e.ejercicio, e.peso, e.repeticiones, e.rpe, e.sensaciones, s.fecha
           FROM ejercicios_fuerza e
           JOIN sesiones_fuerza s ON s.id = e.sesion_id
           WHERE s.usuario_id=? AND LOWER(e.ejercicio) LIKE ?
           ORDER BY s.fecha DESC LIMIT 4""",
        conn, params=(usuario_id, f"%{ejercicio.lower()}%"))

    if df.empty:
        ref = next((e["peso_referencia"] for e in _EJERCICIOS_BASE
                    if ejercicio.lower() in e["ejercicio"].lower()), 0)
        return {"peso_actual": ref, "reps_actual": 10,
                "sugerencia_peso": ref, "sugerencia_reps": 10,
                "razon": "Sin historial — usando peso de referencia"}

    ultima = df.iloc[0]
    peso_actual = float(ultima["peso"] or 0)
    reps_actual = int(ultima["repeticiones"] or 0)
    sensaciones = str(ultima["sensaciones"] or "").lower().strip()

    if not sensaciones or "técnica perfecta" in sensaciones or "bien" in sensaciones:
        sugerencia_peso = round(peso_actual * 1.025 / 2.5) * 2.5  # redondear a 2.5kg
        sugerencia_reps = reps_actual
        razon = "Técnica correcta — progresión +2.5% peso"
    elif "pesado" in sensaciones or "difícil" in sensaciones or "malo" in sensaciones:
        sugerencia_peso = peso_actual
        sugerencia_reps = reps_actual
        razon = "Sensaciones negativas — mantener carga"
    else:
        sugerencia_peso = peso_actual
        sugerencia_reps = reps_actual + 1
        razon = "Mantener peso, añadir 1 repetición"

    return {"peso_actual": peso_actual, "reps_actual": reps_actual,
            "sugerencia_peso": sugerencia_peso, "sugerencia_reps": sugerencia_reps,
            "razon": razon}


def generar_tabla_fuerza_semana(usuario_id: int, fase_macrociclo: dict,
                                 semaforo: dict, acwr: float = None, conn=None) -> list:
    """
    Genera lista de ejercicios con pesos sugeridos según fase y división muscular:
    Push, Pull y Tren inferior + glúteo.
    El semáforo de recuperación solo añade recomendaciones visuales.
    Si ACWR > 1.3 → reducir series -1 pero mantener peso (calidad > cantidad).
    Devuelve lista de dicts listos para st.dataframe.
    """
    fase_nombre = fase_macrociclo.get("fase_nombre", "Acondicionamiento")
    esquema_key = next((k for k in _ESQUEMAS if k in fase_nombre), "Acondicionamiento")
    esquema = _ESQUEMAS[esquema_key]

    color = semaforo.get("color", "verde")
    filas = []

    for ej in _EJERCICIOS_BASE:
        prog = obtener_progresion_ejercicio(usuario_id, ej["ejercicio"], conn)

        series = esquema["series"]
        reps = esquema["reps"]
        peso = prog["sugerencia_peso"]
        razon = prog["razon"]

        if acwr is not None and acwr > 1.3:
            # ACWR alto: reducir series pero mantener peso (calidad biomecánica)
            series = max(series - 1, 2)
            razon = f"{prog['razon']} · ACWR {acwr:.2f} alto — mantener peso, -1 serie"

        # Semáforo solo informativo: no altera series ni peso.
        if color == "rojo":
            razon = f"{razon} · Recomendación recuperación baja: ajusta intensidad si hay fatiga"
        elif color == "ambar":
            razon = f"{razon} · Recomendación recuperación moderada: valora reducir exigencia"
        
        filas.append({
            "Día": ej["dia_fuerza"],
            "Ejercicio": ej["ejercicio"],
            "Grupo": ej["grupo"],
            "Series": series,
            "Reps": reps,
            "Peso (kg)": peso if peso > 0 else "Peso corporal",
            "Nota": f"{esquema['nota']} · {razon}",
        })

    return filas
