"""
src/plan/protocolo_selector.py
Selector dinámico de Protocolo A (Fuerza Prioridad) vs Protocolo B (Híbrido Real)
Recomienda según fase del macrociclo, pero permite override manual.
"""


def recomendar_protocolo(fase_nombre: str, acwr: float = 1.0) -> dict:
    """
    Recomienda Protocolo A o B según la fase del macrociclo.

    Protocolo A: Fuerza como Prioridad
    - Fases: Acondicionamiento, Preparación General
    - Fuerza: 2-3 días/semana @ 70-95% 1RM, 5-12 reps
    - Carrera: ≤2 días/semana @ Z2 baja (<165 ppm)
    - Objetivo: Construir fuerza base e hipertrofia

    Protocolo B: Rendimiento en Carrera (Híbrido Real)
    - Fases: Preparación Específica, Pico de Forma, Tapering
    - Fuerza: 1-2 días/semana @ 80% 1RM, <6 reps (funcional)
    - Carrera: 3-5 días/semana con regla 80/20
    - Objetivo: Optimizar rendimiento carrera, mantener fuerza útil

    Retorna:
    {
        "protocolo": "A" | "B",
        "recomendacion": str (ej: "Fase Preparación General → Protocolo A"),
        "dias_fuerza": int,
        "reps_fuerza": str (ej: "5-12"),
        "pct_1rm": str (ej: "70-95%"),
        "dias_carrera_min": int,
        "carrera_intensidad_dominante": "Z2" | "80/20",
        "enfoque_resumen": str,
        "permitir_override": bool,
    }
    """

    fase_lower = str(fase_nombre).lower()

    # ---- PROTOCOLO A: Acondicionamiento + Preparación General ----
    if any(x in fase_lower for x in ("acondicionamiento", "preparacion general")):
        return {
            "protocolo": "A",
            "recomendacion": f"Fase '{fase_nombre}' → Protocolo A (Fuerza Prioridad)",
            "dias_fuerza": 3,
            "reps_fuerza": "5-12",
            "pct_1rm": "70-95%",
            "dias_carrera_min": 2,
            "carrera_intensidad_dominante": "Z2",
            "enfoque_resumen": "Construir fuerza base e hipertrofia. Carrera como complemento.",
            "permitir_override": True,
        }

    # ---- PROTOCOLO B: Preparación Específica + Pico + Tapering ----
    elif any(x in fase_lower for x in ("preparacion especifica", "pico", "tapering")):
        return {
            "protocolo": "B",
            "recomendacion": f"Fase '{fase_nombre}' → Protocolo B (Híbrido Real)",
            "dias_fuerza": 1,
            "reps_fuerza": "<6",
            "pct_1rm": "80%+",
            "dias_carrera_min": 3,
            "carrera_intensidad_dominante": "80/20",
            "enfoque_resumen": "Optimizar rendimiento carrera. Fuerza funcional y mantenimiento.",
            "permitir_override": True,
        }

    # ---- DEFAULT: Protocolo B si no reconoce la fase ----
    return {
        "protocolo": "B",
        "recomendacion": f"Fase desconocida '{fase_nombre}' → Protocolo B (default)",
        "dias_fuerza": 1,
        "reps_fuerza": "<6",
        "pct_1rm": "80%+",
        "dias_carrera_min": 3,
        "carrera_intensidad_dominante": "80/20",
        "enfoque_resumen": "Plan híbrido estándar.",
        "permitir_override": True,
    }


def validar_protocolo_seleccionado(protocolo_seleccionado: str | None, protocolo_recomendado: str) -> dict:
    """
    Valida si el protocolo seleccionado por el usuario es consistente.
    Si no selecciona, usa el recomendado.

    Retorna:
    {
        "protocolo_final": "A" | "B",
        "es_override": bool (True si usuario cambió la recomendación),
        "advertencia": str | None,
    }
    """
    if not protocolo_seleccionado or protocolo_seleccionado not in ("A", "B"):
        return {
            "protocolo_final": protocolo_recomendado,
            "es_override": False,
            "advertencia": None,
        }

    es_override = protocolo_seleccionado != protocolo_recomendado
    advertencia = None

    if es_override:
        if protocolo_seleccionado == "A" and protocolo_recomendado == "B":
            advertencia = "⚠️ Overriding Protocolo B → A. Riesgo: menos carrera de calidad en fase específica."
        elif protocolo_seleccionado == "B" and protocolo_recomendado == "A":
            advertencia = "⚠️ Overriding Protocolo A → B. Riesgo: menos desarrollo de fuerza en acondicionamiento."

    return {
        "protocolo_final": protocolo_seleccionado,
        "es_override": es_override,
        "advertencia": advertencia,
    }


def obtener_restricciones_protocolo(protocolo: str) -> dict:
    """
    Retorna restricciones específicas del protocolo para distribuir sesiones.
    """
    if protocolo == "A":
        return {
            "max_dias_carrera_consecutivos": 2,
            "min_descanso_entre_carrera_calidad": 2,  # días
            "permite_fuerza_pierna_antes_carrera_calidad": False,
            "carrera_calidad_max_km": 12,
        }
    else:  # Protocolo B
        return {
            "max_dias_carrera_consecutivos": 3,
            "min_descanso_entre_carrera_calidad": 1,  # días
            "permite_fuerza_pierna_antes_carrera_calidad": True,  # pero validar interferencia
            "carrera_calidad_max_km": 20,
        }
