"""
src/plan/reglas.py
Reglas fisiológicas del macrociclo: semáforo HRV/sueño, catálogo de lesiones,
volumen semanal, cadencia y validación de sesiones concurrentes.
"""

import pandas as pd
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# 1. DIRECTOR DE ORQUESTA
# ---------------------------------------------------------------------------

def obtener_fase_macrociclo(fecha_actual=None) -> dict:
    """
    Retorna fase activa, volumen máx, días fuerza, enfoques y restricciones.
    Maratón objetivo: febrero.
    FIX tapering: segunda quincena de enero = pre-tapering (volumen -20%, sin series largas).
    Enero primera quincena = Pico de Forma. Enero segunda quincena = Tapering.
    """
    if fecha_actual is None:
        fecha_actual = datetime.now()
    mes = fecha_actual.month
    dia = fecha_actual.day

    if mes in [3, 4, 5]:
        return {"fase_nombre": "Acondicionamiento", "km_semanales_max": 30, "dias_fuerza": 4,
                "enfoque_fuerza": "Hipertrofia base y glúteo (3×12-15, 65-70% 1RM)",
                "enfoque_running": "Base aeróbica Z2. Bici/elíptica en días de tibia.",
                "sesion_calidad": "progresiva",
                "restricciones": {"limitar_impacto": True, "permitir_series": False}}
    if mes in [6, 7, 8]:
        return {"fase_nombre": "Preparación General", "km_semanales_max": 45, "dias_fuerza": 3,
                "enfoque_fuerza": "Fuerza Máxima (4×4-6, 85-90% 1RM)",
                "enfoque_running": "Construcción de resistencia aeróbica.",
                "sesion_calidad": "intervalos_vo2max",
                "restricciones": {"limitar_impacto": False, "permitir_series": True}}
    if mes in [9, 10, 11]:
        return {"fase_nombre": "Preparación Específica", "km_semanales_max": 60, "dias_fuerza": 2,
                "enfoque_fuerza": "Mantenimiento (2×8, mismo peso)",
                "enfoque_running": "Ritmos competición. Media Maratón noviembre.",
                "sesion_calidad": "tempo",
                "restricciones": {"limitar_impacto": False, "permitir_series": True}}
    if mes == 12:
        return {"fase_nombre": "Pico de Forma", "km_semanales_max": 75, "dias_fuerza": 2,
                "enfoque_fuerza": "Funcional: core y estabilidad",
                "enfoque_running": "Tiradas largas y ritmo Maratón.",
                "sesion_calidad": "tempo",
                "restricciones": {"limitar_impacto": False, "permitir_series": True}}
    if mes == 1:
        if dia <= 15:
            # Primera quincena enero: último bloque de carga máxima
            return {"fase_nombre": "Pico de Forma", "km_semanales_max": 75, "dias_fuerza": 2,
                    "enfoque_fuerza": "Funcional: core y estabilidad",
                    "enfoque_running": "Tiradas largas y ritmo Maratón.",
                    "sesion_calidad": "tempo",
                    "restricciones": {"limitar_impacto": False, "permitir_series": True}}
        else:
            # Segunda quincena enero: pre-tapering — reducir volumen progresivamente
            return {"fase_nombre": "Tapering", "km_semanales_max": 50, "dias_fuerza": 1,
                    "enfoque_fuerza": "Movilidad, core y activación",
                    "enfoque_running": "Reducción progresiva. Ritmo maratón en tirada larga.",
                    "sesion_calidad": "progresiva",
                    "restricciones": {"limitar_impacto": True, "permitir_series": False}}
    if mes == 2:
        return {"fase_nombre": "Tapering", "km_semanales_max": 30, "dias_fuerza": 1,
                "enfoque_fuerza": "Movilidad y activación mínima",
                "enfoque_running": "Supercompensación (GAS). Mínima fatiga.",
                "sesion_calidad": "progresiva",
                "restricciones": {"limitar_impacto": True, "permitir_series": False}}
    return {"fase_nombre": "Desconocida", "km_semanales_max": 20, "dias_fuerza": 2,
            "enfoque_fuerza": "", "enfoque_running": "", "sesion_calidad": "progresiva",
            "restricciones": {"limitar_impacto": False, "permitir_series": False}}


def obtener_fase_macrociclo_ultra(fecha_actual=None, fecha_carrera_str: str = "2026-09-19") -> dict:
    """
    Macrociclo dinámico para ultramaratón calculado hacia atrás desde fecha_carrera.
    Fases (semanas antes de la carrera):
      Tapering        : 3 semanas antes
      Pico de Forma   : 6 semanas antes del tapering (semanas 4–9)
      Prep. Específica: 8 semanas (semanas 10–17) — volumen + elevación + back-to-back
      Prep. General   : 8 semanas (semanas 18–25) — construcción base ultra
      Acondicionamiento: todo lo anterior
    """
    if fecha_actual is None:
        fecha_actual = datetime.now()
    try:
        fecha_carrera = datetime.strptime(fecha_carrera_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        fecha_carrera = datetime(2026, 9, 19)

    dias_para_carrera = (fecha_carrera - fecha_actual).days

    # Límites en días antes de la carrera
    TAPERING_INICIO   = 21    # 3 semanas
    PICO_INICIO       = 21 + 42   # 9 semanas
    ESPECIFICA_INICIO = 21 + 42 + 56   # 17 semanas
    GENERAL_INICIO    = 21 + 42 + 56 + 56   # 25 semanas

    if dias_para_carrera < 0:
        return {"fase_nombre": "Post-Carrera", "km_semanales_max": 40, "dias_fuerza": 2,
                "enfoque_fuerza": "Recuperación activa: movilidad y fuerza ligera",
                "enfoque_running": "Recuperación progresiva. Volumen muy bajo.",
                "sesion_calidad": "progresiva",
                "restricciones": {"limitar_impacto": True, "permitir_series": False},
                "fecha_carrera": fecha_carrera_str}
    if dias_para_carrera <= TAPERING_INICIO:
        return {"fase_nombre": "Tapering", "km_semanales_max": 50, "dias_fuerza": 1,
                "enfoque_fuerza": "Movilidad y activación mínima",
                "enfoque_running": "Supercompensación. Mínima fatiga. Algún ritmo objetivo.",
                "sesion_calidad": "progresiva",
                "restricciones": {"limitar_impacto": True, "permitir_series": False},
                "fecha_carrera": fecha_carrera_str}
    if dias_para_carrera <= PICO_INICIO:
        return {"fase_nombre": "Pico de Forma", "km_semanales_max": 120, "dias_fuerza": 1,
                "enfoque_fuerza": "Funcional: core, estabilidad y fuerza excéntrica",
                "enfoque_running": "Back-to-back largos. Ritmo ultra. Elevación máxima.",
                "sesion_calidad": "tempo",
                "restricciones": {"limitar_impacto": False, "permitir_series": True},
                "fecha_carrera": fecha_carrera_str}
    if dias_para_carrera <= ESPECIFICA_INICIO:
        return {"fase_nombre": "Preparación Específica", "km_semanales_max": 100, "dias_fuerza": 2,
                "enfoque_fuerza": "Fuerza excéntrica (nórdico, sentadilla búlgara). Cadera.",
                "enfoque_running": "Simulacros de carrera: elevación, back-to-back, ritmo ultra.",
                "sesion_calidad": "tempo",
                "restricciones": {"limitar_impacto": False, "permitir_series": True},
                "fecha_carrera": fecha_carrera_str}
    if dias_para_carrera <= GENERAL_INICIO:
        return {"fase_nombre": "Preparación General", "km_semanales_max": 80, "dias_fuerza": 2,
                "enfoque_fuerza": "Fuerza Máxima (4×4-6, 85-90% 1RM). Glúteo y core.",
                "enfoque_running": "Construcción de volumen aeróbico base. Primer desnivel.",
                "sesion_calidad": "intervalos_vo2max",
                "restricciones": {"limitar_impacto": False, "permitir_series": True},
                "fecha_carrera": fecha_carrera_str}
    return {"fase_nombre": "Acondicionamiento", "km_semanales_max": 60, "dias_fuerza": 3,
            "enfoque_fuerza": "Hipertrofia base y glúteo (3×12-15, 65-70% 1RM)",
            "enfoque_running": "Base aeróbica Z2. Foco en técnica de trail.",
            "sesion_calidad": "progresiva",
            "restricciones": {"limitar_impacto": True, "permitir_series": False},
            "fecha_carrera": fecha_carrera_str}


def obtener_fase_macrociclo_usuario(usuario_id: int = 1, fecha_actual=None) -> dict:
    """
    Dispatcher: usa macrociclo Maratón (Malena) o Ultra dinámico (Dani / objetivo_tipo='ultramaraton').
    Si no se puede cargar el perfil, usa macrociclo maratón por defecto.
    """
    if fecha_actual is None:
        fecha_actual = datetime.now()
    try:
        from src.db.db_manager import obtener_perfil
        perfil = obtener_perfil(usuario_id) or {}
        objetivo_tipo = str(perfil.get("objetivo_tipo") or "").lower()
        fecha_objetivo = perfil.get("fecha_objetivo")
        if objetivo_tipo in ("ultramaraton", "ultra", "trail_ultra") and fecha_objetivo:
            return obtener_fase_macrociclo_ultra(fecha_actual, fecha_objetivo)
    except Exception:
        pass
    return obtener_fase_macrociclo(fecha_actual)


# ---------------------------------------------------------------------------
# 2. SEMÁFORO HRV + SUEÑO
# ---------------------------------------------------------------------------

def calcular_semaforo(hrv_actual, hrv_media_7d, sleep_score,
                      sleep_breakdown=None, estres_medio=None,
                      body_battery_min=None, training_status=None) -> dict:
    """
    Semáforo de recuperación multi-señal:
    - VERDE:  HRV >= media + sleep > 85 + no factores negativos → plan completo, PR permitido.
    - ÁMBAR:  HRV cae 0-10% O sleep 60-80 O stress > 70 O body battery < 20 al levantarse.
    - ROJO:   HRV cae > 10% O sleep < 60 O sueño profundo < 45min O training_status=overreaching.
    Sin datos HRV: VERDE por defecto (no penalizar sin información).
    Retorna también "causa" para diferentes restricciones según factor.
    """
    razones_rojo = []
    razones_ambar = []
    causa_rojo = []
    causa_ambar = []

    # — HRV —
    caida = 0.0
    if hrv_actual is not None and hrv_media_7d and hrv_media_7d > 0:
        caida = (hrv_media_7d - hrv_actual) / hrv_media_7d
        if caida > 0.10:
            razones_rojo.append(f"HRV caído {caida*100:.0f}%")
            causa_rojo.append("hrv")
        elif caida > 0.0:
            razones_ambar.append(f"HRV ligeramente bajo (-{caida*100:.0f}%)")
            causa_ambar.append("hrv")
    elif hrv_actual is None and hrv_media_7d is None:
        return {"color": "verde", "mensaje": "Sin datos HRV — plan base aplicado.",
                "multiplicador_volumen": 1.0, "permitir_calidad": True, "causa": []}

    # — Sleep score —
    if sleep_score is not None:
        if sleep_score < 60:
            razones_rojo.append(f"Sleep score crítico ({sleep_score}/100)")
            causa_rojo.append("sleep")
        elif sleep_score <= 80:
            razones_ambar.append(f"Sleep score subóptimo ({sleep_score}/100)")
            causa_ambar.append("sleep")

    # — Sleep profundo (< 45 min = 0.75 h → señal rojo) —
    if sleep_breakdown:
        prof = sleep_breakdown.get("profundo_h")
        if prof is not None and prof < 0.75:
            razones_rojo.append(f"Sueño profundo insuficiente ({prof*60:.0f} min)")
            causa_rojo.append("sleep")
        rem = sleep_breakdown.get("rem_h")
        if rem is not None and rem < 1.0:
            razones_ambar.append(f"REM escaso ({rem:.1f} h)")
            causa_ambar.append("sleep")

    # — Estrés —
    if estres_medio is not None:
        if estres_medio > 75:
            razones_rojo.append(f"Estrés muy alto ({estres_medio})")
            causa_rojo.append("stress")
        elif estres_medio > 55:
            razones_ambar.append(f"Estrés elevado ({estres_medio})")
            causa_ambar.append("stress")

    # — Body Battery —
    if body_battery_min is not None:
        if body_battery_min < 10:
            razones_rojo.append(f"Body Battery crítico al levantarse ({body_battery_min})")
            causa_rojo.append("battery")
        elif body_battery_min < 25:
            razones_ambar.append(f"Body Battery bajo ({body_battery_min})")
            causa_ambar.append("battery")

    # — Training Status Garmin —
    if training_status:
        ts = training_status.lower()
        if any(k in ts for k in ("overreaching", "strained", "detraining")):
            razones_rojo.append(f"Training Status: {training_status}")
            causa_rojo.append("training_status")
        elif any(k in ts for k in ("maintaining", "recovery", "unproductive")):
            razones_ambar.append(f"Training Status: {training_status}")
            causa_ambar.append("training_status")

    # — Decisión final —
    if razones_rojo:
        hrv_msg = f"HRV -{caida*100:.0f}%" if caida > 0 else "recuperación baja"
        return {
            "color": "rojo",
            "mensaje": f"💡 Recuperación baja ({hrv_msg}) — El plan se genera completo. Recomendación: considera hacer la sesión de mayor intensidad regenerativa si te encuentras muy fatigada. Señales: " + "; ".join(razones_rojo),
            "multiplicador_volumen": 1.0,  # NO modifica automáticamente
            "permitir_calidad": True,  # NO bloquea automáticamente
            "causa": list(set(causa_rojo)),
            "nota": "⚠️ Este es solo un AVISO. El plan NO se modifica automáticamente. Usa el 'Target Intensity' diario para decidir qué hacer.",
        }
    if razones_ambar:
        return {
            "color": "ambar",
            "mensaje": "💡 Recuperación moderada — Plan completo. Si lo necesitas, reduce la intensidad de la sesión más exigente. Señales: " + "; ".join(razones_ambar),
            "multiplicador_volumen": 1.0,  # NO modifica automáticamente
            "permitir_calidad": True,  # NO bloquea automáticamente
            "causa": list(set(causa_ambar)),
            "nota": "ℹ️ Este es solo un AVISO. El plan NO se modifica automáticamente. Usa el 'Target Intensity' diario para decidir qué hacer.",
        }
    return {
        "color": "verde",
        "mensaje": "Recuperación óptima. Entrenamiento completo.",
        "multiplicador_volumen": 1.0,
        "permitir_calidad": True,
        "causa": [],
    }


# ---------------------------------------------------------------------------
# 2.5. VO2MAX + TRAINING EFFECT
# ---------------------------------------------------------------------------

def evaluar_vo2max(vo2max: float | None, genero: str = "Mujer") -> dict:
    """
    Determina capacidad cardiaca y restringe sesiones high intensity.
    Umbrales diferenciados por género (21-25 años, corredor de resistencia):
      Mujer: bajo <35 | adecuado 35-40 | muy bueno 40-48 | excelente ≥48
      Hombre: bajo <42 | adecuado 42-50 | muy bueno 50-60 | excelente ≥60
    """
    if vo2max is None:
        return {"puede_alta_intensidad": True, "sesiones_max_intensidad": 2, "mensaje": None}

    vo2 = float(vo2max)
    es_hombre = str(genero).lower() in ("hombre", "male", "m")

    if es_hombre:
        if vo2 < 42:
            return {"puede_alta_intensidad": False, "sesiones_max_intensidad": 0,
                    "mensaje": "VO2max bajo — foco en base aeróbica (Z2). Evitar alta intensidad."}
        if vo2 < 50:
            return {"puede_alta_intensidad": True, "sesiones_max_intensidad": 1,
                    "mensaje": f"VO2max {vo2:.1f} (adecuado) — máximo 1 sesión de alta intensidad/semana."}
        if vo2 < 60:
            return {"puede_alta_intensidad": True, "sesiones_max_intensidad": 2,
                    "mensaje": f"VO2max {vo2:.1f} (muy bueno) — 2 sesiones de alta intensidad permitidas."}
        return {"puede_alta_intensidad": True, "sesiones_max_intensidad": 2,
                "mensaje": f"VO2max {vo2:.1f} (excelente) — capacidad cardíaca óptima."}
    else:
        # Mujer
        if vo2 < 35:
            return {"puede_alta_intensidad": False, "sesiones_max_intensidad": 0,
                    "mensaje": "VO2max bajo — foco en base aeróbica (Z2). Evitar alta intensidad."}
        if vo2 < 40:
            return {"puede_alta_intensidad": True, "sesiones_max_intensidad": 1,
                    "mensaje": f"VO2max {vo2:.1f} (adecuado) — máximo 1 sesión de alta intensidad/semana."}
        if vo2 < 48:
            return {"puede_alta_intensidad": True, "sesiones_max_intensidad": 2,
                    "mensaje": f"VO2max {vo2:.1f} (muy bueno) — 2 sesiones de alta intensidad permitidas."}
        return {"puede_alta_intensidad": True, "sesiones_max_intensidad": 2,
                "mensaje": f"VO2max {vo2:.1f} (excelente) — capacidad cardíaca óptima."}


def evaluar_training_effect(training_effect_aerobico: float | None,
                            training_effect_anaerobico: float | None,
                            ultimas_actividades: list) -> dict:
    """
    Detecta acumulación de fatiga neuro-muscular y cardiaca.
    ultimas_actividades = [{"tipo": "intervalos", "training_effect_aer": 3.8, "training_effect_ana": 4.2}, ...]
    """
    if not ultimas_actividades or len(ultimas_actividades) < 2:
        return {"necesita_descanso": False, "mensaje": None, "severidad": 0}

    # Promedio de training effect anaeróbico últimas 3 sesiones
    ana_effects = [a.get("training_effect_anaerobico", 0) for a in ultimas_actividades[:3]]
    ana_promedio = sum(ana_effects) / len(ana_effects) if ana_effects else 0

    # Promedio de training effect aeróbico
    aer_effects = [a.get("training_effect_aerobico", 0) for a in ultimas_actividades[:3]]
    aer_promedio = sum(aer_effects) / len(aer_effects) if aer_effects else 0

    severidad = 0
    mensajes = []

    if ana_promedio > 4.5:  # Acumulación anaeróbica alta
        severidad = 2
        mensajes.append(f"Acumulación anaeróbica muy alta ({ana_promedio:.1f}/5) — reducir series esta semana")
    elif ana_promedio > 4.0:  # Moderada
        severidad = 1
        mensajes.append(f"Acumulación anaeróbica moderada ({ana_promedio:.1f}/5) — cuidado con más series")

    if aer_promedio > 4.3:  # Fatiga cardiaca
        severidad = max(severidad, 2)
        mensajes.append(f"Fatiga cardiaca detectada (TE aer {aer_promedio:.1f}/5) — descanso recomendado")

    return {
        "necesita_descanso": severidad >= 2,
        "mensaje": " | ".join(mensajes) if mensajes else None,
        "severidad": severidad,
        "ana_promedio": round(ana_promedio, 1),
        "aer_promedio": round(aer_promedio, 1),
    }


# ---------------------------------------------------------------------------
# 3. CICLO MENSTRUAL
# ---------------------------------------------------------------------------

# Ventanas de rendimiento según fase del ciclo
_CICLO_FASES = {
    # Fase folicular (días 1-13): energía ascendente, buena tolerancia al entrenamiento
    "folicular": {
        "multiplicador_volumen": 1.0,
        "permitir_calidad": True,
        "mensaje": "Fase folicular — buena tolerancia al entrenamiento.",
        "hidratacion_extra": False,
    },
    # Ovulación (días 14-16): pico de rendimiento, ventana de alto desempeño
    "ovulatoria": {
        "multiplicador_volumen": 1.05,
        "permitir_calidad": True,
        "mensaje": "Fase ovulatoria — ventana de máximo rendimiento. Ideal para PR.",
        "hidratacion_extra": False,
    },
    # Fase lútea temprana (días 17-21): energía empieza a bajar
    "lutea": {
        "multiplicador_volumen": 0.85,
        "permitir_calidad": False,
        "mensaje": "Fase lútea — reducir volumen 15%, evitar máxima intensidad. Mayor hidratación.",
        "hidratacion_extra": True,
    },
    # Premenstrual / menstruación (días 22-28 y 1-3): fatiga, inflamación
    "premenstrual": {
        "multiplicador_volumen": 0.80,
        "permitir_calidad": False,
        "mensaje": "Fase premenstrual — foco en Z2 y fuerza moderada. Atención a señales de dolor.",
        "hidratacion_extra": True,
    },
    "menstruacion": {
        "multiplicador_volumen": 0.85,
        "permitir_calidad": False,
        "mensaje": "Menstruación — escuchar el cuerpo. Mantener Z2, evitar alta intensidad si hay dolor.",
        "hidratacion_extra": True,
    },
}


def ajustar_por_ciclo(fase_ciclo_info: dict | None) -> dict:
    """
    Devuelve ajustes de volumen e intensidad según la fase del ciclo menstrual.
    Si no hay datos, devuelve ajuste neutro.
    """
    neutro = {"multiplicador_volumen": 1.0, "permitir_calidad": True,
              "mensaje": None, "hidratacion_extra": False}
    if not fase_ciclo_info:
        return neutro
    fase = str(fase_ciclo_info.get("fase", "")).lower().strip()
    for key, config in _CICLO_FASES.items():
        if key in fase:
            return config
    return neutro


# ---------------------------------------------------------------------------
# 4. CATÁLOGO DE LESIONES
# ---------------------------------------------------------------------------

LESIONES_CATALOGO = {
    "Periostitis (Tibia)": {
        1: {"bloqueo_carrera": True, "sustitucion": "Bici Z2 o Elíptica 45min"},
        2: {"bloqueo_carrera": True, "sustitucion": "Bici Z2 o Elíptica 45min"},
        3: {"bloqueo_carrera": True, "bloqueo_piernas": True, "sustitucion": "Reposo total. Solo tren superior"},
    },
    "Tendón de Aquiles": {
        1: {"prohibir_series": True, "sustitucion": "Carrera suave Z2 solo llano"},
        2: {"bloqueo_carrera": True, "sustitucion": "Elíptica o Bici"},
        3: {"bloqueo_carrera": True, "sustitucion": "Solo natación sin aletas"},
    },
    "Fascitis Plantar": {
        1: {"prohibir_cinta": True, "sustitucion": "Correr en césped o tierra"},
        2: {"bloqueo_carrera": True, "sustitucion": "Bici"},
        3: {"bloqueo_carrera": True, "bloqueo_piernas": True, "sustitucion": "Reposo tren inferior"},
    },
    "Rodilla Corredor": {
        1: {"prohibir_bajadas": True, "sustitucion": "Solo llano o cinta 1% inclinación"},
        2: {"bloqueo_carrera": True, "sustitucion": "Bici sillín alto baja resistencia"},
        3: {"bloqueo_carrera": True, "bloqueo_piernas": True, "sustitucion": "Sin flexión. No prensa ni sentadilla"},
    },
    "Lumbalgia": {
        1: {"sustitucion": "Cambiar sentadilla por Prensa 45°. Sin carga axial"},
        2: {"sustitucion": "Solo ejercicios en banco (press, jalón)"},
        3: {"bloqueo_piernas": True, "sustitucion": "Solo movilidad gato-camello"},
    },
    "Isquiotibial": {
        1: {"prohibir_series": True, "sustitucion": "Sin sprints. Añadir nórdico excéntrico"},
        2: {"bloqueo_carrera": True, "sustitucion": "Bici o natación"},
        3: {"bloqueo_carrera": True, "bloqueo_piernas": True, "sustitucion": "Reposo"},
    },
}


def aplicar_restricciones_lesion(lesiones_activas: list) -> dict:
    """lesiones_activas = [{"zona": str, "grado": int}, ...]"""
    resultado = {"bloqueo_carrera": False, "bloqueo_piernas": False,
                 "prohibir_series": False, "prohibir_bajadas": False,
                 "sustituciones": [], "alertas": []}
    for lesion in lesiones_activas:
        zona = lesion.get("zona", "")
        try:
            grado = int(lesion.get("grado") or 1)
        except (ValueError, TypeError):
            grado = 1
        cat = LESIONES_CATALOGO.get(zona)
        if not cat:
            resultado["alertas"].append(f"Lesión '{zona}' no catalogada. Consulta fisio.")
            continue
        regla = cat.get(grado, cat[max(cat.keys())])
        for flag in ("bloqueo_carrera", "bloqueo_piernas", "prohibir_series", "prohibir_bajadas"):
            if regla.get(flag):
                resultado[flag] = True
        if regla.get("sustitucion"):
            resultado["sustituciones"].append(f"[{zona} G{grado}] {regla['sustitucion']}")
        resultado["alertas"].append(f"⚠️ {zona} grado {grado} activa.")
    return resultado


# ---------------------------------------------------------------------------
# 4. CADENCIA
# ---------------------------------------------------------------------------

def evaluar_cadencia(cadencia_media_spm) -> dict:
    """< 170: drills. > 175: puede subir volumen si ACWR < 1.3."""
    if cadencia_media_spm is None:
        return {"necesita_drills": False, "puede_subir_volumen": False,
                "mensaje": "Sin datos de cadencia."}
    c = float(cadencia_media_spm)
    if c < 170:
        return {"necesita_drills": True, "puede_subir_volumen": False,
                "mensaje": f"Cadencia {c:.0f} spm — añadir 5min drills técnica antes de cada rodaje."}
    if c > 175:
        return {"necesita_drills": False, "puede_subir_volumen": True,
                "mensaje": f"Cadencia {c:.0f} spm — excelente. Permite +10% volumen si ACWR < 1.3."}
    return {"necesita_drills": False, "puede_subir_volumen": False,
            "mensaje": f"Cadencia {c:.0f} spm — correcta."}


def recomendar_drills_especificos(gct_ms: float | None, oscilacion_cm: float | None) -> dict:
    """
    Recomenda drills específicos basados en biomecánica (GCT y oscilación vertical).
    GCT (Ground Contact Time) > 270ms = contacto prolongado → enfoque cadencia.
    Oscilación > 9cm = ineficiencia vertical → enfoque cadera/glúteo.
    """
    drills = []
    mensajes = []

    if gct_ms is not None and float(gct_ms) > 270:
        drills.append("cadencia_media_zancada")
        mensajes.append(f"GCT elevado ({gct_ms:.0f}ms) → drills de cadencia (180+ spm) + media zancada")

    if oscilacion_cm is not None and float(oscilacion_cm) > 9:
        drills.append("cadera_gluteo")
        mensajes.append(f"Oscilación vertical alta ({oscilacion_cm:.1f}cm) → drills de cadera y glúteo")

    if not drills:
        drills.append("general_tecnica")
        mensajes.append("Técnica general: alta cadencia, brazos, postura")

    return {
        "drills": drills,
        "mensaje": " | ".join(mensajes),
        "necesita_drills": len(drills) > 0,
    }



def calcular_volumen_semana(km_anterior: float, acwr: float,
                             lesiones_activas: list, km_max_fase: float,
                             km_4w_mediana: float = None,
                             km_4w_max: float = None,
                             es_step_back: bool = False) -> dict:
    """
    Devuelve {km, motivo, cap_aplicado, modo}.
    Reglas (basadas en JOSPT 2014, BJSM 2024 y Pfitzinger):
      • Lesión / ACWR > 1.5 → -50%.
      • ACWR > 1.3          → mantener.
      • Step-back week      → -25% sobre km_anterior.
      • BASE BUILDING (km_anterior < 20 km/sem o sin histórico):
            cap absoluto 25 km/sem ignorando macrociclo. Subir solo +10%.
      • Modo normal:
            objetivo = min(km_anterior * 1.10,
                           mediana_4sem * 1.30,    ← evita usar un pico raro como base
                           km_max_4sem * 1.20,     ← nunca > 20% sobre el máximo reciente
                           km_max_fase)            ← cap del macrociclo
    Sin histórico real (km_anterior < 1) arranca con 5 km, no 15.
    """
    msg = []
    sin_historial = (not km_anterior) or km_anterior < 1.0
    if sin_historial:
        km_anterior = 5.0
        msg.append("Sin histórico — arranque seguro 5 km/sem")

    base_ref = float(km_4w_mediana) if (km_4w_mediana and km_4w_mediana > 0) else float(km_anterior)
    # FIX: consideramos también km_anterior real — si la usuaria está progresando y la
    # semana pasada hizo 19 km, el plan no puede mandarle 12. Esto es lo que un
    # entrenador real haría: progresión sobre lo que ya ejecutó.
    km_progresion = max(float(km_anterior), base_ref)
    es_principiante = km_progresion < 15.0

    # BASE BUILDING — un principiante NO va a 75 km porque toque "Pico de Forma"
    if es_principiante:
        # Cap personal = +10% sobre lo que ya hace (km_anterior real), nunca menos
        cap_personal = max(round(km_progresion * 1.10, 1), 8.0)
        cap_personal = min(cap_personal, 25.0)
        km_max_efectivo = min(km_max_fase, cap_personal)
        msg.append(f"Modo Base Building (refer. {km_progresion:.0f} km, cap {km_max_efectivo:.0f})")
    else:
        # Modo normal — cap = +15% sobre lo que ya hace, acotado por el cap del macrociclo
        cap_progresion = round(km_progresion * 1.15, 1)
        km_max_efectivo = min(km_max_fase, cap_progresion + 5)
        msg.append(f"Progresión sobre {km_progresion:.0f} km/sem (cap {km_max_efectivo:.0f})")

    tiene_lesion = bool(lesiones_activas)
    acwr_v = float(acwr or 0)

    if tiene_lesion or acwr_v > 1.5:
        km = km_anterior * 0.5
        msg.append("Descarga 50% (lesión / ACWR > 1.5)")
    elif acwr_v > 1.3:
        km = km_anterior
        msg.append("Mantener volumen (ACWR > 1.3)")
    elif es_step_back:
        km = km_anterior * 0.75
        msg.append("Step-back week (-25%)")
    else:
        # Subida controlada: +10% sobre la semana anterior REAL es la base.
        # No usamos topes que bloqueen el progreso (mediana×1.30, max×1.20)
        # porque le penalizan a quien progresa.
        km_subida = km_anterior * 1.10
        # Tope de seguridad: +20% como máximo (regla del 10-20% de la literatura)
        km_techo = km_anterior * 1.20
        km = min(km_subida, km_techo)
        msg.append(f"Subida +10% (de {km_anterior:.0f} a {km:.0f} km)")

    km_final = min(round(km, 1), km_max_efectivo)
    return {
        "km": km_final,
        "motivo": " · ".join(msg) if msg else "Subida normal +10%",
        "cap_aplicado": km_max_efectivo,
        "modo": "base_building" if es_principiante else ("step_back" if es_step_back else "normal"),
    }


# ---------------------------------------------------------------------------
# 6. EFICIENCIA AERÓBICA PACE/HR
# ---------------------------------------------------------------------------

def evaluar_eficiencia_aerobica(actividades_z2: list) -> dict:
    """
    actividades_z2 = [{"fecha": ..., "ritmo_medio": float, "fc_media": float}, ...]
    Sin mejora en 30 días → forzar fartleks. Mínimo 4 actividades para evaluar.
    """
    if not actividades_z2 or len(actividades_z2) < 4:
        return {"tendencia": "sin_datos", "necesita_fartlek": False,
                "ultimo_ratio": None, "ratio_anterior": None}
    df = pd.DataFrame(actividades_z2)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.dropna(subset=["ritmo_medio", "fc_media"]).sort_values("fecha")
    df["ratio"] = df["ritmo_medio"] / df["fc_media"]
    mitad = max(len(df) // 2, 1)
    r_ant = df.iloc[:mitad]["ratio"].mean()
    r_rec = df.iloc[mitad:]["ratio"].mean()
    mejora = r_rec < r_ant  # ratio menor = más veloz por latido = mejor
    return {"tendencia": "mejorando" if mejora else "estancada",
            "necesita_fartlek": not mejora,
            "ultimo_ratio": round(r_rec, 4), "ratio_anterior": round(r_ant, 4)}


# ---------------------------------------------------------------------------
# 7. VALIDACIÓN ORDEN SESIONES
# ---------------------------------------------------------------------------

def validar_orden_sesiones(plan_dia: dict) -> dict:
    """
    plan_dia = {"fuerza_piernas": bool, "carrera_calidad": bool, "carrera_z2": bool}
    """
    advertencias = []
    es_valido = True
    if plan_dia.get("fuerza_piernas") and plan_dia.get("carrera_calidad"):
        advertencias.append("Fuerza piernas + series el mismo día. Mínimo 48h de separación.")
        es_valido = False
    if plan_dia.get("fuerza_piernas") and plan_dia.get("carrera_z2"):
        advertencias.append("Fuerza + Z2 mismo día: hacer fuerza primero o separar 6h.")
    return {"es_valido": es_valido, "advertencias": advertencias}


# ---------------------------------------------------------------------------
# Heredadas (compatibilidad con generar_reporte_semanal)
# ---------------------------------------------------------------------------

def detectar_conflictos_48h(ultimas_actividades: list) -> dict:
    """
    Detecta conflictos potenciales en las últimas 48-72 horas:
    - Si hay VO2max/series en últimas 3 actividades: avisar de descanso o Z2 solo
    - Si hay fuerza piernas reciente: no permitir series la próxima sesión
    """
    if not ultimas_actividades or len(ultimas_actividades) < 1:
        return {"hay_conflicto": False, "mensaje": None, "alerta": None}

    conflictos = []
    tiene_vo2max_reciente = False
    tiene_fuerza_piernas_reciente = False

    # Revisar últimas 3 actividades (últimos 3 días aproximadamente)
    for act in ultimas_actividades[:3]:
        if not act:
            continue
        # Detectar si fue sesión de alta intensidad (VO2max/series)
        te_aer = act.get("training_effect_aerobico", 0)
        te_ana = act.get("training_effect_anaerobico", 0)
        if te_aer > 4.0 or te_ana > 4.0:
            tiene_vo2max_reciente = True
            conflictos.append("VO2max/series detectado en últimas 48h")

    if tiene_vo2max_reciente:
        return {
            "hay_conflicto": True,
            "mensaje": "Zona de descanso activo detectada (VO2max reciente)",
            "alerta": "⚠️ Última sesión de alta intensidad hace <48h. Evitar repetir, foco en Z2 y fuerza ligera.",
        }

    return {"hay_conflicto": False, "mensaje": None, "alerta": None}



def evaluar_cadencia_y_recomendar(df_actividades):
    recomendaciones, mensajes = [], []
    for _, row in df_actividades.iterrows():
        c = row.get("cadencia_media")
        if c is None:
            continue
        if c < 170:
            recomendaciones.append({"fecha": row.get("fecha"), "tipo": row.get("tipo"),
                                    "recomendacion": "Añadir 5' técnica antes del rodaje"})
        elif c > 175:
            mensajes.append({"fecha": row.get("fecha"), "mensaje": "Excelente cadencia."})
    return recomendaciones, mensajes


def controlar_distribucion_intensidad(entrenamientos):
    """FIX: usar campo 'intensidad' (string) en lugar de 'zona' (inexistente en días del plan)."""
    total = len(entrenamientos)
    _BAJA = {"Muy baja", "Baja"}
    baja_pct = 100 * len([e for e in entrenamientos if e.get("intensidad") in _BAJA]) / max(total, 1)
    alta_pct = 100 - baja_pct
    msg = f"Distribución intensidad: {baja_pct:.0f}% baja / {alta_pct:.0f}% alta."
    if baja_pct < 80:
        msg += " ⚠️ Aumentar proporción Z1/Z2 (objetivo 80/20)."
    return entrenamientos, msg


def aplicar_regla_10pct(volumen_actual, volumen_prev, lesion_activa=False, acwr=None):
    if lesion_activa or (acwr is not None and acwr > 1.3):
        return volumen_prev, "Incremento bloqueado (lesión o ACWR > 1.3)."
    max_v = volumen_prev * 1.10
    if volumen_actual > max_v:
        return max_v, f"Ajustado 10%: {max_v:.1f} km."
    return volumen_actual, "Volumen en rango seguro."


def resumen_fases_plan(plan):
    fases_def = [
        {"nombre": "Acondicionamiento", "resumen": "Base aeróbica, fuerza glúteo, volumen bajo."},
        {"nombre": "Preparación General", "resumen": "Resistencia y fuerza máxima, volumen medio."},
        {"nombre": "Preparación Específica", "resumen": "Ritmos competición, volumen alto."},
        {"nombre": "Pico de Forma", "resumen": "Tiradas largas, core, volumen máximo."},
        {"nombre": "Tapering", "resumen": "Descanso, activación, supercompensación."},
    ]
    semanas_por_fase = {f["nombre"]: 0 for f in fases_def}
    for s in plan:
        semanas_por_fase[s["fase"]] = semanas_por_fase.get(s["fase"], 0) + 1
    return [{"fase": f["nombre"], "semanas": semanas_por_fase.get(f["nombre"], 0),
             "resumen": f["resumen"]} for f in fases_def]


# ---------------------------------------------------------------------------
# BEVEL-INSPIRED: TARGET INTENSITY (HRV Baseline Comparison)
# ---------------------------------------------------------------------------

def calcular_target_intensidad_bevel(hrv_actual, hrv_media_60d):
    """
    Calcula la "capacidad" de entrenamiento del día basada en HRV vs media 60 días.
    Es la "joya de corona" de Bevel: compara HRV actual contra tu baseline personal.

    Si HRV > baseline → puedes dar más caña (intensidad permitida sube)
    Si HRV < baseline → sé conservador (intensidad recomendada baja)

    Retorna:
    {
        "hrv_baseline_60d": float,
        "hrv_today": float,
        "hrv_vs_baseline_pct": float,  # % respecto a baseline
        "intensity_allowance": "Alta" | "Moderada" | "Baja" | "Regenerativa",
        "recommendation": str,  # Consejo específico
        "intensity_modifier": float,  # 1.2 = puedes más, 0.8 = sé conservador
    }
    """
    if not hrv_actual or not hrv_media_60d or hrv_media_60d <= 0:
        return {
            "hrv_baseline_60d": None,
            "hrv_today": hrv_actual,
            "hrv_vs_baseline_pct": None,
            "intensity_allowance": "Moderada",
            "recommendation": "Sin datos de baseline — sigue plan normal.",
            "intensity_modifier": 1.0,
        }

    hrv_actual = float(hrv_actual)
    hrv_baseline_60d = float(hrv_media_60d)

    # % respecto a baseline (+ = mejor, - = peor)
    hrv_pct = ((hrv_actual - hrv_baseline_60d) / hrv_baseline_60d) * 100

    # Determinar allowance e intensity modifier
    if hrv_pct > 15:
        intensity_allowance = "Alta"
        intensity_modifier = 1.2
        recommendation = f"Excelente recuperación (HRV +{hrv_pct:.0f}% vs baseline). Puedes mantener sesión de calidad completa."
    elif hrv_pct > 5:
        intensity_allowance = "Moderada"
        intensity_modifier = 1.0
        recommendation = f"Recuperación buena (HRV +{hrv_pct:.0f}% vs baseline). Sesión normal según plan."
    elif hrv_pct > -5:
        intensity_allowance = "Moderada"
        intensity_modifier = 1.0
        recommendation = f"Recuperación estable (HRV {hrv_pct:.0f}% vs baseline). Mantén el plan."
    elif hrv_pct > -15:
        intensity_allowance = "Baja"
        intensity_modifier = 0.8
        recommendation = f"Recuperación subóptima (HRV {hrv_pct:.0f}% vs baseline). Reduce volumen -20% o convierte en Z2."
    else:
        intensity_allowance = "Regenerativa"
        intensity_modifier = 0.5
        recommendation = f"Recuperación muy baja (HRV {hrv_pct:.0f}% vs baseline). Solo regenerativo/descanso recomendado."

    return {
        "hrv_baseline_60d": round(hrv_baseline_60d, 1),
        "hrv_today": round(hrv_actual, 1),
        "hrv_vs_baseline_pct": round(hrv_pct, 1),
        "intensity_allowance": intensity_allowance,
        "recommendation": recommendation,
        "intensity_modifier": intensity_modifier,
    }


# ---------------------------------------------------------------------------
# HRV RECOVERY EVALUATION
# ---------------------------------------------------------------------------

def evaluar_hrv_recovery(hrv_data, sleep_score, estres_medio, body_battery_min,
                         body_battery_max, carga_aguda, carga_cronica):
    """
    Evalúa Recovery vs Strain basado en HRV trend, sueño, estrés y carga de entrenamiento.

    Retorna:
    {
        "status": "green" | "yellow" | "red",
        "recovery_score": 0-100,
        "hrv_trend": "increasing" | "stable" | "decreasing",
        "hrv_change_pct": float,  # cambio % en últimos 7 días
        "readiness": "Ready to train" | "Proceed with caution" | "Prioritize recovery",
        "causas": str,  # razones del status
    }
    """
    recovery_score = 50  # base score
    causas = []

    # HRV Trend (últimos 7 días): si tenemos lista de HRV
    hrv_trend = "stable"
    hrv_change_pct = 0

    if isinstance(hrv_data, list) and len(hrv_data) >= 2:
        # Asumir que hrv_data está ordenado descendente (más reciente primero)
        hrv_reciente = float(hrv_data[0]) if hrv_data[0] else 0
        hrv_pasado = float(hrv_data[-1]) if hrv_data[-1] else hrv_reciente

        if hrv_pasado > 0:
            hrv_change_pct = ((hrv_reciente - hrv_pasado) / hrv_pasado) * 100

            if hrv_change_pct > 5:
                hrv_trend = "increasing"
                recovery_score += 15
                causas.append("HRV aumentando (↑ recuperación)")
            elif hrv_change_pct < -5:
                hrv_trend = "decreasing"
                recovery_score -= 15
                causas.append("HRV disminuyendo (↓ fatiga acumulada)")
            else:
                causas.append("HRV estable")

    # Sleep Score
    if sleep_score:
        sleep_score_val = float(sleep_score)
        if sleep_score_val >= 75:
            recovery_score += 10
            causas.append(f"Sueño excelente ({sleep_score_val:.0f}/100)")
        elif sleep_score_val >= 60:
            causas.append(f"Sueño adecuado ({sleep_score_val:.0f}/100)")
        elif sleep_score_val >= 50:
            recovery_score -= 10
            causas.append(f"Sueño deficiente ({sleep_score_val:.0f}/100)")
        else:
            recovery_score -= 15
            causas.append(f"Sueño muy bajo ({sleep_score_val:.0f}/100)")

    # Stress Level
    if estres_medio is not None:
        estres_val = float(estres_medio)
        if estres_val <= 25:
            recovery_score += 5
        elif estres_val >= 50:
            recovery_score -= 10
            causas.append(f"Estrés elevado ({estres_val:.0f}/100)")

    # Body Battery
    if body_battery_min is not None and body_battery_max is not None:
        battery_range = float(body_battery_max) - float(body_battery_min)
        if battery_range >= 60:
            recovery_score += 5
            causas.append(f"Batería completa ({body_battery_max:.0f}%)")
        elif battery_range < 30:
            recovery_score -= 10
            causas.append(f"Batería baja ({body_battery_max:.0f}%)")

    # Training Load (ACWR)
    if carga_aguda is not None and carga_cronica is not None:
        acwr = float(carga_aguda) / float(carga_cronica) if float(carga_cronica) > 0 else 1
        if acwr > 1.5:
            recovery_score -= 15
            causas.append(f"Carga muy alto (ACWR {acwr:.2f})")
        elif acwr > 1.3:
            recovery_score -= 5
            causas.append(f"Carga moderado (ACWR {acwr:.2f})")

    # Clamp score
    recovery_score = max(0, min(100, recovery_score))

    # Determine status and readiness
    if recovery_score >= 70:
        status = "green"
        readiness = "Ready to train"
    elif recovery_score >= 50:
        status = "yellow"
        readiness = "Proceed with caution"
    else:
        status = "red"
        readiness = "Prioritize recovery"

    return {
        "status": status,
        "recovery_score": int(recovery_score),
        "hrv_trend": hrv_trend,
        "hrv_change_pct": round(hrv_change_pct, 1),
        "readiness": readiness,
        "causas": " • ".join(causas) if causas else "Estado neutral",
    }
