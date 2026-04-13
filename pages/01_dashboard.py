"""
pages/1_dashboard.py — Dashboard principal: saludo, métricas, plan semana, biométricos.
"""

import streamlit as st
from datetime import datetime, timedelta

from src.db.db_manager import obtener_perfil
from src.core.navbar import render_navbar
from src.core.dashboard_data import (
    resumen_semana_con_delta, metricas_garmin, progresion_pesos_ejercicios,
    inicio_semana, cargar_plan_semana_cache, checkpoints_objetivo_dashboard,
)
from src.core.dashboard_ui import (
    obtener_estado_ciclo_malena,
    render_macrociclo,
    render_grafico_sueno,
    obtener_titulo_macrociclo,
    render_objetivos_rendimiento_cards,
)
from src.core.dashboard_visuals import (
    render_strain_recovery_donuts, render_rhr_card, render_heatmap_training_intensity,
    render_metrics_sparklines,
)
from src.plan.reglas import obtener_fase_macrociclo
from src.db.db_manager import get_db_connection

render_navbar("dashboard")

if "usuario_id" not in st.session_state:
    st.warning("Selecciona tu perfil en la página de inicio.")
    st.stop()
user_actual = st.session_state.usuario_id

# Validar que los datos sean consistentes con el usuario actual
# Si cambió de usuario, limpiar caché y datos del dashboard anterior
if "dashboard_last_user" not in st.session_state:
    st.session_state["dashboard_last_user"] = user_actual
elif st.session_state["dashboard_last_user"] != user_actual:
    # Usuario cambió — limpiar todos los caches para este dashboard
    st.cache_data.clear()
    st.session_state["dashboard_last_user"] = user_actual

perfil = obtener_perfil(user_actual) or {}
nombre = perfil.get("nombre", "Atleta")

# ---------------------------------------------------------------------------
# 1. Saludo contextual en español
# ---------------------------------------------------------------------------
_DIAS_ES  = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles",
             "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo"}
_MESES_ES = {"January":"enero","February":"febrero","March":"marzo","April":"abril",
             "May":"mayo","June":"junio","July":"julio","August":"agosto",
             "September":"septiembre","October":"octubre","November":"noviembre","December":"diciembre"}
hora = datetime.now().hour
saludo = "Buenos días" if hora < 13 else ("Buenas tardes" if hora < 20 else "Buenas noches")
hoy = datetime.now()
fecha_es = f"{_DIAS_ES[hoy.strftime('%A')]} {hoy.day} de {_MESES_ES[hoy.strftime('%B')]} de {hoy.year}"

_objetivo_tipo = str(perfil.get("objetivo_tipo") or "maraton").lower()
_es_ultra_dash = _objetivo_tipo in ("ultramaraton", "ultra", "trail_ultra")
if _es_ultra_dash:
    from src.plan.reglas import obtener_fase_macrociclo_ultra
    fase_hoy = obtener_fase_macrociclo_ultra(datetime.now(), perfil.get("fecha_objetivo", ""))
else:
    fase_hoy = obtener_fase_macrociclo()
_genero_dash = str(perfil.get("genero", "")).strip().lower()
_es_mujer_dash = _genero_dash in ("mujer", "female", "f", "w")
estado_ciclo = obtener_estado_ciclo_malena(user_actual) if _es_mujer_dash else None
fase_ciclo_txt = estado_ciclo["fase"] if estado_ciclo else ""
ciclo_sub = f" · Ciclo: **{fase_ciclo_txt}**" if fase_ciclo_txt else ""
st.markdown(f"## {saludo}, {nombre} 👋")
st.caption(f"{fecha_es} · Fase: **{fase_hoy['fase_nombre']}**{ciclo_sub}")

# ---------------------------------------------------------------------------
# 2. Métricas 7d con delta
# ---------------------------------------------------------------------------
res = resumen_semana_con_delta(user_actual)

def _delta_fmt(v):
    if v is None or v == 0: return None
    return f"+{v}" if v > 0 else str(v)

def _delta_badge(v, positivos_arriba=True, decimales=1):
    if v is None:
        return "-"
    try:
        num = float(v)
    except (TypeError, ValueError):
        return "-"
    if num == 0:
        return "- 0"
    sube = num > 0
    mejora = sube if positivos_arriba else not sube
    flecha = "↗" if mejora else "↘"
    signo = "+" if num > 0 else ""
    return f"{flecha} {signo}{num:.{decimales}f}"

st.markdown(
    """
    <style>
    .kpi-title {
        display:flex;
        align-items:center;
        gap:8px;
        font-size:2rem;
        font-weight:700;
        color:#ffffff;
        margin:4px 0 10px;
    }
    .kpi-grid {
        display:grid;
        grid-template-columns:repeat(4, minmax(180px, 1fr));
        gap:14px;
        margin-bottom:4px;
    }
    .kpi-card {
        background:linear-gradient(165deg, #141b27 0%, #101722 100%);
        border:1px solid rgba(255,255,255,0.04);
        border-left:4px solid var(--kpi-accent);
        border-radius:16px;
        padding:14px 16px 12px;
        min-height:108px;
        box-shadow:0 12px 28px rgba(0,0,0,0.22);
    }
    .kpi-top {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:8px;
        margin-bottom:10px;
    }
    .kpi-label {
        display:flex;
        align-items:center;
        gap:8px;
        color:#b4c0cf;
        font-size:0.82rem;
        font-weight:700;
        text-transform:uppercase;
        letter-spacing:0.55px;
    }
    .kpi-chip {
        background:#273241;
        color:#9da9b8;
        border-radius:7px;
        font-size:0.74rem;
        font-weight:600;
        padding:4px 8px;
        line-height:1;
    }
    .kpi-value {
        color:#ffffff;
        font-size:2.15rem;
        font-weight:800;
        line-height:1;
        margin:2px 0 10px;
    }
    .kpi-delta {
        display:inline-block;
        border-radius:7px;
        padding:4px 8px;
        font-size:0.8rem;
        font-weight:700;
        line-height:1;
    }
    .kpi-delta.pos {
        color:#19db8a;
        background:rgba(25, 219, 138, 0.15);
    }
    .kpi-delta.neg {
        color:#ff8a5b;
        background:rgba(255, 138, 91, 0.12);
    }
    .kpi-delta.neu {
        color:#a9b3c0;
        background:rgba(169, 179, 192, 0.14);
    }
    @media (max-width: 1024px) {
        .kpi-grid { grid-template-columns:repeat(2, minmax(180px, 1fr)); }
    }
    @media (max-width: 640px) {
        .kpi-grid { grid-template-columns:1fr; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

km_val = f"{(res.get('km') or 0):.1f}"
fuerza_val = str(int(res.get("fuerza") or 0))
sueno_raw = res.get("sueno")
sueno_val = f"{float(sueno_raw):.1f}" if sueno_raw else "-"
hrv_raw = res.get("hrv")
hrv_val = f"{float(hrv_raw):.0f}" if hrv_raw else "-"

km_delta_num = float(res.get("km_delta") or 0)
fuerza_delta_num = float(res.get("fuerza_delta") or 0)
sueno_delta_num = float(res.get("sueno_delta") or 0)
hrv_delta_num = float(res.get("hrv_delta") or 0)

km_delta_cls = "pos" if km_delta_num > 0 else ("neg" if km_delta_num < 0 else "neu")
fuerza_delta_cls = "pos" if fuerza_delta_num > 0 else ("neg" if fuerza_delta_num < 0 else "neu")
sueno_delta_cls = "pos" if sueno_delta_num > 0 else ("neg" if sueno_delta_num < 0 else "neu")
hrv_delta_cls = "pos" if hrv_delta_num > 0 else ("neg" if hrv_delta_num < 0 else "neu")

st.markdown(
    f"""
    <div class='kpi-title'>
        <span style='color:#b7ff33;'>⏱</span>
        <span>Resumen Últimos 7 Días</span>
    </div>
    <div class='kpi-grid'>
        <div class='kpi-card' style='--kpi-accent:#00db81;'>
            <div class='kpi-top'>
                <div class='kpi-label'><span style='color:#00db81;'>⌁</span> KM</div>
                <span class='kpi-chip'>Últimos 7 días</span>
            </div>
            <div class='kpi-value'>{km_val}</div>
            <span class='kpi-delta {km_delta_cls}'>{_delta_badge(res.get('km_delta'), positivos_arriba=True, decimales=1)}</span>
        </div>
        <div class='kpi-card' style='--kpi-accent:#3b82f6;'>
            <div class='kpi-top'>
                <div class='kpi-label'><span style='color:#3b82f6;'>∿</span> HRV MEDIO</div>
                <span class='kpi-chip'>ms</span>
            </div>
            <div class='kpi-value'>{hrv_val}</div>
            <span class='kpi-delta {hrv_delta_cls}'>{_delta_badge(res.get('hrv_delta'), positivos_arriba=True, decimales=1)}</span>
        </div>
        <div class='kpi-card' style='--kpi-accent:#a855f7;'>
            <div class='kpi-top'>
                <div class='kpi-label'><span style='color:#a855f7;'>✤</span> FUERZA</div>
                <span class='kpi-chip'>Sesiones</span>
            </div>
            <div class='kpi-value'>{fuerza_val}</div>
            <span class='kpi-delta {fuerza_delta_cls}'>{_delta_badge(res.get('fuerza_delta'), positivos_arriba=True, decimales=0)}</span>
        </div>
        <div class='kpi-card' style='--kpi-accent:#ff7a1a;'>
            <div class='kpi-top'>
                <div class='kpi-label'><span style='color:#ff7a1a;'>◔</span> SUEÑO MEDIO</div>
                <span class='kpi-chip'>h/noche</span>
            </div>
            <div class='kpi-value'>{sueno_val}</div>
            <span class='kpi-delta {sueno_delta_cls}'>{_delta_badge(res.get('sueno_delta'), positivos_arriba=True, decimales=1)}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 3. Macrociclo — 5 fases + barra global hacia el objetivo
# DYNAMIC TITLE v2 - Updated 2026-04-06
# ---------------------------------------------------------------------------
titulo_macrociclo = obtener_titulo_macrociclo(user_actual)
st.subheader(titulo_macrociclo)
render_macrociclo(user_actual)

objetivos_cards = checkpoints_objetivo_dashboard(user_actual, _objetivo_tipo)
render_objetivos_rendimiento_cards(objetivos_cards)

st.divider()

# ---------------------------------------------------------------------------
# 5. Recovery & Load Analysis (Compact)
# ---------------------------------------------------------------------------
conn = get_db_connection()
try:
    st.subheader("💓 Recovery & Load Analysis")

    # RHR Card
    render_rhr_card(user_actual, conn)

    # Donuts: Recovery vs Strain (Independent metrics)
    try:
        from src.plan.helpers import cargar_datos_plan
        datos = cargar_datos_plan(user_actual)
        recovery_score = datos.get("hrv_recovery", {}).get("recovery_score", 50)
        acwr = datos.get("acwr", 1.0)
        render_strain_recovery_donuts(recovery_score, acwr)
    except Exception as e:
        st.caption(f"No se pudo cargar datos de recuperación: {e}")

    st.divider()

    # Sparklines: Métricas de últimos 7 días (Compact)
    render_metrics_sparklines(user_actual, conn)

    st.divider()

    # Heatmap: Intensidad de entrenamientos
    render_heatmap_training_intensity(user_actual, conn)

finally:
    conn.close()

st.divider()

# ---------------------------------------------------------------------------
# 6. Plan semana + Progresión pesos
# ---------------------------------------------------------------------------
_EMOJIS = {"Tirada Larga":"🏃","Progresiva":"📈","Tempo (umbral)":"⚡","Intervalos VO2max":"🔥",
           "Carrera Z2":"🚶","Regenerativo":"💧","Fuerza":"💪","Fuerza Activ.":"💪",
           "Fuerza Tren Superior":"💪","Descanso":"🛌","Movilidad":"🧘","Sustitución":"🔄","Rodaje Corto":"🏃"}
_BADGE  = {"Fuerza":"#9B59B6","Tirada Larga":"#C9FF00","Progresiva":"#C9FF00","Carrera Z2":"#C9FF00",
           "Tempo (umbral)":"#C9FF00","Regenerativo":"#00C8C8","Intervalos VO2max":"#FF6B6B",
           "Descanso":"#3a4150","Movilidad":"#3a4150"}

col_plan, col_pesos = st.columns(2, gap="large")

with col_plan:
    st.subheader("Plan esta semana")
    lunes_str = inicio_semana(datetime.now()).strftime("%Y-%m-%d")
    try:
        plan_dash = cargar_plan_semana_cache(user_actual, lunes_str)
    except Exception as e:
        # No usar fallback viejo — mejor mostrar que hay error
        import logging
        logging.error(f"Error cargando plan: {e}")
        plan_dash = None
    if plan_dash:
        for dia in plan_dash["dias"]:
            bc  = _BADGE.get(dia["tipo"], "#8B949E")
            sub = f"{dia['km']} km" if dia["km"] else f"{dia['duracion_min']}'"
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"background:#131D2B;border-radius:8px;padding:6px 12px;margin-bottom:7px;'>"
                f"<span style='color:#C9E1FF;font-size:0.82rem;font-weight:700;min-width:70px;'>{dia['dia']}</span>"
                f"<span style='color:{bc};font-size:0.82rem;flex:1;padding:0 8px;'>"
                f"{_EMOJIS.get(dia['tipo'],'📅')} {dia['tipo']}</span>"
                f"<span style='color:#8B949E;font-size:0.75rem;'>{sub}</span></div>",
                unsafe_allow_html=True)
    else:
        st.info("Aún no hay plan para esta semana.")
        st.page_link("pages/02_plan.py", label="→ Ir a Plan Semanal y generar uno")

with col_pesos:
    st.subheader("Progresión de pesos")
    df_pesos = progresion_pesos_ejercicios(user_actual)
    if df_pesos.empty:
        st.info("Registra sesiones de fuerza en el **Diario** para ver la progresión.")
    else:
        for _, row in df_pesos.iterrows():
            color = "#00C896" if row["_trend"] == "up" else ("#FF6B6B" if row["_trend"] == "dn" else "#8B949E")
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"background:#131D2B;border-radius:8px;padding:6px 12px;margin-bottom:7px;'>"
                f"<span style='color:#C9E1FF;font-size:0.82rem;flex:1;'>{row['Ejercicio']}</span>"
                f"<span style='color:#d8e9db;font-size:0.82rem;margin:0 8px;'>{row['Peso']} kg &nbsp; {row['S×R']}</span>"
                f"<span style='color:{color};font-weight:800;font-size:0.82rem;'>{row['Δ']}</span></div>",
                unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# 5. Grid biométrico Garmin (1×7)
# ---------------------------------------------------------------------------
st.subheader("Biométricos Garmin (últimos 7 días)")
met = metricas_garmin(user_actual)

if all(v is None for v in met.values()):
    st.markdown("<div style='background:#161b22;border:1px solid #30363d;border-radius:10px;"
                "padding:20px;text-align:center;color:#484f58;font-size:13px;'>"
                "Sin datos Garmin aún — sincroniza en la página de <b>Garmin</b> para ver tus métricas."
                "</div>", unsafe_allow_html=True)
else:
    def _card(label, value, unit="", max_val=100, color="#C9FF00"):
        v_str = f"{value:.0f} {unit}".strip() if value is not None else "—"
        pct   = min(int(100 * float(value) / max_val), 100) if value is not None else 0
        return (f"<div style='background:#131D2B;border:1px solid rgba(201,255,0,0.15);"
                f"border-radius:8px;padding:8px 10px;min-height:74px;'>"
                f"<div style='color:#8B949E;font-size:0.62rem;font-weight:700;text-transform:uppercase;line-height:1.1;'>{label}</div>"
                f"<div style='color:{color};font-weight:800;font-size:0.95rem;margin:4px 0;'>{v_str}</div>"
                f"<div style='background:#0c2922;border-radius:3px;height:4px;'>"
                f"<div style='background:{color};width:{pct}%;height:4px;border-radius:3px;'></div></div></div>")

    acwr_color = "#FF6B6B" if (met["acwr"] or 0) > 1.3 else "#C9FF00"
    cards = [
        ("HRV", met["hrv"], "ms", 80, "#C9FF00"),
        ("Sueño", met["sueno_h"], "h", 9, "#7EB8E0"),
        ("Score sueño", met["sueno_score"], "", 100, "#7EB8E0"),
        ("Cadencia", met["cadencia"], "spm", 200, "#00C896"),
        ("ACWR", met["acwr"], "", 1.5, acwr_color),
        ("FC Reposo", met["fc_reposo"], "bpm", 80, "#C9E1FF"),
        ("Estrés", met["estres"], "", 100, "#F5A623"),
    ]
    row = st.columns(7, gap="small")
    for col, (lbl, val, unit, mx, colr) in zip(row, cards):
        col.markdown(_card(lbl, val, unit, mx, colr), unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# 6. Recordatorio analítica
# ---------------------------------------------------------------------------
FECHA_ANALITICA = datetime(2026, 5, 1)
dias_anal = (FECHA_ANALITICA - datetime.now()).days
if dias_anal < 0:
    st.info("🩸 Analítica completada. Siguiente revisión: noviembre 2026.")
elif dias_anal < 15:
    st.error(f"🩸 Analítica en **{dias_anal} días** (antes del 1 mayo). ¡Pide cita urgente!")
elif dias_anal < 30:
    st.warning(f"🩸 Analítica en **{dias_anal} días** (antes del 1 mayo). Empieza a gestionar cita.")
else:
    st.info(f"🩸 Próxima analítica: 1 mayo 2026 (en {dias_anal} días).")

st.divider()

# ---------------------------------------------------------------------------
# 7. Gráfico de sueño — última semana
# ---------------------------------------------------------------------------
st.subheader("😴 Sueño — última semana")
render_grafico_sueno(user_actual)
