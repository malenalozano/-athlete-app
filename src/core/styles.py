"""
src/core/styles.py — Sistema de diseño global.
CSS tokens, componentes HTML reutilizables. Sin lógica de negocio.
"""

# ---------------------------------------------------------------------------
# TOKENS
# ---------------------------------------------------------------------------
BG          = "#0d1117"
CARD        = "#161b22"
CARD2       = "#1c2128"
BORDER      = "#21262d"
BORDER_H    = "#30363d"
ACCENT      = "#a3e635"       # verde lima — running / acento principal
FUERZA      = "#818cf8"       # morado — fuerza
REGEN       = "#22d3ee"       # cyan — regenerativo
DESCANSO    = "#484f58"       # gris — descanso
TXT1        = "#e6edf3"       # texto primario
TXT2        = "#8b949e"       # texto secundario
TXT3        = "#484f58"       # hint / placeholder

FASE_COLORS = {
    "Menstruación": "#e05",
    "Menstruacion": "#e05",
    "Folicular": "#0ab",
    "Ovulación": "#fa0",
    "Ovulacion": "#fa0",
    "Lútea": "#69f",
    "Lutea": "#69f",
}

TIPO_COLORS = {
    "running": ACCENT,
    "carrera": ACCENT,
    "cycling": "#f59e0b",
    "fuerza": FUERZA,
    "strength": FUERZA,
    "regenerativo": REGEN,
    "descanso": DESCANSO,
}

# ---------------------------------------------------------------------------
# CSS GLOBAL (inyectado en app.py una sola vez)
# ---------------------------------------------------------------------------
GLOBAL_CSS = f"""<style>
/* ── Fondo y layout ── */
.stApp, [data-testid="stAppViewContainer"] {{
    background: {BG} !important;
}}
.main .block-container {{
    padding-top: 0 !important;
    max-width: 100% !important;
    background: {BG} !important;
}}

/* ── Inputs / Textareas ── */
textarea, input[type="text"], input[type="number"], input[type="email"], input[type="password"] {{
    background: {BG} !important;
    border: 1px solid {BORDER_H} !important;
    border-radius: 8px !important;
    color: {TXT1} !important;
}}
textarea:focus, input:focus {{
    border-color: {ACCENT}60 !important;
    box-shadow: 0 0 0 2px {ACCENT}18 !important;
}}

/* ── Botones primary ── */
[data-testid="stBaseButton-primary"] > button,
button[kind="primary"] {{
    background: {ACCENT} !important;
    color: #0d1117 !important;
    border: none !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}}
[data-testid="stBaseButton-secondary"] > button,
button[kind="secondary"] {{
    background: transparent !important;
    border: 1px solid {BORDER_H} !important;
    color: {TXT2} !important;
    border-radius: 8px !important;
}}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {{
    background: {BG} !important;
    border: 1px solid {BORDER_H} !important;
    border-radius: 8px !important;
    color: {TXT1} !important;
}}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tab"] {{
    color: {TXT2} !important;
    font-size: 13px !important;
}}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: {ACCENT} !important;
    border-bottom: 2px solid {ACCENT} !important;
}}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}}

/* ── Métricas ── */
[data-testid="stMetric"] label {{
    color: {TXT3} !important;
    font-size: 10px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}}
[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    color: {ACCENT} !important;
    font-size: 1.4rem !important;
    font-weight: 700 !important;
}}

/* ── Alerts / Info ── */
[data-testid="stAlert"] {{
    border-radius: 10px !important;
    border-left-width: 3px !important;
}}

/* ── Expanders ── */
[data-testid="stExpander"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    background: {CARD} !important;
}}

/* ── Divider ── */
hr {{ border-color: {BORDER} !important; }}

/* ── Page links ── */
[data-testid="stPageLink"] p {{
    font-size: 13px !important;
    color: {TXT2} !important;
    margin: 0 !important;
    padding: 0 !important;
}}
[data-testid="stPageLink"] {{ background: transparent !important; border: none !important; }}
</style>"""


def apply_custom_css() -> None:
    """Backward-compatible helper used by pages that expect this function."""
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# HELPERS HTML
# ---------------------------------------------------------------------------

def card(content_html: str, bg: str = CARD, border: str = BORDER,
         radius: str = "12px", padding: str = "16px", extra_style: str = "") -> str:
    return (f"<div style='background:{bg};border:1px solid {border};border-radius:{radius};"
            f"padding:{padding};{extra_style}'>{content_html}</div>")


def badge(text: str, color: str = ACCENT, bg: str = "", radius: str = "999px",
          size: str = "11px") -> str:
    bg = bg or f"{color}22"
    return (f"<span style='background:{bg};color:{color};border-radius:{radius};"
            f"padding:2px 8px;font-size:{size};font-weight:600;white-space:nowrap;'>{text}</span>")


def label_upper(text: str, color: str = TXT3) -> str:
    return (f"<p style='color:{color};font-size:10px;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:0.8px;margin:12px 0 4px;'>{text}</p>")


def dot(color: str, size: int = 6) -> str:
    return (f"<span style='display:inline-block;width:{size}px;height:{size}px;"
            f"border-radius:50%;background:{color};margin-right:7px;flex-shrink:0;'></span>")


def stat_row(items: list) -> str:
    """items = list of (label, value, color)"""
    parts = []
    for lbl, val, col in items:
        parts.append(
            f"<div style='text-align:center;'>"
            f"<div style='color:{col};font-size:1.1rem;font-weight:700;'>{val}</div>"
            f"<div style='color:{TXT3};font-size:10px;text-transform:uppercase;"
            f"letter-spacing:0.6px;margin-top:2px;'>{lbl}</div></div>")
    return (f"<div style='display:flex;gap:24px;justify-content:center;"
            f"padding:12px 0;'>" + "".join(parts) + "</div>")


def tipo_color(tipo: str) -> str:
    if not tipo:
        return DESCANSO
    t = str(tipo).lower()
    for k, v in TIPO_COLORS.items():
        if k in t:
            return v
    return TXT2
