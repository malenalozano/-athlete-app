"""
src/core/ciclo_helpers.py
Predicción de fases del ciclo menstrual y renderizado de calendario.
Módulo refactorizado desde el código monolítico original.
NOTA: render_calendario_ciclo supera las 200 líneas por sí sola; se mantiene
en un único archivo para no duplicar la función de calendario.
"""

import calendar
import calendar as _calendar
import pandas as pd
import streamlit as st
from datetime import date, timedelta


_SANGRADO_REGLA = {"Ligero", "Medio", "Fuerte"}


def _normalizar_fase(fase_raw):
    fase = str(fase_raw or "").strip().lower()
    if fase in ("menstruacion", "menstruación"):
        return "Menstruación"
    if fase in ("folicular", "fase folicular"):
        return "Folicular"
    if fase in ("ovulacion", "ovulación", "fase ovulatoria", "ovulatoria"):
        return "Ovulación"
    if fase in ("lutea", "lútea", "fase lútea", "fase lutea"):
        return "Lútea"
    return ""


def _fase_por_dia(posicion_dia):
    if posicion_dia <= 5:
        return "Menstruación"
    if posicion_dia <= 11:
        return "Folicular"
    if posicion_dia <= 16:
        return "Ovulación"
    return "Lútea"


def _inferir_inicios_regla(real_df):
    inicios = []
    if "sangre" in real_df.columns:
        sangres = real_df[real_df["sangre"].isin(list(_SANGRADO_REGLA))]["fecha_dt"].drop_duplicates().sort_values().tolist()

        # Construir bloques consecutivos de sangrado real
        bloques = []
        if sangres:
            bloque = [sangres[0]]
            for f in sangres[1:]:
                if (f - bloque[-1]).days <= 1:
                    bloque.append(f)
                else:
                    bloques.append(bloque)
                    bloque = [f]
            bloques.append(bloque)

        # Validar inicios: aceptar bloques de 2+ días o, si son de 1 día,
        # solo cuando respetan separación mínima respecto al ciclo anterior.
        for bloque in bloques:
            inicio = bloque[0]
            duracion = len(bloque)
            if not inicios:
                inicios.append(inicio)
                continue
            dias_desde_anterior = (inicio - inicios[-1]).days
            if duracion >= 2 or dias_desde_anterior >= 20:
                inicios.append(inicio)

    if not inicios:
        men_days = real_df[real_df["fase_norm"] == "Menstruación"]["fecha_dt"].drop_duplicates().sort_values().tolist()
        for d in men_days:
            if not inicios or (d - inicios[-1]).days > 5:
                inicios.append(d)
    return inicios


def predecir_fases_ciclo(df_fisio, horizonte_dias=90, ciclo_dias_personalizado=None):
    """Combina registros reales con predicción hacia horizonte_dias días.
    
    Args:
        df_fisio: DataFrame con registros de ciclo
        horizonte_dias: Días a predecir hacia el futuro
        ciclo_dias_personalizado: Si se proporciona, usar este valor en lugar de calcular automáticamente
    """
    if df_fisio.empty:
        ciclo_default = ciclo_dias_personalizado if ciclo_dias_personalizado else 28
        return pd.DataFrame(columns=["fecha", "fase_ciclo", "origen"]), ciclo_default

    real = df_fisio.copy()
    real["fecha_dt"] = pd.to_datetime(real["fecha"]).dt.date
    real = real.sort_values("fecha_dt")
    real = real[real["fecha_dt"].notna()].copy()
    real["fase_norm"] = real.get("fase_ciclo", pd.Series([None] * len(real))).apply(_normalizar_fase)
    if "sangre" in real.columns:
        real["sangre"] = real["sangre"].fillna("").astype(str).str.strip()
    else:
        real["sangre"] = ""

    starts = _inferir_inicios_regla(real)

    ciclo_dias = ciclo_dias_personalizado if ciclo_dias_personalizado else 28
    if not ciclo_dias_personalizado and len(starts) >= 2:
        diffs = [d for d in [(starts[i] - starts[i-1]).days for i in range(1, len(starts))] if 20 <= d <= 40]
        if diffs:
            ciclo_dias = int(round(sum(diffs) / len(diffs)))

    base = starts[-1] if starts else real["fecha_dt"].max()

    registros = []
    for _, row in real.iterrows():
        fecha = row["fecha_dt"]
        sangre = row.get("sangre", "")
        fase_real = row.get("fase_norm", "")

        if sangre in _SANGRADO_REGLA:
            fase_real = "Menstruación"
        elif starts:
            # Si hay anclas de regla, priorizar cálculo por día de ciclo para evitar
            # que fases guardadas antiguas/desfasadas deformen el calendario.
            ini = max((s for s in starts if s <= fecha), default=starts[0])
            pos = ((fecha - ini).days % ciclo_dias) + 1
            fase_real = _fase_por_dia(pos)
        elif not fase_real:
            # Sin anclas ni fase explícita: no forzar dato.
            fase_real = ""

        if fase_real:
            registros.append({"fecha": fecha, "fase_ciclo": fase_real, "origen": "Registrado"})

    pred = []
    for day in range(1, horizonte_dias + 1):
        fecha = base + timedelta(days=day)
        pos = ((day - 1) % ciclo_dias) + 1
        fase = _fase_por_dia(pos)
        pred.append({"fecha": fecha, "fase_ciclo": fase, "origen": "Predicho"})

    pred_df = pd.DataFrame(pred)
    real_df = pd.DataFrame(registros) if registros else pd.DataFrame(columns=["fecha", "fase_ciclo", "origen"])
    combinado = pd.concat([pred_df, real_df], ignore_index=True)
    combinado = combinado.sort_values(["fecha", "origen"]).drop_duplicates(subset=["fecha"], keep="last")
    return combinado, ciclo_dias


def render_calendario_ciclo(df_ciclo, anio, mes, df_registros=None):
    """Renderiza el calendario mensual coloreado por fase del ciclo."""
    hoy = date.today()
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

    sangre_emoji = {"Sin sangre": "⚪", "Ligero": "🩸", "Medio": "🩸🩸", "Fuerte": "🩸🩸🩸", "Flujo": "🟤"}
    sintomas_emoji = {"Dolor de ovarios": "🥚", "Dolor de senos": "🍒", "Antojos": "🍫", "Dolor de cabeza": "💢", "Hinchazón": "🎈"}
    animo_emoji = {"Ansiedad/Estrés": "😰", "Triste": "😭", "Enfadada": "😡", "Feliz": "😄", "Cansada": "🪫", "Energética": "⚡"}
    feedback_emoji = {"A tope": "🚀", "Regulero": "🗿", "Bajito": "⛈️", "No completo": "⛔"}
    colores = {
        "Menstruación": {"bg": "rgba(244, 63, 94, 0.16)", "border": "rgba(244, 63, 94, 0.55)", "txt": "#ffe4ea"},
        "Folicular": {"bg": "rgba(34, 211, 238, 0.14)", "border": "rgba(34, 211, 238, 0.55)", "txt": "#dbfdff"},
        "Ovulación": {"bg": "rgba(201, 255, 0, 0.14)", "border": "rgba(201, 255, 0, 0.65)", "txt": "#f5ffd1"},
        "Lútea": {"bg": "rgba(168, 85, 247, 0.16)", "border": "rgba(168, 85, 247, 0.55)", "txt": "#f2e8ff"},
        "Fase Folicular": {"bg": "rgba(34, 211, 238, 0.14)", "border": "rgba(34, 211, 238, 0.55)", "txt": "#dbfdff"},
        "Fase Ovulatoria": {"bg": "rgba(201, 255, 0, 0.14)", "border": "rgba(201, 255, 0, 0.65)", "txt": "#f5ffd1"},
        "Fase Lútea": {"bg": "rgba(168, 85, 247, 0.16)", "border": "rgba(168, 85, 247, 0.55)", "txt": "#f2e8ff"},
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
                    bg, txt_color, borde = "rgba(20, 25, 36, 0.92)", "#566173", "1px dashed rgba(139, 149, 158, 0.18)"
                else:
                    fase = fases.get(day)
                    org = origen_map.get(day, "")
                    estilo_fase = colores.get(fase, {"bg": "rgba(22, 27, 34, 0.96)", "border": "rgba(139, 149, 158, 0.22)", "txt": "#e6edf3"})
                    bg = estilo_fase["bg"]
                    txt_color = estilo_fase["txt"]
                    borde = f"2px solid {estilo_fase['border']}" if org == "Registrado" else f"1px solid {estilo_fase['border']}"

                    es_hoy = (anio == hoy.year and mes == hoy.month and day == hoy.day)
                    if es_hoy:
                        bg = "linear-gradient(180deg, rgba(201, 255, 0, 0.24), rgba(201, 255, 0, 0.12))"
                        txt_color = "#f8ffd8"
                        borde = "2px solid rgba(201, 255, 0, 0.92)"

                em_sangre = em_sintomas = em_animo = em_feedback = ""
                marca_hoy = ""
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

                if tipo == "curr" and anio == hoy.year and mes == hoy.month and day == hoy.day:
                    marca_hoy = (
                        "<div style='display:inline-flex;align-items:center;gap:4px;"
                        "margin-top:4px;padding:2px 7px;border-radius:999px;"
                        "background:rgba(201,255,0,0.16);border:1px solid rgba(201,255,0,0.52);"
                        "color:#f8ffd8;font-size:0.62rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;'>"
                        "Hoy</div>"
                    )

                st.markdown(
                    f"<div style='background:{bg};border:{borde};border-radius:14px;padding:10px 9px 8px;height:130px;"
                    f"overflow:hidden;display:flex;flex-direction:column;justify-content:flex-start;backdrop-filter:blur(8px);"
                    f"box-shadow:inset 0 1px 0 rgba(255,255,255,0.04);'>"
                    f"<div style='font-weight:800;color:{txt_color};line-height:1.1;font-size:0.98rem;display:flex;align-items:center;justify-content:space-between;gap:6px;'>"
                    f"<span>{day}</span>"
                    f"{marca_hoy}"
                    f"</div>"
                    f"<div style='font-size:1rem;line-height:1.1;margin-top:6px;'>{em_sangre}</div>"
                    f"<div style='font-size:1rem;line-height:1.1;margin-top:2px;'>{em_sintomas}</div>"
                    f"<div style='font-size:1rem;line-height:1.1;margin-top:2px;'>{em_animo}</div>"
                    f"<div style='font-size:1rem;line-height:1.1;margin-top:2px;'>{em_feedback}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )


def calcular_ciclos_desde_registros(usuario_id, conn):
    """
    Calcula todos los ciclos menstruales basados en registros de sangrado.
    Solo cuenta como sangrado: Ligero, Medio, Fuerte.
    
    Returns:
        List of dicts con: fecha_inicio, fecha_fin, duracion_menstruacion, duracion_ciclo
    """
    query = (
        "SELECT fecha, sangre FROM diario_fisiologia "
        "WHERE usuario_id=? AND sangre IN ('Ligero','Medio','Fuerte') "
        "ORDER BY fecha ASC"
    )
    df = pd.read_sql_query(query, conn, params=(usuario_id,))
    if df.empty:
        return []
    
    df["fecha_dt"] = pd.to_datetime(df["fecha"]).dt.date
    fechas_sangrado = sorted(df["fecha_dt"].unique().tolist())
    
    ciclos = []
    bloques = []  # Bloques de días consecutivos con sangrado
    
    if fechas_sangrado:
        bloque = [fechas_sangrado[0]]
        for f in fechas_sangrado[1:]:
            if (f - bloque[-1]).days <= 1:
                bloque.append(f)
            else:
                bloques.append(bloque)
                bloque = [f]
        bloques.append(bloque)
    
    # Procesar bloques para crear ciclos
    for i, bloque in enumerate(bloques):
        inicio = bloque[0]
        fin = bloque[-1]
        duracion_menstruacion = len(bloque)
        
        ciclo_info = {
            "fecha_inicio_regla": inicio,
            "fecha_fin_regla": fin,
            "duracion_menstruacion_dias": duracion_menstruacion,
            "duracion_ciclo_dias": None,
            "fecha_siguiente_regla": None,
        }
        
        # Si hay un ciclo siguiente, calcular duración del ciclo
        if i + 1 < len(bloques):
            siguiente_inicio = bloques[i + 1][0]
            duracion_ciclo = (siguiente_inicio - inicio).days
            # Validar que sea un ciclo realista (20-40 días)
            if 20 <= duracion_ciclo <= 40:
                ciclo_info["duracion_ciclo_dias"] = duracion_ciclo
                ciclo_info["fecha_siguiente_regla"] = siguiente_inicio
        
        ciclos.append(ciclo_info)
    
    return ciclos


def obtener_estadisticas_ciclo(usuario_id, conn):
    """
    Calcula estadísticas del ciclo menstrual.
    
    Returns:
        dict con: duracion_promedio_ciclo, duracion_promedio_menstruacion, 
                  ciclos_registrados, proxima_regla_predicha, duracion_proxima_predicha
    """
    ciclos = calcular_ciclos_desde_registros(usuario_id, conn)
    
    if not ciclos:
        return {
            "duracion_promedio_ciclo": 28,
            "duracion_promedio_menstruacion": 5,
            "ciclos_registrados": 0,
            "proxima_regla_predicha": None,
            "duracion_proxima_predicha": None,
        }
    
    # Calcular duraciones de ciclos válidos (solo los que tienen siguiente)
    duraciones_ciclo = [c["duracion_ciclo_dias"] for c in ciclos if c["duracion_ciclo_dias"] is not None]
    duraciones_menstruacion = [c["duracion_menstruacion_dias"] for c in ciclos]
    
    duracion_promedio_ciclo = int(round(sum(duraciones_ciclo) / len(duraciones_ciclo))) if duraciones_ciclo else 28
    duracion_promedio_menstruacion = int(round(sum(duraciones_menstruacion) / len(duraciones_menstruacion))) if duraciones_menstruacion else 5
    
    # Predecir próxima regla basada en el último ciclo
    ultimo_ciclo = ciclos[-1]
    proxima_regla_predicha = None
    duracion_proxima_predicha = duracion_promedio_menstruacion
    
    if ultimo_ciclo["fecha_siguiente_regla"]:
        # Ya conocemos la siguiente, no hay que predecir
        proxima_regla_predicha = ultimo_ciclo["fecha_siguiente_regla"]
    else:
        # Predecir: última regla + duración promedio del ciclo
        ultima_regla_inicio = ultimo_ciclo["fecha_inicio_regla"]
        proxima_regla_predicha = ultima_regla_inicio + timedelta(days=duracion_promedio_ciclo)
    
    return {
        "duracion_promedio_ciclo": duracion_promedio_ciclo,
        "duracion_promedio_menstruacion": duracion_promedio_menstruacion,
        "ciclos_registrados": len(ciclos),
        "proxima_regla_predicha": proxima_regla_predicha,
        "duracion_proxima_predicha": duracion_proxima_predicha,
    }


def guardar_ciclo_en_historial(usuario_id, conn, ciclo_info):
    """
    Guarda un ciclo menstrual en la tabla de historial.
    """
    try:
        conn.execute(
            "INSERT OR REPLACE INTO historial_ciclos_menstruales "
            "(usuario_id, fecha_inicio_regla, fecha_fin_regla, duracion_menstruacion_dias, "
            "duracion_ciclo_dias, fecha_siguiente_regla) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                usuario_id,
                str(ciclo_info.get("fecha_inicio_regla")),
                str(ciclo_info.get("fecha_fin_regla")),
                ciclo_info.get("duracion_menstruacion_dias"),
                ciclo_info.get("duracion_ciclo_dias"),
                str(ciclo_info.get("fecha_siguiente_regla")) if ciclo_info.get("fecha_siguiente_regla") else None,
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error guardando ciclo: {e}")
        return False
