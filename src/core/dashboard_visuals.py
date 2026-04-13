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
# HELPER: Convertir colores hex a rgba
# ============================================================================

def _hex_to_rgba(color, alpha=0.15):
    """Convierte color HEX a rgba(r,g,b,a), compatible con Plotly."""
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

    # #RGB -> #RRGGBB
    if len(hex_color) == 3:
        hex_color = "".join(ch * 2 for ch in hex_color)

    # #RRGGBBAA -> ignorar AA en favor de alpha explícito para Plotly
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
# 1. DONUT CHARTS (STRAIN vs RECOVERY)
# ============================================================================

def render_strain_recovery_donuts(recovery_score, acwr=None):
    """
    Renderiza dos anillos (donut charts) independientes:

    LEFT - Recovery (0-100): Estado fisiológico (HRV + sleep + stress + battery)
    RIGHT - Strain (0-100): Carga acumulada (ACWR normalizado)

    ACWR (Acute/Chronic Workload):
    - 0.8-1.3 = normal (strain 0-50%)
    - > 1.5 = muy alto (strain 100%)
    - < 0.8 = bajo (strain ~0%)
    """
    if acwr is None:
        acwr = 1.0

    acwr = float(acwr)
    recovery_score = max(0, min(100, recovery_score))

    # Normalizar ACWR a escala 0-100 para strain
    # ACWR 0.8 = 0%, ACWR 1.3 = 50%, ACWR 1.5 = 100%
    if acwr < 0.8:
        strain_score = 0
    elif acwr > 1.5:
        strain_score = 100
    else:
        # Mapeo lineal: 0.8->0%, 1.5->100%
        strain_score = ((acwr - 0.8) / (1.5 - 0.8)) * 100

    strain_score = max(0, min(100, strain_score))

    col1, col2 = st.columns(2)

    # RECOVERY DONUT
    with col1:
        fig_recovery = go.Figure(data=[go.Pie(
            labels=["Recovered", "Depleted"],
            values=[recovery_score, 100 - recovery_score],
            hole=0.75,
            marker=dict(colors=["#00C8C8", "#2a2a2a"]),
            textposition="inside",
            hoverinfo="label+percent",
        )])
        fig_recovery.update_layout(
            title="Recovery Status",
            height=280,
            showlegend=False,
            paper_bgcolor="#1A1A1A",
            plot_bgcolor="#1A1A1A",
            font=dict(color="#FFFFFF", size=11),
            margin=dict(l=0, r=0, t=25, b=0),
        )
        fig_recovery.add_annotation(
            text=f"{int(recovery_score)}%",
            x=0.5, y=0.5,
            font=dict(size=20, color="#00C8C8", family="Arial Black"),
            showarrow=False,
        )
        st.plotly_chart(fig_recovery, use_container_width=True, config={"displayModeBar": False})
        st.caption("HRV + sleep + stress + battery")

    # STRAIN DONUT
    with col2:
        fig_strain = go.Figure(data=[go.Pie(
            labels=["Accumulated", "Available"],
            values=[strain_score, 100 - strain_score],
            hole=0.75,
            marker=dict(colors=["#FF6B6B", "#2a2a2a"]),
            textposition="inside",
            hoverinfo="label+percent",
        )])
        fig_strain.update_layout(
            title="Strain Load",
            height=280,
            showlegend=False,
            paper_bgcolor="#1A1A1A",
            plot_bgcolor="#1A1A1A",
            font=dict(color="#FFFFFF", size=11),
            margin=dict(l=0, r=0, t=25, b=0),
        )
        fig_strain.add_annotation(
            text=f"{int(strain_score)}%",
            x=0.5, y=0.5,
            font=dict(size=20, color="#FF6B6B", family="Arial Black"),
            showarrow=False,
        )
        st.plotly_chart(fig_strain, use_container_width=True, config={"displayModeBar": False})
        st.caption(f"ACWR: {acwr:.2f} (Agudo/Crónico)")


# ============================================================================
# 2. HEATMAPS (Intensidad por día del mes)
# ============================================================================

def render_heatmap_training_intensity(usuario_id, conn, dias=60):
    """
    Renderiza calendario-heatmap de intensidad de entrenamiento (60 días).
    Visualización tipo: semana x día con escala de colores Bevel.
    Verde oscuro = bajo | Amarillo = moderado | Rojo intenso = alto
    """
    try:
        df = pd.read_sql_query(
            """SELECT fecha, training_effect_aerobico, training_effect_anaerobico
               FROM actividades_garmin
               WHERE usuario_id=? AND fecha >= date('now', '-' || ? || ' days')
               ORDER BY fecha ASC""",
            conn, params=(usuario_id, dias))

        if df.empty:
            st.caption("Sin datos de entrenamiento en los últimos 60 días.")
            return

        df["fecha"] = pd.to_datetime(df["fecha"])
        df["intensity"] = (df["training_effect_aerobico"].fillna(0) +
                          df["training_effect_anaerobico"].fillna(0)) / 2

        # Crear matriz: semana x día
        df["year_week"] = df["fecha"].dt.strftime("%Y-W%U")
        df["day_of_week"] = df["fecha"].dt.day_name()
        df["day_num"] = df["fecha"].dt.dayofweek  # 0=Lunes, 6=Domingo

        heatmap_data = df.pivot_table(
            values="intensity",
            index="year_week",
            columns="day_num",
            aggfunc="max",
            fill_value=0
        )

        # Normalizar intensidad a 0-1 para colorscale
        max_intensity = heatmap_data.max().max() or 1
        heatmap_normalized = heatmap_data / max_intensity

        # Escala personalizada Bevel: Verde oscuro → Amarillo → Rojo
        custom_colorscale = [
            [0.0, "#0D3D2C"],      # Verde muy oscuro (sin entrenar)
            [0.2, "#1A6B4F"],      # Verde oscuro
            [0.4, "#4CAF50"],      # Verde
            [0.6, "#FFE082"],      # Amarillo (moderado)
            [0.8, "#FF8A65"],      # Naranja
            [1.0, "#FF4444"],      # Rojo incandescente (muy intenso)
        ]

        fig = go.Figure(data=go.Heatmap(
            z=heatmap_normalized.values,
            x=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
            y=[f"Sem {i+1}" for i in range(len(heatmap_normalized))],
            colorscale=custom_colorscale,
            hovertemplate="<b>%{y} - %{x}</b><br>Intensidad: %{z:.0%}<extra></extra>",
            colorbar=dict(
                title="Intensidad",
                thickness=15,
                len=0.7,
            ),
            showscale=True,
        ))

        fig.update_layout(
            title="📅 Mapa de Calor - Intensidad de Entrenamientos (últimos 60 días)",
            title_font_size=14,
            height=400,
            paper_bgcolor="#1A1A1A",
            plot_bgcolor="#1A1A1A",
            font=dict(color="#FFFFFF", size=10),
            xaxis_title="Día de la semana",
            xaxis_title_font_size=11,
            yaxis_title="Semana",
            yaxis_title_font_size=11,
            margin=dict(l=60, r=80, t=50, b=50),
            xaxis=dict(side="bottom"),
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Legend
        st.caption(
            "🟩 **Verde**: bajo | 🟨 **Amarillo**: moderado | 🟥 **Rojo**: alto"
        )

    except Exception as e:
        st.error(f"Error al renderizar heatmap: {e}")
        st.caption("Intenta sincronizar datos desde Garmin en la sección de **Garmin**")


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

    # Crear sparkline con Plotly (más compacto)
    # Usar rgba para fillcolor
    line_color = _hex_to_rgba(color, alpha=1)
    fillcolor = _hex_to_rgba(color, alpha=0.12)

    fig = go.Figure(data=[
        go.Scatter(
            y=clean_vals,
            mode="lines",
            line=dict(color=line_color, width=1.5),
            fill="tozeroy",
            fillcolor=fillcolor,
            hoverinfo="skip",
            showlegend=False,
        )
    ])
    fig.update_layout(
        height=50,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.markdown(f"**{label}**: `{value_text}`")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


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
