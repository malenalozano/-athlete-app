"""
pages/4_garmin.py — Garmin Connect: sync + historial.
"""

import warnings
# Suprimir warning de pandas sobre Turso HTTP connection (no es SQLAlchemy pero funciona)
warnings.filterwarnings("ignore", message=".*pandas only supports SQLAlchemy.*")

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import requests as _requests

from src.core.navbar import render_navbar
from src.core.styles import (
    ACCENT, CARD, BORDER, BORDER_H, TXT1, TXT2, TXT3,
    label_upper, badge, tipo_color, format_hours,
)
from src.db.db_manager import get_db_connection, obtener_credenciales_garmin
try:
    from src.garmin.garmin_sync import (
        sincronizar_todo_con_sesion, sincronizar_actividades_con_sesion,
        sincronizar_biometricos_garmin, obtener_datos_sueno, guardar_sueno_db,
        iniciar_sesion_garmin, cargar_sesion_tokens, check_garmin_blockade,
    )
    _GARMIN_SYNC_OK = True
except ImportError as _e:
    _GARMIN_SYNC_OK = False
    _GARMIN_IMPORT_ERR = str(_e)
    def sincronizar_todo_con_sesion(*a, **kw): return None
    def sincronizar_actividades_con_sesion(*a, **kw): return None
    def sincronizar_biometricos_garmin(*a, **kw): return None
    def obtener_datos_sueno(*a, **kw): return None
    def guardar_sueno_db(*a, **kw): return None
    def iniciar_sesion_garmin(*a, **kw): return None
    def cargar_sesion_tokens(*a, **kw): return None
    def check_garmin_blockade(*a, **kw): return None
from src.core.seguridad import encriptar_password, desencriptar_password

render_navbar("garmin")

_worker_api_url = ""
_worker_api_token = ""
if hasattr(st, "secrets"):
    _worker_api_url = str(st.secrets.get("WORKER_API_URL", "")).strip()
    _worker_api_token = str(st.secrets.get("WORKER_API_TOKEN", "")).strip()
_worker_enabled = bool(_worker_api_url and _worker_api_token)

# Verificar si hay bloqueo 429 activo
_blockade = check_garmin_blockade()
_is_blocked = bool(_blockade and _blockade.get('is_blocked'))
if _blockade and _blockade.get('is_blocked'):
    hours = int(_blockade['remaining_hours'])
    minutes = int((_blockade['remaining_hours'] % 1) * 60)
    
    st.error(
        f"🚫 **Garmin bloqueado por error 429 (demasiados intentos)**\n\n"
        f"Tiempo restante de bloqueo: **{hours}h {minutes}m**\n"
        f"(hasta {_blockade['blocked_until'].split('T')[1][:5]})\n\n"
        f"**⚠️  No intentes conectar ni sincronizar ahora** — alargaría el bloqueo.\n\n"
        f"Los datos guardados seguirán siendo accesibles. "
        f"Cuando pase el bloqueo, vuelve a conectar desde tu ordenador:\n"
        f"`python scripts/garmin_login_once.py`"
    )

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

# Validar que los datos sean consistentes con el usuario actual
if "garmin_last_user" not in st.session_state:
    st.session_state["garmin_last_user"] = user_actual
elif st.session_state["garmin_last_user"] != user_actual:
    # Usuario cambió — limpiar caches
    st.cache_data.clear()
    st.session_state["garmin_last_user"] = user_actual


def _get_saved_password(cred_row):
    if not cred_row or not cred_row[1]:
        return None
    try:
        return desencriptar_password(cred_row[1])
    except Exception:
        return None


def _sync_via_worker_api(usuario_id: int, dias: int):
    if not _worker_enabled:
        return None
    endpoint = _worker_api_url.rstrip("/") + "/sync/manual"
    headers = {
        "Authorization": f"Bearer {_worker_api_token}",
        "Content-Type": "application/json",
    }
    payload = {"usuario_id": int(usuario_id), "dias": int(dias)}
    return _requests.post(endpoint, json=payload, headers=headers, timeout=90)


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
            st.dataframe(df_a[cols], use_container_width=True, hide_index=True)
        else:
            st.caption("No se importaron actividades nuevas en la última sync.")

    with c_b:
        st.markdown("**Biométricos / Sueño importados**")
        if bio:
            df_b = pd.DataFrame(bio)
            df_b = _mark_pending_df(df_b, ["sleep_score"])
            cols = [c for c in ["fecha", "hrv_ms", "fc_reposo", "sleep_score", "spo2", "estres_medio"] if c in df_b.columns]
            st.dataframe(df_b[cols], use_container_width=True, hide_index=True)
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
                st.dataframe(df_s[cols], use_container_width=True, hide_index=True)
# Auto-auth: try token first, then saved credentials (single-profile friendly)
cred = obtener_credenciales_garmin(user_actual)
if "gc" not in st.session_state and not st.session_state.get("gc_failed"):
    gc_tok = cargar_sesion_tokens(cred[0] if cred else None, usuario_id=user_actual)
    if gc_tok is not None:
        st.session_state["gc"] = gc_tok
    # Importante: no intentar login automático con contraseña al cargar la página,
    # porque en errores 429 de Garmin eso puede aumentar el bloqueo por reintentos.

st.markdown("<div class='garmin-wrap'>", unsafe_allow_html=True)
st.markdown(f"<h2 style='color:#e6edf3;font-weight:700;margin:4px 0 4px;'>Garmin Connect</h2>",
            unsafe_allow_html=True)
st.markdown("<div class='garmin-sub'>Sincroniza tu reloj y revisa exactamente qué datos han entrado.</div>", unsafe_allow_html=True)

if "garmin_active_tab" not in st.session_state:
    st.session_state["garmin_active_tab"] = "sync"

active_tab = st.session_state.get("garmin_active_tab", "sync")

# ===========================================================================
# TAB 1 — SINCRONIZACIÓN
# ===========================================================================
if active_tab == "sync":
    # Device connection card (blue gradient Figma design)
    gc_email = cred[0] if (cred and cred[0]) else "cuenta guardada"
    is_connected = bool(st.session_state.get("gc"))

    if is_connected:
        badge_color = "#22c55e"
        badge_text = "● Conectado"
    elif st.session_state.get("gc_failed"):
        badge_color = "#ef4444"
        badge_text = "● Error de conexión"
    else:
        badge_color = "#f59e0b"
        badge_text = "● Desconectado"

    st.markdown(f"""
<div style="background:linear-gradient(135deg,rgba(96,165,250,0.12),rgba(99,102,241,0.08));
border:1px solid rgba(96,165,250,0.25);border-radius:16px;padding:2rem;position:relative;overflow:hidden;">
  <div style="position:absolute;top:-20px;right:-20px;width:150px;height:150px;
  background:#3B82F6;border-radius:50%;opacity:0.1;filter:blur(30px);pointer-events:none;"></div>
  <div style="display:flex;flex-wrap:wrap;align-items:center;gap:2rem;position:relative;">
    <div style="width:100px;height:100px;border-radius:16px;display:flex;align-items:center;
    justify-content:center;font-size:3rem;background:linear-gradient(135deg,#1e3a5f,#0f172a);
    border:2px solid rgba(96,165,250,0.4);box-shadow:0 0 30px rgba(96,165,250,0.2);flex-shrink:0;">⌚</div>
    <div style="flex:1;">
      <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
        <span style="color:{badge_color};font-weight:700;font-size:0.9rem;">{badge_text}</span>
      </div>
      <div style="color:#e6edf3;font-size:1.1rem;font-weight:700;margin-bottom:0.3rem;">Garmin Connect</div>
      <div style="color:#8B949E;font-size:0.85rem;">{gc_email}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)

    # Connection management section (left) + sync section (right)
    col_est, col_act = st.columns(2, gap="large")

    # ── Estado de conexión ───────────────────────────────────────────
    with col_est:
        st.markdown(label_upper("Gestión de cuenta"), unsafe_allow_html=True)
        if st.session_state.get("gc"):
            st.success(f"✅ Conectado como {gc_email}")

        elif st.session_state.get("gc_failed"):
            st.error("❌ Error de conexión con Garmin")
            gc_err = str(st.session_state.get("gc_error", ""))
            if "429" in gc_err or "rate" in gc_err.lower() or "bloqueado" in gc_err.lower():
                st.warning(
                    "**Garmin bloqueado temporalmente (error 429)**\n\n"
                    "Garmin ha detectado demasiados intentos de login recientes.\n\n"
                    "**No intentes reconectar ahora** — solo alargarías el bloqueo.\n"
                    "Espera 24-48 horas y luego vuelve a introducir tus credenciales aquí una sola vez."
                )
            else:
                if gc_err:
                    st.error(f"Error: {gc_err}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔄 Reintentar", use_container_width=True):
                    st.session_state.pop("gc_failed", None); st.rerun()
            with c2:
                if st.button("📖 Ver instrucciones", use_container_width=True, type="secondary"):
                    with st.expander("ℹ️ Cómo resolver el bloqueo de Garmin"):
                        st.markdown("""
### Garmin bloquea login desde Cloud después de 2-3 intentos fallidos

**El login DEBE hacerse una sola vez desde tu ordenador local:**

1. Abre terminal en `athlete-performance-tracker`
2. `.venv\\Scripts\\activate` (Windows)
3. `python scripts/garmin_login_once.py`
4. Introduce tu email y contraseña
5. Espera a que veas `✅ SUCCESS: Tokens guardados`
6. Vuelve al Cloud → Debería funcionar

**Tiempo de espera:**
- 1er intento fallido: 15-30 min
- 2do intento: 1-2 horas
- 3er intento: 24-48 horas

Para detalles: Ver `GARMIN_BLOCKED_FIX.md` en el repositorio.""")
        else:
            st.markdown("**Desconectado** — Conecta tu cuenta para sincronizar datos.")
            with st.form("garmin_cred_form"):
                email_def = cred[0] if cred and cred[0] else ""
                email_g = st.text_input("Email Garmin", value=email_def).strip()
                pass_g  = st.text_input("Contraseña", type="password", help="Vacía = mantener actual")
                if st.form_submit_button("Guardar y conectar", type="primary", use_container_width=True):
                    if _is_blocked:
                        st.error("Bloqueo 429 activo. Espera a que termine el contador antes de reconectar.")
                        st.stop()
                    # Validar email más estrictamente
                    email_valid = True
                    if email_g:
                        if "@" not in email_g:
                            st.error("Email inválido: sin '@'.")
                            email_valid = False
                        elif email_g.count("@") > 1:
                            st.error("Email inválido: múltiples '@'.")
                            email_valid = False
                        elif not email_g.split("@")[0]:
                            st.error("Email inválido: vacío antes de '@'.")
                            email_valid = False
                        elif "." not in email_g.split("@")[1]:
                            st.error("Email inválido: sin dominio (sin '.').")
                            email_valid = False
                    
                    # Validar contraseña
                    pass_valid = True
                    pass_g_clean = pass_g.strip() if pass_g else ""
                    if not pass_g_clean and not (cred and cred[1]):
                        st.error("Introduce la contraseña (mín. 4 caracteres).")
                        pass_valid = False
                    elif pass_g_clean and len(pass_g_clean) < 4:
                        st.error("Contraseña muy corta (mín. 4 caracteres).")
                        pass_valid = False
                    
                    if email_valid and pass_valid:
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
                                gc_new = iniciar_sesion_garmin(email_g or cred[0], pw, usuario_id=user_actual)
                                st.session_state["gc"] = gc_new
                                st.session_state.pop("gc_failed", None)
                                st.cache_data.clear(); st.rerun()
                            except Exception as e:
                                st.session_state["gc_failed"] = True
                                st.session_state["gc_error"] = str(e)
                                err_str = str(e)
                                err_low = err_str.lower()
                                
                                # Errores específicos 429
                                if "429" in err_str or "bloqueado" in err_low:
                                    st.error(
                                        "🚫 **Garmin ha bloqueado las peticiones (error 429)**\n\n"
                                        "Se registró un bloqueo por 48 horas por demasiados intentos. "
                                        "**NO intentes connecting de nuevo ahora** — alargaría el bloqueo.\n\n"
                                        "Cuando pase el tiempo, vuelve a intentar desde tu ordenador executando:\n"
                                        "`python scripts/garmin_login_once.py`"
                                    )
                                else:
                                    st.error(f"Error al conectar: {e}")

    # ── Última actividad + botones sync ─────────────────────────────
    with col_act:
        st.markdown(label_upper("Sincronizar"), unsafe_allow_html=True)

        if _worker_enabled:
            st.info("🛡️ Modo anti-429 activo: esta sincronización se ejecuta en Worker externo (IP estable).")

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
                if _is_blocked:
                    st.error("⏳ Bloqueo 429 activo. No sincronices hasta que finalice el tiempo de bloqueo.")
                    st.stop()
                gc = st.session_state.get("gc")
                # Intentar cargar tokens guardados (sin hacer login SSO)
                if gc is None:
                    gc = cargar_sesion_tokens(cred[0] if cred else None, usuario_id=user_actual)
                    if gc is not None:
                        st.session_state["gc"] = gc

                if gc is None:
                    st.error(
                        "🔑 **Cuenta no conectada** — No hay sesión activa de Garmin.\n\n"
                        "Conecta tu cuenta en el panel izquierdo bajo '**Sin conectar**'."
                    )
                else:
                    with st.spinner("Sincronizando actividades y biométricos…"):
                        try:
                            if _worker_enabled:
                                resp = _sync_via_worker_api(user_actual, int(n_dias))
                                if resp is None:
                                    raise RuntimeError("Worker API no configurada")
                                if resp.status_code == 200:
                                    body = resp.json() or {}
                                    r = body.get("result") or {}
                                elif resp.status_code == 401:
                                    raise RuntimeError("Worker API rechazó autenticación. Revisa WORKER_API_TOKEN.")
                                elif resp.status_code == 409:
                                    raise RuntimeError("Ya hay una sincronización en curso para este usuario en el worker.")
                                elif resp.status_code == 429:
                                    raise RuntimeError("Worker reporta bloqueo 429 activo. Espera a que termine el bloqueo antes de reintentar.")
                                else:
                                    raise RuntimeError(f"Worker API error ({resp.status_code}): {resp.text[:200]}")
                            else:
                                r = sincronizar_todo_con_sesion(gc, user_actual, dias=int(n_dias))
                            ts = datetime.now().strftime("%d/%m %H:%M")
                            st.session_state["g_sync"] = ts
                            st.session_state["g_sync_r"] = r
                            st.session_state["garmin_last_sync"] = {
                                "ts": ts,
                                "source": "garmin",
                                "result": r,
                            }
                            st.success(f"✅ Sincronización exitosa: {r.get('actividades', 0)} actividades, {r.get('dias_bio', 0)} días biométricos")
                            st.cache_data.clear(); st.rerun()
                        except RuntimeError as e:
                            err_str = str(e)
                            err_low = err_str.lower()
                            
                            # Errores de autenticación / token expirado
                            if any(k in err_low for k in ["401", "token expirado", "token", "unauthorized", "expired", "invalid", "desconecta"]):
                                st.error(f"🔑 **Error de sesión** — {err_str}")
                                # Limpiar tokens para forzar reconexión
                                try:
                                    _c = get_db_connection()
                                    _c.execute("UPDATE usuarios SET garmin_tokens=NULL WHERE id=?", (user_actual,))
                                    _c.commit(); _c.close()
                                except Exception:
                                    pass
                                st.session_state.pop("gc", None)
                                st.session_state.pop("gc_failed", None)
                            
                            # Error 429 - Bloqueado by Garmin
                            elif "429" in err_str or "bloqueado" in err_low or "rate" in err_low:
                                st.error(
                                    "⏳ **Garmin bloqueado temporalmente (error 429)**\n\n"
                                    f"{err_str}\n\n"
                                    "**Acción recomendada:**\n"
                                    "1. Espera 24-48 horas\n"
                                    "2. Desconecta tu cuenta (panel izquierdo)\n"
                                    "3. Reconecta introduciendo tus credenciales UNA SOLA VEZ\n\n"
                                    "No intentes sincronizar ni reconectar antes de esperar el tiempo completo."
                                )
                            
                            # Connection / Network errors
                            elif any(k in err_low for k in ["timeout", "timed out", "connection", "network", "ssl", "connect", "error de conexión"]):
                                st.error(
                                    f"🌐 **Error de red** — No se pudo conectar con Garmin.\n\n"
                                    f"Detalle: `{err_str[:200]}`\n\n"
                                    "Inténtalo de nuevo en unos minutos."
                                )
                            
                            # Other errors
                            else:
                                st.error(f"❌ Error al sincronizar:\n\n`{err_str[:500]}`")
                                st.info("💡 Si el error persiste, desconecta (panel izquierdo) y vuelve a conectar tu cuenta.")
                        except Exception as e:
                            err_str = str(e)
                            st.error(f"❌ Error inesperado: `{err_str[:300]}`")
                            st.info("💡 Si el problema continúa, reinicia la aplicación o contacta con soporte.")

        evt = _resolve_last_sync_event()
        if evt:
            r = evt.get("result", {}) or {}
            st.caption(
                f"Última sync: {evt.get('ts','-')} — "
                f"{r.get('actividades','?')} actividades nuevas · "
                f"{r.get('dias_bio','?')} días biométricos · {r.get('dias_sueno','?')} días sueño"
            )

    # ── 6 Metric cards from Figma design ──────────────────────────────
    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
    st.markdown(label_upper("Métricas últimas 24h"), unsafe_allow_html=True)

    conn = get_db_connection()
    try:
        # Get latest biometrics data
        df_latest_bio = pd.read_sql_query("""
            SELECT hrv_ms, fc_reposo, sleep_score, estres_medio, carga_aguda
            FROM datos_biometricos_premium
            WHERE usuario_id=?
            ORDER BY fecha DESC LIMIT 1
        """, conn, params=(user_actual,))

        # Get latest sleep data
        df_latest_sleep = pd.read_sql_query("""
            SELECT horas_totales
            FROM datos_sueno
            WHERE usuario_id=?
            ORDER BY fecha DESC LIMIT 1
        """, conn, params=(user_actual,))

        # Get Body Battery from biometricos_garmin (if available)
        df_body_battery = pd.read_sql_query("""
            SELECT valor
            FROM biometricos_garmin
            WHERE usuario_id=? AND tipo='body_battery'
            ORDER BY fecha DESC LIMIT 1
        """, conn, params=(user_actual,))

    except Exception:
        df_latest_bio = df_latest_sleep = df_body_battery = pd.DataFrame()
    finally:
        conn.close()

    # Extract values
    hrv_val = df_latest_bio["hrv_ms"].iloc[0] if not df_latest_bio.empty and df_latest_bio["hrv_ms"].notna().any() else "—"
    fc_reposo_val = df_latest_bio["fc_reposo"].iloc[0] if not df_latest_bio.empty and df_latest_bio["fc_reposo"].notna().any() else "—"
    sleep_score_val = df_latest_bio["sleep_score"].iloc[0] if not df_latest_bio.empty and df_latest_bio["sleep_score"].notna().any() else "—"
    estres_val = df_latest_bio["estres_medio"].iloc[0] if not df_latest_bio.empty and df_latest_bio["estres_medio"].notna().any() else "—"
    sleep_hours_val = df_latest_sleep["horas_totales"].iloc[0] if not df_latest_sleep.empty else "—"
    body_battery_val = df_body_battery["valor"].iloc[0] if not df_body_battery.empty else "—"

    # Format values
    hrv_text = f"{int(hrv_val)} ms" if isinstance(hrv_val, (int, float)) else hrv_val
    fc_text = f"{int(fc_reposo_val)} bpm" if isinstance(fc_reposo_val, (int, float)) else fc_reposo_val
    sleep_score_text = f"{int(sleep_score_val)}" if isinstance(sleep_score_val, (int, float)) else sleep_score_val
    estres_text = f"{int(estres_val)}" if isinstance(estres_val, (int, float)) else estres_val
    sleep_hours_text = format_hours(sleep_hours_val) if isinstance(sleep_hours_val, (int, float)) else sleep_hours_val
    body_battery_text = f"{int(body_battery_val)}" if isinstance(body_battery_val, (int, float)) else body_battery_val

    # Metric cards
    metric_cards = [
        {"emoji": "💚", "label": "HRV", "value": hrv_text, "unit": "", "color": "#C9FF00", "bg": "linear-gradient(135deg,rgba(201,255,0,0.05),rgba(201,255,0,0.02))"},
        {"emoji": "😴", "label": "Sueño", "value": sleep_hours_text, "unit": "", "color": "#A855F7", "bg": "linear-gradient(135deg,rgba(168,85,247,0.05),rgba(168,85,247,0.02))"},
        {"emoji": "❤️", "label": "FC Reposo", "value": fc_text, "unit": "", "color": "#EC4899", "bg": "linear-gradient(135deg,rgba(236,72,153,0.05),rgba(236,72,153,0.02))"},
        {"emoji": "⚡", "label": "Body Battery", "value": body_battery_text, "unit": "%", "color": "#06B6D4", "bg": "linear-gradient(135deg,rgba(6,182,212,0.05),rgba(6,182,212,0.02))"},
        {"emoji": "🔥", "label": "Estrés", "value": estres_text, "unit": "", "color": "#F97316", "bg": "linear-gradient(135deg,rgba(249,115,22,0.05),rgba(249,115,22,0.02))"},
        {"emoji": "⭐", "label": "Score Sueño", "value": sleep_score_text, "unit": "", "color": "#6366F1", "bg": "linear-gradient(135deg,rgba(99,102,241,0.05),rgba(99,102,241,0.02))"},
    ]

    cols = st.columns(6, gap="small")
    for idx, card in enumerate(metric_cards):
        with cols[idx]:
            st.markdown(f"""
<div style="background:{card['bg']};border:1px solid rgba(96,165,250,0.15);border-radius:12px;padding:1rem;text-align:center;transition:transform 0.2s;">
  <div style="font-size:1.5rem;margin-bottom:.4rem;">{card['emoji']}</div>
  <p style="color:#8B949E;font-size:.65rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.3rem;">{card['label']}</p>
  <p style="color:white;font-size:1.2rem;font-weight:800;margin:0;">{card['value']}</p>
  <p style="font-size:.65rem;margin:0;color:{card['color']};">{card['unit']}</p>
</div>""", unsafe_allow_html=True)

    # ── GitHub Actions sync (fallback cuando Garmin bloquea la IP del cloud) ──
        _gh_pat = st.secrets.get("GITHUB_PAT", "") if hasattr(st, "secrets") else ""
        if _gh_pat:
            st.markdown("<hr style='border:none;border-top:1px solid #1e2a3b;margin:14px 0 10px;'>", unsafe_allow_html=True)
            st.markdown(
                f"<div style='font-size:11px;color:{TXT3};margin-bottom:8px;'>"
                f"🤖 Alternativa si Garmin bloquea esta IP:</div>",
                unsafe_allow_html=True)

            if st.button("🚀 Sync vía GitHub Actions", use_container_width=True, key="gh_sync_btn",
                         help="Lanza la sincronización desde GitHub (diferente IP, evita el bloqueo 429)"):
                _owner = "malenalozano"
                _repo = "athlete-performance-tracker"
                _workflow = "garmin-worker.yml"
                _url = f"https://api.github.com/repos/{_owner}/{_repo}/actions/workflows/{_workflow}/dispatches"
                _headers = {
                    "Authorization": f"Bearer {_gh_pat}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
                _payload = {
                    "ref": "main",
                    "inputs": {
                        "dias": "7",
                        "usuario": str(user_actual),
                    },
                }
                try:
                    _resp = _requests.post(_url, json=_payload, headers=_headers, timeout=15)
                    if _resp.status_code == 204:
                        st.success(
                            "✅ Sincronización iniciada en GitHub Actions. "
                            "Tardará ~2-3 minutos. Recarga la página para ver los datos nuevos.",
                        )
                        st.session_state["gh_sync_triggered"] = datetime.now().strftime("%d/%m %H:%M")
                    elif _resp.status_code == 401:
                        st.error("❌ GitHub PAT inválido. Actualiza el secreto GITHUB_PAT en Streamlit Cloud.")
                    elif _resp.status_code == 404:
                        st.error("❌ Workflow no encontrado. Verifica que garmin-worker.yml esté en el repositorio.")
                    else:
                        st.error(f"❌ Error GitHub API: {_resp.status_code} — {_resp.text[:200]}")
                except Exception as _e:
                    st.error(f"❌ No se pudo contactar con GitHub: {_e}")

            if st.session_state.get("gh_sync_triggered"):
                st.caption(f"⏳ Última ejecución lanzada: {st.session_state['gh_sync_triggered']} · [Ver en GitHub Actions](https://github.com/malenalozano/athlete-performance-tracker/actions)")

    # ── HRV 7-day chart ──────────────────────────────────────────────
    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
    st.markdown(label_upper("HRV últimos 7 días"), unsafe_allow_html=True)

    conn = get_db_connection()
    try:
        df_hrv = pd.read_sql_query("""
            SELECT fecha, hrv_ms
            FROM datos_biometricos_premium
            WHERE usuario_id=?
            ORDER BY fecha DESC
            LIMIT 7
        """, conn, params=(user_actual,))
    except Exception:
        df_hrv = pd.DataFrame()
    finally:
        conn.close()

    if not df_hrv.empty:
        df_hrv = df_hrv.sort_values("fecha")
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_hrv["fecha"],
                y=df_hrv["hrv_ms"],
                fill="tozeroy",
                line=dict(color="#C9FF00", width=2),
                fillcolor="rgba(201,255,0,0.15)",
                name="HRV",
                hovertemplate="<b>%{x}</b><br>HRV: %{y:.0f} ms<extra></extra>"
            ))
            fig.update_layout(
                template="plotly_dark",
                hovermode="x unified",
                margin=dict(l=0, r=0, t=0, b=0),
                height=250,
                plot_bgcolor="#161B22",
                paper_bgcolor="#0D1117",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(201,255,0,0.1)"),
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.info("Plotly no disponible. Instala: pip install plotly")
    else:
        st.info("Sin datos de HRV en los últimos 7 días.")

    # ── 3 status summary cards ─────────────────────────────────────────
    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
    st.markdown(label_upper("Resumen"), unsafe_allow_html=True)

    conn = get_db_connection()
    try:
        # Count activities
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM actividades_garmin WHERE usuario_id=?", (user_actual,))
        total_acts = cursor.fetchone()[0] or 0

        # Last activity
        cursor.execute("""
            SELECT fecha, tipo_deporte, ROUND(distancia_m/1000,2)
            FROM actividades_garmin
            WHERE usuario_id=?
            ORDER BY fecha DESC
            LIMIT 1
        """, (user_actual,))
        last_act = cursor.fetchone()

        # Sleep days count
        cursor.execute("SELECT COUNT(*) FROM datos_sueno WHERE usuario_id=?", (user_actual,))
        sleep_days = cursor.fetchone()[0] or 0
    except Exception:
        total_acts = 0
        last_act = None
        sleep_days = 0
    finally:
        conn.close()

    col_s1, col_s2, col_s3 = st.columns(3, gap="large")
    with col_s1:
        st.metric("Actividades sincronizadas", total_acts)
    with col_s2:
        if last_act:
            st.metric("Última actividad", last_act[1], delta=last_act[0])
        else:
            st.metric("Última actividad", "—")
    with col_s3:
        st.metric("Días con sueño", sleep_days)

# ===========================================================================
# TAB 2 — HISTORIAL
# ===========================================================================
elif active_tab == "hist":
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
        tipos = ["Todos"] + sorted(df_all["tipo_deporte"].dropna().unique().tolist())
        filtro = st.selectbox("Tipo de actividad", tipos, key="garmin_tipo_filtro", label_visibility="collapsed")
        df_show = df_all if filtro == "Todos" else df_all[df_all["tipo_deporte"] == filtro]
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        mes = datetime.now().strftime("%Y-%m")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total actividades", len(df_all))
        try:
            c2.metric("Km totales", f"{float(df_all['km'].dropna().sum()):.1f}")
        except Exception:
            c2.metric("Km totales", "—")
        try:
            c3.metric("Este mes", len(df_all[df_all["fecha"].astype(str).str.startswith(mes)]))
        except Exception:
            c3.metric("Este mes", "—")

    st.divider()
    h_sue, h_bio = st.columns(2)
    with h_sue:
        st.markdown(label_upper("Sueño (últimos 30 días)"), unsafe_allow_html=True)
        if not df_sueno.empty:
            df_sueno_fmt = df_sueno.copy()
            # Formatear columnas de horas a "Xh Ymin"
            for c in ["horas_totales", "sleep_profundo_horas", "sleep_rem_horas", "sleep_vigilia_horas"]:
                if c in df_sueno_fmt.columns:
                    def _fmt_h(v):
                        try:
                            if pd.isna(v) or str(v) in ("", "None", "nan"): return "—"
                            return format_hours(v)
                        except Exception:
                            return str(v)
                    df_sueno_fmt[c] = df_sueno_fmt[c].apply(_fmt_h)
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
