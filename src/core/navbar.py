"""
src/core/navbar.py — Navbar horizontal con dot de color por item activo.
"""

import streamlit as st
from datetime import datetime
from src.core.styles import ACCENT, BORDER, TXT2, TXT3, CARD
from src.db.db_manager import obtener_credenciales_garmin

PAGES = [
    ("pages/01_dashboard.py",  "Dashboard",    "dashboard"),
    ("pages/02_plan.py",       "Plan semanal", "plan"),
    ("pages/03_diario.py",     "Diario",       "diario"),
    ("pages/04_garmin.py",     "Garmin",       "garmin"),
    ("pages/05_ejercicios.py", "Ejercicios",   "ejercicios"),
    ("pages/06_entrenador.py", "Entrenador",   "entrenador"),
]

_CSS = f"""<style>
/* ── Topbar container — selector específico para evitar contaminar columnas anidadas ── */
.main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-child {{
    background: {CARD} !important;
    border-bottom: 1px solid {BORDER} !important;
    padding: 0 16px !important;
    margin: 0 -2rem 1.5rem -2rem !important;
    align-items: center !important;
    min-height: 52px !important;
}}
/* Page links dentro del topbar */
.main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-child [data-testid="stPageLink"] p {{
    font-size: 13px !important;
    color: {TXT2} !important;
    padding: 16px 12px !important;
    margin: 0 !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.15s, border-color 0.15s !important;
    display: flex !important;
    align-items: center !important;
}}
.main .block-container > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-child [data-testid="stPageLink"]:hover p {{
    color: #c9d1d9 !important;
}}
</style>"""


def _dot(active: bool) -> str:
    color = ACCENT if active else TXT3
    return (f"<span style='display:inline-block;width:6px;height:6px;border-radius:50%;"
            f"background:{color};margin-right:8px;flex-shrink:0;vertical-align:middle;'></span>")


def render_navbar(pagina_activa: str):
    st.markdown(_CSS, unsafe_allow_html=True)

    # Columnas: logo | nav items | spacer | sync | avatar
    cols = st.columns([2.0, 1.05, 1.2, 0.95, 1.05, 1.15, 1.25, 3.35, 0.45, 0.45])

    with cols[0]:
        st.markdown(
            f"<div style='padding:14px 20px 14px 0;font-size:15px;font-weight:600;"
            f"color:{ACCENT};border-right:1px solid {BORDER};letter-spacing:-0.3px;"
            f"line-height:52px;'>athlete.</div>",
            unsafe_allow_html=True)

    for i, (path, label, key) in enumerate(PAGES):
        with cols[i + 1]:
            active = key == pagina_activa
            if active:
                st.markdown(
                    f"<div style='padding:16px 12px;font-size:13px;color:{ACCENT};"
                    f"border-bottom:2px solid {ACCENT};font-weight:500;"
                    f"display:flex;align-items:center;white-space:nowrap;'>"
                    f"{_dot(True)}{label}</div>",
                    unsafe_allow_html=True)
            else:
                # Wrap page_link in a flex div so the dot appears before the link text
                st.markdown(
                    f"<div style='display:flex;align-items:center;padding-left:2px;'>"
                    f"{_dot(False)}</div>",
                    unsafe_allow_html=True)
                st.page_link(path, label=label)

    # Botón sync — llama a sincronizar_todo_con_sesion si hay sesión activa
    with cols[7]:
        st.markdown("""<style>
        div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-child
        button[kind="secondary"] {
            width:32px !important; height:32px !important; padding:0 !important;
            border-radius:50% !important; border:1px solid #30363d !important;
            background:transparent !important; color:#8b949e !important;
            font-size:15px !important; min-height:0 !important; line-height:1 !important;
            margin-top:10px !important;
        }
        </style>""", unsafe_allow_html=True)
        if st.button("↻", key="navbar_sync", help="Sincronizar Garmin (últimos 7 días)"):
            gc = st.session_state.get("gc")
            if gc is None:
                from src.garmin.garmin_sync import cargar_sesion_tokens
                usuario_id = st.session_state.get("usuario_id", 1)
                cred = obtener_credenciales_garmin(usuario_id)
                email = cred[0] if cred else None
                gc = cargar_sesion_tokens(email)
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
                        st.session_state["garmin_last_sync"] = {
                            "ts": ts,
                            "source": "navbar",
                            "result": r,
                        }
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error sync: {e}")

    # Avatar
    with cols[8]:
        st.markdown(
            f"<div style='width:32px;height:32px;border-radius:50%;"
            f"background:linear-gradient(135deg,{ACCENT}40,{ACCENT}15);"
            f"border:1px solid {ACCENT}50;"
            f"color:{ACCENT};display:flex;align-items:center;justify-content:center;"
            f"font-size:12px;font-weight:700;margin-top:10px;'>M</div>",
            unsafe_allow_html=True)
