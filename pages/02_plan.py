"""
pages/2_plan.py — Plan semanal: semáforo, 7 días, detalle, fuerza, Garmin.
Selección de días con st.radio + CSS (sin botones sueltos).
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from src.core.navbar import render_navbar
from src.plan.motor import generar_plan_semana
from src.plan.memoria_fuerza import generar_tabla_fuerza_semana
from src.garmin.workout_builder import crear_workout_garmin, sesion_a_bloques, programar_workout_garmin
from src.db.db_manager import get_db_connection, obtener_credenciales_garmin
from src.core.plan_ui_helpers import (
    html_semaforo, html_barra_fase,
    html_detalle_carrera, html_detalle_fuerza, html_detalle_descanso,
)

render_navbar("plan")

if "usuario_id" not in st.session_state:
    st.warning("Selecciona tu perfil en la página de inicio.")
    st.stop()
user_actual = st.session_state.usuario_id

st.title("Plan Semanal")

_TIPOS_CARRERA = {"Tirada Larga", "Progresiva", "Carrera Z2", "Regenerativo",
                  "Tempo (umbral)", "Intervalos VO2max", "Rodaje Corto",
                  "Fartlek", "Sustitución", "Calidad"}
_TIPOS_FUERZA  = {"Fuerza", "Fuerza Activ.", "Fuerza Tren Superior", "Movilidad"}
_EMOJIS = {"Tirada Larga": "🏃", "Progresiva": "📈", "Tempo (umbral)": "⚡",
           "Intervalos VO2max": "🔥", "Carrera Z2": "🚶", "Regenerativo": "💧",
           "Fuerza": "💪", "Fuerza Activ.": "💪", "Fuerza Tren Superior": "💪",
           "Descanso": "🛌", "Movilidad": "🧘", "Sustitución": "🔄",
           "Rodaje Corto": "🏃"}

# CSS radio → tarjeta clickable (sin puntos de selección visibles)
st.markdown("""<style>
div[data-testid="stRadio"] > div[role="radiogroup"] { gap: 0 !important; }
div[data-testid="stRadio"] label {
  background:#131D2B; border:1px solid rgba(201,255,0,0.15); border-radius:10px;
  padding:10px 12px; margin-bottom:6px; cursor:pointer; width:100%;
  color:#C9E1FF !important; font-size:0.84rem; display:block; }
div[data-testid="stRadio"] label:has(input[type="radio"]:checked) {
  border-color:#C9FF00 !important; background:#111f11 !important; color:#C9FF00 !important; }
div[data-testid="stRadio"] input[type="radio"] { display:none; }
</style>""", unsafe_allow_html=True)


def _lunes_de(dt): return dt - timedelta(days=dt.weekday())

def _cargar_plan_de_bd(usuario_id: int, lunes: datetime) -> dict | None:
    """Carga el plan guardado en BD para esta semana."""
    conn = get_db_connection()
    try:
        semana_str = lunes.strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT fecha, tipo, sesion, duracion_min, intensidad FROM plan_entrenamiento "
            "WHERE usuario_id=? AND semana_inicio=? ORDER BY fecha",
            (usuario_id, semana_str)
        ).fetchall()
        if not rows:
            return None
        # Convertir rows a estructura de días
        dias = []
        for row in rows:
            dias.append({
                "fecha": row[0],
                "dia": datetime.fromisoformat(row[0]).strftime("%a").upper()[:3],
                "tipo": row[1],
                "descripcion_ia": row[2] or "",
                "duracion_min": row[3] or 0,
                "intensidad": row[4] or "Z1-Z2",
                "km": 0,
                "alerta": "",
            })
        # Hidratar metadata del plan para que la página siempre tenga estructura completa
        try:
            base = generar_plan_semana(usuario_id, lunes)
            if isinstance(base, dict):
                base["dias"] = dias
                base["existe_en_bd"] = True
                return base
        except Exception:
            pass

        # Fallback mínimo (evita bloquear UI si falla la hidratación)
        return {
            "dias": dias,
            "fase": {"fase_nombre": "Plan guardado", "km_semanales_max": 0, "dias_fuerza": 0},
            "semaforo": {"color": "ambar", "mensaje": "Plan recuperado desde BD", "permitir_calidad": True, "multiplicador_volumen": 1.0},
            "km_totales": round(sum(float(d.get("km") or 0) for d in dias), 1),
            "acwr": None,
            "alertas": [],
            "existe_en_bd": True,
        }
    except:
        return None
    finally:
        conn.close()

def _adaptar_plan_a_hoy(plan: dict, lunes: datetime, hoy: datetime) -> dict:
    """Si hoy es miércoles, mantiene solo de miércoles a domingo y rellena pasados con historial."""
    hoy_date = hoy.date()
    dias_adaptados = []

    # Días que ya pasaron (lunes, martes si es miércoles) → usar historial
    dias_pasados = (hoy_date - lunes.date()).days

    if dias_pasados > 0:
        # Cargar actividades realizadas de los días pasados
        conn = get_db_connection()
        try:
            actvs = conn.execute(
                "SELECT fecha, tipo, duracion_min, distancia_m/1000.0 as km FROM actividades_garmin "
                "WHERE usuario_id=? AND fecha >= ? AND fecha < ? ORDER BY fecha",
                (st.session_state.usuario_id, lunes.strftime("%Y-%m-%d"), hoy_date)
            ).fetchall()
            for i in range(dias_pasados):
                fecha_dia = lunes + timedelta(days=i)
                # Buscar actividad del día
                actv = next((a for a in actvs if a[0][:10] == fecha_dia.strftime("%Y-%m-%d")), None)
                if actv:
                    dias_adaptados.append({
                        "fecha": actv[0][:10],
                        "dia": fecha_dia.strftime("%a").upper()[:3],
                        "tipo": "Realizado: " + (actv[1] or "Actividad"),
                        "km": actv[3] or 0,
                        "duracion_min": actv[2] or 0,
                        "intensidad": "Histórico",
                        "descripcion_ia": "[De historial Garmin]",
                        "alerta": "✓ Completado",
                    })
        finally:
            conn.close()

    # Días futuros (a partir de hoy)
    for dia in plan.get("dias", []):
        dia_date = datetime.fromisoformat(dia["fecha"]).date()
        if dia_date >= hoy_date:
            dias_adaptados.append(dia)

    plan["dias"] = dias_adaptados
    return plan


if "plan_cursor" not in st.session_state:
    st.session_state.plan_cursor = _lunes_de(datetime.now())
if "plan_data" not in st.session_state:
    st.session_state.plan_data = None
if "plan_ia" not in st.session_state:
    st.session_state.plan_ia = True  # Ahora por defecto con IA

# Intentar cargar plan guardado en BD para esta semana
lunes = st.session_state.plan_cursor
if st.session_state.plan_data is None:
    plan_bd = _cargar_plan_de_bd(user_actual, lunes)
    if plan_bd:
        st.session_state.plan_data = plan_bd
        st.session_state.plan_ia = False  # Marcado como plan guardado
c1, c2, c3, c4 = st.columns([0.08, 0.52, 0.08, 0.32])
with c1:
    if st.button("◀", key="plan_prev"):
        st.session_state.plan_cursor -= timedelta(weeks=1)
        st.session_state.plan_data = None; st.rerun()
with c2:
    st.markdown(f"<div style='text-align:center;font-weight:700;color:#C9E1FF;padding-top:6px;'>"
                f"{lunes.strftime('%d/%m')} – {(lunes+timedelta(6)).strftime('%d/%m/%Y')}</div>",
                unsafe_allow_html=True)
with c3:
    if st.button("▶", key="plan_next"):
        st.session_state.plan_cursor += timedelta(weeks=1)
        st.session_state.plan_data = None; st.rerun()
with c4:
    c4a, c4b = st.columns([2, 1])
    with c4a:
        if st.button("⚡ Regenerar plan (con IA)", type="primary", use_container_width=True):
            with st.spinner():
                try:
                    from src.plan.entrenador import generar_entrenamiento_semana
                    plan_nuevo = generar_entrenamiento_semana(user_actual, lunes)
                    plan_nuevo = _adaptar_plan_a_hoy(plan_nuevo, lunes, datetime.now())
                    st.session_state.plan_data = plan_nuevo
                    st.session_state.plan_ia = True
                except Exception as e:
                    st.error(f"❌ Error generando plan:\n\n{str(e)}")
                    st.stop()
            st.rerun()
    with c4b:
        sin_ia = st.checkbox("Sin IA", key="plan_sin_ia", label_visibility="collapsed")
        if sin_ia:
            st.session_state.plan_ia = False

if st.session_state.plan_data is None:
    st.info("Pulsa **⚡ Regenerar plan** para generar el plan de esta semana con IA personalizada.")
    st.stop()

plan = st.session_state.plan_data
if not isinstance(plan, dict) or "fase" not in plan:
    # Intentar reparar automáticamente desde BD de la semana activa
    plan_bd = _cargar_plan_de_bd(user_actual, lunes)
    if plan_bd and isinstance(plan_bd, dict) and "fase" in plan_bd:
        st.session_state.plan_data = plan_bd
        st.rerun()
    st.error("Error: El plan no contiene datos válidos. Intenta regenerarlo.")
    st.stop()

fase = plan["fase"]
semaforo = plan["semaforo"]

st.markdown(html_semaforo(semaforo, plan["km_totales"], plan["acwr"]), unsafe_allow_html=True)
st.markdown(html_barra_fase(fase), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Layout 2 columnas
# ---------------------------------------------------------------------------
col_lista, col_det = st.columns([0.36, 0.64])

with col_lista:
    opciones = []
    for dia in plan["dias"]:
        emoji = _EMOJIS.get(dia["tipo"], "📅")
        sub = f"{dia['km']} km" if dia["km"] else f"{dia['duracion_min']}'"
        opciones.append(f"{dia['dia']}  {emoji} {dia['tipo']}  ·  {sub}")

    elegido = st.radio("Días", opciones, label_visibility="collapsed", key="plan_dia_radio")
    idx = opciones.index(elegido) if elegido in opciones else 0

with col_det:
    dia = plan["dias"][idx]
    tipo = dia["tipo"]
    st.markdown(f"<div style='font-weight:800;color:#C9E1FF;font-size:1rem;margin-bottom:8px;'>"
                f"{dia['dia']} — {dia['fecha'][5:]}</div>", unsafe_allow_html=True)

    if tipo in _TIPOS_FUERZA:
        st.markdown(html_detalle_fuerza(dia), unsafe_allow_html=True)
        if fase["dias_fuerza"] > 0:
            conn = get_db_connection()
            try:
                tabla = generar_tabla_fuerza_semana(user_actual, fase, semaforo, conn=conn)
            finally:
                conn.close()
            st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)

    elif tipo in _TIPOS_CARRERA:
        bloques = sesion_a_bloques(dia)
        st.markdown(html_detalle_carrera(dia, bloques), unsafe_allow_html=True)

        if st.button("⌚ Enviar workout a Garmin", key=f"garmin_{idx}"):
            from src.garmin.garmin_sync import cargar_sesion_tokens
            cred = obtener_credenciales_garmin(user_actual)
            email = cred[0] if cred else None
            gc = st.session_state.get("gc") or cargar_sesion_tokens(email)
            if gc is None:
                st.warning("Conecta tu cuenta Garmin primero en la página Garmin.")
            else:
                with st.spinner("Enviando workout a Garmin..."):
                    try:
                        wid = crear_workout_garmin(dia, gc)
                        ok = programar_workout_garmin(gc, wid, dia["fecha"])
                        cal = " y programado en calendario Garmin." if ok else "."
                        st.success(f"✅ Workout enviado (ID: {wid}){cal} Sincroniza tu reloj.")
                    except Exception as e:
                        st.error(f"Error al enviar a Garmin: {e}")
    else:
        st.markdown(html_detalle_descanso(dia), unsafe_allow_html=True)

    # Descripción IA (si existe)
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

# Guardar
st.divider()
if st.button("💾 Guardar plan en BD", type="primary"):
    conn = get_db_connection(); semana_str = lunes.strftime("%Y-%m-%d")
    try:
        conn.execute("DELETE FROM plan_entrenamiento WHERE usuario_id=? AND semana_inicio=?",
                     (user_actual, semana_str))
        for d in plan["dias"]:
            # Guardar descripcion_ia si existe; si no, guardar alerta
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
