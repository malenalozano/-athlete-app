"""
pages/3_diario.py — 4 tabs: Ciclo | Entreno | Ejercicios | Lesiones.
"""

import pandas as pd
import streamlit as st
from datetime import datetime

from src.core.navbar import render_navbar
from src.core.styles import ACCENT, CARD, BORDER, TXT2, TXT3, FASE_COLORS, label_upper, badge, card
from src.db.db_manager import get_db_connection
from src.core.ciclo_helpers import predecir_fases_ciclo, render_calendario_ciclo
from src.core.ui_helpers_a import (
    _dividir_nota_por_fechas, _clasificar_segmento_diario, _extraer_nota_estado,
    _inferir_tipo_carrera, _buscar_actividad_running_fecha,
)
from src.core.ui_helpers_b import extraer_fecha_historica
from src.core.ai_coach import procesar_nota_fuerza
from src.core.diario_tab_entreno import render_tab_entreno
from src.core.ejercicios_lesiones_ui import render_tab_ejercicios, render_tab_lesiones

render_navbar("diario")

if "usuario_id" not in st.session_state:
    st.warning("Selecciona tu perfil en la página de inicio.")
    st.stop()
user_actual = st.session_state.usuario_id

# Validar que los datos sean consistentes con el usuario actual
if "diario_last_user" not in st.session_state:
    st.session_state["diario_last_user"] = user_actual
elif st.session_state["diario_last_user"] != user_actual:
    # Usuario cambió — limpiar caches
    st.cache_data.clear()
    st.session_state["diario_last_user"] = user_actual


def _inicio_ultima_regla(conn, usuario_id: int, fecha_ref=None):
    """Devuelve el primer día del último bloque de sangrado real (Ligero/Medio/Fuerte)."""
    q = (
        "SELECT fecha FROM diario_fisiologia WHERE usuario_id=? "
        "AND sangre IN ('Ligero','Medio','Fuerte')"
    )
    params = [usuario_id]
    if fecha_ref is not None:
        q += " AND fecha<=?"
        params.append(str(fecha_ref))
    q += " ORDER BY fecha ASC"

    df = pd.read_sql_query(q, conn, params=tuple(params))
    if df.empty:
        return None

    fechas = sorted(pd.to_datetime(df["fecha"]).dt.date.tolist())

    # Bloques de días consecutivos con sangrado real
    bloques = []
    bloque = [fechas[0]]
    for f in fechas[1:]:
        if (f - bloque[-1]).days <= 1:
            bloque.append(f)
        else:
            bloques.append(bloque)
            bloque = [f]
    bloques.append(bloque)

    # Aceptar bloques de 2+ días o bloque de 1 día solo si está separado >=20 días
    inicios_validos = []
    for b in bloques:
        inicio = b[0]
        duracion = len(b)
        if not inicios_validos:
            inicios_validos.append(inicio)
            continue
        dias = (inicio - inicios_validos[-1]).days
        if duracion >= 2 or dias >= 20:
            inicios_validos.append(inicio)

    return inicios_validos[-1] if inicios_validos else None

st.markdown(f"<h2 style='color:#e6edf3;font-weight:600;margin:8px 0 16px;'>Diario</h2>",
            unsafe_allow_html=True)

from src.db.db_manager import obtener_perfil as _obtener_perfil
_perfil_actual = _obtener_perfil(user_actual) or {}
_genero_actual = str(_perfil_actual.get("genero", "")).strip().lower()
_es_mujer = _genero_actual in ("mujer", "female", "f", "w", "femenino")

# Initialize tab state
uid = st.session_state.get("usuario_id", 1)
active_tab = st.session_state.get("diario_active_tab", "libre")
if active_tab == "ciclo" and uid != 1:
    active_tab = "libre"

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

# ===========================================================================
# TAB 1 — CICLO MENSTRUAL (solo mujeres)
# ===========================================================================
if _es_mujer and active_tab == "ciclo":
    # Get current cycle phase
    _conn = get_db_connection()
    _last_bleed_start = _inicio_ultima_regla(_conn, user_actual, datetime.now().date())
    _conn.close()

    if _last_bleed_start is not None:
        _cycle_day = (datetime.now().date() - _last_bleed_start).days + 1
        _fase_actual = ("Menstruación" if _cycle_day <= 5 else "Folicular" if _cycle_day <= 11
                        else "Ovulación" if _cycle_day <= 16 else "Lútea")
    else:
        _cycle_day = None
        _fase_actual = None

    # Phase banner with 4 phase icons
    if _fase_actual and _cycle_day:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,rgba(244,63,94,0.12),rgba(168,85,247,0.1));border:1px solid rgba(244,63,94,0.25);border-radius:16px;padding:1.5rem;margin-bottom:1.5rem;'>"
            f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:16px;'>"
            f"<span style='background:#A855F7;color:#fff;padding:6px 12px;border-radius:8px;font-weight:600;font-size:12px;'>● {_fase_actual.upper()}</span>"
            f"<span style='color:#8b949e;'>Día {_cycle_day} del ciclo</span></div>"
            f"<div style='display:flex;justify-content:space-between;gap:12px;'>"
            f"<div style='text-align:center;'><span style='font-size:1.8rem;'>🌑</span><span style='display:block;color:#e05;font-size:10px;font-weight:600;margin-top:4px;'>MENSTRUAL</span></div>"
            f"<div style='text-align:center;'><span style='font-size:1.8rem;'>🌒</span><span style='display:block;color:#A855F7;font-size:10px;font-weight:600;margin-top:4px;border-bottom:2px solid #A855F7;padding-bottom:2px;'>FOLICULAR</span></div>"
            f"<div style='text-align:center;'><span style='font-size:1.8rem;'>🌕</span><span style='display:block;color:#C9FF00;font-size:10px;font-weight:600;margin-top:4px;'>OVULACIÓN</span></div>"
            f"<div style='text-align:center;'><span style='font-size:1.8rem;'>🌖</span><span style='display:block;color:#FF9500;font-size:10px;font-weight:600;margin-top:4px;'>LÚTEA</span></div>"
            f"</div></div>",
            unsafe_allow_html=True)

    # Today's log card with symptom progress bars
    st.markdown(label_upper("Registro de hoy"), unsafe_allow_html=True)

    cols_sym = st.columns(4)

    # Symptom progress bars - Energía, Ánimo, Dolor, Sueño
    symptoms = {
        "Energía": ("#C9FF00", "diario_energia"),
        "Ánimo": ("#A855F7", "diario_animo"),
        "Dolor": ("#F43F5E", "diario_dolor"),
        "Sueño": ("#00D4FF", "diario_sueno"),
    }

    for idx, (sym_name, (sym_color, sym_key)) in enumerate(symptoms.items()):
        with cols_sym[idx]:
            sym_val = st.session_state.get(sym_key, 0)
            new_val = st.slider(sym_name, 0, 10, sym_val, label_visibility="collapsed")
            st.session_state[sym_key] = new_val

            # Render 10-segment progress bar
            segments_html = ""
            for i in range(10):
                segment_color = sym_color if new_val >= (i + 1) else "#30363d"
                segments_html += f"<div style='width:8px;height:8px;background:{segment_color};border-radius:2px;'></div>"

            st.markdown(
                f"<div style='font-size:10px;color:#8b949e;margin-bottom:8px;'>{sym_name}</div>"
                f"<div style='display:flex;gap:2px;margin-bottom:6px;'>{segments_html}</div>"
                f"<div style='font-size:11px;color:{sym_color};font-weight:600;text-align:right;'>{new_val}/10</div>",
                unsafe_allow_html=True)

    # Form for logging cycle data
    st.markdown(label_upper("Registrar síntomas"), unsafe_allow_html=True)
    sangre_opts = ["⚪ Sin sangre","🩸 Manchado","🟤 Flujo","🩸 Ligero","🩸🩸 Medio","🩸🩸🩸 Fuerte"]
    sangre_map  = {
        "⚪ Sin sangre": "Sin sangre",
        "🩸 Manchado": "Manchado",
        "🟤 Flujo": "Flujo",
        "🩸 Ligero": "Ligero",
        "🩸🩸 Medio": "Medio",
        "🩸🩸🩸 Fuerte": "Fuerte",
    }
    sint_opts   = ["🥚 Dolor de ovarios","🍒 Dolor de senos","🍫 Antojos","💢 Dolor de cabeza","🎈 Hinchazón"]
    sint_map    = {o: o.split(" ",1)[1] for o in sint_opts}
    animo_opts  = ["😰 Ansiedad/Estrés","😭 Triste","😡 Enfadada","😄 Feliz","🪫 Cansada","⚡ Energética"]
    animo_map   = {o: o.split(" ",1)[1] for o in animo_opts}
    fb_opts     = ["🚀 A tope","🗿 Regulero","⛈️ Bajito","⛔ No completo"]
    fb_map      = {"🚀 A tope":"A tope","🗿 Regulero":"Regulero","⛈️ Bajito":"Bajito","⛔ No completo":"No completo"}

    with st.form(f"fisio_ciclo_{user_actual}"):
        fecha = st.date_input("Fecha del registro", value=datetime.now().date(), format="DD/MM/YYYY")
        st.markdown(label_upper("Sangre"), unsafe_allow_html=True)
        sangre = st.pills("_s", sangre_opts, selection_mode="single", default="⚪ Sin sangre", label_visibility="collapsed")
        st.markdown(label_upper("Síntomas"), unsafe_allow_html=True)
        sint_sel = st.pills("_si", sint_opts, selection_mode="multi", label_visibility="collapsed")
        st.markdown(label_upper("Ánimo"), unsafe_allow_html=True)
        animo_sel = st.pills("_a", animo_opts, selection_mode="multi", label_visibility="collapsed")
        st.markdown(label_upper("Entreno"), unsafe_allow_html=True)
        fb_sel = st.pills("_f", fb_opts, selection_mode="single", label_visibility="collapsed")
        if st.form_submit_button("Guardar", use_container_width=True, type="primary"):
            sv = sangre_map.get(sangre or "⚪ Sin sangre", "Sin sangre")
            fase = "Menstruación" if sv in ("Ligero", "Medio", "Fuerte") else "Lútea"

            conn = get_db_connection()
            try:
                if sv not in ("Ligero", "Medio", "Fuerte"):
                    _ld = _inicio_ultima_regla(conn, user_actual, fecha)
                    if _ld is not None:
                        _cd = (fecha - _ld).days + 1
                        _pos = ((_cd - 1) % 28) + 1
                        fase = "Menstruación" if _pos <= 5 else "Folicular" if _pos <= 11 else "Ovulación" if _pos <= 16 else "Lútea"

                sint_str  = ", ".join([sint_map.get(x,x)  for x in (sint_sel  or [])])
                animo_str = ", ".join([animo_map.get(x,x) for x in (animo_sel or [])]) or "Normal"
                fb_str    = fb_map.get(fb_sel, "") if fb_sel else ""
                conn.cursor().execute(
                    "INSERT INTO diario_fisiologia (usuario_id,fecha,fase_ciclo,fatiga_subjetiva,"
                    "dolor_notas,sangre,sintomas,estado_animo,feedback_entreno) VALUES (?,?,?,?,?,?,?,?,?)",
                    (user_actual, str(fecha), fase, None, sint_str,
                     sv if sv != "Sin sangre" else None, sint_str, animo_str, fb_str))
                conn.commit()
            finally:
                conn.close()
            st.cache_data.clear()
            st.success("Registro guardado.")

    # Training recommendation card
    st.markdown(
        f"<div style='background:#161B22;border:1px solid #C9FF0040;border-radius:16px;padding:1.25rem;margin-top:1.5rem;'>"
        f"<div style='display:flex;align-items:flex-start;gap:12px;'>"
        f"<span style='font-size:1.5rem;'>💡</span>"
        f"<div><p style='color:#C9FF00;font-weight:600;margin:0 0 4px;'>Recomendación del día</p>"
        f"<p style='color:#8b949e;margin:0;font-size:13px;'>Entreno de recuperación recomendado hoy.</p></div>"
        f"</div></div>",
        unsafe_allow_html=True)

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # Menstrual calendar
    conn = get_db_connection()
    try:
        df_fisio = pd.read_sql_query(
            "SELECT fecha,fase_ciclo,sangre,sintomas,estado_animo,feedback_entreno "
            "FROM diario_fisiologia WHERE usuario_id=? ORDER BY fecha DESC",
            conn, params=(user_actual,))
    except Exception:
        df_fisio = pd.read_sql_query(
            "SELECT fecha,fase_ciclo,fatiga_subjetiva,dolor_notas FROM diario_fisiologia "
            "WHERE usuario_id=? ORDER BY fecha DESC", conn, params=(user_actual,))
        df_fisio[["sangre","sintomas","estado_animo","feedback_entreno"]] = None
    finally:
        conn.close()

    if not df_fisio.empty:
        conn_ciclo = get_db_connection()
        try:
            ciclo_personalizado = conn_ciclo.execute(
                "SELECT ciclo_dias_personalizado FROM usuarios WHERE id=?",
                (user_actual,)).fetchone()
            ciclo_dias_override = ciclo_personalizado[0] if ciclo_personalizado and ciclo_personalizado[0] else None
        except Exception:
            ciclo_dias_override = None
        finally:
            conn_ciclo.close()

        ciclo_df, _ = predecir_fases_ciclo(df_fisio[["fecha", "fase_ciclo", "sangre"]].copy(),
                                          horizonte_dias=120,
                                          ciclo_dias_personalizado=ciclo_dias_override)
        if not ciclo_df.empty:
            hoy = datetime.now().date()
            if "mes_ciclo_cursor" not in st.session_state:
                st.session_state.mes_ciclo_cursor = hoy.replace(day=1)
            nav_l, nav_c, nav_r = st.columns([0.15, 0.70, 0.15])
            with nav_l:
                if st.button("◀", key="mes_prev"):
                    m = st.session_state.mes_ciclo_cursor.month - 1
                    y = st.session_state.mes_ciclo_cursor.year
                    if m < 1: m, y = 12, y-1
                    st.session_state.mes_ciclo_cursor = st.session_state.mes_ciclo_cursor.replace(year=y,month=m,day=1)
            with nav_c:
                mn = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"][st.session_state.mes_ciclo_cursor.month-1]
                st.markdown(f"<div style='text-align:center;font-weight:700;color:#c9d1d9;padding:4px 0;'>{mn} {st.session_state.mes_ciclo_cursor.year}</div>", unsafe_allow_html=True)
            with nav_r:
                if st.button("▶", key="mes_next"):
                    m = st.session_state.mes_ciclo_cursor.month + 1
                    y = st.session_state.mes_ciclo_cursor.year
                    if m > 12: m, y = 1, y+1
                    st.session_state.mes_ciclo_cursor = st.session_state.mes_ciclo_cursor.replace(year=y,month=m,day=1)
            render_calendario_ciclo(ciclo_df, st.session_state.mes_ciclo_cursor.year, st.session_state.mes_ciclo_cursor.month, df_registros=df_fisio)
        else:
            st.info("Registra al menos una menstruación para ver el calendario.")
    else:
        st.info("Aún no hay datos. ¡Empieza registrando hoy!")

# ===========================================================================
# TAB "libre" — DIARIO DE ENTRENAMIENTO (ENTRENO LIBRE)
# ===========================================================================
if active_tab == "libre":
    render_tab_entreno(user_actual)

# ===========================================================================
# TAB "ejercicios" — EJERCICIOS
# ===========================================================================
if active_tab == "ejercicios":
    st.markdown(
        "<div style='background:linear-gradient(135deg,rgba(168,85,247,0.12),rgba(0,212,255,0.05));border:1px solid rgba(168,85,247,0.25);border-radius:16px;padding:1.5rem;margin-bottom:1.5rem;'>"
        "<h3 style='margin:0;color:#e6edf3;'>🏋️ Ejercicios</h3>"
        "</div>",
        unsafe_allow_html=True)
    render_tab_ejercicios(user_actual)

# ===========================================================================
# TAB "lesiones" — LESIONES
# ===========================================================================
if active_tab == "lesiones":
    st.markdown(
        "<div style='background:linear-gradient(135deg,rgba(244,63,94,0.12),rgba(255,149,0,0.05));border:1px solid rgba(244,63,94,0.25);border-radius:16px;padding:1.5rem;margin-bottom:1.5rem;'>"
        "<h3 style='margin:0;color:#e6edf3;'>🩹 Lesiones</h3>"
        "</div>",
        unsafe_allow_html=True)
    render_tab_lesiones(user_actual)

