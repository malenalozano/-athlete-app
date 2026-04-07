"""
app.py — Punto de entrada.
st.navigation(position="hidden") + navbar HTML propia en cada página.
"""

import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from src.core.access_control import require_auth

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
except Exception:
    pass

require_auth(_cm)

# Ocultar TODO lo nativo de Streamlit + CSS global del sistema de diseño
from src.core.styles import GLOBAL_CSS
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
</style>""", unsafe_allow_html=True)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# Init BD
from src.db.db_manager import (
    init_db, asegurar_tabla_plan_entrenamiento, asegurar_tablas_fuerza,
    asegurar_tablas_premium, asegurar_indices_consulta,
    asegurar_tabla_ejercicios, asegurar_tabla_lesiones,
)
init_db()
asegurar_tabla_plan_entrenamiento()
asegurar_tablas_fuerza()
asegurar_tablas_premium()
asegurar_indices_consulta()
asegurar_tabla_lesiones()

# Exponer el cookie manager para que navbar.py pueda usarlo en logout/switch
if _cm is not None:
    st.session_state["_cm"] = _cm

# Persistencia usuario + init ejercicios (necesita usuario_id)
auth_user = str(st.session_state.get("auth_user", "")).strip().lower()
auth_user_to_id = {"malena": 1, "dani": 2, "malenita88": 1, "danielito99": 2}
forced_uid = auth_user_to_id.get(auth_user)

if forced_uid in (1, 2):
    # Usuario autenticado determina el perfil
    if st.session_state.get("usuario_id") != forced_uid:
        st.session_state["usuario_id"] = forced_uid
elif "usuario_id" not in st.session_state:
    # Sin auth requerida: intentar cookie, luego default=1
    if _cm is not None:
        try:
            cookie_uid = _cm.get("athlete_uid")
            uid = int(cookie_uid) if str(cookie_uid) in ("1", "2") else 1
        except Exception:
            uid = 1
    else:
        uid = 1
    st.session_state["usuario_id"] = uid
asegurar_tabla_ejercicios(st.session_state["usuario_id"])

# Routing: position="hidden" oculta la navbar nativa
dashboard  = st.Page("pages/01_dashboard.py",  title="Dashboard",    icon="📊", default=True)
plan       = st.Page("pages/02_plan.py",       title="Plan semanal", icon="📅")
diario     = st.Page("pages/03_diario.py",     title="Diario",       icon="📓")
garmin     = st.Page("pages/04_garmin.py",     title="Garmin",       icon="⌚")
ejercicios = st.Page("pages/05_ejercicios.py", title="Ejercicios",   icon="🏋️")
entrenador = st.Page("pages/06_entrenador.py", title="Entrenador",   icon="🧠")

pg = st.navigation([dashboard, plan, diario, garmin, ejercicios, entrenador], position="hidden")
pg.run()
