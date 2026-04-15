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
button[kind="primary"],
.stFormSubmitButton > button,
form button[type="submit"] {{
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
[data-testid="stMetric"] {{
    background: linear-gradient(180deg, rgba(22,27,34,0.96), rgba(20,25,31,0.96)) !important;
    border: 1px solid {BORDER_H} !important;
    border-radius: 14px !important;
    padding: 12px 14px !important;
    box-shadow: 0 1px 0 rgba(255,255,255,0.03), inset 0 1px 0 rgba(255,255,255,0.02) !important;
}}
[data-testid="stMetric"] > div {{
    padding: 0 !important;
}}
[data-testid="stMetric"] label {{
    color: {TXT3} !important;
    font-size: 10px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}}
[data-testid="stMetric"] [data-testid="stMetricDelta"] {{
    font-size: 0.8rem !important;
    font-weight: 700 !important;
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

def format_hours(horas_decimales) -> str:
    """Convierte horas decimales a formato legible: 47min, 1h 7min, etc."""
    if horas_decimales is None or horas_decimales == "Pendiente Garmin":
        return horas_decimales
    try:
        h = float(horas_decimales)
        if h <= 0:
            return "—"
        hours = int(h)
        minutes = int(round((h - hours) * 60))
        # Si redondeó a 60 minutos, sumar a horas
        if minutes == 60:
            hours += 1
            minutes = 0
        if hours == 0:
            return f"{minutes}min"
        elif minutes == 0:
            return f"{hours}h"
        else:
            return f"{hours}h {minutes}min"
    except (ValueError, TypeError):
        return str(horas_decimales)


def analizar_ultima_noche_sueno(score: float, horas_totales: float, profundo_min: float,
                                rem_min: float, vigilia_min: float, estres_medio: float,
                                genero: str = "mujer") -> str:
    """
    Analiza la última noche de sueño y genera un comentario personalizado.
    genera: "hombre" o "mujer"
    """
    if score is None or score == 0:
        return ""

    es_mujer = str(genero).lower() in ("mujer", "woman", "f", "female")
    score_int = int(score)

    # Criterios según sexo
    if es_mujer:
        profundo_min_ok, profundo_max_ok = 90, 160
        rem_min_ok, rem_max_ok = 105, 155
        vigilia_max_ok = 20
        horas_min_ok = 8.5
        estres_max_ok = 15
        icono = "👩"
    else:
        profundo_min_ok, profundo_max_ok = 80, 140
        rem_min_ok, rem_max_ok = 100, 150
        vigilia_max_ok = 20
        horas_min_ok = 7.5
        estres_max_ok = 15
        icono = "🧔"

    # Análisis de factores limitantes
    problemas = []

    # Estrés (el "killer")
    if estres_medio > estres_max_ok:
        problemas.append(("estrés alto", f"tu estrés fue {estres_medio:.0f} (objetivo <{estres_max_ok})"))

    # Vigilia/Inquietud
    if vigilia_min > vigilia_max_ok:
        problemas.append(("vigilia alta", f"tuviste {vigilia_min:.0f} min de vigilia (objetivo <{vigilia_max_ok} min)"))

    # REM
    if rem_min < rem_min_ok:
        problemas.append(("falta de REM", f"necesitas {rem_min_ok}-{rem_max_ok} min, tienes {rem_min:.0f} min"))

    # Profundo
    if profundo_min < profundo_min_ok:
        problemas.append(("falta de sueño profundo", f"necesitas {profundo_min_ok}-{profundo_max_ok} min, tienes {profundo_min:.0f} min"))

    # Horas totales
    if horas_totales < horas_min_ok:
        problemas.append(("pocas horas", f"tienes {format_hours(horas_totales)}, objetivo {format_hours(horas_min_ok)}+"))

    # Generar comentario
    if score_int >= 90:
        emoji_score = "🏆"
        if problemas:
            razon = problemas[0][1]
            return f"{emoji_score} <b>Excelente:</b> {score_int}/100 — Casi perfecto. Aunque {razon}."
        else:
            return f"{emoji_score} <b>Excelente:</b> {score_int}/100 — Noche perfecta de recuperación."

    elif score_int >= 70:
        emoji_score = "👍"
        if problemas:
            razon = problemas[0][1]
            return f"{emoji_score} <b>Bueno:</b> {score_int}/100 — {razon.capitalize()}."
        else:
            return f"{emoji_score} <b>Bueno:</b> {score_int}/100 — Noche sólida de recuperación."

    elif score_int >= 50:
        emoji_score = "⚠️"
        if problemas:
            razon = problemas[0][1]
            return f"{emoji_score} <b>Normal:</b> {score_int}/100 — {razon.capitalize()}."
        else:
            return f"{emoji_score} <b>Normal:</b> {score_int}/100 — Hay espacio para mejorar."

    else:
        emoji_score = "⛔"
        if problemas:
            razon = problemas[0][1]
            return f"{emoji_score} <b>Pobre:</b> {score_int}/100 — {razon.capitalize()}. Hay que trabajar en recuperación."
        else:
            return f"{emoji_score} <b>Pobre:</b> {score_int}/100 — Necesitas mejorar significativamente tu sueño."
