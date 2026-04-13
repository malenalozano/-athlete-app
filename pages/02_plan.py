"""
pages/2_plan.py — Plan semanal rediseñado.
Sub-tabs: Generar Plan (cards de días) | Datos (análisis completo del entrenador).
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from src.core.navbar import render_navbar
from src.db.db_manager import get_db_connection, obtener_credenciales_garmin, obtener_perfil as _obtener_perfil
from src.core.plan_ui_helpers import (
    html_semaforo, html_barra_fase,
    html_detalle_carrera, html_detalle_fuerza, html_detalle_descanso,
)

render_navbar("plan")

if "usuario_id" not in st.session_state:
    st.warning("Selecciona tu perfil en la página de inicio.")
    st.stop()
user_actual = st.session_state.usuario_id

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_TIPOS_CARRERA = {"Tirada Larga", "Progresiva", "Carrera Z2", "Regenerativo",
                  "Tempo (umbral)", "Intervalos VO2max", "Rodaje Corto",
                  "Fartlek", "Sustitución", "Calidad"}
_TIPOS_FUERZA  = {"Fuerza", "Fuerza Activ.", "Fuerza Tren Superior", "Movilidad"}
_EMOJIS = {"Tirada Larga":"🏃","Progresiva":"📈","Tempo (umbral)":"⚡",
           "Intervalos VO2max":"🔥","Carrera Z2":"🚶","Regenerativo":"💧",
           "Fuerza":"💪","Fuerza Activ.":"💪","Fuerza Tren Superior":"💪",
           "Descanso":"🛌","Movilidad":"🧘","Sustitución":"🔄","Rodaje Corto":"🏃"}
_BADGE = {"Fuerza":"#a855f7","Tirada Larga":"#C9FF00","Progresiva":"#C9FF00",
          "Carrera Z2":"#22c55e","Tempo (umbral)":"#f97316","Regenerativo":"#00D4FF",
          "Intervalos VO2max":"#ef4444","Descanso":"#3a4150","Movilidad":"#3a4150"}

# ---------------------------------------------------------------------------
# CSS global: cards de días via radio grid
# ---------------------------------------------------------------------------
st.markdown("""<style>
/* ── Day cards grid (radio horizontal) ── */
div[data-testid="stRadio"] > label { display:none; }
div[data-testid="stRadio"] > div > div[role="radiogroup"] {
  display: grid !important;
  grid-template-columns: repeat(7, 1fr) !important;
  gap: 6px !important;
}
div[data-testid="stRadio"] label {
  background: linear-gradient(135deg,#0f1724,#101928) !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: 14px !important;
  padding: 0.75rem 0.4rem !important;
  text-align: center !important;
  cursor: pointer !important;
  min-height: 94px !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 3px !important;
  color: #9ca3af !important;
  font-size: 0.72rem !important;
  line-height: 1.4 !important;
  transition: border-color 0.15s !important;
}
div[data-testid="stRadio"] label:hover {
  border-color: rgba(201,255,0,0.4) !important;
  color: #e6edf3 !important;
}
div[data-testid="stRadio"] label:has(input[type="radio"]:checked) {
  border-color: #C9FF00 !important;
  background: rgba(201,255,0,0.08) !important;
  color: #C9FF00 !important;
  box-shadow: 0 0 18px rgba(201,255,0,0.15) !important;
}
div[data-testid="stRadio"] input[type="radio"] { display:none !important; }
</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _lunes_de(dt): return dt - timedelta(days=dt.weekday())

def _cargar_plan_de_bd(usuario_id: int, lunes: datetime) -> dict | None:
    conn = get_db_connection()
    try:
        semana_str = lunes.strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT fecha, tipo, sesion, duracion_min, intensidad FROM plan_entrenamiento "
            "WHERE usuario_id=? AND semana_inicio=? ORDER BY fecha",
            (usuario_id, semana_str)).fetchall()
        if not rows:
            return None
        dias = [{
            "fecha": r[0], "dia": datetime.fromisoformat(r[0]).strftime("%a").upper()[:3],
            "tipo": r[1], "descripcion_ia": r[2] or "", "duracion_min": r[3] or 0,
            "intensidad": r[4] or "Z1-Z2", "km": 0, "alerta": "",
        } for r in rows]
        try:
            from src.plan.motor import generar_plan_semana
            base = generar_plan_semana(usuario_id, lunes)
            if isinstance(base, dict):
                base["dias"] = dias; base["existe_en_bd"] = True
                return base
        except Exception:
            pass
        return {
            "dias": dias,
            "fase": {"fase_nombre": "Plan guardado", "km_semanales_max": 0, "dias_fuerza": 0},
            "semaforo": {"color": "ambar", "mensaje": "Plan recuperado desde BD",
                         "permitir_calidad": True, "multiplicador_volumen": 1.0},
            "km_totales": round(sum(float(d.get("km") or 0) for d in dias), 1),
            "acwr": None, "alertas": [], "existe_en_bd": True,
        }
    except Exception:
        return None
    finally:
        conn.close()

def _adaptar_plan_a_hoy(plan: dict, usuario_id: int, lunes: datetime, hoy: datetime) -> dict:
    hoy_date = hoy.date()
    dias_adaptados = []
    dias_pasados = (hoy_date - lunes.date()).days
    if dias_pasados > 0:
        conn = get_db_connection()
        try:
            actvs = conn.execute(
                "SELECT fecha, tipo, duracion_min, distancia_m/1000.0 FROM actividades_garmin "
                "WHERE usuario_id=? AND fecha >= ? AND fecha < ? ORDER BY fecha",
                (usuario_id, lunes.strftime("%Y-%m-%d"), hoy_date)).fetchall()
            for i in range(dias_pasados):
                fd = lunes + timedelta(days=i)
                a = next((x for x in actvs if x[0][:10] == fd.strftime("%Y-%m-%d")), None)
                if a:
                    dias_adaptados.append({"fecha": a[0][:10], "dia": fd.strftime("%a").upper()[:3],
                                           "tipo": "Realizado: " + (a[1] or "Actividad"),
                                           "km": a[3] or 0, "duracion_min": a[2] or 0,
                                           "intensidad": "Histórico", "descripcion_ia": "[Historial Garmin]",
                                           "alerta": "✓ Completado"})
        finally:
            conn.close()
    for dia in plan.get("dias", []):
        if datetime.fromisoformat(dia["fecha"]).date() >= hoy_date:
            dias_adaptados.append(dia)
    plan["dias"] = dias_adaptados
    return plan

def _auto_guardar(usuario_id, lunes, plan_nuevo):
    semana_str = lunes.strftime("%Y-%m-%d")
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM plan_entrenamiento WHERE usuario_id=? AND semana_inicio=?",
                     (usuario_id, semana_str))
        for d in plan_nuevo.get("dias", []):
            desc = d.get("descripcion_ia") or d.get("alerta", "")
            conn.execute(
                "INSERT INTO plan_entrenamiento "
                "(usuario_id,semana_inicio,fecha,tipo,sesion,duracion_min,intensidad,creado_en) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (usuario_id, semana_str, d["fecha"], d["tipo"], desc,
                 d["duracion_min"], d["intensidad"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); st.cache_data.clear()
    except Exception:
        pass
    finally:
        conn.close()

def _section(icon, title, color="#C9FF00"):
    grad = f"rgba({','.join(str(int(color.lstrip('#')[i:i+2],16)) for i in (0,2,4))},0.35)" if color.startswith('#') else "rgba(201,255,0,0.35)"
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:0.5rem;margin:1.25rem 0 0.75rem;">
  <span style="color:{color};font-size:1rem;">{icon}</span>
  <span style="font-size:0.8rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:.07em;">{title}</span>
  <div style="flex:1;height:1px;background:linear-gradient(90deg,{grad},transparent);margin-left:.5rem;"></div>
</div>""", unsafe_allow_html=True)

def _metric_card(col, label, value, sub="", color="#C9FF00"):
    sub_html = f"<div style='color:#6b7280;font-size:0.7rem;margin-top:2px;'>{sub}</div>" if sub else ""
    col.markdown(
        f"<div style='background:linear-gradient(135deg,#0f1724,#101928);border:1px solid {color}33;"
        f"border-radius:12px;padding:0.9rem 1rem;'>"
        f"<div style='color:#8B949E;font-size:0.65rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:.07em;margin-bottom:4px;'>{label}</div>"
        f"<div style='color:{color};font-size:1.25rem;font-weight:800;'>{value}</div>"
        f"{sub_html}"
        f"</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------
if "plan_last_user" not in st.session_state:
    st.session_state["plan_last_user"] = user_actual
elif st.session_state["plan_last_user"] != user_actual:
    for _k in ("plan_cursor", "plan_data", "plan_ia", "plan_dia_sel"):
        st.session_state.pop(_k, None)
    st.session_state["plan_last_user"] = user_actual

if "plan_cursor" not in st.session_state:
    st.session_state.plan_cursor = _lunes_de(datetime.now())
if "plan_data" not in st.session_state:
    st.session_state.plan_data = None
if "plan_ia" not in st.session_state:
    st.session_state.plan_ia = True
if "plan_dia_sel" not in st.session_state:
    st.session_state.plan_dia_sel = 0

lunes = st.session_state.plan_cursor
if st.session_state.plan_data is None:
    plan_bd = _cargar_plan_de_bd(user_actual, lunes)
    if plan_bd:
        st.session_state.plan_data = plan_bd
        st.session_state.plan_ia = False

# ---------------------------------------------------------------------------
# SUB-TABS
# ---------------------------------------------------------------------------
tab_plan, tab_datos = st.tabs(["📋 Generar Plan", "📊 Datos del Entrenador"])

# ============================================================================
# TAB 1: GENERAR PLAN
# ============================================================================
with tab_plan:

    # ── Cabecera: navegación semana + botón generar ─────────────────────────
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:0.5rem;margin:0.5rem 0 1rem;">
  <span style="color:#00D4FF;font-size:1rem;">📋</span>
  <span style="font-size:0.82rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:.07em;">Plan Semanal</span>
  <div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(0,212,255,0.3),transparent);margin-left:.4rem;"></div>
</div>""", unsafe_allow_html=True)

    nav_c1, nav_c2, nav_c3, nav_c4 = st.columns([0.07, 0.46, 0.07, 0.40])
    with nav_c1:
        if st.button("◀", key="plan_prev", help="Semana anterior"):
            st.session_state.plan_cursor -= timedelta(weeks=1)
            st.session_state.plan_data = None
            st.session_state.plan_dia_sel = 0
            st.rerun()
    with nav_c2:
        st.markdown(
            f"<div style='text-align:center;font-weight:700;color:#C9E1FF;font-size:0.95rem;padding-top:6px;'>"
            f"Semana del {lunes.strftime('%-d/%m')} al {(lunes+timedelta(6)).strftime('%-d/%m/%Y')}</div>",
            unsafe_allow_html=True)
    with nav_c3:
        if st.button("▶", key="plan_next", help="Semana siguiente"):
            st.session_state.plan_cursor += timedelta(weeks=1)
            st.session_state.plan_data = None
            st.session_state.plan_dia_sel = 0
            st.rerun()
    with nav_c4:
        btn_c1, btn_c2 = st.columns([3, 1])
        with btn_c1:
            if st.button("⚡ Generar plan con IA", type="primary", use_container_width=True):
                with st.spinner("Generando tu plan personalizado…"):
                    try:
                        from src.plan.entrenador import generar_entrenamiento_semana
                        plan_nuevo = generar_entrenamiento_semana(user_actual, lunes)
                        plan_nuevo = _adaptar_plan_a_hoy(plan_nuevo, user_actual, lunes, datetime.now())
                        st.session_state.plan_data = plan_nuevo
                        st.session_state.plan_ia = True
                        st.session_state.plan_dia_sel = 0
                        _auto_guardar(user_actual, lunes, plan_nuevo)
                    except Exception as e:
                        st.error(f"❌ Error generando plan: {e}")
                        st.stop()
                st.rerun()
        with btn_c2:
            if st.checkbox("Sin IA", key="plan_sin_ia"):
                st.session_state.plan_ia = False

    # ── Sin plan ────────────────────────────────────────────────────────────
    if st.session_state.plan_data is None:
        st.markdown("""
<div style="background:linear-gradient(135deg,rgba(0,212,255,0.06),rgba(201,255,0,0.04));
border:1px solid rgba(0,212,255,0.2);border-radius:16px;padding:2rem;text-align:center;margin:1rem 0;">
  <div style="font-size:2rem;margin-bottom:0.5rem;">📋</div>
  <div style="color:white;font-size:1rem;font-weight:700;margin-bottom:0.5rem;">Sin plan para esta semana</div>
  <div style="color:#8B949E;font-size:0.85rem;">Pulsa ⚡ Generar plan con IA para crear tu entrenamiento personalizado.</div>
</div>""", unsafe_allow_html=True)
        st.stop()

    plan = st.session_state.plan_data
    if not isinstance(plan, dict) or "fase" not in plan:
        plan_bd = _cargar_plan_de_bd(user_actual, lunes)
        if plan_bd and isinstance(plan_bd, dict) and "fase" in plan_bd:
            st.session_state.plan_data = plan_bd; st.rerun()
        st.error("Plan no válido. Intenta regenerarlo.")
        st.stop()

    fase     = plan["fase"]
    semaforo = plan["semaforo"]

    # ── Semáforo — solo advertencia visual, no modifica el plan ────────────
    _color_sem = semaforo.get("color", "verde")
    _color_map = {"verde": "#22c55e", "ambar": "#f59e0b", "rojo": "#ef4444"}
    _icon_map  = {"verde": "🟢", "ambar": "🟡", "rojo": "🔴"}
    _sem_color = _color_map.get(_color_sem, "#22c55e")
    _sem_icon  = _icon_map.get(_color_sem, "🟢")

    st.markdown(f"""
<div style="background:linear-gradient(135deg,{_sem_color}10,transparent);
border:1px solid {_sem_color}33;border-radius:12px;padding:0.6rem 1rem;
display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;">
  <span style="font-size:1.2rem;">{_sem_icon}</span>
  <div>
    <span style="color:{_sem_color};font-weight:700;font-size:0.82rem;">{_color_sem.upper()}</span>
    <span style="color:#8B949E;font-size:0.78rem;margin-left:0.5rem;">{semaforo.get('mensaje','')}</span>
    {"<span style='color:#ef4444;font-size:0.72rem;margin-left:0.75rem;font-weight:700;'>⚠️ Advertencia — el plan no ha sido modificado.</span>" if _color_sem == "rojo" else ""}
  </div>
  <div style="margin-left:auto;color:#6b7280;font-size:0.72rem;">
    {plan['km_totales']:.1f} km · Fase: {fase['fase_nombre']}
  </div>
</div>""", unsafe_allow_html=True)

    # ── Barra de fase ───────────────────────────────────────────────────────
    st.markdown(html_barra_fase(fase), unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    # ── Cards de días (radio con CSS grid) ─────────────────────────────────
    opciones_dia = []
    for _d in plan["dias"]:
        _em  = _EMOJIS.get(_d["tipo"], "📅")
        _sub = f"{_d['km']} km" if _d.get("km") else f"{_d.get('duracion_min', 0)}'"
        _tipo_short = _d["tipo"][:11]
        opciones_dia.append(f"{_d['dia']}  {_em}\n{_tipo_short}\n{_sub}")

    # Índice actual — limitado al rango válido
    _idx_max = len(opciones_dia) - 1
    _idx_cur = min(st.session_state.get("plan_dia_sel", 0), _idx_max)

    elegido = st.radio(
        "Día",
        opciones_dia,
        index=_idx_cur,
        key="plan_dia_radio",
        label_visibility="collapsed",
    )
    _new_idx = opciones_dia.index(elegido) if elegido in opciones_dia else 0
    if _new_idx != st.session_state.get("plan_dia_sel", 0):
        st.session_state["plan_dia_sel"] = _new_idx

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    # ── Panel de detalle del día seleccionado ───────────────────────────────
    idx = st.session_state.get("plan_dia_sel", 0)
    dia = plan["dias"][idx]
    tipo = dia["tipo"]

    _acc = _BADGE.get(tipo, "#8B949E")
    _em  = _EMOJIS.get(tipo, "📅")
    _sub = f"{dia['km']} km" if dia.get("km") else f"{dia.get('duracion_min', 0)}'"
    _fecha_fmt = datetime.fromisoformat(dia["fecha"]).strftime("%-d de %b") if dia.get("fecha") else dia["dia"]

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#0f1724,#101928);border:1px solid {_acc}33;
border-radius:16px;padding:1.25rem 1.5rem;margin-bottom:0.75rem;">
  <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.75rem;">
    <span style="font-size:1.5rem;">{_em}</span>
    <div>
      <div style="color:white;font-size:1rem;font-weight:800;">{dia['dia']} — {_fecha_fmt}</div>
      <div style="color:{_acc};font-size:0.8rem;font-weight:700;">{tipo}</div>
    </div>
    <span style="margin-left:auto;color:#6b7280;font-size:0.78rem;background:#161B22;
    padding:4px 10px;border-radius:20px;">{_sub}</span>
  </div>
""", unsafe_allow_html=True)

    if tipo in _TIPOS_FUERZA:
        st.markdown(html_detalle_fuerza(dia), unsafe_allow_html=True)
        if fase.get("dias_fuerza", 0) > 0:
            from src.plan.memoria_fuerza import generar_tabla_fuerza_semana
            _conn = get_db_connection()
            try:
                tabla = generar_tabla_fuerza_semana(user_actual, fase, semaforo, conn=_conn)
            finally:
                _conn.close()
            st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)
    elif tipo in _TIPOS_CARRERA:
        from src.garmin.workout_builder import sesion_a_bloques
        bloques = sesion_a_bloques(dia)
        st.markdown(html_detalle_carrera(dia, bloques), unsafe_allow_html=True)
        if st.button("⌚ Enviar workout a Garmin", key=f"gwk_{idx}"):
            from src.garmin.garmin_sync import cargar_sesion_tokens
            from src.garmin.workout_builder import crear_workout_garmin, programar_workout_garmin
            cred = obtener_credenciales_garmin(user_actual)
            email = cred[0] if cred else None
            gc = st.session_state.get("gc") or cargar_sesion_tokens(email, usuario_id=user_actual)
            if gc is None:
                st.warning("Conecta Garmin primero en la página Garmin.")
            else:
                with st.spinner("Enviando…"):
                    try:
                        wid = crear_workout_garmin(dia, gc)
                        ok = programar_workout_garmin(gc, wid, dia["fecha"])
                        st.success(f"✅ Workout enviado (ID: {wid}){' y programado en Garmin.' if ok else '.'}")
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        st.markdown(html_detalle_descanso(dia), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Descripción IA
    if st.session_state.get("plan_ia") and dia.get("descripcion_ia"):
        st.markdown(
            f"<div style='background:rgba(163,230,53,0.05);border-left:3px solid #a3e635;"
            f"border-radius:0 10px 10px 0;padding:10px 14px;margin:0 0 0.75rem;font-size:0.82rem;color:#c9d1d9;'>"
            f"<span style='font-size:0.65rem;color:#a3e635;text-transform:uppercase;letter-spacing:.07em;"
            f"font-weight:700;'>🤖 Entrenador IA</span><br><br>"
            f"{dia['descripcion_ia']}</div>",
            unsafe_allow_html=True)

    # Ajuste manual
    with st.expander("✏️ Añadir ajuste a este día"):
        ajuste = st.text_area("Ajuste", placeholder="Ej: reducir 3km, cambiar a Z1 todo…",
                              height=68, key=f"ajuste_{idx}", label_visibility="collapsed")
        if st.button("Aplicar", key=f"ajuste_btn_{idx}", type="primary"):
            plan["dias"][idx]["alerta"] = f"[Ajuste] {ajuste}"
            st.session_state.plan_data = plan
            _auto_guardar(user_actual, lunes, plan)
            st.success("Ajuste guardado."); st.rerun()

    # Alertas del plan
    if plan.get("alertas"):
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        for a in plan["alertas"]:
            (st.error if "⛔" in a or "🚫" in a else st.warning if "⚠️" in a else st.info)(a)


# ============================================================================
# TAB 2: DATOS DEL ENTRENADOR
# ============================================================================
with tab_datos:

    st.markdown("""
<div style="display:flex;align-items:center;gap:0.5rem;margin:0.5rem 0 1.25rem;">
  <span style="color:#6366f1;font-size:1rem;">🧠</span>
  <span style="font-size:0.82rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:.07em;">Análisis completo — datos que generan tu plan</span>
  <div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(99,102,241,0.3),transparent);margin-left:.4rem;"></div>
</div>""", unsafe_allow_html=True)

    # Imports específicos de esta sección
    from src.plan.helpers import cargar_datos_plan
    from src.plan.reglas import (
        obtener_fase_macrociclo_usuario, calcular_semaforo,
        aplicar_restricciones_lesion, evaluar_cadencia,
        calcular_volumen_semana, evaluar_eficiencia_aerobica,
    )
    from src.plan.motor import generar_plan_semana
    from src.plan.memoria_fuerza import generar_tabla_fuerza_semana

    _conn_dat = get_db_connection()
    _perfil   = _obtener_perfil(user_actual) or {}
    _genero   = str(_perfil.get("genero", "")).strip().lower()
    _es_mujer = _genero in ("mujer", "female", "f", "w", "femenino")
    _obj_tipo = str(_perfil.get("objetivo_tipo", "")).strip().lower()

    datos = {}
    try:
        datos = cargar_datos_plan(user_actual)
    except Exception as e:
        st.warning(f"No se pudieron cargar datos biométricos: {e}")

    # ── 1. Biométricos ──────────────────────────────────────────────────────
    _section("📊", "Biométricos Actuales", "#00D4FF")

    _m1, _m2, _m3, _m4 = st.columns(4, gap="small")
    _metric_card(_m1, "HRV", f"{datos.get('hrv_actual',0):.0f} ms" if datos.get('hrv_actual') else "—",
                 color="#00D4FF")
    _metric_card(_m2, "Sleep Score", f"{datos.get('sleep_score',0)}/100" if datos.get('sleep_score') else "—",
                 color="#7EB8E0")
    _metric_card(_m3, "Estrés Medio",
                 f"{datos.get('estres_medio',0)}/100" if datos.get('estres_medio') else "—",
                 color="#f97316")
    _metric_card(_m4, "Body Battery",
                 f"{datos.get('body_battery_min',0)}/100" if datos.get('body_battery_min') else "—",
                 color="#a855f7")

    sb = datos.get("sleep_breakdown", {})
    if sb:
        _s1, _s2, _s3, _s4 = st.columns(4, gap="small")
        _metric_card(_s1, "Sueño Total",   f"{sb.get('horas_totales','—'):.1f}h" if sb.get('horas_totales') is not None else "—", color="#7EB8E0")
        _metric_card(_s2, "Profundo",      f"{sb.get('profundo_h','—'):.1f}h"    if sb.get('profundo_h')    is not None else "—", color="#22c55e")
        _metric_card(_s3, "REM",           f"{sb.get('rem_h','—'):.1f}h"         if sb.get('rem_h')         is not None else "—", color="#f59e0b")
        _metric_card(_s4, "Vigilia",       f"{sb.get('vigilia_h','—'):.1f}h"     if sb.get('vigilia_h')     is not None else "—", color="#ef4444")

    # ── 2. Análisis de Carrera ──────────────────────────────────────────────
    _section("🏃", "Análisis de Carrera & Rendimiento", "#22c55e")

    _r1, _r2, _r3 = st.columns(3, gap="small")
    _cad = datos.get("cadencia_media", 0)
    _cad_note = "↓ Mejorar técnica" if _cad < 170 else ("↑ Excelente" if _cad > 175 else "→ Normal")
    _acwr_v = datos.get("acwr", 0)
    _acwr_note = "🔴 Elevado" if _acwr_v > 1.5 else ("🟡 Moderado" if _acwr_v > 1.3 else "🟢 Normal")
    _metric_card(_r1, "Cadencia Media", f"{_cad:.0f} spm", _cad_note, color="#22c55e")
    _metric_card(_r2, "VO2max",         "—",               "No disponible", color="#8B949E")
    _metric_card(_r3, "ACWR",           f"{_acwr_v:.2f}",  _acwr_note, color="#f59e0b" if _acwr_v > 1.3 else "#22c55e")

    try:
        df_act_week = pd.read_sql_query(
            """SELECT fecha, ROUND(distancia_m/1000,2) as km, cadencia_media, fc_media, ritmo_medio
               FROM actividades_garmin
               WHERE usuario_id=? AND fecha >= date('now','-7 days')
               AND LOWER(COALESCE(tipo_deporte,'')) LIKE '%run%'
               ORDER BY fecha DESC""",
            _conn_dat, params=(user_actual,))
        if not df_act_week.empty:
            st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)
            st.caption("Últimas actividades de running (7 días)")
            st.dataframe(df_act_week, use_container_width=True, hide_index=True)
        else:
            st.caption("Sin actividades de running en los últimos 7 días.")
    except Exception:
        pass

    # ── 3. Fase del Macrociclo ──────────────────────────────────────────────
    _section("📅", "Fase del Macrociclo", "#C9FF00")

    _fase_dat = obtener_fase_macrociclo_usuario(user_actual)
    _fecha_obj_s = _perfil.get("fecha_objetivo")
    _dias_rest = _sem_rest = None
    if _fecha_obj_s:
        try:
            _fobj = datetime.strptime(str(_fecha_obj_s), "%Y-%m-%d")
            _dias_rest = (_fobj - datetime.now()).days
            _sem_rest  = _dias_rest // 7
        except Exception:
            pass

    _f1, _f2, _f3 = st.columns(3, gap="small")
    _metric_card(_f1, "Fase Actual",    _fase_dat.get("fase_nombre","—"),          color="#C9FF00")
    _metric_card(_f2, "KM Máx/Semana", f"{_fase_dat.get('km_semanales_max',0)} km", color="#00D4FF")
    _metric_card(_f3, "Días Fuerza",   f"{_fase_dat.get('dias_fuerza',0)} días",    color="#a855f7")

    if _dias_rest is not None:
        _d1, _d2 = st.columns(2, gap="small")
        _metric_card(_d1, "Días hasta objetivo", str(_dias_rest), color="#f59e0b")
        _metric_card(_d2, "Semanas hasta objetivo", str(_sem_rest), color="#f59e0b")

    st.markdown(
        f"<div style='background:#0f1724;border:1px solid rgba(201,255,0,0.1);border-radius:10px;"
        f"padding:0.75rem 1rem;margin-top:0.5rem;font-size:0.8rem;color:#9ca3af;'>"
        f"<b style='color:#C9E1FF;'>Enfoque Running:</b> {_fase_dat.get('enfoque_running','—')}<br>"
        f"<b style='color:#C9E1FF;'>Enfoque Fuerza:</b> {_fase_dat.get('enfoque_fuerza','—')}</div>",
        unsafe_allow_html=True)

    # ── 4. Semáforo ─────────────────────────────────────────────────────────
    _section("🚦", "Semáforo de Recuperación", "#f59e0b")

    _sem_dat = calcular_semaforo(
        hrv_actual=datos.get("hrv_actual"),
        hrv_media_7d=datos.get("hrv_media_7d"),
        sleep_score=datos.get("sleep_score"),
        sleep_breakdown=datos.get("sleep_breakdown"),
        estres_medio=datos.get("estres_medio"),
        body_battery_min=datos.get("body_battery_min"),
        training_status=datos.get("training_status"),
    )
    _sc = {"verde":"#22c55e","ambar":"#f59e0b","rojo":"#ef4444"}.get(_sem_dat["color"],"#22c55e")
    _si = {"verde":"🟢","ambar":"🟡","rojo":"🔴"}.get(_sem_dat["color"],"🟢")
    st.markdown(f"""
<div style="background:{_sc}10;border:1px solid {_sc}33;border-radius:12px;padding:1rem 1.25rem;">
  <div style="font-size:1rem;font-weight:800;color:{_sc};margin-bottom:4px;">{_si} {_sem_dat['color'].upper()}</div>
  <div style="color:#C9E1FF;font-size:0.85rem;margin-bottom:8px;">{_sem_dat['mensaje']}</div>
  <div style="color:#8B949E;font-size:0.78rem;">
    Multiplicador volumen: <b style="color:{_sc};">{_sem_dat['multiplicador_volumen']:.2f}x</b>
    &nbsp;·&nbsp; Calidad permitida: <b style="color:{_sc};">{'Sí' if _sem_dat['permitir_calidad'] else 'No'}</b>
  </div>
  {"<div style='color:#ef4444;font-size:0.75rem;font-weight:700;margin-top:6px;'>⚠️ Recuperación baja — el plan no se modifica automáticamente. Considera reducir intensidad manualmente.</div>" if _sem_dat['color']=='rojo' else ""}
</div>""", unsafe_allow_html=True)

    # ── 5. Ciclo (mujeres) ──────────────────────────────────────────────────
    ciclo_data = None
    if _es_mujer:
        _section("🩸", "Ciclo Menstrual", "#ec4899")
        ciclo_data = datos.get("ciclo_menstrual") or datos.get("fase_ciclo")
        if ciclo_data:
            _c1, _c2, _c3 = st.columns(3, gap="small")
            _metric_card(_c1, "Fase", ciclo_data.get("fase") or ciclo_data.get("fase_nombre","—"), color="#ec4899")
            _metric_card(_c2, "Multiplicador Vol.", f"{ciclo_data.get('multiplicador_volumen',1):.2f}x", color="#ec4899")
            _metric_card(_c3, "¿Calidad permitida?", "Sí" if ciclo_data.get("permitir_calidad",True) else "No", color="#ec4899")
            if ciclo_data.get("hidratacion_extra"):
                st.info("💧 Fase de estrés hormonal — aumentar hidratación y electrolitos.")
        else:
            st.info("Sin datos de ciclo. Añade registros en la pestaña Diario.")

    # ── 6. Restricciones / Lesiones ─────────────────────────────────────────
    _section("⚠️", "Restricciones & Lesiones Activas", "#ef4444")

    _restricciones = aplicar_restricciones_lesion(datos.get("lesiones_activas", []))
    if datos.get("lesiones_activas"):
        st.error(f"**{len(datos['lesiones_activas'])} lesión(es) activa(s)**")
        for _les in datos["lesiones_activas"]:
            st.markdown(
                f"- **{_les.get('tipo','?')}** (Grado {_les.get('grado','?')}/10) — "
                f"{', '.join(_restricciones.get('alertas',[]) or ['Sin restricciones específicas'])}")
    else:
        st.success("✅ Sin lesiones activas")

    # ── 7. Evaluaciones Especializadas ──────────────────────────────────────
    _section("🔍", "Evaluaciones Especializadas", "#6366f1")

    _e1, _e2, _e3 = st.columns(3, gap="small")
    _cad_eval = evaluar_cadencia(datos.get("cadencia_media"))
    with _e1:
        st.markdown(f"<div style='font-size:0.72rem;font-weight:700;color:#8B949E;text-transform:uppercase;"
                    f"letter-spacing:.07em;margin-bottom:6px;'>Cadencia</div>", unsafe_allow_html=True)
        (st.warning if _cad_eval.get("necesita_drills") else st.success)(f"{'🔧' if _cad_eval.get('necesita_drills') else '✅'} {_cad_eval.get('mensaje','—')}")

    _efic = evaluar_eficiencia_aerobica(datos.get("actividades_z2", []))
    with _e2:
        st.markdown(f"<div style='font-size:0.72rem;font-weight:700;color:#8B949E;text-transform:uppercase;"
                    f"letter-spacing:.07em;margin-bottom:6px;'>Eficiencia Aeróbica</div>", unsafe_allow_html=True)
        if _efic.get("tendencia") == "sin_datos":
            st.info("Sin datos suficientes (mín. 4 sesiones Z2 en 28 días).")
        elif _efic.get("necesita_fartlek"):
            st.warning("⚠️ Tendencia estancada. Añadir fartlek suave.")
        else:
            st.success("✅ Tendencia positiva")

    _km_obj = calcular_volumen_semana(
        datos.get("km_semana_anterior", 15), datos.get("acwr", 0.8),
        datos.get("lesiones_activas", []), _fase_dat.get("km_semanales_max", 60))
    with _e3:
        _metric_card(_e3, "Volumen Estimado Semana", f"{_km_obj:.1f} km", color="#C9FF00")

    # ── 8. Tabla de Fuerza ──────────────────────────────────────────────────
    _section("💪", "Sesión de Fuerza Propuesta", "#a855f7")

    try:
        _tabla_f = generar_tabla_fuerza_semana(user_actual, _fase_dat, _sem_dat,
                                               acwr=datos.get("acwr"), conn=_conn_dat)
        st.dataframe(pd.DataFrame(_tabla_f), use_container_width=True, hide_index=True)
    except Exception as e:
        st.caption(f"No se pudo generar tabla de fuerza: {e}")

    # ── 9. Resumen Ejecutivo ─────────────────────────────────────────────────
    _section("📌", "Resumen Ejecutivo", "#00D4FF")

    _rx1, _rx2 = st.columns(2, gap="small")
    with _rx1:
        _km_tot_dat = float(st.session_state.plan_data.get("km_totales", 0)) if st.session_state.plan_data else 0
        st.markdown(f"""
<div style="background:#0f1724;border:1px solid rgba(0,212,255,0.15);border-radius:12px;padding:1rem;">
  <div style="color:#8B949E;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">Estado de Entrenamiento</div>
  <div style="font-size:0.8rem;color:#C9E1FF;line-height:2;">
    Recuperación: <b style="color:{_sc};">{_sem_dat['color'].upper()}</b><br>
    Volumen objetivo: <b style="color:#C9FF00;">{_km_tot_dat:.1f} km</b><br>
    Calidad permitida: <b>{'Sí' if _sem_dat['permitir_calidad'] else 'No — Solo Z1/Z2'}</b><br>
    ACWR: <b>{datos.get('acwr',0):.2f}</b>
  </div>
</div>""", unsafe_allow_html=True)
    with _rx2:
        st.markdown(f"""
<div style="background:#0f1724;border:1px solid rgba(0,212,255,0.15);border-radius:12px;padding:1rem;">
  <div style="color:#8B949E;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">Ajustes Aplicados</div>
  <div style="font-size:0.8rem;color:#C9E1FF;line-height:2;">
    Ciclo menstrual: <b>{ciclo_data.get('fase','N/A') if (_es_mujer and ciclo_data) else ('N/A' if _es_mujer else 'No aplica')}</b><br>
    Drills cadencia: <b>{'Sí — 5min técnica' if _cad_eval.get('necesita_drills') else 'No necesarios'}</b><br>
    Lesiones: <b>{'Sí — sustituciones aplicadas' if datos.get('lesiones_activas') else 'Ninguna'}</b><br>
    Fase: <b>{_fase_dat.get('fase_nombre','—')}</b>
  </div>
</div>""", unsafe_allow_html=True)

    st.success("✅ Datos listos para generar tu plan semanal personalizado.")

    if _conn_dat:
        try:
            _conn_dat.close()
        except Exception:
            pass
