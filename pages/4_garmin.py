"""
pages/4_garmin.py — Garmin Connect: sync + historial.
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from src.core.navbar import render_navbar
from src.core.styles import (
    ACCENT, CARD, BORDER, BORDER_H, TXT1, TXT2, TXT3,
    label_upper, badge, tipo_color,
)
from src.db.db_manager import get_db_connection, obtener_credenciales_garmin
from src.garmin.garmin_sync import (
    sincronizar_todo_con_sesion, sincronizar_actividades_con_sesion,
    sincronizar_biometricos_garmin, obtener_datos_sueno, guardar_sueno_db,
    iniciar_sesion_garmin, cargar_sesion_tokens,
)
from src.core.seguridad import encriptar_password, desencriptar_password

render_navbar("garmin")

if "usuario_id" not in st.session_state:
    st.warning("Selecciona tu perfil en la página de inicio.")
    st.stop()
user_actual = st.session_state.usuario_id

# Auto-auth: load tokens from disk only — never SSO on page load
cred = obtener_credenciales_garmin(user_actual)
if "gc" not in st.session_state and not st.session_state.get("gc_failed"):
    gc_tok = cargar_sesion_tokens()
    if gc_tok is not None:
        st.session_state["gc"] = gc_tok

st.markdown(f"<h2 style='color:#e6edf3;font-weight:600;margin:8px 0 16px;'>Garmin Connect</h2>",
            unsafe_allow_html=True)

tab_sync, tab_hist = st.tabs(["🔄 Sincronización", "📊 Historial"])

# ===========================================================================
# TAB 1 — SINCRONIZACIÓN
# ===========================================================================
with tab_sync:
    col_est, col_act = st.columns(2, gap="large")

    # ── Estado de conexión ───────────────────────────────────────────
    with col_est:
        st.markdown(label_upper("Estado de conexión"), unsafe_allow_html=True)
        if st.session_state.get("gc"):
            gc_email = cred[0] if (cred and cred[0]) else "cuenta guardada"
            dot_color = "#22c55e"
            st.markdown(
                f"<div style='background:{CARD};border:1px solid {BORDER};border-radius:10px;"
                f"padding:14px 16px;'>"
                f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;'>"
                f"<span style='width:8px;height:8px;border-radius:50%;background:{dot_color};"
                f"display:inline-block;'></span>"
                f"<span style='color:{dot_color};font-weight:600;font-size:13px;'>Conectado</span></div>"
                f"<div style='color:{TXT2};font-size:12px;'>{gc_email}</div></div>",
                unsafe_allow_html=True)
            if st.button("↔ Cambiar cuenta", key="cambiar_cta"):
                st.session_state.pop("gc", None); st.session_state.pop("gc_failed", None); st.rerun()

        elif st.session_state.get("gc_failed"):
            dot_color = "#ef4444"
            st.markdown(
                f"<div style='background:{CARD};border:1px solid {BORDER};border-radius:10px;"
                f"padding:14px 16px;'>"
                f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;'>"
                f"<span style='width:8px;height:8px;border-radius:50%;background:{dot_color};"
                f"display:inline-block;'></span>"
                f"<span style='color:{dot_color};font-weight:600;font-size:13px;'>Error de conexión</span></div>"
                f"<div style='color:{TXT2};font-size:12px;'>No se pudo conectar con Garmin.</div></div>",
                unsafe_allow_html=True)

            if "429" in str(st.session_state.get("gc_error","")) or True:
                st.markdown(
                    f"<div style='background:#1a1200;border:1px solid #f59e0b40;border-radius:8px;"
                    f"padding:10px 14px;margin-top:8px;font-size:12px;color:#f59e0b;'>"
                    f"Si ves error <b>429</b> (demasiados intentos), ejecuta una vez desde terminal:<br>"
                    f"<code style='background:#0d1117;padding:2px 6px;border-radius:4px;'>"
                    f"python scripts/garmin_login_once.py</code></div>",
                    unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔄 Reintentar", use_container_width=True):
                    st.session_state.pop("gc_failed", None); st.rerun()
            with c2:
                if st.button("↔ Cambiar cuenta", use_container_width=True):
                    st.session_state.pop("gc", None); st.session_state.pop("gc_failed", None); st.rerun()
        else:
            dot_color = "#f59e0b"
            st.markdown(
                f"<div style='background:{CARD};border:1px solid {BORDER};border-radius:10px;"
                f"padding:14px 16px;'>"
                f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:10px;'>"
                f"<span style='width:8px;height:8px;border-radius:50%;background:{dot_color};"
                f"display:inline-block;'></span>"
                f"<span style='color:{dot_color};font-weight:600;font-size:13px;'>Sin conectar</span></div>",
                unsafe_allow_html=True)
            with st.form("garmin_cred_form"):
                email_def = cred[0] if cred and cred[0] else ""
                email_g = st.text_input("Email Garmin", value=email_def)
                pass_g  = st.text_input("Contraseña", type="password", help="Vacía = mantener actual")
                if st.form_submit_button("Guardar y conectar", type="primary", use_container_width=True):
                    if email_g and "@" not in email_g:
                        st.error("Email sin formato válido.")
                    elif not pass_g.strip() and not (cred and cred[1]):
                        st.error("Introduce la contraseña.")
                    else:
                        conn = get_db_connection()
                        try:
                            if email_g and pass_g.strip():
                                conn.execute("UPDATE usuarios SET email_garmin=?,password_garmin_enc=? WHERE id=?",
                                             (email_g, encriptar_password(pass_g), user_actual))
                            elif email_g:
                                conn.execute("UPDATE usuarios SET email_garmin=? WHERE id=?", (email_g, user_actual))
                            conn.commit()
                        finally:
                            conn.close()
                        # Only here do we trigger SSO — explicit user action
                        with st.spinner("Conectando con Garmin (puede tardar 15-30 seg)..."):
                            try:
                                pw = pass_g.strip() or desencriptar_password(cred[1])
                                gc_new = iniciar_sesion_garmin(email_g or cred[0], pw)
                                st.session_state["gc"] = gc_new
                                st.session_state.pop("gc_failed", None)
                                st.cache_data.clear(); st.rerun()
                            except Exception as e:
                                st.session_state["gc_failed"] = True
                                st.session_state["gc_error"] = str(e)
                                st.error(f"Error al conectar: {e}")
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Última actividad + botones sync ─────────────────────────────
    with col_act:
        st.markdown(label_upper("Sincronizar"), unsafe_allow_html=True)

        conn = get_db_connection()
        try:
            df_last = pd.read_sql_query(
                "SELECT fecha,tipo_deporte,ROUND(distancia_m/1000,2) AS km,"
                "ROUND(tiempo_seg/60,1) AS min,fc_media,cadencia_media,potencia_media_w "
                "FROM actividades_garmin WHERE usuario_id=? ORDER BY fecha DESC LIMIT 1",
                conn, params=(user_actual,))
        except Exception:
            df_last = pd.DataFrame()
        finally:
            conn.close()

        if not df_last.empty:
            last = df_last.iloc[0]
            tc = tipo_color(last.get("tipo_deporte",""))
            st.markdown(
                f"<div style='background:{CARD};border:1px solid {BORDER};border-radius:10px;"
                f"padding:12px 14px;margin-bottom:10px;'>"
                f"<div style='font-size:12px;color:{TXT3};text-transform:uppercase;letter-spacing:0.6px;'>Última actividad</div>"
                f"<div style='font-size:15px;font-weight:600;color:{TXT1};margin:4px 0;'>{last.get('tipo_deporte','')}</div>"
                f"<div style='font-size:11px;color:{TXT2};margin-bottom:8px;'>{last.get('fecha','')}</div>"
                f"<div style='display:flex;gap:16px;'>"
                f"<div><div style='color:{ACCENT};font-weight:700;'>{last.get('km','—')}</div>"
                f"<div style='color:{TXT3};font-size:10px;'>km</div></div>"
                f"<div><div style='color:{ACCENT};font-weight:700;'>{last.get('min','—')}</div>"
                f"<div style='color:{TXT3};font-size:10px;'>min</div></div>"
                f"<div><div style='color:{ACCENT};font-weight:700;'>{last.get('fc_media','—')}</div>"
                f"<div style='color:{TXT3};font-size:10px;'>bpm</div></div>"
                f"<div><div style='color:{ACCENT};font-weight:700;'>{last.get('cadencia_media','—')}</div>"
                f"<div style='color:{TXT3};font-size:10px;'>spm</div></div>"
                f"</div></div>",
                unsafe_allow_html=True)

        with st.form("sync_todo"):
            n_dias = st.number_input("Días a sincronizar", min_value=1, max_value=30, value=7)
            if st.form_submit_button("↻ Sincronizar todo", use_container_width=True, type="primary"):
                if not st.session_state.get("gc"):
                    st.warning("Primero conecta tu cuenta Garmin.")
                else:
                    with st.spinner("Sincronizando actividades y biométricos…"):
                        try:
                            r = sincronizar_todo_con_sesion(
                                st.session_state["gc"], user_actual, dias=int(n_dias))
                            st.session_state["g_sync"] = datetime.now().strftime("%d/%m %H:%M")
                            st.session_state["g_sync_r"] = r
                            st.cache_data.clear(); st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        if "g_sync" in st.session_state:
            r = st.session_state.get("g_sync_r", {})
            st.caption(
                f"Última sync: {st.session_state['g_sync']} — "
                f"{r.get('actividades','?')} actividades nuevas · {r.get('dias_bio','?')} días biométricos"
            )

    # ── Panel de verificación ────────────────────────────────────────
    st.markdown(f"<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.markdown(label_upper("Verificación de campos importados"), unsafe_allow_html=True)
    CAMPOS = ["fecha","tipo_deporte","distancia_m","tiempo_seg","ritmo_medio",
              "fc_media","fc_max","cadencia_media","longitud_zancada_m","potencia_media_w"]
    conn = get_db_connection()
    try:
        df_v = pd.read_sql_query(
            f"SELECT {','.join(CAMPOS)} FROM actividades_garmin WHERE usuario_id=? "
            f"ORDER BY fecha DESC LIMIT 5", conn, params=(user_actual,))
    except Exception:
        df_v = pd.DataFrame()
    finally:
        conn.close()

    if df_v.empty:
        st.info("Sin actividades importadas aún.")
    else:
        # Grid de campos: verde si tiene dato, gris si None
        cols_grid = st.columns(4)
        last_row = df_v.iloc[0]
        for idx, campo in enumerate(CAMPOS):
            val = last_row.get(campo)
            has_val = val is not None and str(val) not in ("None","nan","")
            col_v = ACCENT if has_val else TXT3
            val_txt = str(round(float(val),2)) if has_val and isinstance(val,(int,float)) else (str(val) if has_val else "—")
            with cols_grid[idx % 4]:
                st.markdown(
                    f"<div style='background:{CARD};border:1px solid {BORDER};border-radius:8px;"
                    f"padding:8px 10px;margin-bottom:6px;'>"
                    f"<div style='color:{TXT3};font-size:10px;text-transform:uppercase;letter-spacing:0.5px;'>{campo}</div>"
                    f"<div style='color:{col_v};font-size:13px;font-weight:600;margin-top:2px;'>{val_txt}</div>"
                    f"</div>",
                    unsafe_allow_html=True)

# ===========================================================================
# TAB 2 — HISTORIAL
# ===========================================================================
with tab_hist:
    conn = get_db_connection()
    try:
        df_all = pd.read_sql_query(
            "SELECT fecha,tipo_deporte,ROUND(distancia_m/1000,2) AS km,"
            "ROUND(tiempo_seg/60,1) AS min,ritmo_medio,fc_media,cadencia_media "
            "FROM actividades_garmin WHERE usuario_id=? ORDER BY fecha DESC",
            conn, params=(user_actual,))
        df_sueno = pd.read_sql_query(
            "SELECT fecha,horas_totales,score,sleep_profundo_horas,sleep_rem_horas "
            "FROM datos_sueno WHERE usuario_id=? ORDER BY fecha DESC LIMIT 30",
            conn, params=(user_actual,))
        df_bio = pd.read_sql_query(
            "SELECT fecha,hrv_ms,fc_reposo,estres_vital "
            "FROM datos_biometricos_premium WHERE usuario_id=? ORDER BY fecha DESC LIMIT 30",
            conn, params=(user_actual,))
    except Exception:
        df_all = df_sueno = df_bio = pd.DataFrame()
    finally:
        conn.close()

    st.markdown(label_upper("Actividades"), unsafe_allow_html=True)
    if df_all.empty:
        st.info("Sin actividades sincronizadas.")
    else:
        # Filter pills por tipo
        tipos = ["Todos"] + sorted(df_all["tipo_deporte"].dropna().unique().tolist())
        filtro = st.pills("filtro_tipo", tipos, selection_mode="single", default="Todos",
                          label_visibility="collapsed")
        df_show = df_all if filtro == "Todos" else df_all[df_all["tipo_deporte"] == filtro]
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        mes = datetime.now().strftime("%Y-%m")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total actividades", len(df_all))
        c2.metric("Km totales", f"{df_all['km'].sum():.1f}")
        c3.metric("Este mes", len(df_all[df_all["fecha"].str.startswith(mes)]))

    st.divider()
    h_sue, h_bio = st.columns(2)
    with h_sue:
        st.markdown(label_upper("Sueño"), unsafe_allow_html=True)
        if not df_sueno.empty:
            st.dataframe(df_sueno, use_container_width=True, hide_index=True)
        else:
            st.info("Sin datos de sueño.")
    with h_bio:
        st.markdown(label_upper("Biométricos"), unsafe_allow_html=True)
        if not df_bio.empty:
            st.dataframe(df_bio, use_container_width=True, hide_index=True)
        else:
            st.info("Sin datos biométricos.")
