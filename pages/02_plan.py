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
_TYPE_COLORS = {"running":"#22d3ee", "strength":"#c084fc", "rest":"#4ade80", "default":"#C9FF00"}

# ---------------------------------------------------------------------------
# CSS global: radio como tarjeta clickable vertical
# ---------------------------------------------------------------------------
st.markdown("""<style>
div[data-testid="stRadio"] > div[role="radiogroup"] { gap: 0 !important; display: flex; flex-wrap: wrap; }
div[data-testid="stRadio"] label {
  background:#131D2B; border:1px solid rgba(201,255,0,0.15); border-radius:10px;
  padding:10px 12px; margin-bottom:6px; margin-right:6px; cursor:pointer; flex: 1; min-width:150px;
  color:#C9E1FF !important; font-size:0.84rem; display:flex; align-items:center; justify-content:center; }
div[data-testid="stRadio"] label:has(input[type="radio"]:checked) {
  border-color:#C9FF00 !important; background:#111f11 !important; color:#C9FF00 !important; }
div[data-testid="stRadio"] input[type="radio"] { display:none; }
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
                "SELECT fecha, tipo_deporte, ROUND(CAST(tiempo_seg AS REAL)/60, 1) as duracion_min, distancia_m/1000.0 FROM actividades_garmin "
                "WHERE usuario_id=? AND fecha >= ? AND fecha < ? ORDER BY fecha",
                (usuario_id, lunes.strftime("%Y-%m-%d"), hoy_date)).fetchall()
            for i in range(dias_pasados):
                fd = lunes + timedelta(days=i)
                a = next((x for x in actvs if x[0][:10] == fd.strftime("%Y-%m-%d")), None)
                if i < len(plan.get("dias", [])):
                    dia_plan = plan["dias"][i]
                    if a:
                        # Día pasado con actividad realizada
                        dias_adaptados.append({"fecha": a[0][:10], "dia": fd.strftime("%a").upper()[:3],
                                               "tipo": "Realizado: " + (a[1] or "Actividad"),
                                               "km": a[3] or 0, "duracion_min": a[2] or 0,
                                               "intensidad": "Histórico", "descripcion_ia": "[Historial Garmin]",
                                               "alerta": "✓ Completado"})
                    else:
                        # Día pasado SIN actividad — mostrar lo que se planificó
                        dias_adaptados.append(dia_plan)
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

def _kpi_card(col, icon, label, value, color, bg, border):
    """Render a KPI card with icon, label, and value."""
    col.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:12px;padding:1rem;">
  <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem;">
    <span style="color:{color};font-size:1rem;">{icon}</span>
    <span style="color:#8B949E;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;">{label}</span>
  </div>
  <p style="color:white;font-size:1.5rem;font-weight:800;margin:0;">{value}</p>
</div>""", unsafe_allow_html=True)

def _get_activity_type(tipo: str) -> str:
    """Classify activity type into running, strength, or rest."""
    if tipo in _TIPOS_FUERZA or "Fuerza" in tipo:
        return "strength"
    elif tipo == "Descanso" or "Descanso" in tipo:
        return "rest"
    elif tipo in _TIPOS_CARRERA:
        return "running"
    return "default"

def _get_activity_color(tipo: str) -> str:
    """Get color for activity type."""
    activity_type = _get_activity_type(tipo)
    return _TYPE_COLORS.get(activity_type, _TYPE_COLORS["default"])

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
# TAB STATE & NAVIGATION
# ---------------------------------------------------------------------------
active_tab = st.session_state.get("plan_active_tab", "generar")

# Tab navigation using radio (styled with CSS)
tab_options = ["📋 Generar Plan", "📊 Datos del Entrenador"]
current_index = 0 if active_tab == "generar" else 1
selected_tab_display = st.radio(
    "", 
    tab_options, 
    index=current_index,
    label_visibility="collapsed", 
    key="plan_tab_radio",
    horizontal=False
)

# Update active_tab based on selection
if selected_tab_display == tab_options[0] and active_tab != "generar":
    st.session_state.plan_active_tab = "generar"
    st.rerun()
elif selected_tab_display == tab_options[1] and active_tab != "datos":
    st.session_state.plan_active_tab = "datos"
    st.rerun()
# ============================================================================
# TAB 1: GENERAR PLAN
# ============================================================================
if active_tab == "generar":

    # Hero banner with week navigation
    st.markdown(f"""
<div style="background:linear-gradient(135deg,rgba(0,212,255,0.15) 0%,rgba(34,197,94,0.08) 50%,rgba(168,85,247,0.1) 100%);
border:1px solid rgba(0,212,255,0.25);border-radius:16px;padding:1.5rem 2rem;
position:relative;overflow:hidden;margin-bottom:1rem;">
  <div style="position:absolute;top:-20px;right:-20px;width:160px;height:160px;
  border-radius:50%;background:radial-gradient(circle,rgba(0,212,255,0.2),transparent);
  filter:blur(30px);pointer-events:none;"></div>
  <div style="display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:1rem;position:relative;">
    <div style="flex:1;min-width:250px;">
      <div style="display:flex;gap:.5rem;margin-bottom:.6rem;flex-wrap:wrap;">
        <span style="background:rgba(34,211,238,0.2);color:#22d3ee;border:1px solid rgba(34,211,238,0.3);border-radius:20px;padding:2px 10px;font-size:11px;font-weight:600;">Semana 8 · Pre-Específico</span>
        <span style="background:rgba(74,222,128,0.2);color:#4ade80;border:1px solid rgba(74,222,128,0.3);border-radius:20px;padding:2px 10px;font-size:11px;font-weight:600;">Plan Activo ✓</span>
      </div>
      <h2 style="color:white;font-size:1.25rem;font-weight:800;margin:0 0 .3rem;">Plan Semanal — {lunes.strftime('%-d al')} {(lunes+timedelta(6)).strftime('%-d %b')}</h2>
      <p style="color:#8B949E;font-size:.82rem;margin:0;">Semana del {lunes.strftime('%d/%m/%Y')}</p>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # Week navigation
    nav_c1, nav_c2, nav_c3 = st.columns([0.08, 0.84, 0.08])
    with nav_c1:
        if st.button("◀", key="plan_prev"):
            st.session_state.plan_cursor -= timedelta(weeks=1)
            st.session_state.plan_data = None; st.rerun()
    with nav_c2:
        pass
    with nav_c3:
        if st.button("▶", key="plan_next"):
            st.session_state.plan_cursor += timedelta(weeks=1)
            st.session_state.plan_data = None; st.rerun()

    # Generate button
    col_gen1, col_gen2 = st.columns([0.7, 0.3])
    with col_gen1:
        if st.button("⚡ Regenerar plan (con IA)", type="primary", use_container_width=True, key="plan_generate"):
            with st.spinner("Generando plan..."):
                try:
                    from src.plan.entrenador import generar_entrenamiento_semana
                    plan_nuevo = generar_entrenamiento_semana(user_actual, lunes)
                    
                    # DEBUG: mostrar tipos generados
                    tipos_gen = [d.get("tipo", "?") for d in plan_nuevo.get("dias", [])]
                    if not any(t not in ("Regenerativo", "Descanso", "Movilidad") for t in tipos_gen):
                        st.warning(f"⚠️ Aviso: Plan generado solo con tipos: {tipos_gen}. Revisando...")
                    
                    plan_nuevo = _adaptar_plan_a_hoy(plan_nuevo, user_actual, lunes, datetime.now())
                    st.session_state.plan_data = plan_nuevo
                    st.session_state.plan_ia = True
                    _auto_guardar(user_actual, lunes, plan_nuevo)
                except Exception as e:
                    st.error(f"❌ Error generando plan:\n\n{str(e)}")
                    import traceback
                    st.error(f"**Traceback completo:**\n\n```\n{traceback.format_exc()}\n```")
                    st.stop()
            st.rerun()
    with col_gen2:
        sin_ia = st.checkbox("Sin IA", key="plan_sin_ia")
        if sin_ia:
            st.session_state.plan_ia = False

    if st.session_state.plan_data is None:
        st.info("Pulsa **⚡ Regenerar plan** para generar el plan de esta semana con IA personalizada.")
        st.stop()

    plan = st.session_state.plan_data
    if not isinstance(plan, dict) or "fase" not in plan:
        plan_bd = _cargar_plan_de_bd(user_actual, lunes)
        if plan_bd and isinstance(plan_bd, dict) and "fase" in plan_bd:
            st.session_state.plan_data = plan_bd
            st.rerun()
        st.error("Error: El plan no contiene datos válidos. Intenta regenerarlo.")
        st.stop()

    fase = plan["fase"]
    semaforo = plan["semaforo"]

    # KPI Cards (4 columns)
    kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4, gap="small")

    km_totales = plan.get("km_totales", 0)
    sesiones_no_descanso = len([d for d in plan.get("dias", []) if d.get("tipo") != "Descanso"])
    fuerza_count = len([d for d in plan.get("dias", []) if d.get("tipo") in _TIPOS_FUERZA])
    fase_nombre = fase.get("fase_nombre", "—")

    _kpi_card(kpi_c1, "🏃", "KM Semana", f"{km_totales:.1f}", "#00D4FF", "rgba(0,212,255,0.1)", "rgba(0,212,255,0.25)")
    _kpi_card(kpi_c2, "📋", "Sesiones", str(sesiones_no_descanso), "#4ade80", "rgba(74,222,128,0.1)", "rgba(74,222,128,0.25)")
    _kpi_card(kpi_c3, "💪", "Fuerza", str(fuerza_count), "#c084fc", "rgba(192,132,252,0.1)", "rgba(192,132,252,0.25)")
    _kpi_card(kpi_c4, "📍", "Fase", fase_nombre, "#f97316", "rgba(249,115,22,0.1)", "rgba(249,115,22,0.25)")

    # Semáforo and fase bar
    st.markdown(html_semaforo(semaforo, plan["km_totales"], plan["acwr"]), unsafe_allow_html=True)
    st.markdown(html_barra_fase(fase), unsafe_allow_html=True)

    # "Distribución Semanal" heading
    st.markdown("""
<div style="display:flex;align-items:center;gap:0.5rem;margin:1.5rem 0 1rem;">
  <span style="color:#C9FF00;font-size:1rem;">📅</span>
  <span style="font-size:0.85rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:.07em;">Distribución Semanal</span>
  <div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(201,255,0,0.3),transparent);margin-left:.5rem;"></div>
</div>""", unsafe_allow_html=True)

    # Week day cards (7 columns) with click interactivity
    week_cols = st.columns(7, gap="small")

    # Initialize selected_day_idx in session state
    if "plan_selected_day_idx" not in st.session_state:
        st.session_state["plan_selected_day_idx"] = None

    for i, dia in enumerate(plan.get("dias", [])):
        if i >= 7:
            break
        with week_cols[i]:
            tipo = dia.get("tipo", "—")
            color = _get_activity_color(tipo)
            fecha_obj = datetime.fromisoformat(dia.get("fecha", "2000-01-01"))
            day_name = fecha_obj.strftime("%a").upper()[:3]
            day_date = fecha_obj.strftime("%d")

            duration_km = f"{dia.get('km', 0):.1f} km" if dia.get('km', 0) else f"{dia.get('duracion_min', '—')}''"
            zone = dia.get('intensidad', 'Z1-Z2')
            emoji = _EMOJIS.get(tipo, "📅")

            # Add border glow effect when selected
            is_selected = st.session_state.get("plan_selected_day_idx") == i
            border_style = f"2px solid {color};box-shadow:0 0 16px {color}66;" if is_selected else f"4px solid {color};"
            bg_style = f"linear-gradient(135deg,{color}15,{color}08);" if is_selected else "#161B22;"

            card_html = f"""
<div style="border-left:{border_style}background:{bg_style}border-radius:14px;padding:1rem 0.75rem;cursor:pointer;transition:all 0.2s;position:relative;">
  <div style="color:#8B949E;font-size:.7rem;font-weight:700;text-transform:uppercase;margin-bottom:.3rem;">{day_name}</div>
  <div style="color:white;font-size:.95rem;font-weight:700;margin-bottom:.5rem;">{day_date}</div>
  <div style="display:flex;align-items:center;gap:.4rem;margin-bottom:.5rem;">
    <span style="font-size:.9rem;">{emoji}</span>
    <span style="color:{color};font-size:.75rem;font-weight:700;">{tipo}</span>
  </div>
  <div style="color:#C9E1FF;font-size:.8rem;font-weight:600;margin-bottom:.4rem;">{duration_km}</div>
  <div style="background:rgba(255,255,255,0.1);border-radius:4px;padding:.3rem .5rem;font-size:.65rem;color:#8B949E;">{zone}</div>
</div>"""
            st.markdown(card_html, unsafe_allow_html=True)

            if st.button(f"Ver {day_name}", key=f"plan_day_{i}", use_container_width=True,
                        type="primary" if is_selected else "secondary"):
                st.session_state["plan_selected_day_idx"] = i
                st.rerun()

    # Detailed day view (show when day is selected from grid)
    selected_idx = st.session_state.get("plan_selected_day_idx")
    if selected_idx is not None and selected_idx < len(plan.get("dias", [])):
        st.divider()
        st.markdown(f"<div style='font-weight:800;color:#C9E1FF;font-size:1.1rem;margin-bottom:1rem;'>"
                    f"📋 Detalles de la Sesión</div>", unsafe_allow_html=True)

        col_lista, col_det = st.columns([0.36, 0.64])

        with col_lista:
            opciones = []
            for dia in plan["dias"]:
                emoji = _EMOJIS.get(dia["tipo"], "📅")
                sub = f"{dia['km']} km" if dia["km"] else f"{dia['duracion_min']}'"
                opciones.append(f"{dia['dia']}  {emoji} {dia['tipo']}  ·  {sub}")

            elegido = st.radio("Días", opciones, label_visibility="collapsed", key="plan_dia_radio")
            idx = opciones.index(elegido) if elegido in opciones else selected_idx

        with col_det:
            dia = plan["dias"][idx]
            tipo = dia["tipo"]
            st.markdown(f"<div style='font-weight:800;color:#C9E1FF;font-size:1rem;margin-bottom:8px;'>"
                        f"{dia['dia']} — {dia['fecha'][5:]}</div>", unsafe_allow_html=True)

            if tipo in _TIPOS_FUERZA:
                st.markdown(html_detalle_fuerza(dia), unsafe_allow_html=True)
                if fase["dias_fuerza"] > 0:
                    from src.plan.memoria_fuerza import generar_tabla_fuerza_semana
                    conn = get_db_connection()
                    try:
                        tabla = generar_tabla_fuerza_semana(user_actual, fase, semaforo, conn=conn)
                    finally:
                        conn.close()
                    st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)

            elif tipo in _TIPOS_CARRERA:
                from src.garmin.workout_builder import sesion_a_bloques
                bloques = sesion_a_bloques(dia)
                st.markdown(html_detalle_carrera(dia, bloques), unsafe_allow_html=True)

                if st.button("⌚ Enviar workout a Garmin", key=f"garmin_{idx}"):
                    from src.garmin.garmin_sync import cargar_sesion_tokens
                    cred = obtener_credenciales_garmin(user_actual)
                    email = cred[0] if cred else None
                    gc = st.session_state.get("gc") or cargar_sesion_tokens(email, usuario_id=user_actual)
                    if gc is None:
                        st.warning("Conecta tu cuenta Garmin primero en la página Garmin.")
                    else:
                        with st.spinner("Enviando workout a Garmin..."):
                            try:
                                from src.garmin.workout_builder import crear_workout_garmin, programar_workout_garmin
                                wid = crear_workout_garmin(dia, gc)
                                ok = programar_workout_garmin(gc, wid, dia["fecha"])
                                cal = " y programado en calendario Garmin." if ok else "."
                                st.success(f"✅ Workout enviado (ID: {wid}){cal} Sincroniza tu reloj.")
                            except Exception as e:
                                st.error(f"Error al enviar a Garmin: {e}")
            else:
                st.markdown(html_detalle_descanso(dia), unsafe_allow_html=True)

            # Descripción IA
            if st.session_state.get("plan_ia") and dia.get("descripcion_ia"):
                st.markdown(
                    f"<div style='background:#0f1e10;border-left:3px solid #a3e635;border-radius:0 8px 8px 0;"
                    f"padding:10px 14px;margin:8px 0;font-size:12px;color:#c9d1d9;'>"
                    f"<span style='font-size:10px;color:#a3e635;text-transform:uppercase;letter-spacing:0.6px;"
                    f"font-weight:700;'>🤖 Entrenador IA</span><br><br>"
                    f"{dia['descripcion_ia']}</div>",
                    unsafe_allow_html=True)

            ajuste = st.text_area("Ajuste", placeholder="Ej: reducir 3km, cambiar a Z1 todo...",
                                  height=68, key=f"ajuste_{idx}", label_visibility="collapsed")
            if st.button("Aplicar cambio", key=f"ajuste_btn_{idx}"):
                plan["dias"][idx]["alerta"] = f"[Ajuste] {ajuste}"
                st.session_state.plan_data = plan
                st.success("Cambio anotado."); st.rerun()

    # Alertas
    if plan["alertas"]:
        st.divider()
        for a in plan["alertas"]:
            (st.error if "⛔" in a or "🚫" in a else st.warning if "⚠️" in a else st.info)(a)

    # AI Recommendations card
    if plan.get("alertas") or (st.session_state.get("plan_ia") and any(d.get("descripcion_ia") for d in plan.get("dias", []))):
        st.markdown("""
<div style="background:linear-gradient(135deg,rgba(168,85,247,0.1),rgba(0,212,255,0.05));
border:1px solid rgba(168,85,247,0.25);border-radius:16px;padding:1.5rem;margin:1.5rem 0;">
  <div style="color:white;font-size:.9rem;font-weight:700;margin-bottom:1rem;display:flex;align-items:center;gap:.5rem;">
    ✨ Recomendaciones del Entrenador IA
  </div>
  <div style="color:#C9E1FF;font-size:.85rem;line-height:1.6;">""", unsafe_allow_html=True)

        for a in plan.get("alertas", []):
            st.markdown(f"<div style='margin-bottom:.5rem;'>• {a}</div>", unsafe_allow_html=True)

        st.markdown("</div></div>", unsafe_allow_html=True)

    # Guardar
    st.divider()
    if st.button("💾 Guardar plan en BD", type="primary", use_container_width=True):
        conn = get_db_connection(); semana_str = lunes.strftime("%Y-%m-%d")
        try:
            conn.execute("DELETE FROM plan_entrenamiento WHERE usuario_id=? AND semana_inicio=?",
                         (user_actual, semana_str))
            for d in plan["dias"]:
                desc = d.get("descripcion_ia") or d.get("alerta","")
                conn.execute(
                    "INSERT INTO plan_entrenamiento (usuario_id,semana_inicio,fecha,tipo,sesion,duracion_min,intensidad,creado_en) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (user_actual, semana_str, d["fecha"], d["tipo"], desc,
                     d["duracion_min"], d["intensidad"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit(); st.cache_data.clear(); st.success("Plan guardado.")
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            conn.close()


# ============================================================================
# TAB 2: DATOS DEL ENTRENADOR
# ============================================================================
elif active_tab == "datos":

    # Header with gradient
    st.markdown("""
<div style="background:linear-gradient(135deg,rgba(34,211,238,0.15),rgba(74,222,128,0.1));
border:1px solid rgba(74,222,128,0.25);border-radius:16px;padding:1.5rem 2rem;margin-bottom:1.5rem;">
  <h2 style="color:white;font-size:1.25rem;font-weight:800;margin:0 0 .3rem;">Análisis del Entrenador</h2>
  <p style="color:#8B949E;font-size:.82rem;margin:0;">Datos biométricos y análisis que generan tu plan personalizado</p>
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

    # ── 2. Tablas de Sueño y Biométricos ────────────────────────────────────
    _section("😴", "Sueño — Últimos 30 Días", "#7EB8E0")

    try:
        _df_sueno = pd.read_sql_query(
            """SELECT fecha,
                      ROUND(horas_totales, 1) as horas_totales,
                      score,
                      ROUND(sleep_profundo_horas, 1) as deep_sleep_h,
                      ROUND(sleep_rem_horas, 1) as rem_sleep_h,
                      ROUND(sleep_vigilia_horas, 1) as awake_h
               FROM datos_sueno
               WHERE usuario_id=? AND fecha >= date('now','-30 days')
               ORDER BY fecha DESC""",
            _conn_dat, params=(user_actual,))

        if not _df_sueno.empty:
            # Rename columns for display
            _df_sueno_display = _df_sueno.copy()
            _df_sueno_display.columns = ["Fecha", "Total (h)", "Score", "Profundo (h)", "REM (h)", "Vigilia (h)"]
            st.dataframe(_df_sueno_display, use_container_width=True, hide_index=True)
        else:
            st.info("Sin datos de sueño en los últimos 30 días. Sincroniza tu dispositivo Garmin.")
    except Exception as e:
        st.caption(f"Error cargando datos de sueño: {e}")

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    # ── 2b. Biométricos Diarios ─────────────────────────────────────────────
    _section("❤️", "Biométricos — Últimos 30 Días", "#3B82F6")

    try:
        _df_biom = pd.read_sql_query(
            """SELECT fecha,
                      ROUND(hrv_ms) as hrv_ms,
                      fc_reposo as rhr,
                      sleep_score,
                      ROUND(estres_medio) as stress_level_avg,
                      body_battery_min
               FROM datos_biometricos_premium
               WHERE usuario_id=? AND fecha >= date('now','-30 days')
               ORDER BY fecha DESC""",
            _conn_dat, params=(user_actual,))

        if not _df_biom.empty:
            # Rename columns for display
            _df_biom_display = _df_biom.copy()
            _df_biom_display.columns = ["Fecha", "HRV (ms)", "RHR", "Sleep Score", "Estrés", "Battery"]
            st.dataframe(_df_biom_display, use_container_width=True, hide_index=True)
        else:
            st.info("Sin datos biométricos en los últimos 30 días. Sincroniza tu dispositivo Garmin.")
    except Exception as e:
        st.caption(f"Error cargando datos biométricos: {e}")

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    # ── 3. Análisis de Carrera ──────────────────────────────────────────────
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

    # ── 4. Fase del Macrociclo ──────────────────────────────────────────────
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

    # ── 5. Semáforo ─────────────────────────────────────────────────────────
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
    _color_map = {"verde": "#22c55e", "ambar": "#f59e0b", "rojo": "#ef4444"}
    _sc = _color_map.get(_sem_dat["color"], "#9ca3af")
    _icono = {"verde":"🟢","ambar":"💡","rojo":"💡"}.get(_sem_dat["color"],"💡")
    _titulo = "Recuperación óptima" if _sem_dat["color"] == "verde" else "Recomendación de recuperación"
    st.info(
        f"{_icono} {_titulo}\n\n"
        f"{_sem_dat['mensaje']}\n"
        "El plan se genera con carga completa. Aplica estas recomendaciones si lo consideras necesario.\n"
        f"Multiplicador volumen: {_sem_dat['multiplicador_volumen']:.2f}x · "
        f"Calidad permitida: {'Sí' if _sem_dat['permitir_calidad'] else 'No'}"
    )

    # ── 6. Ciclo (mujeres) ──────────────────────────────────────────────────
    ciclo_data = None
    if _es_mujer:
        _section("🩸", "Ciclo Menstrual", "#ec4899")
        ciclo_data = datos.get("ciclo_menstrual") or datos.get("fase_ciclo")
        if ciclo_data:
            _c1, _c2, _c3 = st.columns(3, gap="small")
            _metric_card(_c1, "Fase", ciclo_data.get("fase") or ciclo_data.get("fase_nombre","—"), color="#ec4899")
            _metric_card(_c2, "Multiplicador Vol.", f"{ciclo_data.get('multiplicador_volumen',1):.2f}x", color="#ec4899")
            _metric_card(_c3, "¿Calidad permitida?", "Sí" if ciclo_data.get("permitir_calidad",True) else "No", color="#ec4899")
            st.info("💡 El ciclo menstrual se usa como recomendación. El plan semanal se mantiene completo y tú decides si ajustar intensidad.")
            if ciclo_data.get("hidratacion_extra"):
                st.info("💧 Fase de estrés hormonal — aumentar hidratación y electrolitos.")
        else:
            st.info("Sin datos de ciclo. Añade registros en la pestaña Diario.")

    # ── 7. Restricciones / Lesiones ─────────────────────────────────────────
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

    # ── 8. Evaluaciones Especializadas ──────────────────────────────────────
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

    # ── 9. Tabla de Fuerza ──────────────────────────────────────────────────
    _section("💪", "Sesión de Fuerza Propuesta", "#a855f7")

    try:
        _tabla_f = generar_tabla_fuerza_semana(user_actual, _fase_dat, _sem_dat,
                                               acwr=datos.get("acwr"), conn=_conn_dat)
        _df_f = pd.DataFrame(_tabla_f)
        if "Día" in _df_f.columns:
            for _dia in ["Push", "Pull", "Tren inferior + glúteo"]:
                _df_dia = _df_f[_df_f["Día"] == _dia]
                if not _df_dia.empty:
                    st.markdown(f"**{_dia}**")
                    st.dataframe(_df_dia.drop(columns=["Día"]), use_container_width=True, hide_index=True)
        else:
            st.dataframe(_df_f, use_container_width=True, hide_index=True)
    except Exception as e:
        st.caption(f"No se pudo generar tabla de fuerza: {e}")

    # ── 10. Resumen Ejecutivo ───────────────────────────────────────────────
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
