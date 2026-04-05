"""
src/plan/memoria_fuerza.py
Progresión de ejercicios de fuerza y generación de tabla semanal con pesos sugeridos.
"""

import pandas as pd

# ---------------------------------------------------------------------------
# Esquemas por fase del macrociclo
# ---------------------------------------------------------------------------

_ESQUEMAS = {
    "Acondicionamiento":    {"series": 3, "reps": "12-15", "pct_1rm": 0.67, "nota": "65-70% 1RM, foco glúteo"},
    "Preparación General":  {"series": 4, "reps": "4-6",   "pct_1rm": 0.875,"nota": "85-90% 1RM, fuerza máxima"},
    "Preparación Específica":{"series": 2,"reps": "8",     "pct_1rm": 0.80, "nota": "Mantenimiento de peso"},
    "Pico de Forma":        {"series": 2, "reps": "8-10",  "pct_1rm": 0.75, "nota": "Funcional/movilidad"},
    "Tapering":             {"series": 2, "reps": "10",    "pct_1rm": 0.65, "nota": "Activación mínima"},
}

# Ejercicios siempre incluidos + grupo muscular
_EJERCICIOS_BASE = [
    {"ejercicio": "Hip Thrust",           "grupo": "Glúteos",          "peso_referencia": 40},
    {"ejercicio": "Sentadilla Búlgara",   "grupo": "Glúteos/Cuádriceps","peso_referencia": 14},
    {"ejercicio": "Dominadas",            "grupo": "Espalda/Bíceps",   "peso_referencia": 0},
    {"ejercicio": "Peso Muerto Rumano",   "grupo": "Isquios/Glúteos",  "peso_referencia": 30},
    {"ejercicio": "Press Banca",          "grupo": "Pecho/Tríceps",    "peso_referencia": 20},
    {"ejercicio": "Prensa 45°",           "grupo": "Cuádriceps",       "peso_referencia": 60},
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
                                 semaforo: dict, conn) -> list:
    """
    Genera lista de ejercicios con pesos sugeridos según fase y semáforo.
    Si semáforo ROJO → reducir series a 2 y peso al 80%.
    Si semáforo ÁMBAR → mantener peso actual sin subir.
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

        if color == "rojo":
            series = min(series, 2)
            peso = round(float(prog["peso_actual"]) * 0.80 / 2.5) * 2.5
            razon = "Semáforo rojo — -20% peso"
        elif color == "ambar":
            peso = prog["peso_actual"]  # no subir
            razon = f"Semáforo ámbar — {prog['razon']} (sin subir)"
        else:
            razon = prog["razon"]

        filas.append({
            "Ejercicio": ej["ejercicio"],
            "Grupo": ej["grupo"],
            "Series": series,
            "Reps": reps,
            "Peso (kg)": peso if peso > 0 else "Peso corporal",
            "Nota": f"{esquema['nota']} · {razon}",
        })

    return filas
