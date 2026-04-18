"""
src/core/dashboard_ui.py
Componentes de UI del Dashboard: checkpoints, ciclo, macrociclo, tema Plotly.
Módulo refactorizado desde el código monolítico original.
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


def render_objetivos_rendimiento_cards(tarjetas):
    """Renderiza 3 tarjetas de objetivo (5K, 10K, media) con estado dinámico."""
    if not tarjetas:
        return

    st.markdown(
        """
        <style>
        .goal-grid {
            display:grid;
            grid-template-columns:repeat(3, minmax(220px, 1fr));
            gap:16px;
            margin:10px 0 8px;
        }
        .goal-card {
            background:linear-gradient(165deg, #0f1724 0%, #101928 100%);
            border:1px solid color-mix(in srgb, var(--goal-accent) 58%, #1f2937 42%);
            border-radius:18px;
            padding:18px 18px 14px;
            box-shadow:0 12px 30px rgba(0,0,0,0.24);
        }
        .goal-top {
            display:flex;
            justify-content:space-between;
            align-items:flex-start;
            gap:10px;
            margin-bottom:8px;
        }
        .goal-title {
            color:var(--goal-accent);
            font-size:1.05rem;
            font-weight:800;
            line-height:1.2;
        }
        .goal-target {
            color:#ffffff;
            font-size:1.02rem;
            font-weight:700;
            margin:3px 0 12px;
        }
        .goal-badge {
            border-radius:999px;
            font-size:0.75rem;
            font-weight:700;
            line-height:1;
            padding:6px 10px;
            border:1px solid transparent;
            text-transform:uppercase;
            letter-spacing:0.2px;
            white-space:nowrap;
        }
        .goal-badge.done {
            color:#00db81;
            border-color:rgba(0, 219, 129, 0.65);
            background:rgba(0, 219, 129, 0.12);
        }
        .goal-badge.pending {
            color:#ff9f43;
            border-color:rgba(255, 159, 67, 0.68);
            background:rgba(255, 159, 67, 0.12);
        }
        .goal-detail {
            color:#9fb0c4;
            font-size:0.9rem;
            min-height:44px;
            margin-bottom:14px;
        }
        .goal-sep {
            height:1px;
            background:color-mix(in srgb, var(--goal-accent) 55%, #233042 45%);
            opacity:0.55;
            margin-bottom:12px;
        }
        .goal-sub {
            color:#9db0c8;
            font-size:0.88rem;
            margin-bottom:5px;
        }
        .goal-mark {
            display:flex;
            align-items:baseline;
            gap:8px;
        }
        .goal-mark-time {
            color:var(--goal-accent);
            font-size:1.05rem;
            font-weight:800;
            line-height:1;
        }
        .goal-mark-hint {
            color:#ff9f43;
            font-size:0.9rem;
            font-weight:700;
        }
        .goal-mark-hint.done {
            color:#00db81;
        }
        @media (max-width: 1100px) {
            .goal-grid { grid-template-columns:1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    cards_html = []
    for card in tarjetas:
        done = bool(card.get("hecho"))
        badge_txt = "HECHO" if done else "PENDIENTE"
        hint = str(card.get("estado_hint") or "").upper()
        cards_html.append(
            f"""
            <div class='goal-card' style='--goal-accent:{card.get("accent", "#00db81")};'>
                <div class='goal-top'>
                    <div>
                        <div class='goal-title'>{card.get("titulo", "-")}</div>
                        <div class='goal-target'>{card.get("meta_txt", "-")}</div>
                    </div>
                    <span class='goal-badge {'done' if done else 'pending'}'>{badge_txt}</span>
                </div>
                <div class='goal-detail'>{card.get("detalle", "")}</div>
                <div class='goal-sep'></div>
                <div class='goal-sub'>Mejor Marca</div>
                <div class='goal-mark'>
                    <span class='goal-mark-time'>{card.get("mejor_txt", "-")}</span>
                    <span class='goal-mark-hint {'done' if done else ''}'>{hint}</span>
                </div>
            </div>
            """
        )

    st.markdown(f"<div class='goal-grid'>{''.join(cards_html)}</div>", unsafe_allow_html=True)


@st.cache_data(ttl=120, show_spinner=False)
def obtener_estado_ciclo_malena(usuario_id: int = 1):
    """Estado actual del ciclo solo para Malena (usuario_id=1).
    Cache keyed by usuario_id to prevent cross-user contamination."""
    if int(usuario_id or 0) != 1:
        return None
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
    proximas = ciclo_df[
        (ciclo_df["fecha"] >= hoy)
        & (ciclo_df["fase_ciclo"].isin(["Fase Folicular", "Folicular", "Menstruación"]))
    ].head(2)
    proxima_regla = proximas.iloc[0]["fecha"] if not proximas.empty and proximas.iloc[0]["fecha"] >= hoy else None

    sugerencias = {
        "Fase Folicular": ["Buen momento para proponer planes, viajes o entrenos más exigentes juntos.", "Las conversaciones importantes suelen ir mejor en esta fase."],
        "Folicular": ["Buen momento para proponer planes, viajes o entrenos más exigentes juntos.", "Las conversaciones importantes suelen ir mejor en esta fase."],
        "Fase Ovulatoria": ["Buena ventana para citas, conexión y refuerzo positivo.", "Si entrenáis juntos, suele tolerar bien intensidad y sesiones sociales."],
        "Ovulación": ["Buena ventana para citas, conexión y refuerzo positivo.", "Si entrenáis juntos, suele tolerar bien intensidad y sesiones sociales."],
        "Fase Lútea": ["Prioriza paciencia, validación emocional y menos fricción innecesaria.", "Suman mucho los mimos prácticos: cena reconfortante, masaje, bajar carga social."],
        "Lútea": ["Prioriza paciencia, validación emocional y menos fricción innecesaria.", "Suman mucho los mimos prácticos: cena reconfortante, masaje, bajar carga social."],
    }
    return {
        "fase": fase, "origen": origen, "proxima_regla": proxima_regla,
        "consejos": sugerencias.get(fase, ["Acompaña y ajusta el contexto según cómo se encuentre ese día."]),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_titulo_macrociclo(usuario_id: int | None = None) -> str:
    """Devuelve el título dinámico del macrociclo basado en perfil usuario."""
    from src.db.db_manager import obtener_perfil
    from datetime import datetime

    if usuario_id is None:
        usuario_id = int(st.session_state.get("usuario_id", 1))

    perfil = obtener_perfil(usuario_id) or {}
    objetivo_tipo = str(perfil.get("objetivo_tipo") or "maraton").lower()
    fecha_objetivo = perfil.get("fecha_objetivo", "")

    try:
        fecha_obj = datetime.strptime(fecha_objetivo, "%Y-%m-%d").date()
        fecha_str = fecha_obj.strftime("%b %Y")
    except:
        fecha_str = ""

    if objetivo_tipo in ("ultramaraton", "ultra", "trail_ultra"):
        return f"Macrociclo — Ultra 100km · {fecha_str}"
    else:
        return f"Macrociclo — Maratón Sub 3:30 · {fecha_str}"


def render_macrociclo(usuario_id: int | None = None):
    """Grid 5 fases del macrociclo + barra global de progreso.
    Dinámico: calcula fases según perfil del usuario (maratón o ultramaratón)."""
    from src.plan.reglas import obtener_fase_macrociclo, obtener_fase_macrociclo_ultra
    from src.db.db_manager import obtener_perfil
    from datetime import timedelta

    if usuario_id is None:
        try:
            usuario_id = int(st.session_state.get("usuario_id", 1))
        except Exception:
            usuario_id = 1

    perfil = obtener_perfil(usuario_id) or {}
    objetivo_tipo = str(perfil.get("objetivo_tipo") or "maraton").lower()
    fecha_objetivo_str = perfil.get("fecha_objetivo")
    es_ultra = objetivo_tipo in ("ultramaraton", "ultra", "trail_ultra")
    hoy = date.today()

    if es_ultra and fecha_objetivo_str:
        try:
            fecha_carrera = datetime.strptime(fecha_objetivo_str, "%Y-%m-%d").date()
        except ValueError:
            fecha_carrera = date(2026, 9, 19)
        fase_actual = obtener_fase_macrociclo_ultra(datetime.now(), fecha_objetivo_str)
        # Fases calculadas hacia atrás desde la carrera
        tap_inicio  = fecha_carrera - timedelta(weeks=3)
        pico_inicio = tap_inicio    - timedelta(weeks=6)
        esp_inicio  = pico_inicio   - timedelta(weeks=8)
        gen_inicio  = esp_inicio    - timedelta(weeks=8)
        acon_inicio = gen_inicio    - timedelta(weeks=12)
        label_inicio  = acon_inicio.strftime("%-d %b %Y") if hasattr(acon_inicio, 'strftime') else str(acon_inicio)
        label_carrera = f"Ultra — {fecha_carrera.strftime('%d %b %Y')}"
        fases = [
            {"nombre": "Acondicionamiento", "meses": f"hasta {gen_inicio.strftime('%d %b')}",
             "color": "#a3e635", "inicio": acon_inicio, "fin": gen_inicio - timedelta(days=1),
             "desc": "Base aeróbica Z2, técnica trail, fuerza glúteo"},
            {"nombre": "Prep. General",     "meses": f"{gen_inicio.strftime('%d %b')}–{esp_inicio.strftime('%d %b')}",
             "color": "#22d3ee", "inicio": gen_inicio, "fin": esp_inicio - timedelta(days=1),
             "desc": "Volumen base, desnivel progresivo, fuerza máxima"},
            {"nombre": "Prep. Específica",  "meses": f"{esp_inicio.strftime('%d %b')}–{pico_inicio.strftime('%d %b')}",
             "color": "#f59e0b", "inicio": esp_inicio, "fin": pico_inicio - timedelta(days=1),
             "desc": "Simulacros ultra, back-to-back, elevación específica"},
            {"nombre": "Pico de Forma",     "meses": f"{pico_inicio.strftime('%d %b')}–{tap_inicio.strftime('%d %b')}",
             "color": "#f87171", "inicio": pico_inicio, "fin": tap_inicio - timedelta(days=1),
             "desc": "Back-to-back máximos, ritmo ultra, core"},
            {"nombre": "Tapering",          "meses": f"{tap_inicio.strftime('%d %b')}–{fecha_carrera.strftime('%d %b')}",
             "color": "#a855f7", "inicio": tap_inicio, "fin": fecha_carrera,
             "desc": "Supercompensación. Mínima fatiga. Activación."},
        ]
        inicio_macro  = acon_inicio
        objetivo_date = fecha_carrera
    else:
        # Malena — maratón Feb 2027
        fecha_carrera = date(2027, 2, 21)
        fase_actual   = obtener_fase_macrociclo(datetime.now())
        label_inicio  = "6 Abr 2026"
        label_carrera = "Maratón — 21 Feb 2027"
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
        inicio_macro  = date(2026, 4, 6)
        objetivo_date = fecha_carrera

    total_dias = (objetivo_date - inicio_macro).days
    pct_total  = max(0, min(100, int((hoy - inicio_macro).days / max(total_dias, 1) * 100)))

    cols = st.columns(5, gap="large")
    for col, fase in zip(cols, fases):
        dias_fase  = max((fase["fin"] - fase["inicio"]).days, 1)
        dias_en    = max(0, (hoy - fase["inicio"]).days)
        pct_fase   = max(0, min(100, int(dias_en / dias_fase * 100)))
        es_actual  = fase_actual["fase_nombre"].lower() in fase["nombre"].lower()
        borde      = f"border:2px solid {fase['color']};" if es_actual else f"border:1px solid {fase['color']}33;"
        opacidad   = "opacity:1" if es_actual or hoy >= fase["inicio"] else "opacity:0.4"
        col.markdown(
            f"<div style='background:#161b22;{borde}border-radius:12px;"
            f"padding:14px;{opacidad};min-height:140px;margin-bottom:8px;'>"
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
        f"<span>Inicio — {label_inicio}</span>"
        f"<span style='color:#a3e635;font-weight:500'>{pct_total}% del macrociclo completado</span>"
        f"<span>{label_carrera}</span></div>"
        f"<div style='height:6px;background:#21262d;border-radius:3px;overflow:hidden'>"
        f"<div style='height:100%;width:{pct_total}%;background:linear-gradient("
        f"to right,#a3e635,#22d3ee,#f59e0b,#f87171,#a855f7);border-radius:3px'>"
        f"</div></div></div>", unsafe_allow_html=True)


@st.cache_data(ttl=120, show_spinner=False)
def render_grafico_sueno(usuario_id: int):
    """Barras de horas + línea de score (eje Y2) para los últimos 7 días.
    Debajo: análisis de la última noche sincronizada."""
    import plotly.graph_objects as go
    from src.core.styles import format_hours, analizar_ultima_noche_sueno
    from src.db.db_manager import obtener_perfil

    conn = get_db_connection()
    # Intenta leer desde datos_sueno; si score está vacío, intenta desde datos_biometricos_premium
    df = pd.read_sql_query(
        """SELECT ds.fecha, ds.horas_totales, COALESCE(ds.score, bp.sleep_score) as score,
                  ds.sleep_profundo_horas, ds.sleep_rem_horas, ds.sleep_vigilia_horas,
                  bp.estres_medio
           FROM datos_sueno ds
           LEFT JOIN datos_biometricos_premium bp ON ds.usuario_id = bp.usuario_id AND ds.fecha = bp.fecha
           WHERE ds.usuario_id = ? ORDER BY ds.fecha DESC LIMIT 7""",
        conn, params=(usuario_id,),
    )
    conn.close()

    if df.empty:
        st.markdown(
            "<div style='background:#161b22;border:1px solid #30363d;border-radius:10px;"
            "padding:20px;text-align:center;color:#484f58;font-size:13px'>"
            "Sin datos de sueño — sincroniza Garmin para ver tu historial</div>",
            unsafe_allow_html=True,
        )
        return

    df = df.sort_values("fecha").reset_index(drop=True)
    dias    = [str(f)[:10] for f in df["fecha"]]
    horas   = df["horas_totales"].fillna(0).tolist()
    scores  = pd.to_numeric(df["score"], errors="coerce").fillna(0).tolist()
    colores = [
        "#a3e635" if s >= 80 else "#f59e0b" if s >= 65 else "#ef4444"
        for s in scores
    ]

    # Preparar etiquetas de horas formateadas
    horas_labels = [format_hours(h) if h > 0 else "—" for h in horas]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dias, y=horas, name="Horas",
        text=horas_labels,
        textposition="outside",
        marker_color="#60a5fa", opacity=0.85, yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=dias, y=scores, name="Score",
        mode="lines+markers",
        line=dict(color="#a3e635", width=2),
        marker=dict(color=colores, size=8, line=dict(color="#0d1117", width=1.5)),
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
    st.plotly_chart(fig, use_container_width=True, key="sueno_chart")

    # Análisis de la última noche sincronizada
    if len(df) > 0:
        ultima_noche = df.iloc[-1]  # Más reciente
        score_ultima = pd.to_numeric(ultima_noche["score"], errors="coerce")
        horas_ultima = ultima_noche["horas_totales"]
        profundo_ultima = ultima_noche.get("sleep_profundo_horas") or 0
        rem_ultima = ultima_noche.get("sleep_rem_horas") or 0
        vigilia_ultima = ultima_noche.get("sleep_vigilia_horas") or 0
        estres_ultima = ultima_noche.get("estres_medio") or 0

        if score_ultima and score_ultima > 0:
            # Obtener sexo del usuario
            perfil = obtener_perfil(usuario_id) or {}
            genero = perfil.get("genero", "mujer")

            # Generar análisis
            comentario = analizar_ultima_noche_sueno(
                score=score_ultima,
                horas_totales=horas_ultima,
                profundo_min=profundo_ultima * 60,  # Convertir a minutos
                rem_min=rem_ultima * 60,
                vigilia_min=vigilia_ultima * 60,
                estres_medio=estres_ultima,
                genero=genero,
            )

            if comentario:
                st.markdown(
                    f"<div style='background:#0f1e10;border-left:4px solid #a3e635;border-radius:0 8px 8px 0;"
                    f"padding:12px 14px;margin-top:12px;font-size:13px;color:#c9d1d9;line-height:1.5;'>"
                    f"{comentario}</div>",
                    unsafe_allow_html=True,
                )
