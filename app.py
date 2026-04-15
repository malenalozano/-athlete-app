"""
app.py — Punto de entrada.
st.navigation(position="hidden") + navbar HTML propia en cada página.
"""

import streamlit as st
import os, sys

# Ensure correct import path for both local and Streamlit Cloud
_app_dir = os.path.dirname(os.path.abspath(__file__))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

st.set_page_config(
    page_title="Athlete",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# CookieManager MUST be instantiated before any st.stop() calls so the iframe renders.
_cm = None
try:
    import extra_streamlit_components as stx
    _cm = stx.CookieManager(key="athlete_cm")
except Exception as e:
    import logging
    logging.warning(f"CookieManager failed to initialize: {e}. Cookie-based auth will be unavailable.")

# ⏸️ AUTENTICACIÓN DESACTIVADA TEMPORALMENTE — Se activará más adelante cuando tengamos la versión final
# require_auth(_cm)

# Ocultar TODO lo nativo de Streamlit + CSS global del sistema de diseño
from src.core.styles import GLOBAL_CSS
from src.db.db_manager import (
    init_db, asegurar_tabla_ejercicios, asegurar_tabla_catalogo_ejercicios,
    get_db_connection,
)
st.markdown("""<style>
[data-testid="stSidebar"]        { display:none!important }
[data-testid="collapsedControl"] { display:none!important }
[data-testid="stSidebarNav"]     { display:none!important }
[data-testid="stNavigation"]     { display:none!important }
header[data-testid="stHeader"]   { display:none!important }
#MainMenu                        { display:none!important }
footer                           { display:none!important }
.main .block-container {
    padding-top: 1rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 100% !important;
}
[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
[data-testid="column"] { padding: 0 0.5rem !important; }
div[data-testid="stButton"] button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
}
div[data-testid="stTextArea"] textarea {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    border-radius: 10px !important;
    font-size: 13px !important;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color: #a3e635 !important;
    box-shadow: none !important;
}
div[data-testid="stTextInput"] input {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
}
div[data-testid="stSelectbox"] > div > div {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    color: #e6edf3 !important;
}
div[data-testid="stTabs"] button[role="tab"] {
    color: #8b949e !important;
    font-size: 13px !important;
    padding: 8px 16px !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #a3e635 !important;
    border-bottom: 2px solid #a3e635 !important;
}
div[data-testid="stMetric"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
}
div[data-testid="stMetric"] label {
    color: #484f58 !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.7px !important;
}
div[data-testid="stMetricValue"] { color: #a3e635 !important; font-size: 22px !important; }
div[data-testid="stMetricDelta"] { font-size: 11px !important; }
div[data-testid="stExpander"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 10px !important;
}
div[data-testid="stNumberInput"] input {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
}
.stDataFrame { background: #161b22 !important; border-radius: 10px !important; }
div[data-testid="stDataFrameResizable"] {
    border: 1px solid #21262d !important;
    border-radius: 10px !important;
}
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stFormSubmitButton"] > button[kind="primary"],
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
    background: #a3e635 !important;
    color: #0d1117 !important;
    border: none !important;
    box-shadow: 0 3px 10px rgba(163, 230, 53, 0.25) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover,
div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover,
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
    background: #a3e635 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(163, 230, 53, 0.34) !important;
}
</style>""", unsafe_allow_html=True)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# Init BD — una sola vez por sesión (un único HTTP batch a Turso)
if not st.session_state.get("_db_init_done", False):
    init_db()  # All DDL in one HTTP call
    asegurar_tabla_catalogo_ejercicios(usuario_id=1)
    asegurar_tabla_catalogo_ejercicios(usuario_id=2)
    st.session_state["_db_init_done"] = True

# Exponer el cookie manager para que navbar.py pueda usarlo en logout/switch
if _cm is not None:
    st.session_state["_cm"] = _cm

# Persistencia usuario + init ejercicios (necesita usuario_id)
def _get_user_id_from_auth_user(auth_user: str) -> int | None:
    """Buscar usuario_id dinámicamente desde BD por nombre (auth_user)."""
    if not auth_user or not isinstance(auth_user, str):
        return None
    
    auth_user_clean = str(auth_user).strip().lower()
    if not auth_user_clean:
        return None
    
    try:
        conn = get_db_connection()
        try:
            # Buscar usuario por nombre (case-insensitive)
            row = conn.execute(
                "SELECT id FROM usuarios WHERE LOWER(nombre) = ?",
                (auth_user_clean,)
            ).fetchone()
            if row:
                return row[0]
        finally:
            conn.close()
    except Exception:
        pass
    
    return None

auth_user = str(st.session_state.get("auth_user", "")).strip().lower()
# Cache the DB lookup in session_state to avoid an extra HTTP call on every rerun
_forced_uid_key = f"_forced_uid_{auth_user}"
if _forced_uid_key not in st.session_state:
    st.session_state[_forced_uid_key] = _get_user_id_from_auth_user(auth_user)
forced_uid = st.session_state[_forced_uid_key]

if forced_uid in (1, 2):
    # Usuario autenticado determina el perfil
    if st.session_state.get("usuario_id") != forced_uid:
        st.session_state["usuario_id"] = forced_uid
elif "usuario_id" not in st.session_state:
    # Sin auth requerida: intentar cookie (con validación), luego default=1
    uid = 1  # Default seguro
    if _cm is not None:
        try:
            cookie_uid = _cm.get("athlete_uid")
            # ✅ VALIDACIÓN: Solo aceptar cookies con UID válidos
            if cookie_uid and str(cookie_uid).strip() in ("1", "2"):
                uid = int(str(cookie_uid).strip())
        except (ValueError, TypeError, AttributeError):
            # Cookie corrupta o tipo inválido — usar default
            uid = 1
    st.session_state["usuario_id"] = uid

# Init ejercicios del usuario — pero solo una vez por sesión
_uid = st.session_state["usuario_id"]
_initialized_users = st.session_state.get("_ejercicios_init_users", set())
if _uid not in _initialized_users:
    asegurar_tabla_ejercicios(_uid)
    _initialized_users.add(_uid)
    st.session_state["_ejercicios_init_users"] = _initialized_users

# Routing: position="hidden" oculta la navbar nativa
dashboard  = st.Page("pages/01_dashboard.py",  title="Dashboard",    icon="📊", default=True)
plan       = st.Page("pages/02_plan.py",       title="Plan semanal", icon="📅")
diario     = st.Page("pages/03_diario.py",     title="Diario",       icon="📓")
garmin     = st.Page("pages/04_garmin.py",     title="Garmin",       icon="⌚")
ejercicios = st.Page("pages/05_ejercicios.py", title="Ejercicios",   icon="🏋️")
entrenador = st.Page("pages/06_entrenador.py", title="Entrenador",   icon="🧠")

pg = st.navigation([dashboard, plan, diario, garmin, ejercicios, entrenador], position="hidden")
pg.run()
