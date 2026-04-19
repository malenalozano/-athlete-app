"""
src/plan/interferencia_detector.py
Detector de Interferencia Fuerza-Carrera (Zona de Muerte)
Previene combinaciones que maximizan interferencia (cancelan adaptaciones).

ZONA DE MUERTE:
- Pesas 10-12 reps (hipertrofia) + Carrera 95% capacidad (series/intervalos)
  en el MISMO DÍA o DÍAS CONSECUTIVOS SIN DESCANSO
"""


def evaluar_interferencia_dia(
    actividad_1: dict,
    actividad_2: dict | None = None,
) -> dict:
    """
    Evalúa interferencia entre dos actividades en el MISMO DÍA.

    actividad: {"tipo": "fuerza_pierna|fuerza_superior|carrera_z2|tempo|intervalos|...",
                "reps": int (si aplica), "pct_1rm": float (si aplica)}

    Retorna:
    {
        "interferencia_nivel": "nula" | "baja" | "moderada" | "alta" | "critica",
        "score": 0-100 (0=sin interferencia, 100=crítica),
        "permitido": bool,
        "razon": str,
        "recomendacion": str | None,
    }
    """

    if not actividad_2:
        # Una sola actividad por día = sin interferencia entre actividades
        return {
            "interferencia_nivel": "nula",
            "score": 0,
            "permitido": True,
            "razon": "Una actividad por día.",
            "recomendacion": None,
        }

    tipo1 = str(actividad_1.get("tipo", "")).lower()
    tipo2 = str(actividad_2.get("tipo", "")).lower()

    # Extraer características
    es_fuerza_pierna_1 = any(x in tipo1 for x in ("fuerza_pierna", "pierna", "leg"))
    es_carrera_calidad_1 = any(x in tipo1 for x in ("intervalo", "tempo", "progresiva", "fartlek", "calidad"))

    es_fuerza_pierna_2 = any(x in tipo2 for x in ("fuerza_pierna", "pierna", "leg"))
    es_carrera_calidad_2 = any(x in tipo2 for x in ("intervalo", "tempo", "progresiva", "fartlek", "calidad"))

    es_fuerza_superior_1 = any(x in tipo1 for x in ("fuerza_superior", "push", "pull", "tren_superior"))
    es_fuerza_superior_2 = any(x in tipo2 for x in ("fuerza_superior", "push", "pull", "tren_superior"))

    es_z2_1 = "z2" in tipo1 or "regenerat" in tipo1
    es_z2_2 = "z2" in tipo2 or "regenerat" in tipo2

    reps_1 = actividad_1.get("reps", 0)
    reps_2 = actividad_2.get("reps", 0)

    pct_1rm_1 = actividad_1.get("pct_1rm", 0)
    pct_1rm_2 = actividad_2.get("pct_1rm", 0)

    # ---- ZONA DE MUERTE CRÍTICA ----
    # Hipertrofia (10-12 reps, 65-70% 1RM) + Carrera alta intensidad (95%+ capacidad)
    if (
        (es_fuerza_pierna_1 and 9 <= reps_1 <= 13 and pct_1rm_1 <= 75)
        and (es_carrera_calidad_2)
    ) or (
        (es_fuerza_pierna_2 and 9 <= reps_2 <= 13 and pct_1rm_2 <= 75)
        and (es_carrera_calidad_1)
    ):
        return {
            "interferencia_nivel": "critica",
            "score": 95,
            "permitido": False,
            "razon": "ZONA DE MUERTE: Hipertrofia (10-12 reps) + Carrera de calidad el mismo día causan interferencia máxima.",
            "recomendacion": "❌ Cambia a Carrera Z2 hoy o mueve carrera al día siguiente (+48h de descanso).",
        }

    # ---- INTERFERENCIA ALTA ----
    # Fuerza pesada (3-6 reps, 80-95% 1RM) + Carrera calidad
    if (
        (es_fuerza_pierna_1 and reps_1 <= 6 and pct_1rm_1 >= 80)
        and (es_carrera_calidad_2)
    ) or (
        (es_fuerza_pierna_2 and reps_2 <= 6 and pct_1rm_2 >= 80)
        and (es_carrera_calidad_1)
    ):
        return {
            "interferencia_nivel": "alta",
            "score": 80,
            "permitido": False,
            "razon": "Fuerza pesada (80%+ 1RM) + Carrera de calidad el mismo día: interferencia muy alta.",
            "recomendacion": "❌ Cambiar orden: hacer Fuerza primero (recuperación 4h), luego Z2. O separar días.",
        }

    # ---- INTERFERENCIA MODERADA ----
    # Fuerza Pierna + Carrera Calidad en mismo día pero con suficiente descanso (4h+)
    # Permitido si hay separación clara, pero no ideal
    if (es_fuerza_pierna_1 and es_carrera_calidad_2) or (es_fuerza_pierna_2 and es_carrera_calidad_1):
        return {
            "interferencia_nivel": "moderada",
            "score": 50,
            "permitido": True,  # Permitido con cuidado
            "razon": "Fuerza Pierna + Carrera Calidad en mismo día: interferencia moderada si hay 4h+ entre sesiones.",
            "recomendacion": "⚠️ Separar 4h mínimo entre sesiones. Priorizar fuerza primero. Considerar otro día para carrera de calidad.",
        }

    # ---- BAJA INTERFERENCIA ----
    # Fuerza Tren Superior + Carrera (cualquier intensidad)
    if es_fuerza_superior_1 or es_fuerza_superior_2:
        return {
            "interferencia_nivel": "baja",
            "score": 20,
            "permitido": True,
            "razon": "Fuerza Tren Superior + Carrera: baja interferencia (piernas no están en conflicto).",
            "recomendacion": "✅ OK. Separar 2-3h si es posible.",
        }

    # ---- NINGUNA INTERFERENCIA ----
    # Carrera Z2 + Cualquier Fuerza, o Fuerza Pierna + Carrera Z2
    if (es_z2_1 or es_z2_2) or (es_fuerza_superior_1 and es_fuerza_superior_2):
        return {
            "interferencia_nivel": "nula",
            "score": 0,
            "permitido": True,
            "razon": "Combinación sin interferencia.",
            "recomendacion": None,
        }

    return {
        "interferencia_nivel": "baja",
        "score": 15,
        "permitido": True,
        "razon": "Combinación aceptable.",
        "recomendacion": None,
    }


def evaluar_interferencia_48h(
    dia_actual: dict,
    dia_anterior: dict | None = None,
    dias_anteriores: list | None = None,
) -> dict:
    """
    Evalúa interferencia entre sesiones en DIFERENTES DÍAS (ventana de 48-72h).

    Ejemplo problema:
    - Viernes: Fuerza Pierna (3×12)
    - Sábado: Intervalos 5×1km
    → Interferencia alta (no hay recuperación)

    Retorna:
    {
        "interferencia_48h": "nula" | "baja" | "moderada" | "alta",
        "score": 0-100,
        "permitido": bool,
        "dias_conflictivos": [(dia1, dia2), ...],
        "recomendacion": str | None,
    }
    """

    dias_anteriores = dias_anteriores or []
    conflictos = []
    score_max = 0

    # Evaluar contra día anterior
    if dia_anterior:
        eval_48h = evaluar_interferencia_dia(dia_anterior, dia_actual)
        if eval_48h["score"] > 50:
            conflictos.append((dia_anterior.get("nombre", "Día anterior"), dia_actual.get("nombre", "Día actual")))
            score_max = max(score_max, eval_48h["score"])

    # Evaluar contra hace 2 días
    if len(dias_anteriores) >= 2:
        dia_2d_atras = dias_anteriores[-1]
        eval_72h = evaluar_interferencia_dia(dia_2d_atras, dia_actual)
        if eval_72h["score"] > 40:  # Umbral más bajo para 72h
            conflictos.append((dia_2d_atras.get("nombre", "Hace 2 días"), dia_actual.get("nombre", "Día actual")))
            score_max = max(score_max, eval_72h["score"])

    # Clasificar severidad
    if score_max >= 80:
        nivel = "alta"
        permitido = False
    elif score_max >= 50:
        nivel = "moderada"
        permitido = True
    elif score_max > 0:
        nivel = "baja"
        permitido = True
    else:
        nivel = "nula"
        permitido = True

    recomendacion = None
    if conflictos:
        if nivel == "alta":
            recomendacion = f"❌ Interferencia ALTA entre {conflictos[0][0]} y {conflictos[0][1]}. Cambiar {dia_actual.get('nombre')} a otro día o reducir intensidad."
        elif nivel == "moderada":
            recomendacion = f"⚠️ Interferencia moderada. Considera separar más {conflictos[0][0]} y {conflictos[0][1]}, o reducir volumen."

    return {
        "interferencia_48h": nivel,
        "score": score_max,
        "permitido": permitido,
        "dias_conflictivos": conflictos,
        "recomendacion": recomendacion,
    }
