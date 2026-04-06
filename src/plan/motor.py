"""
src/plan/motor.py
Motor del plan semanal adaptativo + constructores de sesiones base.
Lógica 100% determinista Python — sin IA en la generación.
"""

import pandas as pd
from datetime import datetime

from src.plan.reglas import (
    obtener_fase_macrociclo, obtener_fase_macrociclo_ultra, obtener_fase_macrociclo_usuario,
    calcular_semaforo, aplicar_restricciones_lesion,
    evaluar_cadencia, calcular_volumen_semana, evaluar_eficiencia_aerobica,
    validar_orden_sesiones, evaluar_cadencia_y_recomendar, ajustar_por_ciclo,
    controlar_distribucion_intensidad, evaluar_vo2max, evaluar_training_effect,
    recomendar_drills_especificos, detectar_conflictos_48h,
)
from src.plan.helpers import cargar_datos_plan, distribuir_semana


# ---------------------------------------------------------------------------
# Constructores de sesiones base
# ---------------------------------------------------------------------------

def crear_tirada_larga(distancia_km, fcmax, duracion_min=None):
    return {"tipo": "tirada_larga", "zona": 2, "fcmax_pct": min(fcmax, 80),
            "distancia_km": distancia_km, "duracion_min": duracion_min,
            "descripcion": "Carrera continua fácil, zona 2, <80% FCmax."}


def crear_tempo(distancia_km, fcmax, duracion_min=None):
    return {"tipo": "tempo", "zona": 4, "fcmax_pct": min(fcmax, 90),
            "distancia_km": distancia_km, "duracion_min": duracion_min,
            "descripcion": "Carrera a ritmo umbral, zona 4, ~90% FCmax."}


def crear_progresiva(distancia_km, bloques=4, zonas=None, fcmax=None):
    return {"tipo": "progresiva", "bloques": bloques,
            "zonas": zonas or [1, 2, 3, 4], "fcmax_pct": fcmax or [70, 75, 85, 90],
            "distancia_km": distancia_km,
            "descripcion": "Carrera progresiva en bloques, de zona 1/2 a zona 4."}


def crear_cambios_ritmo(distancia_km, repeticiones, ritmo_rapido_pct=90, ritmo_lento_pct=70):
    return {"tipo": "cambios_ritmo", "repeticiones": repeticiones,
            "ritmo_rapido_pct": ritmo_rapido_pct, "ritmo_lento_pct": ritmo_lento_pct,
            "distancia_km": distancia_km,
            "descripcion": "Carrera alternando ritmos, zona 4 y zona 1/2."}


def crear_intervalos_vo2max(repeticiones, distancia_intervalo_km, fcmax_pct=95, descanso_min=2):
    return {"tipo": "intervalos_vo2max", "repeticiones": repeticiones,
            "distancia_intervalo_km": distancia_intervalo_km,
            "fcmax_pct": fcmax_pct, "descanso_min": descanso_min,
            "descripcion": "Intervalos VO2max, >umbral lactato, descanso pasivo."}


def crear_regenerativo(distancia_km, fcmax_pct=70, duracion_min=None):
    return {"tipo": "regenerativo", "zona": 1, "fcmax_pct": fcmax_pct,
            "distancia_km": distancia_km, "duracion_min": duracion_min,
            "descripcion": "Carrera regenerativa, baja intensidad, <70% FCmax."}


# ---------------------------------------------------------------------------
# Motor del plan semanal
# ---------------------------------------------------------------------------

def generar_plan_semana(usuario_id: int, fecha_inicio_lunes) -> dict:
    """
    Genera el plan de 7 días adaptado a datos reales de la BD.

    Pipeline:
    1. Carga datos (HRV, sueño breakdown, lesiones, km, cadencia, ACWR, Z2,
       métricas running, ciclo menstrual, stress, body battery, VO2max, training status).
    2. Determina fase del macrociclo.
    3. Calcula semáforo multi-señal (HRV + sueño profundo + stress + body battery + training status).
    4. Ajusta por ciclo menstrual.
    5. Aplica restricciones de lesión.
    6. Evalúa cadencia.
    7. Calcula volumen objetivo (10% rule + ACWR + ciclo + semáforo).
    8. Evalúa eficiencia aeróbica.
    9. Distribuye 7 días con template de fase.
    10. Valida orden de sesiones concurrentes.
    """
    datos = cargar_datos_plan(usuario_id)

    # Seleccionar macrociclo según perfil (maratón vs ultramaratón)
    objetivo_tipo = datos.get("objetivo_tipo", "maraton")
    genero = datos.get("genero", "Mujer")
    es_ultra = str(objetivo_tipo).lower() in ("ultramaraton", "ultra", "trail_ultra")

    if es_ultra and datos.get("fecha_objetivo"):
        fase = obtener_fase_macrociclo_ultra(fecha_inicio_lunes, datos["fecha_objetivo"])
    else:
        fase = obtener_fase_macrociclo(fecha_inicio_lunes)

    # Semáforo enriquecido con TODAS las señales de recuperación
    semaforo = calcular_semaforo(
        hrv_actual=datos["hrv_actual"],
        hrv_media_7d=datos["hrv_media_7d"],
        sleep_score=datos["sleep_score"],
        sleep_breakdown=datos.get("sleep_breakdown"),
        estres_medio=datos.get("estres_medio"),
        body_battery_min=datos.get("body_battery_min"),
        training_status=datos.get("training_status"),
    )

    # Ajuste por ciclo menstrual — solo para mujeres
    es_hombre = str(genero).lower() in ("hombre", "male", "m")
    ciclo_ajuste = ajustar_por_ciclo(None if es_hombre else datos.get("fase_ciclo"))

    restricciones = aplicar_restricciones_lesion(datos["lesiones_activas"])
    cadencia_eval = evaluar_cadencia(datos["cadencia_media"])

    # Evaluación VO2max: capacidad cardíaca (umbrales por género)
    vo2_eval = evaluar_vo2max(datos.get("vo2max"), genero=genero)

    # Evaluación Training Effect: fatiga acumulada
    te_eval = evaluar_training_effect(
        datos.get("metricas_running", {}).get("training_effect_aerobico"),
        datos.get("metricas_running", {}).get("training_effect_anaerobico"),
        datos.get("ultimas_3_actividades", [])
    )

    # Recomendación de drills específicos basados en biomecánica
    gct = datos.get("metricas_running", {}).get("tiempo_contacto_ms")
    oscilacion = datos.get("metricas_running", {}).get("oscilacion_vertical_cm")
    drills_eval = recomendar_drills_especificos(gct, oscilacion)

    # Detector de conflictos 48-72h (últimas actividades)
    conflictos_48h = detectar_conflictos_48h(datos.get("ultimas_3_actividades", []))

    km_objetivo = calcular_volumen_semana(
        datos["km_semana_anterior"], datos["acwr"],
        datos["lesiones_activas"], fase["km_semanales_max"])

    eficiencia = evaluar_eficiencia_aerobica(datos["actividades_z2"])

    # Aplicar multiplicadores: semáforo × ciclo menstrual
    km_objetivo = round(km_objetivo * semaforo["multiplicador_volumen"] * ciclo_ajuste["multiplicador_volumen"], 1)

    # Si la fase lútea/premenstrual bloquea calidad, forzarlo en semáforo
    if not ciclo_ajuste["permitir_calidad"] and semaforo["color"] == "verde":
        semaforo = dict(semaforo)  # no mutar original
        semaforo["color"] = "ambar"
        semaforo["permitir_calidad"] = False
        semaforo["mensaje"] = ciclo_ajuste["mensaje"]

    dias = distribuir_semana(fase, km_objetivo, semaforo, restricciones, fecha_inicio_lunes, cadencia_eval,
                            datos.get("sleep_breakdown"), objetivo_tipo=objetivo_tipo)

    # Recoger alertas
    alertas = list(restricciones["alertas"])
    if semaforo["color"] != "verde":
        alertas.append(semaforo["mensaje"])
    # Alertas ciclo menstrual solo para mujeres
    if not es_hombre:
        if ciclo_ajuste["mensaje"] and ciclo_ajuste["mensaje"] not in alertas:
            alertas.append(f"🩸 {ciclo_ajuste['mensaje']}")
        if ciclo_ajuste.get("hidratacion_extra"):
            alertas.append("💧 Fase del ciclo: aumentar hidratación y electrolitos.")
    if cadencia_eval["necesita_drills"]:
        alertas.append(cadencia_eval["mensaje"])
        # Añadir recomendación de drills específicos
        if drills_eval["necesita_drills"]:
            alertas.append(f"👟 {drills_eval['mensaje']}")
    if eficiencia["necesita_fartlek"]:
        alertas.append("📊 Eficiencia aeróbica estancada — añadir fartlek esta semana.")

    # VO2max evaluación
    if vo2_eval["mensaje"]:
        alertas.append(f"💪 {vo2_eval['mensaje']}")

    # Training Effect evaluación (fatiga acumulada)
    if te_eval["mensaje"]:
        alertas.append(f"⚠️ {te_eval['mensaje']}")

    # Alerta sueño profundo insuficiente
    sleep_breakdown = datos.get("sleep_breakdown", {})
    if sleep_breakdown.get("profundo_h") is not None and sleep_breakdown["profundo_h"] < 0.75:
        alertas.append(f"😴 Sueño profundo insuficiente ({sleep_breakdown['profundo_h']*60:.0f} min < 45 min) — reducir series esta semana.")

    # Detección de conflictos 48-72h
    if conflictos_48h["alerta"]:
        alertas.append(conflictos_48h["alerta"])


    # Alerta Training Status Garmin
    ts = datos.get("training_status", "")
    if ts and any(k in str(ts).lower() for k in ("productive", "peaking")):
        alertas.append(f"✅ Garmin Training Status: {ts} — seguir el plan.")
    elif ts and any(k in str(ts).lower() for k in ("overreaching", "strained")):
        alertas.append(f"⚠️ Garmin Training Status: {ts} — reducir carga.")

    # Alerta métricas running si GCT o VO son llamativas
    mrun = datos.get("metricas_running", {})
    if mrun.get("tiempo_contacto_ms") and mrun["tiempo_contacto_ms"] > 270:
        alertas.append(f"👟 GCT elevado ({mrun['tiempo_contacto_ms']:.0f} ms) — trabajar técnica de pisada.")
    if mrun.get("oscilacion_vertical_cm") and mrun["oscilacion_vertical_cm"] > 9:
        alertas.append(f"⬆️ Oscilación vertical alta ({mrun['oscilacion_vertical_cm']:.1f} cm) — foco en cadera y core.")

    for dia in dias:
        val = validar_orden_sesiones({
            "fuerza_piernas": "Fuerza" in dia["tipo"] and "Superior" not in dia["tipo"],
            "carrera_calidad": any(k in dia["tipo"] for k in ("Calidad", "Intervalos", "Tempo", "Progresiva")),
            "carrera_z2": "Z2" in dia["tipo"],
        })
        if not val["es_valido"]:
            alertas.extend(val["advertencias"])
        if dia["alerta"]:
            alertas.append(dia["alerta"])

    km_totales = round(sum(d["km"] for d in dias), 1)

    # Validar distribución 80/20 de intensidad
    entrenamientos_running = [d for d in dias if "Carrera" in d["tipo"]]
    _, validacion_intensidad = controlar_distribucion_intensidad(entrenamientos_running)
    alertas.append(f"📊 {validacion_intensidad}")

    return {
        "dias": dias,
        "alertas": list(dict.fromkeys(alertas)),  # deduplicar manteniendo orden
        "semaforo": semaforo,
        "fase": fase,
        "km_totales": km_totales,
        "acwr": round(datos["acwr"], 2),
        "ciclo_ajuste": ciclo_ajuste,
        "metricas_running": mrun,
        "training_status": datos.get("training_status"),
        "vo2max": datos.get("vo2max"),
        "vo2_eval": vo2_eval,
        "training_effect_eval": te_eval,
        "drills_eval": drills_eval,
        "conflictos_48h": conflictos_48h,
        "body_battery": datos.get("body_battery_max"),
        "estres_medio": datos.get("estres_medio"),
        # Perfil del atleta
        "genero": genero,
        "objetivo_tipo": objetivo_tipo,
        "nombre_atleta": datos.get("nombre", "Atleta"),
        "es_hombre": es_hombre,
    }


# ---------------------------------------------------------------------------
# Análisis de historial + macrociclo (usados en generar_reporte_semanal)
# ---------------------------------------------------------------------------

def analizar_estado_atleta(df_running):
    df_running["fecha"] = pd.to_datetime(df_running["fecha"])
    df_running["week"] = df_running["fecha"].dt.isocalendar().week
    return {
        "volumen_semanal": df_running.groupby("week")["distancia"].sum().mean(),
        "tirada_larga": df_running["distancia"].max(),
        "frecuencia_semanal": df_running.groupby("week").size().mean(),
    }


def generar_reporte_semanal(df_actividades, semana, estado, fase):
    df_semana = df_actividades[df_actividades["week"] == semana]
    recomendaciones, mensajes = evaluar_cadencia_y_recomendar(df_semana)
    return {
        "volumen_total": df_semana["distancia"].sum(),
        "tirada_larga": df_semana["distancia"].max(),
        "sesiones_fuerza": df_semana[df_semana["tipo"].str.lower() == "fuerza"].shape[0],
        "recomendaciones": recomendaciones,
        "mensajes": mensajes,
        "fase": fase,
        "estado": estado,
    }
