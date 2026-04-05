"""
src/plan/reglas.py
Reglas fisiológicas del macrociclo: semáforo HRV/sueño, catálogo de lesiones,
volumen semanal, cadencia y validación de sesiones concurrentes.
"""

import pandas as pd
from datetime import datetime


# ---------------------------------------------------------------------------
# 1. DIRECTOR DE ORQUESTA
# ---------------------------------------------------------------------------

def obtener_fase_macrociclo(fecha_actual=None) -> dict:
    """Retorna fase activa, volumen máx, días fuerza, enfoques y restricciones."""
    if fecha_actual is None:
        fecha_actual = datetime.now()
    mes = fecha_actual.month
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
    if mes in [12, 1]:
        return {"fase_nombre": "Pico de Forma", "km_semanales_max": 75, "dias_fuerza": 2,
                "enfoque_fuerza": "Funcional: core y estabilidad",
                "enfoque_running": "Tiradas largas y ritmo Maratón.",
                "sesion_calidad": "tempo",
                "restricciones": {"limitar_impacto": False, "permitir_series": True}}
    if mes == 2:
        return {"fase_nombre": "Tapering", "km_semanales_max": 30, "dias_fuerza": 1,
                "enfoque_fuerza": "Movilidad y activación mínima",
                "enfoque_running": "Supercompensación (GAS). Mínima fatiga.",
                "sesion_calidad": "progresiva",
                "restricciones": {"limitar_impacto": True, "permitir_series": False}}
    return {"fase_nombre": "Desconocida", "km_semanales_max": 20, "dias_fuerza": 2,
            "enfoque_fuerza": "", "enfoque_running": "", "sesion_calidad": "progresiva",
            "restricciones": {"limitar_impacto": False, "permitir_series": False}}


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
    """
    razones_rojo = []
    razones_ambar = []

    # — HRV —
    caida = 0.0
    if hrv_actual is not None and hrv_media_7d and hrv_media_7d > 0:
        caida = (hrv_media_7d - hrv_actual) / hrv_media_7d
        if caida > 0.10:
            razones_rojo.append(f"HRV caído {caida*100:.0f}%")
        elif caida > 0.0:
            razones_ambar.append(f"HRV ligeramente bajo (-{caida*100:.0f}%)")
    elif hrv_actual is None and hrv_media_7d is None:
        return {"color": "verde", "mensaje": "Sin datos HRV — plan base aplicado.",
                "multiplicador_volumen": 1.0, "permitir_calidad": True}

    # — Sleep score —
    if sleep_score is not None:
        if sleep_score < 60:
            razones_rojo.append(f"Sleep score crítico ({sleep_score}/100)")
        elif sleep_score <= 80:
            razones_ambar.append(f"Sleep score subóptimo ({sleep_score}/100)")

    # — Sleep profundo (< 45 min = 0.75 h → señal rojo) —
    if sleep_breakdown:
        prof = sleep_breakdown.get("profundo_h")
        if prof is not None and prof < 0.75:
            razones_rojo.append(f"Sueño profundo insuficiente ({prof*60:.0f} min)")
        rem = sleep_breakdown.get("rem_h")
        if rem is not None and rem < 1.0:
            razones_ambar.append(f"REM escaso ({rem:.1f} h)")

    # — Estrés —
    if estres_medio is not None:
        if estres_medio > 75:
            razones_rojo.append(f"Estrés muy alto ({estres_medio})")
        elif estres_medio > 55:
            razones_ambar.append(f"Estrés elevado ({estres_medio})")

    # — Body Battery —
    if body_battery_min is not None:
        if body_battery_min < 10:
            razones_rojo.append(f"Body Battery crítico al levantarse ({body_battery_min})")
        elif body_battery_min < 25:
            razones_ambar.append(f"Body Battery bajo ({body_battery_min})")

    # — Training Status Garmin —
    if training_status:
        ts = training_status.lower()
        if any(k in ts for k in ("overreaching", "strained", "detraining")):
            razones_rojo.append(f"Training Status: {training_status}")
        elif any(k in ts for k in ("maintaining", "recovery", "unproductive")):
            razones_ambar.append(f"Training Status: {training_status}")

    # — Decisión final —
    if razones_rojo:
        return {
            "color": "rojo",
            "mensaje": "Adaptación fallida — " + "; ".join(razones_rojo) + ". Solo regenerativo.",
            "multiplicador_volumen": 0.5,
            "permitir_calidad": False,
        }
    if razones_ambar:
        return {
            "color": "ambar",
            "mensaje": "Recuperación subóptima — " + "; ".join(razones_ambar) + ". No buscar PR, -20% series.",
            "multiplicador_volumen": 0.8,
            "permitir_calidad": False,
        }
    return {
        "color": "verde",
        "mensaje": "Recuperación óptima. Entrenamiento completo.",
        "multiplicador_volumen": 1.0,
        "permitir_calidad": True,
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


# ---------------------------------------------------------------------------
# 5. VOLUMEN SEMANAL (ACWR + regla 10%)
# ---------------------------------------------------------------------------

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
    total = len(entrenamientos)
    baja_pct = 100 * len([e for e in entrenamientos if e.get("zona") in [1, 2]]) / max(total, 1)
    alta_pct = 100 - baja_pct
    msg = f"Distribución: {baja_pct:.0f}% baja / {alta_pct:.0f}% alta."
    if baja_pct < 80:
        msg += " Aumentar Z1/Z2."
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
