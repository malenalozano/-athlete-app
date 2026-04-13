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
if "dashboard_last_user" not in st.session_state:
    st.session_state["dashboard_last_user"] = user_actual
elif st.session_state["dashboard_last_user"] != user_actual:
    st.cache_data.clear()
    st.session_state["dashboard_last_user"] = user_actual

perfil = obtener_perfil(user_actual) or {}
nombre = perfil.get("nombre", "Atleta")

# ---------------------------------------------------------------------------
# 1. Saludo contextual + Countdown objetivo
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
ciclo_emoji = " 🌙" if fase_ciclo_txt else ""

# Countdown al objetivo
from datetime import date as _date
_fecha_obj_str = str(perfil.get("fecha_objetivo") or "2027-02-21")
try:
    _fecha_obj = _date.fromisoformat(_fecha_obj_str[:10])
except Exception:
    _fecha_obj = _date(2027, 2, 21)
_dias_left = (_fecha_obj - _date.today()).days
_semanas_left = _dias_left // 7
_obj_nombre = perfil.get("objetivo_nombre") or "Valencia Marathon"

# ---------------------------------------------------------------------------
# Compute KPI data
# ---------------------------------------------------------------------------
res = resumen_semana_con_delta(user_actual)
km_val = f"{(res.get('km') or 0):.1f}"
fuerza_val = str(int(res.get("fuerza") or 0))
sueno_raw = res.get("sueno")
sueno_val = f"{float(sueno_raw):.1f}" if sueno_raw else "—"
hrv_raw = res.get("hrv")
hrv_val = f"{float(hrv_raw):.0f}" if hrv_raw else "—"

km_delta_num     = float(res.get("km_delta") or 0)
fuerza_delta_num = float(res.get("fuerza_delta") or 0)
sueno_delta_num  = float(res.get("sueno_delta") or 0)
hrv_delta_num    = float(res.get("hrv_delta") or 0)

def _delta_html(num, decimales=1):
    if num == 0:
        return '<span style="font-size:0.75rem;font-weight:700;padding:3px 8px;border-radius:6px;background:rgba(125,133,144,0.12);color:#8B949E;">— 0</span>'
    signo = "+" if num > 0 else ""
    color = "#22c55e" if num > 0 else "#f85149"
    bg = "rgba(34,197,94,0.1)" if num > 0 else "rgba(248,81,73,0.1)"
    flecha = "↗" if num > 0 else "↘"
    return f'<span style="font-size:0.75rem;font-weight:700;padding:3px 8px;border-radius:6px;background:{bg};color:{color};">{flecha} {signo}{num:.{decimales}f}</span>'

# Ciclo badge for female users
_ciclo_badge_html = ""
if estado_ciclo:
    _fase_c = estado_ciclo.get("fase", "")
    _dia_c  = estado_ciclo.get("dia_ciclo", "")
    _ciclo_badge_html = f'<span style="background:rgba(236,72,153,0.2);color:#f9a8d4;border:1px solid rgba(236,72,153,0.3);border-radius:9999px;padding:4px 12px;font-size:0.75rem;font-weight:600;">🌸 {_fase_c}{(" — Día " + str(_dia_c)) if _dia_c else ""}</span>'

# ---------------------------------------------------------------------------
# 1. Hero Greeting Section
# ---------------------------------------------------------------------------
st.markdown(f"""
<div style="
  position:relative;
  border-radius:16px;
  padding:2rem;
  overflow:hidden;
  background:linear-gradient(135deg,rgba(201,255,0,0.08) 0%,rgba(0,212,255,0.06) 40%,rgba(168,85,247,0.08) 100%);
  border:1px solid rgba(201,255,0,0.2);
  box-shadow:0 0 60px rgba(201,255,0,0.05),0 0 100px rgba(0,212,255,0.04);
  margin-bottom:1.5rem;
">
  <div style="position:absolute;top:-80px;right:-80px;width:320px;height:320px;border-radius:50%;opacity:0.1;filter:blur(60px);background:radial-gradient(circle,#C9FF00,transparent);pointer-events:none;"></div>
  <div style="position:absolute;bottom:-80px;left:-80px;width:240px;height:240px;border-radius:50%;opacity:0.08;filter:blur(60px);background:radial-gradient(circle,#00D4FF,transparent);pointer-events:none;"></div>
  <div style="position:relative;display:flex;align-items:flex-start;justify-content:space-between;gap:1.5rem;flex-wrap:wrap;">
    <div>
      <h1 style="font-size:2.25rem;font-weight:800;color:white;margin:0 0 0.5rem;line-height:1.2;">
        {saludo}, <span style="background:linear-gradient(90deg,#C9FF00,#00D4FF);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">{nombre}</span> 👋
      </h1>
      <p style="color:#8B949E;font-size:0.875rem;margin:0 0 1rem;">{fecha_es}</p>
      <div style="display:flex;flex-wrap:wrap;gap:0.5rem;align-items:center;">
        {_ciclo_badge_html}
        <span style="background:rgba(59,130,246,0.2);color:#93c5fd;border:1px solid rgba(59,130,246,0.3);border-radius:9999px;padding:4px 12px;font-size:0.75rem;font-weight:600;">🗓 Fase: {fase_hoy['fase_nombre']}</span>
      </div>
    </div>
    <div style="border-radius:16px;padding:1.25rem 2rem;text-align:center;flex-shrink:0;background:linear-gradient(135deg,rgba(0,212,255,0.12),rgba(59,130,246,0.1));border:1px solid rgba(0,212,255,0.3);box-shadow:0 0 24px rgba(0,212,255,0.15);">
      <p style="font-size:0.65rem;color:#8B949E;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 0.25rem;">Objetivo principal</p>
      <p style="font-size:1rem;font-weight:800;color:white;margin:0 0 0.25rem;">{_obj_nombre}</p>
      <p style="font-size:1.875rem;font-weight:900;margin:0.25rem 0 0;background:linear-gradient(90deg,#00D4FF,#C9FF00);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">{_dias_left} días</p>
      <p style="font-size:0.65rem;color:#8B949E;margin:0.25rem 0 0;">{_fecha_obj.strftime('%d %b %Y')} · {_semanas_left} semanas</p>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 2. KPI Cards — Figma style
# ---------------------------------------------------------------------------
st.markdown("""
<div style="display:flex;align-items:center;gap:0.5rem;margin:0.5rem 0 1rem;">
  <span style="color:#C9FF00;font-size:1.1rem;">◈</span>
  <span style="font-size:0.85rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:0.07em;">Resumen Últimos 7 Días</span>
  <div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(201,255,0,0.35),transparent);margin-left:0.5rem;"></div>
</div>
""", unsafe_allow_html=True)

_kpi_cols = st.columns(4, gap="small")

def _kpi_card(col, label, value, period, delta_html_str, border_color, icon_char):
    col.markdown(f"""
<div style="background:#161B22;border-left:4px solid {border_color};border-top:0;border-right:0;border-bottom:0;border-radius:12px;padding:1.4rem 1.2rem 1rem;min-height:110px;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
    <div style="display:flex;align-items:center;gap:0.4rem;">
      <span style="color:{border_color};font-size:1rem;">{icon_char}</span>
      <span style="font-size:0.72rem;color:#8B949E;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">{label}</span>
    </div>
    <span style="font-size:0.68rem;color:#8B949E;background:#30363D;padding:3px 8px;border-radius:6px;">{period}</span>
  </div>
  <div style="display:flex;align-items:flex-end;justify-content:space-between;gap:8px;">
    <span style="font-size:1.875rem;font-weight:800;color:white;line-height:1;">{value}</span>
    {delta_html_str}
  </div>
</div>""", unsafe_allow_html=True)

_kpi_card(_kpi_cols[0], "KM",          km_val,     "Últimos 7 días", _delta_html(km_delta_num, 1),     "#22c55e", "👟")
_kpi_card(_kpi_cols[1], "HRV",         hrv_val,    "ms",             _delta_html(hrv_delta_num, 0),    "#3b82f6", "♡")
_kpi_card(_kpi_cols[2], "FUERZA",      fuerza_val, "sesiones",       _delta_html(fuerza_delta_num, 0), "#a855f7", "💪")
_kpi_card(_kpi_cols[3], "SUEÑO MEDIO", sueno_val,  "h/noche",        _delta_html(sueno_delta_num, 1),  "#f97316", "🌙")

st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 3. Macrociclo
# ---------------------------------------------------------------------------
titulo_macrociclo = obtener_titulo_macrociclo(user_actual)
st.markdown(f"""
<div style="display:flex;align-items:center;gap:0.5rem;margin:1rem 0 1rem;">
  <span style="color:#00D4FF;font-size:1.1rem;">↗</span>
  <span style="font-size:0.85rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:0.07em;">{titulo_macrociclo}</span>
  <div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(0,212,255,0.35),transparent);margin-left:0.5rem;"></div>
</div>
""", unsafe_allow_html=True)
render_macrociclo(user_actual)

st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 4. Checkpoints de rendimiento
# ---------------------------------------------------------------------------
objetivos_cards = checkpoints_objetivo_dashboard(user_actual, _objetivo_tipo)
_total_chk = len(objetivos_cards) if objetivos_cards else 0
_completados = sum(1 for c in (objetivos_cards or []) if c.get("hecho"))
_pct_chk = int(100 * _completados / _total_chk) if _total_chk else 0

st.markdown(f"""
<div style="display:flex;align-items:center;gap:0.5rem;margin:1rem 0 1rem;">
  <span style="color:#C9FF00;font-size:1.1rem;">◎</span>
  <span style="font-size:0.85rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:0.07em;">Checkpoints de Rendimiento</span>
  <div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(201,255,0,0.35),transparent);margin-left:0.5rem;"></div>
</div>
<div style="border-radius:16px;padding:1.25rem;margin-bottom:1rem;background:linear-gradient(135deg,rgba(201,255,0,0.06),rgba(0,212,255,0.04));border:1px solid rgba(201,255,0,0.2);">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
    <span style="font-size:0.875rem;color:white;"><span style="font-weight:700;color:#C9FF00;">{_completados}</span> de <span style="font-weight:700;">{_total_chk}</span> checkpoints completados</span>
    <span style="font-size:0.875rem;font-weight:700;color:#C9FF00;">{_pct_chk}%</span>
  </div>
  <div style="height:12px;border-radius:9999px;overflow:hidden;background:rgba(48,54,61,0.8);">
    <div style="height:100%;border-radius:9999px;width:{_pct_chk}%;background:linear-gradient(90deg,#C9FF00,#00D4FF);box-shadow:0 0 10px rgba(201,255,0,0.5);transition:width 0.5s;"></div>
  </div>
</div>
""", unsafe_allow_html=True)
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
