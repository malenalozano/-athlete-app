"""
app.py — Punto de entrada.
st.navigation(position="hidden") + navbar HTML propia en cada página.
"""

import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="Athlete",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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

# Persistencia usuario + init ejercicios (necesita usuario_id)
from src.core.ui_helpers_a import _leer_ultimo_usuario, _guardar_ultimo_usuario
if "usuario_id" not in st.session_state:
    uid = _leer_ultimo_usuario()
    st.session_state["usuario_id"] = uid if uid else 1
    if not uid:
        _guardar_ultimo_usuario(1)
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
