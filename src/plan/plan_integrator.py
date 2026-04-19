"""
src/plan/plan_integrator.py
Orquestador principal: integra todas las mejoras (GAS, Protocolo A/B, Interferencia, Nutrición, Ciclo+GAS)
en un flujo coherente.

Uso:
  1. generador_plan_integrado() es llamado desde generar_plan_semana()
  2. Retorna plan enriquecido con todas las validaciones
"""

from datetime import datetime

from src.plan.gas_progression import evaluar_fase_gas, calcular_dias_desde_estimulo, mensaje_educativo_gas
from src.plan.protocolo_selector import recomendar_protocolo, validar_protocolo_seleccionado, obtener_restricciones_protocolo
from src.plan.interferencia_detector import evaluar_interferencia_48h
from src.plan.nutrition_recommendations import obtener_macros_objetivo, generar_alerta_nutricional_sesion
from src.plan.menstrual_cycle_gas_sync import evaluar_ciclo_gas_sinergia, calcular_volumen_con_slider, generar_alertas_ciclo_gas, validar_slider_seguridad


def preparar_contexto_plan(datos: dict, fase: dict) -> dict:
    """
    Prepara el contexto integrado con todas las evaluaciones.

    Retorna contexto enriquecido con:
    - gas_info
    - protocolo_recomendado
    - ciclo_gas_sinergia
    - macros_objetivo
    """

    # ---- GAS EVALUATION ----
    dias_desde_estimulo = calcular_dias_desde_estimulo(datos.get("ultimas_3_actividades", []))
    gas_info = evaluar_fase_gas(
        hrv_actual=datos.get("hrv_actual"),
        hrv_media_7d=datos.get("hrv_media_7d"),
        sleep_score=datos.get("sleep_score"),
        sleep_breakdown=datos.get("sleep_breakdown"),
        estres_medio=datos.get("estres_medio"),
        body_battery_min=datos.get("body_battery_min"),
        dias_desde_estimulo_duro=dias_desde_estimulo,
    )

    # ---- PROTOCOLO RECOMMENDATION ----
    protocolo_recomendado = recomendar_protocolo(
        fase_nombre=fase.get("fase_nombre", ""),
        acwr=datos.get("acwr", 1.0),
    )

    # ---- CICLO + GAS SINERGIA (solo mujeres) ----
    es_mujer = str(datos.get("genero", "")).lower() in ("mujer", "female", "f")
    ciclo_gas_sinergia = {}
    if es_mujer:
        ciclo_gas_sinergia = evaluar_ciclo_gas_sinergia(
            fase_ciclo=datos.get("fase_ciclo", {}).get("fase") if isinstance(datos.get("fase_ciclo"), dict) else datos.get("fase_ciclo"),
            gas_fase=gas_info["fase"],
            gas_severidad=gas_info["severidad"],
        )

    # ---- MACROS OBJETIVO ----
    macros_objetivo = obtener_macros_objetivo(
        objetivo_tipo=datos.get("objetivo_tipo", "maraton"),
        genero=datos.get("genero", "mujer"),
    )

    return {
        "gas_info": gas_info,
        "protocolo_recomendado": protocolo_recomendado,
        "ciclo_gas_sinergia": ciclo_gas_sinergia,
        "macros_objetivo": macros_objetivo,
        "es_mujer": es_mujer,
    }


def generar_plan_integrado(
    usuario_id: int,
    datos: dict,
    fase: dict,
    protocolo_seleccionado: str | None = None,  # Usuario puede override
    slider_volumen_pct: float = 100,  # 0-100, para ciclo+GAS
    distribuir_fn=None,  # Función distribuir_semana
) -> dict:
    """
    Pipeline completo con todas las mejoras integradas:

    1. Preparar contexto (GAS, Protocolo, Ciclo+GAS, Macros)
    2. Validar protocolo seleccionado (con override)
    3. Calcular volumen con slider (ciclo+GAS)
    4. Aplicar restricciones protocolo
    5. Detectar interferencia 48h
    6. Generar plan
    7. Validar interferencia PRE-distribución
    8. Retornar plan + alertas
    """

    contexto = preparar_contexto_plan(datos, fase)

    # ---- PROTOCOLO FINAL ----
    protocolo_validado = validar_protocolo_seleccionado(
        protocolo_seleccionado,
        contexto["protocolo_recomendado"]["protocolo"],
    )
    protocolo_final = protocolo_validado["protocolo_final"]
    restricciones_protocolo = obtener_restricciones_protocolo(protocolo_final)

    # ---- VOLUMEN CON SLIDER (CICLO + GAS) ----
    km_objetivo_base = datos.get("km_objetivo", 50)
    multiplicador_ciclo_gas = contexto["ciclo_gas_sinergia"].get("multiplicador_base", 1.0)

    volumen_info = calcular_volumen_con_slider(
        km_objetivo_base=km_objetivo_base,
        multiplicador_ciclo_gas=multiplicador_ciclo_gas,
        slider_porcentaje=slider_volumen_pct,
    )

    # ---- ALERTAS CICLO + GAS ----
    alertas_ciclo_gas = generar_alertas_ciclo_gas(
        fase_ciclo=datos.get("fase_ciclo", {}).get("fase") if isinstance(datos.get("fase_ciclo"), dict) else datos.get("fase_ciclo"),
        gas_fase=contexto["gas_info"]["fase"],
        gas_severidad=contexto["gas_info"]["severidad"],
        sinergia=contexto["ciclo_gas_sinergia"],
    )

    # ---- VALIDAR SLIDER SEGURIDAD ----
    slider_validacion = validar_slider_seguridad(
        slider_volumen_pct,
        contexto["gas_info"]["fase"],
        contexto["gas_info"]["severidad"],
    )

    # ---- PREPARAR PARA DISTRIBUIR ----
    # Pasar volumen ajustado y restricciones a distribuir
    contexto_distribucion = {
        "protocolo": protocolo_final,
        "restricciones": restricciones_protocolo,
        "gas_info": contexto["gas_info"],
        "km_objetivo_ajustado": volumen_info["km_final_con_slider"],
    }

    # Retornar información integrada para pasar a distribuir_semana
    return {
        "protocolo": protocolo_final,
        "protocolo_validado": protocolo_validado,
        "contexto": contexto,
        "volumen_info": volumen_info,
        "restricciones_protocolo": restricciones_protocolo,
        "alertas_ciclo_gas": alertas_ciclo_gas,
        "slider_validacion": slider_validacion,
        "contexto_distribucion": contexto_distribucion,
    }


def generar_alertas_integrales(
    contexto: dict,
    plan_dias: list | None = None,
) -> list[str]:
    """
    Genera alertas consolidadas de TODAS las mejoras.
    """
    alertas = []

    gas_info = contexto["gas_info"]
    protocolo_info = contexto["protocolo_recomendado"]

    # ---- GAS ALERTAS ----
    if gas_info["fase"] == "alarma":
        alertas.append(f"🚨 {gas_info['recomendacion']}")
    elif gas_info["fase"] == "agotamiento":
        alertas.append(f"⚠️ {gas_info['recomendacion']}")

    # ---- PROTOCOLO ALERTAS ----
    if protocolo_info["protocolo"] == "A":
        alertas.append(f"💪 {protocolo_info['recomendacion']}")
    else:
        alertas.append(f"🏃 {protocolo_info['recomendacion']}")

    # ---- INTERFERENCIA ALERTAS (si plan_dias disponible) ----
    if plan_dias and len(plan_dias) >= 2:
        for i in range(len(plan_dias) - 1):
            dia_actual = plan_dias[i]
            dia_siguiente = plan_dias[i + 1]

            eval_48h = evaluar_interferencia_48h(dia_siguiente, dia_actual)
            if eval_48h["recomendacion"]:
                alertas.append(eval_48h["recomendacion"])

    return list(dict.fromkeys(alertas))  # Deduplicar
