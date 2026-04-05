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

st.markdown(f"<h2 style='color:#e6edf3;font-weight:600;margin:8px 0 16px;'>Diario</h2>",
            unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(["🩸 Ciclo", "📓 Entreno libre", "🏋️ Ejercicios", "🩹 Lesiones"])

# ===========================================================================
# TAB 1 — CICLO MENSTRUAL
# ===========================================================================
with tab1:
    if user_actual != 1:
        st.info("Esta sección no está disponible para este perfil.")
    else:
        _conn = get_db_connection()
        _last_bleed = pd.read_sql_query(
            "SELECT fecha FROM diario_fisiologia WHERE usuario_id=? AND sangre IS NOT NULL "
            "AND sangre != 'Sin sangre' ORDER BY fecha DESC LIMIT 1",
            _conn, params=(user_actual,))
        _conn.close()

        if not _last_bleed.empty:
            _last_date = pd.to_datetime(_last_bleed.iloc[0]["fecha"]).date()
            _cycle_day = (datetime.now().date() - _last_date).days + 1
            _fase_actual = ("Menstruación" if _cycle_day <= 5 else "Folicular" if _cycle_day <= 11
                            else "Ovulación" if _cycle_day <= 16 else "Lútea")
        else:
            _cycle_day = None; _fase_actual = None

        if _fase_actual and _cycle_day:
            _c = FASE_COLORS.get(_fase_actual, ACCENT)
            st.markdown(
                f"<div style='background:{_c}12;border-left:3px solid {_c};border-radius:8px;"
                f"padding:10px 16px;margin-bottom:14px;display:flex;align-items:center;gap:12px;'>"
                f"<span style='font-size:1.3rem;'>🌙</span>"
                f"<span style='color:{_c};font-weight:700;'>{_fase_actual}</span>"
                f"<span style='color:{TXT3};font-size:0.82rem;'>· Día {_cycle_day} del ciclo</span></div>",
                unsafe_allow_html=True)

        col1, col2 = st.columns([0.38, 0.62])
        with col1:
            sangre_opts = ["⚪ Sin sangre","🩸 Manchado","🩸 Ligero","🩸🩸 Medio","🩸🩸🩸 Fuerte"]
            sangre_map  = {"⚪ Sin sangre":"Sin sangre","🩸 Manchado":"Manchado","🩸 Ligero":"Ligero","🩸🩸 Medio":"Medio","🩸🩸🩸 Fuerte":"Fuerte"}
            sint_opts   = ["🥚 Dolor de ovarios","🍒 Dolor de senos","🍫 Antojos","💢 Dolor de cabeza","🎈 Hinchazón"]
            sint_map    = {o: o.split(" ",1)[1] for o in sint_opts}
            animo_opts  = ["😰 Ansiedad/Estrés","😭 Triste","😡 Enfadada","😄 Feliz","🪫 Cansada","⚡ Energética"]
            animo_map   = {o: o.split(" ",1)[1] for o in animo_opts}
            fb_opts     = ["🚀 A tope","🗿 Regulero","⛈️ Bajito","⛔ No completo"]
            fb_map      = {"🚀 A tope":"A tope","🗿 Regulero":"Regulero","⛈️ Bajito":"Bajito","⛔ No completo":"No completo"}

            st.markdown(label_upper("Registro diario"), unsafe_allow_html=True)
            with st.form(f"fisio_ciclo_{user_actual}"):
                fecha = st.date_input("Fecha", value=datetime.now().date(), label_visibility="collapsed")
                st.markdown(label_upper("Sangre"), unsafe_allow_html=True)
                sangre = st.pills("_s", sangre_opts, selection_mode="single", default="⚪ Sin sangre", label_visibility="collapsed")
                st.markdown(label_upper("Síntomas"), unsafe_allow_html=True)
                sint_sel = st.pills("_si", sint_opts, selection_mode="multi", label_visibility="collapsed")
                st.markdown(label_upper("Ánimo"), unsafe_allow_html=True)
                animo_sel = st.pills("_a", animo_opts, selection_mode="multi", label_visibility="collapsed")
                st.markdown(label_upper("Entreno"), unsafe_allow_html=True)
                fb_sel = st.pills("_f", fb_opts, selection_mode="single", default="🗿 Regulero", label_visibility="collapsed")
                if st.form_submit_button("Guardar", use_container_width=True, type="primary"):
                    sv = sangre_map.get(sangre or "⚪ Sin sangre", "Sin sangre")
                    fase = "Menstruación" if sv != "Sin sangre" else "Lútea"
                    if sv == "Sin sangre" and not _last_bleed.empty:
                        _ld = pd.to_datetime(_last_bleed.iloc[0]["fecha"]).date()
                        _cd = (fecha - _ld).days + 1
                        fase = "Menstruación" if _cd<=5 else "Folicular" if _cd<=11 else "Ovulación" if _cd<=16 else "Lútea"
                    sint_str  = ", ".join([sint_map.get(x,x)  for x in (sint_sel  or [])])
                    animo_str = ", ".join([animo_map.get(x,x) for x in (animo_sel or [])]) or "Normal"
                    fb_str    = fb_map.get(fb_sel or "🗿 Regulero", "Regulero")
                    conn = get_db_connection()
                    conn.cursor().execute(
                        "INSERT INTO diario_fisiologia (usuario_id,fecha,fase_ciclo,fatiga_subjetiva,"
                        "dolor_notas,sangre,sintomas,estado_animo,feedback_entreno) VALUES (?,?,?,?,?,?,?,?,?)",
                        (user_actual, str(fecha), fase, None, sint_str,
                         sv if sv != "Sin sangre" else None, sint_str, animo_str, fb_str))
                    conn.commit(); conn.close()
                    st.cache_data.clear(); st.success("Registro guardado.")

        with col2:
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

            if df_fisio.empty:
                st.info("Aún no hay datos. ¡Empieza registrando hoy!")
            else:
                df_valid = df_fisio[df_fisio["fase_ciclo"].isin(["Menstruación","Fase Folicular"])].copy()
                if not df_valid.empty:
                    ciclo_df, _ = predecir_fases_ciclo(df_valid[["fecha","fase_ciclo"]].copy(), horizonte_dias=120)
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

# ===========================================================================
# TAB 2 — DIARIO DE ENTRENAMIENTO
# ===========================================================================
with tab2:
    render_tab_entreno(user_actual)

# ===========================================================================
# TAB 3 — EJERCICIOS
# ===========================================================================
with tab3:
    render_tab_ejercicios(user_actual)

# ===========================================================================
# TAB 4 — LESIONES
# ===========================================================================
with tab4:
    render_tab_lesiones(user_actual)
