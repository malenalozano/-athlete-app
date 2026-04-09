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

_tab_labels = ["📓 Entreno libre", "🏋️ Ejercicios", "🩹 Lesiones"]
if _es_mujer:
    _tab_labels.insert(1, "🩸 Ciclo")

if _es_mujer:
    tab2, tab1, tab3, tab4 = st.tabs(_tab_labels)
else:
    tab2, tab3, tab4 = st.tabs(_tab_labels)
    tab1 = None  # no existe para hombres

# ===========================================================================
# TAB 1 — CICLO MENSTRUAL (solo mujeres)
# ===========================================================================
if tab1 is not None:
    with tab1:
        # ─ Personalización del ciclo ─────────────────────────────────────────
        with st.expander("⚙️ Personalizar ciclo"):
            col_info, col_input = st.columns([2, 1])
            with col_info:
                st.markdown(
                    "<p style='color:#a3e635;font-size:11px;margin:0;'>Ingresa la duración de tu ciclo menstrual en días. "
                    "Si lo dejas vacío, se calculará automáticamente.</p>",
                    unsafe_allow_html=True)
            with col_input:
                conn_cycle = get_db_connection()
                try:
                    ciclo_actual = conn_cycle.execute(
                        "SELECT ciclo_dias_personalizado FROM usuarios WHERE id=?",
                        (user_actual,)).fetchone()
                    ciclo_val = ciclo_actual[0] if ciclo_actual and ciclo_actual[0] else None
                except Exception:
                    ciclo_val = None
                finally:
                    conn_cycle.close()
                
                new_ciclo = st.number_input(
                    "Días de ciclo",
                    min_value=21,
                    max_value=40,
                    value=ciclo_val if ciclo_val else 28,
                    step=1,
                    label_visibility="collapsed")
                
                if st.button("Guardar ciclo", use_container_width=True):
                    conn_upd = get_db_connection()
                    try:
                        conn_upd.execute(
                            "UPDATE usuarios SET ciclo_dias_personalizado=? WHERE id=?",
                            (int(new_ciclo), user_actual))
                        conn_upd.commit()
                        st.success(f"✅ Ciclo guardado: {int(new_ciclo)} días")
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        conn_upd.close()
                    st.rerun()
        
        _conn = get_db_connection()
        _last_bleed_start = _inicio_ultima_regla(_conn, user_actual, datetime.now().date())
        _conn.close()

        if _last_bleed_start is not None:
            _cycle_day = (datetime.now().date() - _last_bleed_start).days + 1
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

            st.markdown(label_upper("Registro diario"), unsafe_allow_html=True)
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
                    # Solo Ligero/Medio/Fuerte cuentan como días de regla.
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
                # Obtener ciclo personalizado si existe
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

