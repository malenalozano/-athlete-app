"""
src/core/dashboard_visuals.py
Visualizaciones avanzadas para el dashboard: donut charts, heatmaps, sparklines, tarjeta RHR.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np


# ============================================================================
# 1. DONUT CHARTS (STRAIN vs RECOVERY)
# ============================================================================

def render_strain_recovery_donuts(recovery_score, strain_score=None):
    """
    Renderiza dos anillos (donut charts) para Recovery y Strain.
    recovery_score: 0-100
    strain_score: 0-100 (si es None, calcula como 100 - recovery_score)
    """
    if strain_score is None:
        strain_score = 100 - recovery_score

    # Asegurar que están en rango 0-100
    recovery_score = max(0, min(100, recovery_score))
    strain_score = max(0, min(100, strain_score))

    col1, col2 = st.columns(2)

    # RECOVERY DONUT
    with col1:
        fig_recovery = go.Figure(data=[go.Pie(
            labels=["Recovery", "Remaining"],
            values=[recovery_score, 100 - recovery_score],
            hole=0.7,
            marker=dict(colors=["#00C8C8", "#2a2a2a"]),
            textposition="inside",
            hoverinfo="label+percent",
        )])
        fig_recovery.update_layout(
            title="Recovery Status",
            height=300,
            showlegend=False,
            paper_bgcolor="#1A1A1A",
            plot_bgcolor="#1A1A1A",
            font=dict(color="#FFFFFF", size=12),
            margin=dict(l=0, r=0, t=30, b=0),
        )
        fig_recovery.add_annotation(
            text=f"{int(recovery_score)}%",
            x=0.5, y=0.5,
            font=dict(size=24, color="#00C8C8"),
            showarrow=False,
        )
        st.plotly_chart(fig_recovery, use_container_width=True, config={"displayModeBar": False})

    # STRAIN DONUT
    with col2:
        fig_strain = go.Figure(data=[go.Pie(
            labels=["Strain", "Remaining"],
            values=[strain_score, 100 - strain_score],
            hole=0.7,
            marker=dict(colors=["#FF6B6B", "#2a2a2a"]),
            textposition="inside",
            hoverinfo="label+percent",
        )])
        fig_strain.update_layout(
            title="Strain Status",
            height=300,
            showlegend=False,
            paper_bgcolor="#1A1A1A",
            plot_bgcolor="#1A1A1A",
            font=dict(color="#FFFFFF", size=12),
            margin=dict(l=0, r=0, t=30, b=0),
        )
        fig_strain.add_annotation(
            text=f"{int(strain_score)}%",
            x=0.5, y=0.5,
            font=dict(size=24, color="#FF6B6B"),
            showarrow=False,
        )
        st.plotly_chart(fig_strain, use_container_width=True, config={"displayModeBar": False})


# ============================================================================
# 2. HEATMAPS (Intensidad por día del mes)
# ============================================================================

def render_heatmap_training_intensity(usuario_id, conn, dias=60):
    """
    Renderiza heatmap mostrando intensidad de entrenamiento por día.
    Días más oscuros = entrenamientos más intensos.
    """
    try:
        df = pd.read_sql_query(
            """SELECT fecha, training_effect_aerobico, training_effect_anaerobico
               FROM actividades_garmin
               WHERE usuario_id=? AND fecha >= date('now', '-' || ? || ' days')
               ORDER BY fecha DESC""",
            conn, params=(usuario_id, dias))

        if df.empty:
            st.caption("Sin datos de entrenamiento en los últimos 60 días.")
            return

        df["fecha"] = pd.to_datetime(df["fecha"])
        df["week"] = df["fecha"].dt.isocalendar().week
        df["day"] = df["fecha"].dt.day_name()
        df["intensity"] = (df["training_effect_aerobico"].fillna(0) +
                          df["training_effect_anaerobico"].fillna(0)) / 2

        # Crear matriz semana x día
        df["day_num"] = df["fecha"].dt.dayofweek  # 0=Lunes, 6=Domingo
        heatmap_pivot = df.pivot_table(
            values="intensity",
            index="week",
            columns="day_num",
            aggfunc="max"
        )

        fig = go.Figure(data=go.Heatmap(
            z=heatmap_pivot.values,
            x=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
            y=heatmap_pivot.index,
            colorscale="RdYlGn",
            hovertemplate="Semana %{y}, %{x}<br>Intensidad: %{z:.1f}<extra></extra>",
        ))
        fig.update_layout(
            title="Intensidad de Entrenamiento (últimos 60 días)",
            height=400,
            paper_bgcolor="#1A1A1A",
            plot_bgcolor="#1A1A1A",
            font=dict(color="#FFFFFF"),
            xaxis_title="Día de la semana",
            yaxis_title="Semana",
            margin=dict(l=0, r=0, t=30, b=0),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    except Exception as e:
        st.caption(f"Error al renderizar heatmap: {e}")


# ============================================================================
# 3. SPARKLINES (Mini gráficos de tendencia 7 días)
# ============================================================================

def render_sparkline_metric(label, values, color="#C9FF00", unit=""):
    """
    Renderiza una métrica con sparkline (mini gráfico debajo).
    values: lista de valores de los últimos 7 días (ordenados ascendente en tiempo)
    """
    if not values or all(v is None for v in values):
        st.metric(label, "Sin datos")
        return

    # Filtrar None
    clean_vals = [v for v in values if v is not None]
    if not clean_vals:
        st.metric(label, "Sin datos")
        return

    current = clean_vals[-1] if clean_vals else 0
    value_text = f"{current:.1f}{unit}" if isinstance(current, (int, float)) else str(current)

    # Crear sparkline con Plotly
    fig = go.Figure(data=[
        go.Scatter(
            y=clean_vals,
            mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=color.replace(")", ", 0.1)") if "rgb" in color else color + "20",
            hoverinfo="skip",
            showlegend=False,
        )
    ])
    fig.update_layout(
        height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"**{label}**")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with col2:
        st.metric(label, value_text)


# ============================================================================
# 4. TARJETA RHR (Resting Heart Rate) - BEVEL STYLE
# ============================================================================

def render_rhr_card(usuario_id, conn):
    """
    Renderiza tarjeta oscura de RHR con:
    - RHR de hoy vs promedio 7 días
    - Color: Verde Neón si bien, Rojo si alto
    - Interpretación: Aviso de fatiga si RHR muy alto
    """
    try:
        # Obtener RHR últimos 7 días
        df_rhr = pd.read_sql_query(
            """SELECT fecha, fc_reposo FROM datos_biometricos_premium
               WHERE usuario_id=? AND fecha >= date('now', '-7 days')
               AND fc_reposo IS NOT NULL
               ORDER BY fecha DESC""",
            conn, params=(usuario_id,))

        if df_rhr.empty:
            st.caption("Sin datos de RHR (fc_reposo) disponibles.")
            return

        rhr_today = df_rhr.iloc[0]["fc_reposo"] if len(df_rhr) > 0 else None
        rhr_media_7d = df_rhr["fc_reposo"].mean() if len(df_rhr) > 0 else None

        if rhr_today is None or rhr_media_7d is None:
            st.caption("Datos de RHR incompletos.")
            return

        # Lógica de colores
        umbral_verde = rhr_media_7d + 1
        umbral_rojo = rhr_media_7d + 4

        if rhr_today <= umbral_verde:
            color = "#C9FF00"  # Verde Neón
            status = "Excelente"
            interpretation = "Tu RHR está dentro del rango óptimo. Recuperación normal."
        elif rhr_today <= umbral_rojo:
            color = "#FFB700"  # Amarillo/Naranja
            status = "Elevado"
            interpretation = "Tu RHR está levemente elevado. Monitorea la recuperación."
        else:
            color = "#FF4444"  # Rojo de alerta
            status = "Muy elevado"
            interpretation = "⚠️ Detectada fatiga sistémica. Considera reducir la intensidad hoy."

        # Renderizar tarjeta
        st.markdown(f"""
        <div style="
            background-color: #1A1A1A;
            border: 2px solid {color};
            border-radius: 12px;
            padding: 20px;
            margin: 10px 0;
        ">
            <div style="color: #FFFFFF; font-size: 14px; margin-bottom: 10px;">
                <strong>Resting Heart Rate (RHR)</strong>
            </div>
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            ">
                <div>
                    <div style="color: {color}; font-size: 32px; font-weight: bold;">
                        {int(rhr_today)} bpm
                    </div>
                    <div style="color: #AAAAAA; font-size: 12px;">
                        Promedio 7d: {rhr_media_7d:.0f} bpm
                    </div>
                </div>
                <div style="
                    background-color: {color}20;
                    border-radius: 8px;
                    padding: 10px 15px;
                    text-align: center;
                ">
                    <div style="color: {color}; font-size: 24px;">📊</div>
                    <div style="color: {color}; font-size: 12px; font-weight: bold;">
                        {status}
                    </div>
                </div>
            </div>
            <div style="
                background-color: #2a2a2a;
                border-radius: 8px;
                padding: 12px;
                color: #CCCCCC;
                font-size: 13px;
                border-left: 3px solid {color};
            ">
                {interpretation}
            </div>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.caption(f"Error al renderizar RHR: {e}")


# ============================================================================
# 5. SPARKLINES PARA 7 DÍAS (HRV, Sleep, Stress, etc.)
# ============================================================================

def render_metrics_sparklines(usuario_id, conn):
    """
    Renderiza sparklines para HRV, Sleep, Stress, Body Battery (últimos 7 días).
    """
    try:
        df = pd.read_sql_query(
            """SELECT fecha, hrv_ms, sleep_score, estres_medio,
                      body_battery_max, body_battery_min
               FROM datos_biometricos_premium
               WHERE usuario_id=? AND fecha >= date('now', '-7 days')
               ORDER BY fecha ASC""",
            conn, params=(usuario_id,))

        if df.empty:
            st.caption("Sin datos de los últimos 7 días.")
            return

        st.subheader("📊 Tendencias (últimos 7 días)")

        col1, col2 = st.columns(2)

        with col1:
            hrv_vals = df["hrv_ms"].tolist()
            render_sparkline_metric("HRV", hrv_vals, color="#00C8C8", unit=" ms")

            sleep_vals = df["sleep_score"].tolist()
            render_sparkline_metric("Sleep Score", sleep_vals, color="#C9FF00", unit="/100")

        with col2:
            stress_vals = df["estres_medio"].tolist()
            render_sparkline_metric("Stress", stress_vals, color="#FF6B6B", unit="/100")

            battery_vals = [
                (df["body_battery_max"].iloc[i] + df["body_battery_min"].iloc[i]) / 2
                if pd.notna(df["body_battery_max"].iloc[i]) else None
                for i in range(len(df))
            ]
            render_sparkline_metric("Body Battery", battery_vals, color="#FFB700", unit="%")

    except Exception as e:
        st.caption(f"Error al renderizar sparklines: {e}")
