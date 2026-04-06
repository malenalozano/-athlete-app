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
        return {
            "color": "rojo",
            "mensaje": "Adaptación fallida — " + "; ".join(razones_rojo) + ". Solo regenerativo.",
            "multiplicador_volumen": 0.5,
            "permitir_calidad": False,
            "causa": list(set(causa_rojo)),  # Deduplicar causas
        }
    if razones_ambar:
        return {
            "color": "ambar",
            "mensaje": "Recuperación subóptima — " + "; ".join(razones_ambar) + ". No buscar PR, -20% series.",
            "multiplicador_volumen": 0.8,
            "permitir_calidad": False,
            "causa": list(set(causa_ambar)),
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
                             lesiones_activas: list, km_max_fase: float) -> float:
    """
    Lesión o ACWR > 1.5 → descarga 50%. ACWR > 1.3 → mantener. Normal → +10%.
    Sin historial: parte de 15 km como base.
    """
    if not km_anterior:
        km_anterior = 15.0
    tiene_lesion = bool(lesiones_activas)
    if tiene_lesion or acwr > 1.5:
        km = km_anterior * 0.5
    elif acwr > 1.3:
        km = km_anterior
    else:
        km = km_anterior * 1.10
    return min(round(km, 1), km_max_fase)


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
