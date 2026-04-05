"""
src/core/ciclo_helpers.py
Predicción de fases del ciclo menstrual y renderizado de calendario.
Extraído de src/app_legacy.py (líneas 1543-1762).
NOTA: render_calendario_ciclo supera las 200 líneas por sí sola; se mantiene
en un único archivo para no duplicar la función de calendario.
"""

import calendar
import calendar as _calendar
import pandas as pd
import streamlit as st
from datetime import timedelta


def predecir_fases_ciclo(df_fisio, horizonte_dias=90):
    """Combina registros reales con predicción hacia horizonte_dias días."""
    if df_fisio.empty:
        return pd.DataFrame(columns=["fecha", "fase_ciclo", "origen"]), 28

    real = df_fisio.copy()
    real["fecha_dt"] = pd.to_datetime(real["fecha"]).dt.date
    real = real.sort_values("fecha_dt")

    _period_starts = real[real["fase_ciclo"].isin(["Menstruación", "Fase Folicular"])]["fecha_dt"].drop_duplicates().tolist()
    starts = []
    for _d in _period_starts:
        if not starts or (_d - starts[-1]).days > 5:
            starts.append(_d)

    ciclo_dias = 28
    if len(starts) >= 2:
        diffs = [d for d in [(starts[i] - starts[i-1]).days for i in range(1, len(starts))] if 20 <= d <= 40]
        if diffs:
            ciclo_dias = int(round(sum(diffs) / len(diffs)))

    base = starts[-1] if starts else real["fecha_dt"].max()
    pred = []
    for day in range(1, horizonte_dias + 1):
        fecha = base + timedelta(days=day)
        pos = ((day - 1) % ciclo_dias) + 1
        fase = "Menstruación" if pos <= 5 else "Folicular" if pos <= 11 else "Ovulación" if pos <= 16 else "Lútea"
        pred.append({"fecha": fecha, "fase_ciclo": fase, "origen": "Predicho"})

    pred_df = pd.DataFrame(pred)
    real_df = real[["fecha_dt", "fase_ciclo"]].rename(columns={"fecha_dt": "fecha"})
    real_df["origen"] = "Registrado"
    combinado = pd.concat([pred_df, real_df], ignore_index=True)
    combinado = combinado.sort_values(["fecha", "origen"]).drop_duplicates(subset=["fecha"], keep="last")
    return combinado, ciclo_dias


def render_calendario_ciclo(df_ciclo, anio, mes, df_registros=None):
    """Renderiza el calendario mensual coloreado por fase del ciclo."""
    mes_matrix = calendar.monthcalendar(anio, mes)
    prev_month = 12 if mes == 1 else mes - 1
    prev_year = anio - 1 if mes == 1 else anio
    prev_last_day = _calendar.monthrange(prev_year, prev_month)[1]
    next_month = 1 if mes == 12 else mes + 1
    next_year = anio + 1 if mes == 12 else anio

    # Rellenar ceros primera fila (mes anterior) y última fila (mes siguiente)
    zeros_first = [d for d in mes_matrix[0] if d == 0]
    for d in range(len(mes_matrix[0])):
        if mes_matrix[0][d] == 0:
            mes_matrix[0][d] = prev_last_day - (len(zeros_first) - 1 - d) if zeros_first else prev_last_day - (d - 1)
    next_fill = 1
    for d in range(len(mes_matrix[-1])):
        if mes_matrix[-1][d] == 0:
            mes_matrix[-1][d] = next_fill
            next_fill += 1

    mes_info = []
    for w, semana in enumerate(mes_matrix):
        semana_info = []
        for d, day in enumerate(semana):
            if (w == 0 and day > 7) or (w == 0 and day > 20) or (w == 0 and mes == 1 and day > 15):
                semana_info.append("prev")
            elif (w == len(mes_matrix) - 1 and day < 15) or (w == len(mes_matrix) - 1 and day < 7):
                semana_info.append("next")
            else:
                semana_info.append("curr")
        mes_info.append(semana_info)

    fases = {}
    origen_map = {}
    for _, row in df_ciclo.iterrows():
        d = row["fecha"].date() if isinstance(row["fecha"], pd.Timestamp) else row["fecha"]
        if d.month == mes and d.year == anio:
            fases[d.day] = row["fase_ciclo"]
            origen_map[d.day] = row["origen"]

    reg_por_dia = {}
    if df_registros is not None and not df_registros.empty:
        for _, row in df_registros.iterrows():
            try:
                d = pd.to_datetime(row["fecha"]).date()
            except Exception:
                continue
            if d.month == mes and d.year == anio and d.day not in reg_por_dia:
                reg_por_dia[d.day] = row

    sangre_emoji = {"Sin sangre": "⚪", "Manchado": "🩸", "Ligero": "🩸", "Medio": "🩸🩸", "Fuerte": "🩸🩸🩸"}
    sintomas_emoji = {"Dolor de ovarios": "🥚", "Dolor de senos": "🍒", "Antojos": "🍫", "Dolor de cabeza": "💢", "Hinchazón": "🎈"}
    animo_emoji = {"Ansiedad/Estrés": "😰", "Triste": "😭", "Enfadada": "😡", "Feliz": "😄", "Cansada": "🪫", "Energética": "⚡"}
    feedback_emoji = {"A tope": "🚀", "Regulero": "🗿", "Bajito": "⛈️", "No completo": "⛔"}
    colores = {
        "Menstruación": "#fad2e1", "Folicular": "#cddafd", "Ovulación": "#fff1e6", "Lútea": "#bee1e6",
        "Fase Folicular": "#cddafd", "Fase Ovulatoria": "#fff1e6", "Fase Lútea": "#bee1e6",
    }

    dias_header = ["L", "M", "X", "J", "V", "S", "D"]
    for i, h in enumerate(st.columns(7)):
        h.markdown(f"**{dias_header[i]}**")

    for w, semana in enumerate(mes_matrix):
        cols = st.columns(7)
        for i, day in enumerate(semana):
            with cols[i]:
                tipo = mes_info[w][i]
                if tipo in ("prev", "next"):
                    bg, txt_color, borde = "#232a36", "#3a4150", "1px dashed #334155"
                else:
                    fase = fases.get(day)
                    org = origen_map.get(day, "")
                    bg = colores.get(fase, "#1E2430")
                    txt_color = "#0E1117" if fase in ("Ovulación", "Fase Ovulatoria") else "#0f172a"
                    borde = "2px solid #0f172a" if org == "Registrado" else "1px dashed #334155"

                em_sangre = em_sintomas = em_animo = em_feedback = ""
                if tipo == "curr" and day in reg_por_dia:
                    r = reg_por_dia[day]
                    sangre = str(r.get("sangre") or "Sin sangre").strip()
                    sintomas = str(r.get("sintomas") or "").strip()
                    animo = str(r.get("estado_animo") or "").strip()
                    feedback = str(r.get("feedback_entreno") or "").strip()
                    em_sangre = sangre_emoji.get(sangre, "")
                    em_sintomas = "".join(sintomas_emoji.get(x.strip(), "") for x in sintomas.split(",") if x.strip())
                    em_animo = "".join(animo_emoji.get(x.strip(), "") for x in animo.split(",") if x.strip() and animo not in ("None", "", "Normal"))
                    em_feedback = feedback_emoji.get(feedback, "")

                st.markdown(
                    f"<div style='background:{bg};border:{borde};border-radius:8px;padding:8px;height:130px;"
                    f"overflow:hidden;display:flex;flex-direction:column;justify-content:flex-start;'>"
                    f"<div style='font-weight:700;color:{txt_color};line-height:1.1;'>{day}</div>"
                    f"<div style='font-size:1rem;line-height:1.1;margin-top:6px;'>{em_sangre}</div>"
                    f"<div style='font-size:1rem;line-height:1.1;margin-top:2px;'>{em_sintomas}</div>"
                    f"<div style='font-size:1rem;line-height:1.1;margin-top:2px;'>{em_animo}</div>"
                    f"<div style='font-size:1rem;line-height:1.1;margin-top:2px;'>{em_feedback}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
