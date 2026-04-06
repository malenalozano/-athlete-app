"""
pages/4_garmin.py — Garmin Connect: sync + historial.
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from src.core.navbar import render_navbar
from src.core.styles import (
    ACCENT, CARD, BORDER, BORDER_H, TXT1, TXT2, TXT3,
    label_upper, badge, tipo_color, format_hours,
)
from src.db.db_manager import get_db_connection, obtener_credenciales_garmin
from src.garmin.garmin_sync import (
    sincronizar_todo_con_sesion, sincronizar_actividades_con_sesion,
    sincronizar_biometricos_garmin, obtener_datos_sueno, guardar_sueno_db,
    iniciar_sesion_garmin, cargar_sesion_tokens,
)
from src.core.seguridad import encriptar_password, desencriptar_password

render_navbar("garmin")

st.markdown(
    """
    <style>
    .garmin-wrap {
        margin-top: 6px;
    }
    .garmin-sub {
        color: #9aa7b8;
        font-size: 12px;
        margin-top: -6px;
        margin-bottom: 12px;
    }
    .garmin-sync-head {
        background: linear-gradient(90deg, #0f1722 0%, #131d2c 100%);
        border: 1px solid #233043;
        border-radius: 12px;
        padding: 12px 14px;
        margin: 2px 0 14px;
    }
    .garmin-sync-meta {
        color: #8b949e;
        font-size: 12px;
        margin-top: 4px;
    }
    .garmin-chip-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 8px;
    }
    .garmin-chip {
        border: 1px solid #2a3a52;
        border-radius: 999px;
        padding: 4px 10px;
        background: #101826;
        color: #c9d1d9;
        font-size: 11px;
    }
    .garmin-card {
        border: 1px solid #212b3a;
        border-radius: 12px;
        background: linear-gradient(180deg, #121926 0%, #101722 100%);
        padding: 12px;
        margin-top: 10px;
    }
    .garmin-divider {
        border-top: 1px solid #1e2a3b;
        margin: 14px 0;
    }
    .garmin-field-card {
        background: #161b22;
        border: 1px solid #21262d;
        border-radius: 8px;
        padding: 8px 10px;
        margin-bottom: 12px;
        min-height: 76px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .garmin-field-label {
        color: #484f58;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        line-height: 1.1;
    }
    .garmin-field-value {
        font-size: 13px;
        font-weight: 600;
        margin-top: 2px;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "usuario_id" not in st.session_state:
    st.warning("Selecciona tu perfil en la página de inicio.")
    st.stop()
user_actual = st.session_state.usuario_id


def _get_saved_password(cred_row):
    if not cred_row or not cred_row[1]:
        return None
    try:
        return desencriptar_password(cred_row[1])
    except Exception:
        return None


def _resolve_last_sync_event():
    evt = st.session_state.get("garmin_last_sync")
    if evt and isinstance(evt, dict):
        return evt

    # Compatibilidad con claves previas
    page_ts = st.session_state.get("g_sync")
    page_r = st.session_state.get("g_sync_r")
    nav_ts = st.session_state.get("navbar_sync_ts")
    nav_r = st.session_state.get("navbar_sync_r")
    if page_ts and page_r is not None:
        return {"ts": page_ts, "source": "garmin", "result": page_r}
    if nav_ts and nav_r is not None:
        return {"ts": nav_ts, "source": "navbar", "result": nav_r}
    return None


def _render_last_sync_details():
    evt = _resolve_last_sync_event()
    st.markdown(label_upper("Última sincronización"), unsafe_allow_html=True)

    if not evt:
        st.info("Aún no hay una sincronización registrada en esta sesión.")
        return

    res = evt.get("result", {}) or {}
    ts = evt.get("ts", "-")
    source = evt.get("source", "garmin")
    source_lbl = "Barra de navegación" if source == "navbar" else "Página Garmin"
    n_act = int(res.get("actividades", 0) or 0)
    n_bio = int(res.get("dias_bio", 0) or 0)
    n_sleep = int(res.get("dias_sueno", 0) or 0)

    st.markdown("<div class='garmin-sync-head'>", unsafe_allow_html=True)
    st.markdown("**Resumen de importación**")
    st.caption(f"Sincronizado {ts} · origen: {source_lbl}")
    m1, m2, m3 = st.columns(3, gap="large")
    m1.metric("Actividades", n_act)
    m2.metric("Días biométricos", n_bio)
    m3.metric("Días de sueño", n_sleep)
    st.markdown("</div>", unsafe_allow_html=True)

    acts = res.get("actividades_importadas") or []
    bio = res.get("biometricos_importados") or []
    sleep = res.get("sueno_importado") or []

    def _sleep_pending(v):
        if v is None:
            return "Pendiente Garmin"
        try:
            if float(v) <= 0:
                return "Pendiente Garmin"
        except Exception:
            pass
        return v

    def _mark_pending_df(df_in, cols):
        if df_in.empty:
            return df_in
        df_out = df_in.copy()
        for c in cols:
            if c in df_out.columns:
                df_out[c] = df_out[c].apply(_sleep_pending)
        return df_out

    c_a, c_b = st.columns(2, gap="large")
    with c_a:
        st.markdown("**Actividades importadas**")
        if acts:
            df_a = pd.DataFrame(acts)
            cols = [c for c in ["fecha", "tipo_deporte", "km", "min", "fc_media"] if c in df_a.columns]
            st.dataframe(df_a[cols], width="stretch", hide_index=True)
        else:
            st.caption("No se importaron actividades nuevas en la última sync.")

    with c_b:
        st.markdown("**Biométricos / Sueño importados**")
        if bio:
            df_b = pd.DataFrame(bio)
            df_b = _mark_pending_df(df_b, ["sleep_score"])
            cols = [c for c in ["fecha", "hrv_ms", "fc_reposo", "sleep_score", "spo2", "estres_medio"] if c in df_b.columns]
            st.dataframe(df_b[cols], width="stretch", hide_index=True)
        else:
            st.caption("No hubo días biométricos nuevos en la última sync.")

        if sleep:
            with st.expander("Ver detalle de sueño importado", expanded=False):
                df_s = pd.DataFrame(sleep)
                df_s = _mark_pending_df(df_s, ["horas_totales", "score", "sleep_profundo_horas", "sleep_rem_horas", "sleep_vigilia_horas", "despertares"])
                # Formatear horas
                for c in ["horas_totales", "sleep_profundo_horas", "sleep_rem_horas", "sleep_vigilia_horas"]:
                    if c in df_s.columns:
                        df_s[c] = df_s[c].apply(lambda v: format_hours(v) if pd.notna(v) and str(v) != "Pendiente Garmin" else v)
                cols = [c for c in ["fecha", "horas_totales", "score", "sleep_profundo_horas", "sleep_rem_horas", "sleep_vigilia_horas", "despertares"] if c in df_s.columns]
                st.dataframe(df_s[cols], width="stretch", hide_index=True)
# Auto-auth: try token first, then saved credentials (single-profile friendly)
cred = obtener_credenciales_garmin(user_actual)
if "gc" not in st.session_state and not st.session_state.get("gc_failed"):
    gc_tok = cargar_sesion_tokens(cred[0] if cred else None)
    if gc_tok is not None:
        st.session_state["gc"] = gc_tok
    elif cred and cred[0]:
        saved_pw = _get_saved_password(cred)
        if saved_pw:
            try:
                st.session_state["gc"] = iniciar_sesion_garmin(cred[0], saved_pw)
            except Exception as e:
                st.session_state["gc_failed"] = True
                st.session_state["gc_error"] = str(e)

st.markdown("<div class='garmin-wrap'>", unsafe_allow_html=True)
st.markdown(f"<h2 style='color:#e6edf3;font-weight:700;margin:4px 0 4px;'>Garmin Connect</h2>",
            unsafe_allow_html=True)
st.markdown("<div class='garmin-sub'>Sincroniza tu reloj y revisa exactamente qué datos han entrado.</div>", unsafe_allow_html=True)

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

            if "429" in str(st.session_state.get("gc_error","")):
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
                                pw = pass_g.strip() or _get_saved_password(cred)
                                if not pw:
                                    raise RuntimeError("La contraseña guardada no es válida. Escríbela de nuevo para re-guardarla.")
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
                gc = st.session_state.get("gc")
                if gc is None and cred and cred[0]:
                    try:
                        saved_pw = _get_saved_password(cred)
                        if saved_pw:
                            gc = iniciar_sesion_garmin(cred[0], saved_pw)
                            st.session_state["gc"] = gc
                        else:
                            st.warning("Tu contraseña guardada de Garmin no es válida. Vuelve a guardarla una vez y quedará recordada.")
                    except Exception as e:
                        st.session_state["gc_failed"] = True
                        st.session_state["gc_error"] = str(e)
                        gc = None

                if gc is None:
                    st.warning("Primero conecta tu cuenta Garmin.")
                else:
                    with st.spinner("Sincronizando actividades y biométricos…"):
                        try:
                            r = sincronizar_todo_con_sesion(gc, user_actual, dias=int(n_dias))
                            ts = datetime.now().strftime("%d/%m %H:%M")
                            st.session_state["g_sync"] = ts
                            st.session_state["g_sync_r"] = r
                            st.session_state["garmin_last_sync"] = {
                                "ts": ts,
                                "source": "garmin",
                                "result": r,
                            }
                            st.cache_data.clear(); st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        evt = _resolve_last_sync_event()
        if evt:
            r = evt.get("result", {}) or {}
            st.caption(
                f"Última sync: {evt.get('ts','-')} — "
                f"{r.get('actividades','?')} actividades nuevas · "
                f"{r.get('dias_bio','?')} días biométricos · {r.get('dias_sueno','?')} días sueño"
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
        cols_grid = st.columns(4, gap="medium")
        last_row = df_v.iloc[0]
        for idx, campo in enumerate(CAMPOS):
            val = last_row.get(campo)
            has_val = val is not None and str(val) not in ("None","nan","")
            col_v = ACCENT if has_val else TXT3
            val_txt = str(round(float(val),2)) if has_val and isinstance(val,(int,float)) else (str(val) if has_val else "—")
            with cols_grid[idx % 4]:
                st.markdown(
                    f"<div class='garmin-field-card'>"
                    f"<div class='garmin-field-label'>{campo}</div>"
                    f"<div class='garmin-field-value' style='color:{col_v};'>{val_txt}</div>"
                    f"</div>",
                    unsafe_allow_html=True)

    st.markdown("<div style='margin:16px 0 4px;'></div>", unsafe_allow_html=True)
    _render_last_sync_details()

    # === DEBUG: Mostrar estado de la BD después de sincronizar ===
    st.markdown(label_upper("🔍 Estado de datos importados"), unsafe_allow_html=True)
    conn = get_db_connection()
    try:
        # Biometrics
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(fc_reposo) as fc_reposo_vals,
                   COUNT(sleep_score) as sleep_score_vals,
                   COUNT(carga_aguda) as carga_aguda_vals,
                   COUNT(carga_cronica) as carga_cronica_vals
            FROM datos_biometricos_premium
            WHERE usuario_id=?
        """, (user_actual,))
        row = cursor.fetchone()

        col1, col2, col3, col4 = st.columns(4, gap="large")
        with col1:
            st.metric("Total Biometrics", row[0] or 0)
        with col2:
            st.metric("fc_reposo (n)", row[1] or 0, delta="✅ OK" if row[1] else "❌ sin datos")
        with col3:
            st.metric("sleep_score_bio (n)", row[2] or 0, delta="valores en BD" if row[2] else "—")
        with col4:
            st.metric("ACWR (n)", row[4] or 0, delta="cr+ag" if row[4] else "—")

        # Sleep scores en datos_sueno - ALL fields
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(horas_totales) as horas_totales_vals,
                   COUNT(score) as score_vals,
                   COUNT(sleep_profundo_horas) as profundo_vals,
                   COUNT(sleep_rem_horas) as rem_vals,
                   COUNT(sleep_vigilia_horas) as vigilia_vals,
                   COUNT(despertares) as despertares_vals,
                   MAX(score) as max_score,
                   MIN(score) as min_score,
                   AVG(score) as avg_score
            FROM datos_sueno WHERE usuario_id=?
        """, (user_actual,))
        row_sueno = cursor.fetchone()

        col_s1, col_s2, col_s3 = st.columns(3, gap="large")
        with col_s1:
            st.metric("datos_sueno (días)", row_sueno[0] or 0)
        with col_s2:
            score_count = row_sueno[2] or 0
            st.metric("Score importado (n)", score_count, delta="✅ OK" if score_count > 0 else "❌ sin datos")
        with col_s3:
            if row_sueno[2] and row_sueno[2] > 0:
                st.metric("Score range", f"{int(row_sueno[8])}-{int(row_sueno[7])}", delta=f"avg={int(row_sueno[9])}")
            else:
                st.metric("Score range", "—")

        # Desglose de todos los campos de sueño
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        sleep_cols = [
            ("Horas totales", row_sueno[1] or 0),
            ("Score", row_sueno[2] or 0),
            ("Profundo (h)", row_sueno[3] or 0),
            ("REM (h)", row_sueno[4] or 0),
            ("Vigilia (h)", row_sueno[5] or 0),
            ("Despertares", row_sueno[6] or 0),
        ]
        cols_sleep = st.columns(6, gap="medium")
        for idx, (label, count) in enumerate(sleep_cols):
            with cols_sleep[idx]:
                status = "✅" if count > 0 else "—"
                st.markdown(
                    f"<div style='background:{CARD};border:1px solid {BORDER};border-radius:8px;"
                    f"padding:8px 10px;text-align:center;'>"
                    f"<div style='color:{TXT3};font-size:10px;text-transform:uppercase;letter-spacing:0.5px;font-weight:600;'>{label}</div>"
                    f"<div style='color:{ACCENT if count > 0 else TXT3};font-size:14px;font-weight:700;margin-top:4px;'>{int(count) if count > 0 else '—'}</div>"
                    f"<div style='color:{ACCENT if count > 0 else TXT3};font-size:11px;margin-top:2px;'>{status}</div>"
                    f"</div>",
                    unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error al revisar BD: {e}")
    finally:
        conn.close()

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
            "SELECT fecha,horas_totales,score,sleep_profundo_horas,sleep_rem_horas,sleep_vigilia_horas,despertares "
            "FROM datos_sueno WHERE usuario_id=? ORDER BY fecha DESC LIMIT 30",
            conn, params=(user_actual,))
        df_bio = pd.read_sql_query(
            "SELECT fecha,hrv_ms,fc_reposo,sleep_score,estres_medio,carga_aguda,carga_cronica "
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
        st.markdown(label_upper("Sueño (últimos 30 días)"), unsafe_allow_html=True)
        if not df_sueno.empty:
            df_sueno_fmt = df_sueno.copy()
            # Formatear columnas de horas a "Xh Ymin"
            for c in ["horas_totales", "sleep_profundo_horas", "sleep_rem_horas", "sleep_vigilia_horas"]:
                if c in df_sueno_fmt.columns:
                    df_sueno_fmt[c] = df_sueno_fmt[c].apply(lambda v:
                        format_hours(v) if (pd.notna(v) and str(v) not in ("", "None"))
                        else "Pendiente Garmin" if (pd.notna(v) and float(v) == 0.0) else "—")
            st.dataframe(df_sueno_fmt, use_container_width=True, hide_index=True)
        else:
            st.info("Sin datos de sueño.")
    with h_bio:
        st.markdown(label_upper("Biométricos"), unsafe_allow_html=True)
        if not df_bio.empty:
            # Calcular ACWR
            df_bio_show = df_bio.copy()
            df_bio_show["ACWR"] = df_bio_show.apply(
                lambda row: round(float(row["carga_aguda"]) / float(row["carga_cronica"]), 2)
                if (pd.notna(row["carga_aguda"]) and pd.notna(row["carga_cronica"]) and float(row["carga_cronica"]) > 0) else None,
                axis=1
            )
            # Mostrar solo columnas relevantes
            df_bio_show = df_bio_show[["fecha", "hrv_ms", "fc_reposo", "sleep_score", "estres_medio", "ACWR"]]
            st.dataframe(df_bio_show, use_container_width=True, hide_index=True)
        else:
            st.info("Sin datos biométricos.")

st.markdown("</div>", unsafe_allow_html=True)
