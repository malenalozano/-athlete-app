"""
src/core/navbar.py — Navbar inspirada en el diseño Figma (glassmorphism, íconos, glow, sub-tabs).
"""

import streamlit as st
from datetime import datetime
from src.core.styles import BORDER
from src.db.db_manager import obtener_credenciales_garmin

# ── Configuración de páginas ──────────────────────────────────────────────────
PAGES = [
    ("pages/01_dashboard.py",  "Inicio",      "dashboard", "🏠", "#C9FF00", "rgba(201,255,0,0.15)",  "rgba(201,255,0,0.7)",  "0 0 16px rgba(201,255,0,0.35)"),
    ("pages/02_plan.py",       "Plan Semanal","plan",      "📋", "#00D4FF", "rgba(0,212,255,0.15)",  "rgba(0,212,255,0.7)",  "0 0 16px rgba(0,212,255,0.35)"),
    ("pages/03_diario.py",     "Diario",      "diario",    "📖", "#A855F7", "rgba(168,85,247,0.15)", "rgba(168,85,247,0.7)", "0 0 16px rgba(168,85,247,0.35)"),
    ("pages/04_garmin.py",     "Garmin",      "garmin",    "⌚", "#3B82F6", "rgba(59,130,246,0.15)", "rgba(59,130,246,0.7)", "0 0 16px rgba(59,130,246,0.35)"),
]

# ── Sub-tabs por página ───────────────────────────────────────────────────────
_SUBTABS = {
    "plan": [
        ("generar", "📋 Generar Plan"),
        ("datos",   "📊 Datos"),
    ],
    "diario": [
        ("libre",      "📝 Entreno Libre"),
        ("ciclo",      "🌸 Ciclo Menstrual"),   # solo Malena
        ("ejercicios", "💪 Ejercicios"),
        ("lesiones",   "🩹 Lesiones"),
    ],
    "garmin": [
        ("sync", "⌚ Sincronización"),
        ("hist", "📊 Historial"),
    ],
}

# (color, bg_active, border_active)
_SUBTAB_COLORS = {
    "plan":   ("#00D4FF", "rgba(0,212,255,0.15)",  "rgba(0,212,255,0.5)"),
    "diario": ("#A855F7", "rgba(168,85,247,0.15)", "rgba(168,85,247,0.5)"),
    "garmin": ("#3B82F6", "rgba(59,130,246,0.15)", "rgba(59,130,246,0.5)"),
}

_NAV = (
    ".main .block-container > div > "
    "[data-testid='stVerticalBlock'] > "
    "[data-testid='stHorizontalBlock']:first-child"
)

_CSS = f"""<style>
/* ── Quitar header nativo ── */
[data-testid="stToolbar"] {{ display: none !important; }}
header {{ display: none !important; }}
.main .block-container {{ padding-top: 0 !important; }}

/* ── Navbar container ── */
{_NAV} {{
    position: sticky !important;
    top: 0 !important;
    z-index: 999 !important;
    background: linear-gradient(180deg, rgba(14,17,23,0.98) 0%, rgba(22,27,34,0.95) 100%) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-bottom: 1px solid rgba(255,255,255,0.06) !important;
    padding: 0 24px !important;
    margin: 0 -4rem 0 -4rem !important;
    align-items: center !important;
    min-height: 64px !important;
    gap: 4px !important;
}}

/* ── Page links ── */
{_NAV} [data-testid="stPageLink"] {{
    display: flex !important;
    align-items: center !important;
    height: 64px !important;
}}
{_NAV} [data-testid="stPageLink"] p {{
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #8B949E !important;
    padding: 6px 10px !important;
    margin: 0 !important;
    border-radius: 10px !important;
    border: 1px solid transparent !important;
    white-space: nowrap !important;
    display: flex !important;
    align-items: center !important;
    gap: 5px !important;
    transition: color 0.2s, background 0.2s !important;
}}
{_NAV} [data-testid="stPageLink"]:hover p {{
    color: #e6edf3 !important;
    background: rgba(255,255,255,0.05) !important;
}}

/* ── Sync button ── */
{_NAV} button[kind="secondary"] {{
    width: 32px !important; height: 32px !important;
    padding: 0 !important; border-radius: 50% !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    background: transparent !important;
    color: #8b949e !important;
    font-size: 14px !important;
    min-height: 0 !important;
    line-height: 1 !important;
    margin-top: 16px !important;
}}
{_NAV} button[kind="secondary"]:hover {{
    background: rgba(255,255,255,0.06) !important;
    color: white !important;
}}

/* ── Selectbox user ── */
{_NAV} [data-testid="stSelectbox"] {{ margin-top: 14px !important; }}
{_NAV} [data-testid="stSelectbox"] > div > div {{
    background: rgba(48,54,61,0.6) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: white !important;
    font-size: 12px !important;
    padding: 0 8px !important;
    min-height: 32px !important;
    height: 32px !important;
}}
</style>"""

_SUBTAB_CSS = """<style>
/* Sub-tabs row buttons */
div[data-testid="stHorizontalBlock"].subtab-row button {
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #8B949E !important;
    border-radius: 8px !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    padding: 0 10px !important;
    height: 28px !important;
    min-height: 0 !important;
    line-height: 28px !important;
}
div[data-testid="stHorizontalBlock"].subtab-row button:hover {
    background: rgba(255,255,255,0.05) !important;
    color: white !important;
}
</style>"""


def _logo_html(auth_user: str) -> str:
    sub = f"{auth_user} &nbsp;·&nbsp; Maratón 2026" if auth_user else "Maratón 2026"
    return (
        "<div style='display:flex;align-items:center;gap:10px;height:64px;"
        "padding-right:16px;border-right:1px solid rgba(255,255,255,0.06);'>"
        "<div style='width:36px;height:36px;border-radius:10px;flex-shrink:0;"
        "display:flex;align-items:center;justify-content:center;font-size:18px;"
        "background:linear-gradient(135deg,#C9FF00 0%,#00D4FF 50%,#A855F7 100%);"
        "box-shadow:0 0 20px rgba(201,255,0,0.4);'>⚡</div>"
        "<div style='line-height:1;'>"
        "<p style='font-size:13px;font-weight:700;margin:0;line-height:1;"
        "background:linear-gradient(90deg,#C9FF00,#00D4FF);"
        "-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>"
        "Proyecto Athlete</p>"
        f"<p style='font-size:10px;color:#8B949E;margin:2px 0 0;line-height:1;'>{sub}</p>"
        "</div></div>"
    )


def _active_item_html(label: str, icon: str, color: str, bg: str, border: str, glow: str) -> str:
    return (
        "<div style='display:flex;align-items:center;height:64px;'>"
        f"<div style='position:relative;display:flex;align-items:center;gap:5px;"
        f"padding:6px 10px;border-radius:10px;background:{bg};border:1px solid {border};"
        f"color:{color};font-size:12px;font-weight:600;white-space:nowrap;"
        f"box-shadow:{glow};'>"
        f"<span style='position:absolute;top:-3px;right:-3px;width:8px;height:8px;"
        f"border-radius:50%;background:{color};border:2px solid #0E1117;'></span>"
        f"<span>{icon}</span><span>{label}</span>"
        "</div></div>"
    )


def _gradient_line_html() -> str:
    return (
        "<div style='height:2px;margin:0 -4rem;"
        "background:linear-gradient(90deg,#C9FF00 0%,#00D4FF 25%,#A855F7 50%,#F97316 75%,#3B82F6 100%);"
        "opacity:0.5;margin-bottom:2rem;'></div>"
    )


def _render_subtabs(pagina_activa: str):
    """Renderiza la fila de sub-tabs debajo de la barra de navegación."""
    tabs = _SUBTABS.get(pagina_activa, [])
    if not tabs:
        return

    # Filtrar ciclo para Dani
    uid = st.session_state.get("usuario_id", 1)
    if pagina_activa == "diario" and uid != 1:
        tabs = [(k, l) for k, l in tabs if k != "ciclo"]

    color, bg_act, border_act = _SUBTAB_COLORS[pagina_activa]
    _key = f"{pagina_activa}_active_tab"
    active = st.session_state.get(_key, tabs[0][0])

    # CSS: active subtab (primary button) styled with section color
    st.markdown(f"""<style>
/* Subtab row: force uniform button sizing */
[data-testid="stButton"] button[kind="primary"] {{
    background: {bg_act} !important;
    border: 1px solid {border_act} !important;
    color: {color} !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    box-shadow: 0 0 10px {bg_act} !important;
    min-height: 34px !important;
}}
[data-testid="stButton"] button[kind="secondary"] {{
    font-size: 11px !important;
    font-weight: 500 !important;
    color: #8B949E !important;
    border-color: transparent !important;
    background: transparent !important;
    min-height: 34px !important;
}}
[data-testid="stButton"] button[kind="secondary"]:hover {{
    background: rgba(255,255,255,0.05) !important;
    color: white !important;
}}
</style>""", unsafe_allow_html=True)

    # All tabs as st.button() — consistent sizing, no layout shift
    n = len(tabs)
    weights = [1.5] * n + [max(0.1, 12 - n * 1.5)]
    cols = st.columns(weights)

    for i, (tab_key, tab_label) in enumerate(tabs):
        is_active = (active == tab_key)
        with cols[i]:
            clicked = st.button(
                tab_label,
                key=f"subtab_{pagina_activa}_{tab_key}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            )
            if clicked and not is_active:
                st.session_state[_key] = tab_key
                st.rerun()


def render_navbar(pagina_activa: str):
    st.markdown(_CSS, unsafe_allow_html=True)

    auth_user = str(st.session_state.get("auth_user", "")).strip()

    # ── Main nav row: logo | 4 pages | spacer | sync | user ─────────────────
    cols = st.columns([2.4, 1.1, 1.3, 1.0, 0.95, 4.5, 1.4])

    with cols[0]:
        st.markdown(_logo_html(auth_user), unsafe_allow_html=True)

    for i, (path, label, key, icon, color, bg, border, glow) in enumerate(PAGES):
        with cols[i + 1]:
            if key == pagina_activa:
                st.markdown(_active_item_html(label, icon, color, bg, border, glow), unsafe_allow_html=True)
            else:
                st.page_link(path, label=f"{icon} {label}")

    # Sync button
    with cols[5]:
        if st.button("↻", key="navbar_sync", help="Sincronizar Garmin (últimos 7 días)"):
            gc = st.session_state.get("gc")
            if gc is None:
                from src.garmin.garmin_sync import cargar_sesion_tokens
                usuario_id = st.session_state.get("usuario_id", 1)
                cred = obtener_credenciales_garmin(usuario_id)
                email = cred[0] if cred else None
                gc = cargar_sesion_tokens(email, usuario_id=usuario_id)
                if gc is not None:
                    st.session_state["gc"] = gc
            if gc is None:
                st.warning("Conecta Garmin primero en la página Garmin.")
            else:
                usuario_id = st.session_state.get("usuario_id", 1)
                from src.garmin.garmin_sync import sincronizar_todo_con_sesion
                with st.spinner():
                    try:
                        r = sincronizar_todo_con_sesion(gc, usuario_id, dias=7)
                        ts = datetime.now().strftime("%d/%m %H:%M")
                        st.session_state["navbar_sync_ts"] = ts
                        st.session_state["navbar_sync_r"] = r
                        st.session_state["garmin_last_sync"] = {"ts": ts, "source": "navbar", "result": r}
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        err_str = str(e)
                        err_low = err_str.lower()
                        if any(k in err_low for k in ["401", "authentication", "token", "unauthorized", "expired"]):
                            st.error("🔑 Sesión Garmin expirada. Ve a Garmin y reconecta.")
                            from src.db.db_manager import get_db_connection as _gdc
                            try:
                                _c = _gdc()
                                _c.execute("UPDATE usuarios SET garmin_tokens=NULL WHERE id=?", (usuario_id,))
                                _c.close()
                            except Exception:
                                pass
                            st.session_state.pop("gc", None)
                        elif "429" in err_str or "rate" in err_low:
                            st.error("⏳ Garmin bloqueado temporalmente. Espera unas horas.")
                        elif any(k in err_low for k in ["timeout", "connection", "network", "ssl"]):
                            st.error("🌐 Error de red al contactar Garmin.")
                        else:
                            st.error(f"❌ Error: {err_str[:200]}")

    # User selector
    _perfiles_dict = {"👩 Malena": 1, "👨 Dani": 2}
    _current_uid   = st.session_state.get("usuario_id", 1)
    _opciones      = list(_perfiles_dict.keys())
    _idx_actual    = next((i for i, k in enumerate(_opciones) if _perfiles_dict[k] == _current_uid), 0)

    with cols[6]:
        _sel = st.selectbox(
            "usuario",
            _opciones,
            index=_idx_actual,
            key="navbar_user_select",
            label_visibility="collapsed",
        )
        _new_uid = _perfiles_dict[_sel]
        if _new_uid != _current_uid:
            st.session_state["usuario_id"] = _new_uid
            for _k in ("plan_data", "plan_cursor", "plan_ia", "diario_data",
                       "ejercicios_data", "gc", "gc_failed", "gc_error",
                       "dashboard_last_user", "diario_last_user", "navbar_popover_open"):
                st.session_state.pop(_k, None)
            st.cache_data.clear()
            st.rerun()

    # ── Sub-tabs row (if page has sub-tabs) ─────────────────────────────────
    if pagina_activa in _SUBTABS:
        _render_subtabs(pagina_activa)

    # ── Gradient line ────────────────────────────────────────────────────────
    st.markdown(_gradient_line_html(), unsafe_allow_html=True)
