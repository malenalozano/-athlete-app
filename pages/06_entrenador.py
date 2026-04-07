"""
Página: Entrenador
Muestra todos los datos y decisiones del sistema para generar el siguiente plan semanal.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from src.core.navbar import render_navbar
from src.plan.helpers import cargar_datos_plan
from src.plan.reglas import (
    obtener_fase_macrociclo, obtener_fase_macrociclo_usuario,
    calcular_semaforo, aplicar_restricciones_lesion,
    evaluar_cadencia, calcular_volumen_semana, evaluar_eficiencia_aerobica,
    ajustar_por_ciclo
)
from src.db.db_manager import obtener_perfil as _obtener_perfil
from src.plan.motor import generar_plan_semana
from src.plan.memoria_fuerza import generar_tabla_fuerza_semana
from src.db.db_manager import get_db_connection
from src.core.styles import apply_custom_css

# Configurar página
apply_custom_css()
render_navbar("entrenador")

st.title("🧠 Entrenador — Análisis de Datos y Decisiones")
st.markdown("""
Esta página muestra **TODO** lo que el sistema analiza para generar tu plan semanal.
Datos en tiempo real, decisiones del código y próximas acciones.
""")

# Verificar autenticación
if "usuario_id" not in st.session_state:
    st.warning("Selecciona tu perfil en la página de inicio.")
    st.stop()

usuario_id = st.session_state.get("usuario_id", 1)

# Validar que los datos sean consistentes con el usuario actual
if "entrenador_last_user" not in st.session_state:
    st.session_state["entrenador_last_user"] = usuario_id
elif st.session_state["entrenador_last_user"] != usuario_id:
    # Usuario cambió — limpiar caches
    st.cache_data.clear()
    st.session_state["entrenador_last_user"] = usuario_id

conn = get_db_connection()

# Cargar perfil del usuario actual
_perfil = _obtener_perfil(usuario_id) or {}
_genero = str(_perfil.get("genero", "")).strip().lower()
_es_mujer = _genero in ("mujer", "female", "f", "w", "femenino")
_objetivo_tipo = str(_perfil.get("objetivo_tipo", "")).strip().lower()
_objetivo_label = "Ultra" if "ultra" in _objetivo_tipo else "Maratón"

# ============================================================================
# SECCIÓN 1: DATOS BIOMÉTRICOS ACTUALES
# ============================================================================

st.markdown("---")
st.header("📊 1. Datos Biométricos Actuales")

# Inicializar datos como dict vacío para evitar NameError si hay excepción
datos = {}

try:
    datos = cargar_datos_plan(usuario_id)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "HRV Actual",
            f"{datos['hrv_actual']:.0f} ms" if datos['hrv_actual'] else "—",
            delta=f"{((datos['hrv_actual']-datos['hrv_media_7d'])/datos['hrv_media_7d']*100):.1f}%" if datos['hrv_actual'] and datos['hrv_media_7d'] else None
        )
    
    with col2:
        st.metric(
            "Sleep Score",
            f"{datos['sleep_score']}/100" if datos['sleep_score'] else "—",
            delta="Subóptimo" if datos['sleep_score'] and datos['sleep_score'] < 80 else "Bueno"
        )
    
    with col3:
        st.metric(
            "Estrés Medio",
            f"{datos.get('estres_medio', 0)}/100" if datos.get('estres_medio') else "—"
        )
    
    with col4:
        bb = datos.get('body_battery_min')
        st.metric(
            "Body Battery",
            f"{bb}/100" if bb else "—",
            delta="Bajo" if bb and bb < 20 else "Normal"
        )
    
    # Detalles de sueño
    st.subheader("💤 Desglose de Sueño")
    col_sleep1, col_sleep2, col_sleep3, col_sleep4 = st.columns(4)
    
    sb = datos.get("sleep_breakdown", {})
    with col_sleep1:
        total_h = sb.get('horas_totales')
        st.info(f"**Total:** {total_h:.1f}h" if total_h is not None else "**Total:** —")
    with col_sleep2:
        prof_h = sb.get('profundo_h')
        st.success(f"**Profundo:** {prof_h:.1f}h" if prof_h is not None else "**Profundo:** —")
    with col_sleep3:
        rem_h = sb.get('rem_h')
        st.warning(f"**REM:** {rem_h:.1f}h" if rem_h is not None else "**REM:** —")
    with col_sleep4:
        vig_h = sb.get('vigilia_h')
        st.error(f"**Vigilia:** {vig_h:.1f}h" if vig_h is not None else "**Vigilia:** —")
    
except Exception as e:
    st.error(f"Error cargando datos biométricos: {str(e)}")

# ============================================================================
# SECCIÓN 2: ANÁLISIS DE CARRERA
# ============================================================================

st.markdown("---")
st.header("🏃 2. Análisis de Carrera & Rendimiento")

col_run1, col_run2, col_run3 = st.columns(3)

with col_run1:
    st.metric(
        "Cadencia Media",
        f"{datos.get('cadencia_media', 0):.0f} spm",
        delta="Baja - Técnica" if datos.get('cadencia_media', 0) < 170 else "Excelente" if datos.get('cadencia_media', 0) > 175 else "Normal"
    )

with col_run2:
    st.metric(
        "VO2max",
        "—"  # Métrica no disponible actualmente
    )

with col_run3:
    st.metric(
        "ACWR",
        f"{datos.get('acwr', 0):.2f}",
        delta="🔴 Elevado" if datos.get('acwr', 0) > 1.5 else "🟡 Moderado" if datos.get('acwr', 0) > 1.3 else "🟢 Normal"
    )

# Histórico de corridas últimos 7 días
st.subheader("📈 Últimas 7 Corridas")

try:
    df_act_week = pd.read_sql_query(
        """SELECT fecha, distancia_m/1000 as km, cadencia_media, fc_media, ritmo_medio, 
                  potencia_media_w, tiempo_contacto_ms, oscilacion_vertical_cm
           FROM actividades_garmin
           WHERE usuario_id=? AND fecha >= date('now', '-7 days')
           AND (
               LOWER(COALESCE(tipo_deporte, '')) LIKE '%running%'
               OR LOWER(COALESCE(tipo_deporte, '')) LIKE '%trail%'
               OR LOWER(COALESCE(tipo_deporte, '')) LIKE '%treadmill%'
               OR LOWER(COALESCE(tipo_deporte, '')) LIKE '%street_running%'
               OR LOWER(COALESCE(tipo_deporte, '')) LIKE '%indoor_running%'
           )
           ORDER BY fecha DESC""",
        conn, params=(usuario_id,))
    
    if not df_act_week.empty:
        st.dataframe(df_act_week, use_container_width=True, hide_index=True)
    else:
        st.info("No hay actividades en los últimos 7 días.")
except Exception as e:
    st.error(f"Error: {str(e)}")

# ============================================================================
# SECCIÓN 3: FASE DEL MACROCICLO
# ============================================================================

st.markdown("---")
st.header("📅 3. Fase del Macrociclo")

fase = obtener_fase_macrociclo_usuario(usuario_id)
_fecha_obj_str = _perfil.get("fecha_objetivo")
if _fecha_obj_str:
    try:
        fecha_objetivo = datetime.strptime(str(_fecha_obj_str), '%Y-%m-%d')
        dias_restantes = (fecha_objetivo - datetime.now()).days
        semanas_restantes = dias_restantes // 7
    except Exception:
        dias_restantes = semanas_restantes = None
else:
    dias_restantes = semanas_restantes = None

col_fase1, col_fase2 = st.columns(2)

with col_fase1:
    st.success(f"**Fase Actual:** {fase['fase_nombre']}")
    st.info(f"**KM Máximo Semanal:** {fase['km_semanales_max']} km")
    st.warning(f"**Días Fuerza Recomendados:** {fase['dias_fuerza']} días")

with col_fase2:
    st.metric(f"Días hasta {_objetivo_label}", dias_restantes if dias_restantes is not None else "—")
    st.metric(f"Semanas hasta {_objetivo_label}", semanas_restantes if semanas_restantes is not None else "—")

st.markdown(f"""
**Enfoque de Carrera:** {fase['enfoque_running']}

**Enfoque de Fuerza:** {fase['enfoque_fuerza']}

**Restricciones:** 
- Limitar Impacto: {'Sí' if fase['restricciones']['limitar_impacto'] else 'No'}
- Permitir Series: {'Sí' if fase['restricciones']['permitir_series'] else 'No'}
""")

# ============================================================================
# SECCIÓN 4: SEMÁFORO DE RECUPERACIÓN
# ============================================================================

st.markdown("---")
st.header("🚦 4. Semáforo de Recuperación")

semaforo = calcular_semaforo(
    hrv_actual=datos.get("hrv_actual"),
    hrv_media_7d=datos.get("hrv_media_7d"),
    sleep_score=datos.get("sleep_score"),
    sleep_breakdown=datos.get("sleep_breakdown"),
    estres_medio=datos.get("estres_medio"),
    body_battery_min=datos.get("body_battery_min"),
    training_status=datos.get("training_status"),
)

# Color visual del semáforo
color_map = {"verde": "🟢", "ambar": "🟡", "rojo": "🔴"}
color_visual = color_map.get(semaforo["color"], "⚪")

st.markdown(f"### {color_visual} Color: **{semaforo['color'].upper()}**")
st.markdown(f"#### Mensaje: {semaforo['mensaje']}")
st.markdown(f"""
**Efectos en el Plan:**
- Multiplicador de Volumen: **{semaforo['multiplicador_volumen']:.2f}x**
- ¿Permitir Calidad (Series/Intervalos)?: **{'Sí' if semaforo['permitir_calidad'] else 'No'}**
""")

# ============================================================================
# SECCIÓN 5: CICLO MENSTRUAL (solo perfiles femeninos)
# ============================================================================

ciclo_data = None
if _es_mujer:
    st.markdown("---")
    st.header("🩸 5. Ciclo Menstrual - Ajustes")

    ciclo_data = datos.get("ciclo_menstrual") or datos.get("fase_ciclo")

    if ciclo_data:
        col_ciclo1, col_ciclo2, col_ciclo3 = st.columns(3)

        with col_ciclo1:
            fase_txt = ciclo_data.get('fase') or ciclo_data.get('fase_nombre') or 'Desconocida'
            origen_txt = ciclo_data.get('origen')
            st.info(f"**Fase:** {fase_txt}" + (f" ({origen_txt})" if origen_txt else ""))

        with col_ciclo2:
            st.metric("Multiplicador Volumen", f"{ciclo_data.get('multiplicador_volumen', 1.0):.2f}x")

        with col_ciclo3:
            st.metric("¿Permitir Calidad?", "Sí" if ciclo_data.get('permitir_calidad', True) else "No")

        if ciclo_data.get('hidratacion_extra'):
            st.warning("💧 **Fase de estrés hormonal:** Aumentar hidratación y electrolitos")
    else:
        st.info("No hay datos de ciclo menstrual. Añade tu ciclo en la pestaña Diario.")

# ============================================================================
# SECCIÓN 6: RESTRICCIONES & LESIONES
# ============================================================================

st.markdown("---")
st.header("⚠️ 6. Restricciones & Lesiones Activas")

restricciones = aplicar_restricciones_lesion(datos.get("lesiones_activas", []))

if datos.get("lesiones_activas"):
    st.error(f"**Lesiones Activas:** {len(datos['lesiones_activas'])}")
    
    for les in datos["lesiones_activas"]:
        st.markdown(f"""
        - **{les.get('tipo', 'Desconocida')}** (Grado {les.get('grado', '?')}/10)
          - Restricciones: {', '.join(restricciones.get('alertas', [])) if restricciones.get('alertas') else 'Ninguna'}
        """)
else:
    st.success("✅ Sin lesiones activas")

# ============================================================================
# SECCIÓN 7: EVALUACIONES ESPECIALIZADAS
# ============================================================================

st.markdown("---")
st.header("🔍 7. Evaluaciones Especializadas")

col_evals1, col_evals2, col_evals3 = st.columns(3)

# Cadencia
cadencia_eval = evaluar_cadencia(datos.get("cadencia_media"))
with col_evals1:
    st.subheader("📊 Cadencia")
    if cadencia_eval["necesita_drills"]:
        st.warning(f"🔧 {cadencia_eval['mensaje']}")
    else:
        st.success(f"✅ {cadencia_eval['mensaje']}")

# Eficiencia Aeróbica
eficiencia = evaluar_eficiencia_aerobica(datos.get("actividades_z2", []))
with col_evals2:
    st.subheader("💨 Eficiencia Aeróbica")
    if eficiencia["tendencia"] == "sin_datos":
        st.info("Sin datos suficientes (mínimo 4 sesiones Z2 en 28 días).")
    elif eficiencia["necesita_fartlek"]:
        st.warning("⚠️ Tendencia estancada. Conviene añadir fartlek suave.")
    else:
        st.success("✅ Tendencia positiva")

# Volumen Objetivo
with col_evals3:
    st.subheader("📏 Volumen Estimado")
    km_objetivo = calcular_volumen_semana(
        datos.get("km_semana_anterior", 15),
        datos.get("acwr", 0.8),
        datos.get("lesiones_activas", []),
        fase["km_semanales_max"]
    )
    st.info(f"**{km_objetivo:.1f} km/semana**")

# ============================================================================
# SECCIÓN 8: PLAN SEMANAL GENERADO
# ============================================================================

st.markdown("---")
st.header("📋 8. Plan Semanal Generado")

# Inicializar plan como None para evitar NameError en SECCIÓN 10
plan = None

try:
    hoy = datetime.now()
    lunes = hoy - timedelta(days=hoy.weekday())
    plan = generar_plan_semana(usuario_id, lunes)
    
    st.subheader(f"Total: {plan['km_totales']:.1f} km | Fase: {plan['fase']['fase_nombre']}")
    
    # Tabla de días
    if plan.get('dias'):
        df_dias = pd.DataFrame([
            {
                "Día": dia.get("nombre", "—"),
                "Tipo": dia.get("tipo", "—"),
                "Km": f"{dia.get('km', 0):.1f}",
                "Duración": f"{dia.get('duracion_min', 0):.0f} min",
                "Instrucciones": dia.get("instruccion", "—")[:50] + "..." if dia.get("instruccion") else "—"
            }
            for dia in plan.get('dias', [])
        ])
        st.dataframe(df_dias, use_container_width=True, hide_index=True)
    
    # Alertas
    if plan["alertas"]:
        st.subheader("🔔 Alertas del Plan")
        for alerta in plan["alertas"]:
            st.warning(alerta)
    
except Exception as e:
    st.error(f"Error generando plan: {str(e)}")

# ============================================================================
# SECCIÓN 9: TABLA DE FUERZA
# ============================================================================

st.markdown("---")
st.header("💪 9. Sesión de Fuerza Propuesta")

try:
    tabla_fuerza = generar_tabla_fuerza_semana(
        usuario_id, 
        fase, 
        semaforo, 
        acwr=datos.get("acwr"),
        conn=conn
    )
    
    df_fuerza = pd.DataFrame(tabla_fuerza)
    st.dataframe(df_fuerza, use_container_width=True, hide_index=True)
    
except Exception as e:
    st.error(f"Error generando tabla de fuerza: {str(e)}")

# ============================================================================
# SECCIÓN 10: RESUMEN EJECUTIVO
# ============================================================================

st.markdown("---")
st.header("📌 10. Resumen Ejecutivo - Siguiente Plan Semanal")

if plan:
    summary_col1, summary_col2 = st.columns(2)

    with summary_col1:
        km_vol = float(plan.get('km_totales', 0)) if plan.get('km_totales') else 0
        st.markdown(f"""
        ### Condiciones de Entrenamiento
        - **Estado de Recuperación:** {semaforo['color'].upper()}
        - **Volumen Objetivo:** {km_vol:.1f} km
        - **Esfuerzo Máximo Permitido:** {'Sí' if semaforo['permitir_calidad'] else 'No - Solo Z1/Z2'}
        - **Carga Acumulada (ACWR):** {datos.get('acwr', 0):.2f}
        """)

    with summary_col2:
        st.markdown(f"""
        ### Ajustes Aplicados
        - **Ciclo Menstrual:** {ciclo_data.get('fase_nombre', 'N/A') if (_es_mujer and ciclo_data) else ('N/A' if _es_mujer else 'No aplica')}
        - **Cadencia Drills:** {'Sí - Incluir 5min técnica' if cadencia_eval['necesita_drills'] else 'No necesarios'}
        - **Lesiones Activas:** {'Sí - Aplicadas sustituciones' if datos.get('lesiones_activas') else 'Ninguna'}
        - **Fase del Macrociclo:** {fase['fase_nombre']}
        """)

    st.success("✅ Todos los datos están listos para generar tu plan semanal personalizado.")
else:
    st.warning("⚠️ El plan no se generó correctamente. Revisa los errores en la sección 8.")


if conn:
    try:
        conn.close()
    except:
        pass
