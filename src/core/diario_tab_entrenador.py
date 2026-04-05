"""
src/core/diario_tab_entrenador.py — Tab "Entrenador" dentro de Diario.
Muestra datos y decisiones del motor para el siguiente plan semanal.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from src.db.db_manager import get_db_connection
from src.plan.helpers import cargar_datos_plan
from src.plan.memoria_fuerza import generar_tabla_fuerza_semana
from src.plan.motor import generar_plan_semana
from src.plan.reglas import (
    ajustar_por_ciclo,
    calcular_semaforo,
    calcular_volumen_semana,
    evaluar_cadencia,
    evaluar_eficiencia_aerobica,
    obtener_fase_macrociclo,
    evaluar_vo2max,
    evaluar_training_effect,
    recomendar_drills_especificos,
    detectar_conflictos_48h,
)


def render_tab_entrenador(usuario_id: int) -> None:
    st.markdown(
        "<h4 style='margin:4px 0 10px;'>🧠 Entrenador — Datos y decisiones</h4>",
        unsafe_allow_html=True,
    )
    st.caption("Vista técnica del plan semanal generado para Malena.")

    try:
        datos = cargar_datos_plan(usuario_id)
    except Exception as e:
        st.error(f"No se pudieron cargar los datos del entrenador: {e}")
        return

    fase = obtener_fase_macrociclo(datetime.now())
    semaforo = calcular_semaforo(
        hrv_actual=datos.get("hrv_actual"),
        hrv_media_7d=datos.get("hrv_media_7d"),
        sleep_score=datos.get("sleep_score"),
        sleep_breakdown=datos.get("sleep_breakdown"),
        estres_medio=datos.get("estres_medio"),
        body_battery_min=datos.get("body_battery_min"),
        training_status=datos.get("training_status"),
    )
    ciclo = ajustar_por_ciclo(datos.get("fase_ciclo"))

    st.markdown("---")
    st.subheader("1) Perfil del Atleta")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Edad", "22 años")
    with c2:
        st.metric("Sexo", "🏃‍♀️ Mujer")
    with c3:
        st.metric("Objetivo", "Maratón Feb")
    with c4:
        st.metric("Modalidad", "Running + Fuerza")

    st.markdown("---")
    st.subheader("2) Biomarcadores Garmin")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("HRV", f"{datos.get('hrv_actual') or 0:.0f} ms" if datos.get("hrv_actual") else "—")
    with c2:
        st.metric("Sleep score", f"{datos.get('sleep_score') or 0:.0f}/100" if datos.get("sleep_score") else "—")
    with c3:
        st.metric("Estrés", f"{datos.get('estres_medio') or 0:.0f}/100" if datos.get("estres_medio") else "—")
    with c4:
        st.metric("Body Battery min", f"{datos.get('body_battery_min') or 0:.0f}" if datos.get("body_battery_min") else "—")

    # Sleep breakdown detallado
    sb = datos.get("sleep_breakdown", {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("😴 Profundo", f"{sb.get('profundo_h', 0):.2f}h" if sb.get("profundo_h") else "—")
    with c2:
        st.metric("💭 REM", f"{sb.get('rem_h', 0):.2f}h" if sb.get("rem_h") else "—")
    with c3:
        st.metric("🔄 Vigilia", f"{sb.get('vigilia_h', 0):.2f}h" if sb.get("vigilia_h") else "—")
    with c4:
        st.metric("⏰ Despertares", f"{sb.get('despertares', 0):.0f}" if sb.get("despertares") else "—")

    # VO2max y Training Status
    c1, c2 = st.columns(2)
    with c1:
        st.metric("VO2max", f"{datos.get('vo2max', 0):.1f} ml/kg/min" if datos.get("vo2max") else "—")
    with c2:
        st.metric("Training Status", datos.get("training_status", "—"))

    st.markdown("---")
    st.subheader("3) Métricas Running (promedio 7d)")
    mrun = datos.get("metricas_running", {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("GCT", f"{mrun.get('tiempo_contacto_ms', 0):.0f} ms" if mrun.get("tiempo_contacto_ms") else "—")
    with c2:
        st.metric("Oscilación", f"{mrun.get('oscilacion_vertical_cm', 0):.1f} cm" if mrun.get("oscilacion_vertical_cm") else "—")
    with c3:
        st.metric("Potencia", f"{mrun.get('potencia_media_w', 0):.0f} W" if mrun.get("potencia_media_w") else "—")
    with c4:
        st.metric("FC media Z2", f"{mrun.get('fc_media', 0):.0f} bpm" if mrun.get("fc_media") else "—")

    # Training Effect aeróbico/anaeróbico
    c1, c2 = st.columns(2)
    with c1:
        st.metric("TE Aeróbico", f"{mrun.get('training_effect_aerobico', 0):.1f}/5" if mrun.get("training_effect_aerobico") else "—")
    with c2:
        st.metric("TE Anaeróbico", f"{mrun.get('training_effect_anaerobico', 0):.1f}/5" if mrun.get("training_effect_anaerobico") else "—")

    st.markdown("---")
    st.subheader("4) Lesiones Activas")
    lesiones = datos.get("lesiones_activas", [])
    if lesiones:
        for les in lesiones:
            st.warning(f"🚫 {les.get('zona', 'Desconocida')} — Grado {les.get('grado', '?')}")
    else:
        st.success("✅ Sin lesiones activas")

    st.markdown("---")
    st.subheader("5) Evaluaciones de Adaptación")

    # VO2max evaluation
    vo2_eval = evaluar_vo2max(datos.get("vo2max"))
    if vo2_eval.get("mensaje"):
        st.info(f"💪 VO2max: {vo2_eval['mensaje']}")

    # Training Effect evaluation
    te_eval = evaluar_training_effect(
        mrun.get("training_effect_aerobico"),
        mrun.get("training_effect_anaerobico"),
        datos.get("ultimas_3_actividades", [])
    )
    if te_eval.get("mensaje"):
        if te_eval["severidad"] >= 2:
            st.error(f"⚠️ Fatiga acumulada: {te_eval['mensaje']}")
        else:
            st.warning(f"⚠️ Fatiga moderada: {te_eval['mensaje']}")

    # Drills recommendation
    drills = recomendar_drills_especificos(
        mrun.get("tiempo_contacto_ms"),
        mrun.get("oscilacion_vertical_cm")
    )
    if drills.get("necesita_drills"):
        st.info(f"👟 Drills: {drills['mensaje']}")

    # 48-72h conflict detector
    conflictos = detectar_conflictos_48h(datos.get("ultimas_3_actividades", []))
    if conflictos.get("alerta"):
        st.warning(conflictos["alerta"])

    st.markdown("---")
    st.subheader("6) Estado de Recuperación")
    c1, c2, c3 = st.columns(3)
    with c1:
        color_emoji = {"verde": "🟢", "ambar": "🟡", "rojo": "🔴"}.get(semaforo.get("color", ""), "⚫")
        st.metric("Semáforo", f"{color_emoji} {semaforo.get('color', '—').upper()}")
    with c2:
        st.metric("Fase macrociclo", fase.get("fase_nombre", "—"))
    with c3:
        st.metric("Multiplicador", f"{semaforo.get('multiplicador_volumen', 1.0):.2f}x")

    st.info(semaforo.get("mensaje", "Sin mensaje de recuperación"))

    # Semáforo causa
    causa = semaforo.get("causa", [])
    if causa:
        st.caption(f"🎯 Causas: {', '.join(causa)}")

    st.markdown("---")
    st.subheader("7) Ciclo Menstrual")
    fase_ciclo = datos.get("fase_ciclo", {})
    if fase_ciclo:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Fase", fase_ciclo.get("fase", "—"))
        with c2:
            fatiga = fase_ciclo.get("fatiga_subjetiva", "—")
            st.metric("Fatiga subjetiva", f"{fatiga}/10" if fatiga != "—" else "—")
        with c3:
            st.metric("Estado ánimo", fase_ciclo.get("estado_animo", "—"))

    # Ciclo ajuste
    st.metric("Multiplicador volumen ciclo", f"{ciclo.get('multiplicador_volumen', 1.0):.2f}x")
    if not ciclo.get("permitir_calidad"):
        st.warning(f"⚠️ Fase menstrual: {ciclo.get('mensaje', 'Evitar máxima intensidad')}")
    if ciclo.get("hidratacion_extra"):
        st.info("💧 Aumentar hidratación y electrolitos durante esta fase")

    st.markdown("---")
    st.subheader("8) Carga y Running")

    cadencia_eval = evaluar_cadencia(datos.get("cadencia_media"))
    eficiencia = evaluar_eficiencia_aerobica(datos.get("actividades_z2", []))
    km_obj = calcular_volumen_semana(
        datos.get("km_semana_anterior", 0),
        datos.get("acwr", 1.0),
        datos.get("lesiones_activas", []),
        fase.get("km_semanales_max", 20),
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("ACWR", f"{datos.get('acwr', 0):.2f}")
    with c2:
        st.metric("Cadencia media", f"{datos.get('cadencia_media', 0):.0f} spm" if datos.get("cadencia_media") else "—")
    with c3:
        st.metric("Km objetivo semana", f"{km_obj:.1f} km")

    if cadencia_eval.get("necesita_drills"):
        st.warning(cadencia_eval.get("mensaje", "Cadencia mejorable"))
    else:
        st.success(cadencia_eval.get("mensaje", "Cadencia correcta"))

    if eficiencia.get("necesita_fartlek"):
        st.warning(eficiencia.get("mensaje", "Se recomienda incluir fartlek"))

    st.markdown("---")
    st.subheader("9) Actividades recientes (7 días)")
    conn = get_db_connection()
    try:
        df_act = pd.read_sql_query(
            """SELECT fecha, distancia_m/1000.0 AS km, ritmo_medio, fc_media, cadencia_media,
                      potencia_media_w, tiempo_contacto_ms, oscilacion_vertical_cm
               FROM actividades_garmin
               WHERE usuario_id=? AND fecha >= date('now', '-7 day')
               ORDER BY fecha DESC""",
            conn,
            params=(usuario_id,),
        )
        if df_act.empty:
            st.info("Sin actividades de Garmin en los últimos 7 días.")
        else:
            st.dataframe(df_act, use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"No se pudo leer actividades recientes: {e}")
    finally:
        conn.close()

    st.markdown("---")
    st.subheader("10) Plan semanal generado")
    plan = {}
    try:
        plan = generar_plan_semana(usuario_id, datetime.now())
        st.metric("Km plan", f"{plan.get('km_totales', 0):.1f} km")

        if plan.get("dias"):
            df_plan = pd.DataFrame(
                [
                    {
                        "Día": d.get("nombre", "—"),
                        "Tipo": d.get("tipo", "—"),
                        "Km": d.get("km", 0),
                        "Min": d.get("duracion_min", 0),
                        "Instrucción": d.get("instruccion", "—"),
                    }
                    for d in plan.get("dias", [])
                ]
            )
            st.dataframe(df_plan, use_container_width=True, hide_index=True)

        if plan.get("alertas"):
            for alerta in plan.get("alertas", []):
                st.warning(alerta)
    except Exception as e:
        st.error(f"Error generando plan semanal: {e}")

    st.markdown("---")
    st.subheader("11) Tabla de fuerza propuesta")
    conn = get_db_connection()
    try:
        tabla = generar_tabla_fuerza_semana(
            usuario_id,
            fase,
            semaforo,
            acwr=datos.get("acwr"),
            conn=conn,
        )
        if tabla:
            st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"No se pudo generar tabla de fuerza: {e}")
    finally:
        conn.close()

    st.markdown("---")
    st.subheader("12) Resumen ejecutivo")
    st.markdown(
        f"""
- Recuperación: **{semaforo.get('color', '—').upper()}**
- Fase macrociclo: **{fase.get('fase_nombre', '—')}**
- Multiplicador ciclo menstrual: **{ciclo.get('multiplicador_volumen', 1.0):.2f}x**
- Km objetivo: **{km_obj:.1f} km**
- Km plan final: **{plan.get('km_totales', 0):.1f} km**
"""
    )
