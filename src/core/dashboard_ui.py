"""
src/core/dashboard_ui.py
Componentes de UI del Dashboard: checkpoints, ciclo, macrociclo, tema Plotly.
Extraído de src/app_legacy.py.
"""

import pandas as pd
import streamlit as st
from datetime import datetime, date

from src.db.db_manager import get_db_connection
from src.core.ciclo_helpers import predecir_fases_ciclo


def aplicar_tema_plotly(fig, titulo=None):
    """Unifica el estilo de gráficos con la paleta Athlete (verde/lima)."""
    fig.update_layout(
        paper_bgcolor="#0c2922", plot_bgcolor="#103128",
        font=dict(color="#d8e9db"), title_font=dict(color="#e7f6b7", size=18),
        legend=dict(bgcolor="rgba(12,41,34,0.65)", bordercolor="rgba(217,242,15,0.26)",
                    borderwidth=1, font=dict(color="#d8e9db")),
        margin=dict(l=20, r=20, t=56, b=20),
        xaxis=dict(gridcolor="rgba(217,242,15,0.12)", zerolinecolor="rgba(217,242,15,0.18)", linecolor="rgba(217,242,15,0.20)"),
        yaxis=dict(gridcolor="rgba(217,242,15,0.12)", zerolinecolor="rgba(217,242,15,0.18)", linecolor="rgba(217,242,15,0.20)"),
    )
    if titulo:
        fig.update_layout(title=titulo)
    return fig


def render_checkpoints_moderno(df_check, objetivo_txt="actual"):
    if df_check is None or df_check.empty:
        st.markdown("<div style='color:#8B949E;font-style:italic;'>Aún no hay checkpoints disponibles para este objetivo.</div>", unsafe_allow_html=True)
        return

    st.markdown(
        f"<div style='display:flex;align-items:center;gap:8px;margin:8px 0 10px;font-size:0.98rem;font-weight:800;color:#FFFFFF;'>"
        f"Objetivos checkpoints para {objetivo_txt}</div>",
        unsafe_allow_html=True,
    )
    cards = list(df_check.to_dict(orient="records"))
    for i in range(0, len(cards), 3):
        cols = st.columns(3)
        for j, row in enumerate(cards[i:i+3]):
            hecho = str(row.get("estado", "")) in ("Hecho", "Completado")
            badge_style = (
                "background:#C9FF00;color:#0E1117;border:1px solid #C9FF00;font-weight:700;font-size:0.74rem;border-radius:999px;padding:3px 9px;"
                if hecho else
                "background:transparent;color:#D29922;border:1px solid #D29922;font-weight:700;font-size:0.74rem;border-radius:999px;padding:3px 9px;"
            )
            with cols[j]:
                st.markdown(
                    f"<div style='background:#131D2B;border:1px solid rgba(201,255,0,0.42);border-left:4px solid #7FB300;"
                    f"border-radius:14px;padding:10px 12px;min-height:96px;margin-bottom:8px;'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:8px;'>"
                    f"<div style='font-weight:800;color:#FFFFFF;font-size:0.98rem;line-height:1.2;max-width:72%;'>{row.get('checkpoint','-')}</div>"
                    f"<span style='display:inline-block;{badge_style}'>{'Completado' if hecho else 'Pendiente'}</span>"
                    f"</div>"
                    f"<div style='font-size:0.79rem;color:#8B949E;margin-top:6px;line-height:1.35;'>{row.get('detalle','')}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )


@st.cache_data(ttl=120)
def obtener_estado_ciclo_malena():
    """Estado actual del ciclo de Malena (usuario_id=1) para mostrar en el dashboard de Dani."""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            "SELECT fecha, fase_ciclo, fatiga_subjetiva, dolor_notas FROM diario_fisiologia WHERE usuario_id = 1 ORDER BY fecha",
            conn,
        )
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    if df.empty:
        return None
    df_valid = df[df["fase_ciclo"] != "No Aplica"].copy()
    if df_valid.empty:
        return None

    ciclo_df, _ = predecir_fases_ciclo(df_valid, horizonte_dias=40)
    hoy = datetime.now().date()
    fila_hoy = ciclo_df[ciclo_df["fecha"] == hoy]
    if fila_hoy.empty:
        fila_hoy = ciclo_df[ciclo_df["fecha"] >= hoy].head(1)
    if fila_hoy.empty:
        return None

    fase = fila_hoy.iloc[0]["fase_ciclo"]
    origen = fila_hoy.iloc[0]["origen"]
    proximas = ciclo_df[(ciclo_df["fecha"] >= hoy) & (ciclo_df["fase_ciclo"] == "Fase Folicular")].head(2)
    proxima_regla = proximas.iloc[0]["fecha"] if not proximas.empty and proximas.iloc[0]["fecha"] >= hoy else None

    sugerencias = {
        "Fase Folicular": ["Buen momento para proponer planes, viajes o entrenos más exigentes juntos.", "Las conversaciones importantes suelen ir mejor en esta fase."],
        "Fase Ovulatoria": ["Buena ventana para citas, conexión y refuerzo positivo.", "Si entrenáis juntos, suele tolerar bien intensidad y sesiones sociales."],
        "Fase Lútea": ["Prioriza paciencia, validación emocional y menos fricción innecesaria.", "Suman mucho los mimos prácticos: cena reconfortante, masaje, bajar carga social."],
    }
    return {
        "fase": fase, "origen": origen, "proxima_regla": proxima_regla,
        "consejos": sugerencias.get(fase, ["Acompaña y ajusta el contexto según cómo se encuentre ese día."]),
    }


def render_macrociclo():
    """Grid 5 fases del macrociclo + barra global de progreso hacia el maratón."""
    from src.plan.reglas import obtener_fase_macrociclo

    fase_actual = obtener_fase_macrociclo(datetime.now())
    hoy = date.today()
    inicio_macro = date(2026, 4, 6)
    objetivo     = date(2027, 2, 21)
    total_dias   = (objetivo - inicio_macro).days
    pct_total    = max(0, min(100, int((hoy - inicio_macro).days / total_dias * 100)))

    fases = [
        {"nombre": "Acondicionamiento", "meses": "Abr–May", "color": "#a3e635",
         "inicio": date(2026, 4, 6), "fin": date(2026, 5, 31),
         "desc": "Base aeróbica, fuerza glúteo, volumen bajo"},
        {"nombre": "Prep. General",     "meses": "Jun–Ago", "color": "#22d3ee",
         "inicio": date(2026, 6, 1), "fin": date(2026, 8, 31),
         "desc": "Resistencia y fuerza máxima, volumen medio"},
        {"nombre": "Prep. Específica",  "meses": "Sep–Nov", "color": "#f59e0b",
         "inicio": date(2026, 9, 1), "fin": date(2026, 11, 30),
         "desc": "Ritmos competición, volumen alto"},
        {"nombre": "Pico de Forma",     "meses": "Dic–Ene", "color": "#f87171",
         "inicio": date(2026, 12, 1), "fin": date(2027, 1, 31),
         "desc": "Tiradas largas, core, volumen máximo"},
        {"nombre": "Tapering",          "meses": "Feb 27",  "color": "#a855f7",
         "inicio": date(2027, 2, 1), "fin": date(2027, 2, 21),
         "desc": "Descanso, activación, supercompensación"},
    ]

    cols = st.columns(5)
    for col, fase in zip(cols, fases):
        dias_fase  = (fase["fin"] - fase["inicio"]).days
        dias_en    = max(0, (hoy - fase["inicio"]).days)
        pct_fase   = max(0, min(100, int(dias_en / dias_fase * 100)))
        es_actual  = fase_actual["fase_nombre"].lower() in fase["nombre"].lower()
        borde      = f"border:2px solid {fase['color']};" if es_actual else f"border:1px solid {fase['color']}33;"
        opacidad   = "opacity:1" if es_actual or hoy >= fase["inicio"] else "opacity:0.4"
        col.markdown(
            f"<div style='background:#161b22;{borde}border-radius:12px;"
            f"padding:14px;{opacidad};min-height:140px'>"
            f"<div style='font-size:10px;color:{fase['color']};text-transform:uppercase;"
            f"letter-spacing:0.7px;font-weight:500;margin-bottom:4px'>{fase['nombre']}</div>"
            f"<div style='font-size:22px;font-weight:500;color:{fase['color']};"
            f"margin-bottom:6px'>{pct_fase}%</div>"
            f"<div style='font-size:11px;color:#8b949e;line-height:1.4;"
            f"margin-bottom:8px'>{fase['desc']}</div>"
            f"<div style='height:4px;background:#21262d;border-radius:2px;overflow:hidden'>"
            f"<div style='height:100%;width:{pct_fase}%;background:{fase['color']};"
            f"border-radius:2px'></div></div>"
            f"<div style='font-size:10px;color:#484f58;margin-top:4px'>{fase['meses']}</div>"
            f"</div>", unsafe_allow_html=True)

    st.markdown(
        f"<div style='margin-top:10px;background:#161b22;border:1px solid #30363d;"
        f"border-radius:8px;padding:10px 16px'>"
        f"<div style='display:flex;justify-content:space-between;font-size:11px;"
        f"color:#8b949e;margin-bottom:6px'>"
        f"<span>Inicio — 1 Mar 2026</span>"
        f"<span style='color:#a3e635;font-weight:500'>{pct_total}% del macrociclo completado</span>"
        f"<span>Maratón — 21 Feb 2027</span></div>"
        f"<div style='height:6px;background:#21262d;border-radius:3px;overflow:hidden'>"
        f"<div style='height:100%;width:{pct_total}%;background:linear-gradient("
        f"to right,#a3e635,#22d3ee,#f59e0b,#f87171,#a855f7);border-radius:3px'>"
        f"</div></div></div>", unsafe_allow_html=True)


def render_grafico_sueno(usuario_id: int):
    """Barras de horas + línea de score (eje Y2) para los últimos 7 días."""
    import plotly.graph_objects as go

    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT fecha, horas_totales, score FROM datos_sueno "
        "WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 14",
        conn, params=(usuario_id,),
    )
    df_bio = pd.read_sql_query(
        "SELECT fecha, sleep_score FROM datos_biometricos_premium "
        "WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 14",
        conn, params=(usuario_id,),
    )
    conn.close()

    if df.empty and df_bio.empty:
        st.markdown(
            "<div style='background:#161b22;border:1px solid #30363d;border-radius:10px;"
            "padding:20px;text-align:center;color:#484f58;font-size:13px'>"
            "Sin datos de sueño — sincroniza Garmin para ver tu historial</div>",
            unsafe_allow_html=True,
        )
        return

    if df.empty:
        df = pd.DataFrame({"fecha": df_bio["fecha"], "horas_totales": None, "score": None})

    # Fallback de score: si datos_sueno.score falta, usar datos_biometricos_premium.sleep_score de la misma fecha.
    if not df_bio.empty:
        score_map = {
            str(r["fecha"])[:10]: pd.to_numeric(r["sleep_score"], errors="coerce")
            for _, r in df_bio.iterrows()
        }
    else:
        score_map = {}

    df["fecha_key"] = df["fecha"].astype(str).str[:10]
    df["score_num"] = pd.to_numeric(df["score"], errors="coerce")
    df["score_num"] = df.apply(
        lambda r: r["score_num"] if pd.notna(r["score_num"]) and float(r["score_num"]) > 0
        else score_map.get(r["fecha_key"]),
        axis=1,
    )

    df = df.sort_values("fecha").tail(7).reset_index(drop=True)
    dias    = [str(f)[:10] for f in df["fecha"]]
    horas   = pd.to_numeric(df["horas_totales"], errors="coerce").fillna(0).tolist()
    scores  = pd.to_numeric(df["score_num"], errors="coerce").tolist()
    colores = [
        "#a3e635" if pd.notna(s) and s >= 80 else "#f59e0b" if pd.notna(s) and s >= 65 else "#ef4444"
        for s in scores
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dias, y=horas, name="Horas",
        marker_color="#60a5fa", opacity=0.85, yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=dias, y=scores, name="Score",
        mode="lines+markers",
        line=dict(color="#a3e635", width=2),
        marker=dict(color=colores, size=8, line=dict(color="#0d1117", width=1.5)),
        connectgaps=False,
        yaxis="y2",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0), height=200,
        legend=dict(orientation="h", x=0, y=1.15,
                    font=dict(color="#8b949e", size=11)),
        yaxis=dict(title="horas", color="#484f58", gridcolor="#21262d",
                   range=[0, 10], tickfont=dict(size=10)),
        yaxis2=dict(title="score", color="#484f58", overlaying="y",
                    side="right", range=[0, 100],
                    tickfont=dict(size=10), showgrid=False),
        xaxis=dict(color="#484f58", tickfont=dict(size=10), showgrid=False),
        font=dict(color="#8b949e"),
    )
    st.plotly_chart(fig, width="stretch", key="sueno_chart")
