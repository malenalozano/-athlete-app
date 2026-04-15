"""
src/core/dashboard_visuals.py
Visualizaciones avanzadas para el dashboard: donut charts, sparklines, tarjeta RHR.
Estética actualizada: dark #0d1117, acentos lime/cyan.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np


# ============================================================================
# HELPER: Convertir colores hex a rgba
# ============================================================================

def _hex_to_rgba(color, alpha=0.15):
    if not isinstance(color, str):
        return f"rgba(201, 255, 0, {alpha})"
    color = color.strip()
    if color.startswith("rgba("):
        if alpha is None:
            return color
        body = color[5:-1]
        parts = [p.strip() for p in body.split(",")]
        if len(parts) >= 3:
            return f"rgba({parts[0]}, {parts[1]}, {parts[2]}, {alpha})"
        return f"rgba(201, 255, 0, {alpha})"
    if color.startswith("rgb("):
        body = color[4:-1]
        parts = [p.strip() for p in body.split(",")]
        if len(parts) >= 3:
            a = alpha if alpha is not None else 1
            return f"rgba({parts[0]}, {parts[1]}, {parts[2]}, {a})"
        return f"rgba(201, 255, 0, {alpha})"
    hex_color = color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = "".join(ch * 2 for ch in hex_color)
    if len(hex_color) == 8:
        hex_color = hex_color[:6]
    if len(hex_color) != 6:
        return f"rgba(201, 255, 0, {alpha})"
    try:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return f"rgba(201, 255, 0, {alpha})"
    a = alpha if alpha is not None else 1
    return f"rgba({r}, {g}, {b}, {a})"


# ============================================================================
# 1. DONUT CHARTS (STRAIN vs RECOVERY) — nueva estética
# ============================================================================

def render_strain_recovery_donuts(recovery_score, acwr=None):
    """
    Renderiza dos anillos (donut charts) con la nueva estética dark/lime/cyan.
    LEFT  - Recovery Status (HRV + sleep + stress + battery)
    RIGHT - Strain Load (ACWR normalizado)
    """
    if acwr is None:
        acwr = 1.0
    acwr = float(acwr)
    recovery_score = max(0, min(100, recovery_score))

    if acwr < 0.8:
        strain_score = 0
    elif acwr > 1.5:
        strain_score = 100
    else:
        strain_score = ((acwr - 0.8) / (1.5 - 0.8)) * 100
    strain_score = max(0, min(100, strain_score))

    # Colores según valores
    rec_color   = "#00db81" if recovery_score >= 70 else ("#f59e0b" if recovery_score >= 45 else "#ef4444")
    strain_color = "#ef4444" if strain_score >= 75 else ("#f59e0b" if strain_score >= 50 else "#00D4FF")

    col1, col2 = st.columns(2, gap="small")

    _BG = "rgba(0,0,0,0)"  # transparente — la tarjeta exterior ya tiene fondo

    show_recovery_info = st.session_state.get("show_recovery_donut_info", False)
    show_strain_info = st.session_state.get("show_strain_donut_info", False)

    # RECOVERY DONUT
    with col1:
        fig_rec = go.Figure(data=[go.Pie(
            labels=["Recovery", "Depleted"],
            values=[recovery_score, 100 - recovery_score],
            hole=0.78,
            marker=dict(colors=[rec_color, "rgba(48,54,61,0.6)"], line=dict(width=0)),
            textposition="inside",
            hoverinfo="skip",
            showlegend=False,
        )])
        fig_rec.update_layout(
            height=200,
            showlegend=False,
            paper_bgcolor=_BG,
            plot_bgcolor=_BG,
            font=dict(color="#e6edf3", size=11, family="Inter, sans-serif"),
            margin=dict(l=10, r=10, t=10, b=10),
        )
        fig_rec.add_annotation(
            text=f"<b>{int(recovery_score)}%</b>",
            x=0.5, y=0.55,
            font=dict(size=22, color=rec_color, family="Inter, sans-serif"),
            showarrow=False,
        )
        fig_rec.add_annotation(
            text="recovery",
            x=0.5, y=0.35,
            font=dict(size=10, color="#8B949E", family="Inter, sans-serif"),
            showarrow=False,
        )
        st.plotly_chart(fig_rec, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f"<div style='text-align:center;margin-top:-12px;'>"
            f"<span style='font-size:0.75rem;font-weight:700;color:{rec_color};text-transform:uppercase;"
            f"letter-spacing:0.08em;'>Recovery Status</span><br>"
            f"<span style='font-size:0.72rem;color:#8B949E;'>HRV · sueño · estrés · batería</span></div>",
            unsafe_allow_html=True)

        if st.button("Que significa este numero", key="btn_recovery_donut_info", use_container_width=True):
            st.session_state["show_recovery_donut_info"] = not show_recovery_info

        if st.session_state.get("show_recovery_donut_info", False):
            st.info(
                "Recovery (0-100): indica tu nivel de recuperacion para hoy.\n"
                "- Alto (>=70): buena disponibilidad para entrenar.\n"
                "- Medio (50-69): entrena con control.\n"
                "- Bajo (<50): prioriza recuperacion.\n"
                "Se calcula con HRV, sueno, estres, body battery y carga reciente."
            )

    # STRAIN DONUT
    with col2:
        fig_str = go.Figure(data=[go.Pie(
            labels=["Strain", "Available"],
            values=[strain_score, 100 - strain_score],
            hole=0.78,
            marker=dict(colors=[strain_color, "rgba(48,54,61,0.6)"], line=dict(width=0)),
            textposition="inside",
            hoverinfo="skip",
            showlegend=False,
        )])
        fig_str.update_layout(
            height=200,
            showlegend=False,
            paper_bgcolor=_BG,
            plot_bgcolor=_BG,
            font=dict(color="#e6edf3", size=11, family="Inter, sans-serif"),
            margin=dict(l=10, r=10, t=10, b=10),
        )
        fig_str.add_annotation(
            text=f"<b>{int(strain_score)}%</b>",
            x=0.5, y=0.55,
            font=dict(size=22, color=strain_color, family="Inter, sans-serif"),
            showarrow=False,
        )
        fig_str.add_annotation(
            text="strain",
            x=0.5, y=0.35,
            font=dict(size=10, color="#8B949E", family="Inter, sans-serif"),
            showarrow=False,
        )
        st.plotly_chart(fig_str, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f"<div style='text-align:center;margin-top:-12px;'>"
            f"<span style='font-size:0.75rem;font-weight:700;color:{strain_color};text-transform:uppercase;"
            f"letter-spacing:0.08em;'>Strain Load</span><br>"
            f"<span style='font-size:0.72rem;color:#8B949E;'>ACWR {acwr:.2f} (agudo/crónico)</span></div>",
            unsafe_allow_html=True)

        if st.button("Que significa este numero", key="btn_strain_donut_info", use_container_width=True):
            st.session_state["show_strain_donut_info"] = not show_strain_info

        if st.session_state.get("show_strain_donut_info", False):
            st.info(
                "Strain (0-100): representa la carga de entrenamiento acumulada.\n"
                "Se deriva del ACWR (carga aguda/carga cronica).\n"
                "- ACWR ~0.8-1.3: zona razonable.\n"
                "- ACWR >1.3: aumenta el riesgo por fatiga.\n"
                "- ACWR >1.5: riesgo alto de sobrecarga."
            )


# ============================================================================
# 2. TARJETA RHR — nueva estética
# ============================================================================

def render_rhr_card(usuario_id, conn):
    try:
        df_rhr = pd.read_sql_query(
            """SELECT fecha, fc_reposo FROM datos_biometricos_premium
               WHERE usuario_id=? AND fecha >= date('now', '-7 days')
               AND fc_reposo IS NOT NULL
               ORDER BY fecha DESC""",
            conn, params=(usuario_id,))

        if df_rhr.empty:
            return

        rhr_today = df_rhr.iloc[0]["fc_reposo"]
        rhr_media_7d = df_rhr["fc_reposo"].mean()

        if rhr_today is None or rhr_media_7d is None:
            return

        umbral_verde = rhr_media_7d + 1
        umbral_rojo  = rhr_media_7d + 4

        if rhr_today <= umbral_verde:
            color  = "#00db81"
            status = "Óptimo"
            interp = "RHR dentro del rango normal. Recuperación correcta."
        elif rhr_today <= umbral_rojo:
            color  = "#f59e0b"
            status = "Elevado"
            interp = "RHR levemente elevado. Monitorea la recuperación hoy."
        else:
            color  = "#ef4444"
            status = "⚠️ Muy elevado"
            interp = "Fatiga sistémica detectada. Considera reducir la intensidad."

        delta = int(rhr_today) - int(rhr_media_7d)
        delta_str = f"+{delta}" if delta > 0 else str(delta)

        st.markdown(f"""
<div style="background:linear-gradient(135deg,#0f1724 0%,#101928 100%);border:1px solid {color}44;
border-radius:14px;padding:1rem 1.2rem;display:flex;align-items:center;gap:1.2rem;margin-bottom:0.5rem;">
  <div style="text-align:center;flex-shrink:0;">
    <div style="color:{color};font-size:1.75rem;font-weight:900;line-height:1;">{int(rhr_today)}</div>
    <div style="color:#8B949E;font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;">bpm</div>
  </div>
  <div style="flex:1;border-left:1px solid rgba(255,255,255,0.06);padding-left:1rem;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
      <span style="color:white;font-size:0.82rem;font-weight:700;">FC Reposo</span>
      <span style="color:{color};background:rgba(0,0,0,0.3);border:1px solid {color}55;border-radius:9999px;
            font-size:0.7rem;font-weight:700;padding:2px 8px;">{status}</span>
    </div>
    <div style="color:#8B949E;font-size:0.75rem;margin-bottom:4px;">{interp}</div>
    <div style="color:#6b7280;font-size:0.7rem;">Media 7d: <span style="color:#9ca3af;">{rhr_media_7d:.0f} bpm</span>
    &nbsp;·&nbsp; Delta: <span style="color:{color};">{delta_str} bpm</span></div>
  </div>
</div>""", unsafe_allow_html=True)

    except Exception as e:
        st.caption(f"Sin datos de RHR: {e}")


# ============================================================================
# 3. SPARKLINES — nueva estética
# ============================================================================

def render_sparkline_metric(label, values, color="#C9FF00", unit=""):
    if not values or all(v is None for v in values):
        return
    clean_vals = [v for v in values if v is not None]
    if not clean_vals:
        return

    current = clean_vals[-1]
    value_text = f"{current:.1f}{unit}" if isinstance(current, (int, float)) else str(current)

    def _sanitize(c, a=1):
        if isinstance(c, str) and c.startswith("#") and len(c) == 9:
            return _hex_to_rgba(c, alpha=a)
        return c

    color = _sanitize(color)
    line_color  = _hex_to_rgba(color, alpha=1)
    fillcolor   = _hex_to_rgba(color, alpha=0.12)

    fig = go.Figure(data=[go.Scatter(
        y=clean_vals,
        mode="lines",
        line=dict(color=line_color, width=1.5),
        fill="tozeroy",
        fillcolor=fillcolor,
        hoverinfo="skip",
        showlegend=False,
    )])
    fig.update_layout(
        height=44,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2px;'>"
        f"<span style='font-size:0.72rem;color:#8B949E;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:.06em;'>{label}</span>"
        f"<span style='font-size:0.88rem;font-weight:800;color:{line_color};'>{value_text}</span></div>",
        unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_metrics_sparklines(usuario_id, conn):
    try:
        df = pd.read_sql_query(
            """SELECT fecha, hrv_ms, sleep_score, estres_medio,
                      body_battery_max, body_battery_min
               FROM datos_biometricos_premium
               WHERE usuario_id=? AND fecha >= date('now', '-7 days')
               ORDER BY fecha ASC""",
            conn, params=(usuario_id,))

        if df.empty:
            st.caption("Sin datos de tendencias (últimos 7 días).")
            return

        col1, col2 = st.columns(2, gap="small")
        with col1:
            render_sparkline_metric("HRV",         df["hrv_ms"].tolist(),        color="#00D4FF", unit=" ms")
            render_sparkline_metric("Sleep Score",  df["sleep_score"].tolist(),   color="#C9FF00", unit="/100")
        with col2:
            render_sparkline_metric("Estrés",       df["estres_medio"].tolist(),  color="#f97316", unit="/100")
            battery = [
                (df["body_battery_max"].iloc[i] + df["body_battery_min"].iloc[i]) / 2
                if pd.notna(df["body_battery_max"].iloc[i]) else None
                for i in range(len(df))
            ]
            render_sparkline_metric("Body Battery", battery, color="#a855f7", unit="%")

    except Exception as e:
        st.caption(f"Sin datos de tendencias: {e}")


# ============================================================================
# 4. HEATMAP — eliminado por petición de usuario
# ============================================================================
def render_heatmap_training_intensity(usuario_id, conn, dias=60):
    """Eliminado — conservado por compatibilidad pero no renderiza nada."""
    pass
