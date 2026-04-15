"""
src/core/dashboard_data.py
Funciones de carga y transformación de datos para el Dashboard.
Extraído de src/app_legacy.py.
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from src.db.db_manager import get_db_connection


def inicio_semana(dt):
    """Devuelve el datetime del lunes de la semana de dt."""
    return dt - timedelta(days=dt.weekday())


def resumen_dashboard(usuario_id):
    """Resumen de los últimos 7 días: km, carreras, fuerza y sueño medio."""
    conn = get_db_connection()
    fecha_7d = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    act = pd.read_sql_query(
        "SELECT distancia_m FROM actividades_garmin WHERE usuario_id = ? AND fecha >= ?",
        conn, params=(usuario_id, fecha_7d),
    )
    fuerza = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM sesiones_fuerza WHERE usuario_id = ? AND fecha >= ?",
        conn, params=(usuario_id, fecha_7d),
    )
    sueno = pd.read_sql_query(
        "SELECT horas_totales FROM datos_sueno WHERE usuario_id = ? AND fecha >= ?",
        conn, params=(usuario_id, fecha_7d),
    )
    conn.close()
    return {
        "km_7d": float(act["distancia_m"].fillna(0).sum() / 1000) if not act.empty else 0.0,
        "runs_7d": len(act) if not act.empty else 0,
        "fuerza_7d": int(fuerza.iloc[0]["total"]) if not fuerza.empty else 0,
        "sueno_7d": float(sueno["horas_totales"].fillna(0).mean()) if not sueno.empty else None,
    }


def cargar_datos_dashboard(usuario_id):
    """Carga actividades, sueño y ejercicios de fuerza para el dashboard."""
    conn = get_db_connection()
    try:
        df_act = pd.read_sql_query(
            "SELECT fecha, distancia_m, ritmo_medio, fc_media FROM actividades_garmin WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 200",
            conn, params=(usuario_id,),
        )
        try:
            df_sueno = pd.read_sql_query(
                "SELECT fecha, horas_totales, score FROM datos_sueno WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 7",
                conn, params=(usuario_id,),
            )
        except Exception:
            df_sueno = pd.DataFrame()
        try:
            df_fuerza = pd.read_sql_query(
                """SELECT s.fecha, e.ejercicio, e.peso, e.series, e.repeticiones, e.musculo_principal
                   FROM ejercicios_fuerza e INNER JOIN sesiones_fuerza s ON s.id = e.sesion_id
                   WHERE s.usuario_id = ? ORDER BY s.fecha""",
                conn, params=(usuario_id,),
            )
        except Exception:
            try:
                df_fuerza = pd.read_sql_query(
                    "SELECT fecha, ejercicio, peso, series, repeticiones, musculo_principal "
                    "FROM entrenamientos_fuerza WHERE usuario_id=? OR usuario_id IS NULL",
                    conn, params=(usuario_id,))
            except Exception:
                df_fuerza = pd.DataFrame()
    finally:
        conn.close()
    return df_act, df_sueno, df_fuerza


def construir_checkpoints_objetivo(perfil, df_act):
    """Evalúa checkpoints de rendimiento según objetivo del perfil."""
    objetivo = (perfil.get("objetivo") or "").lower()
    if "marat" in objetivo:
        checkpoints = [
            {"nombre": "5K en Sub 22:30", "dist_min": 4.6, "dist_max": 5.4, "ritmo_max": 4.5, "detalle": "Demuestra la velocidad máxima necesaria."},
            {"nombre": "10K en Sub 46:30", "dist_min": 9.2, "dist_max": 10.8, "ritmo_max": 4.65, "detalle": "Confirma umbral y capacidad de sostener el ritmo."},
            {"nombre": "Media Maratón en Sub 1h42", "dist_min": 20.0, "dist_max": 22.2, "ritmo_max": 4.84, "detalle": "Checkpoint definitivo de preparación."},
        ]
    elif "media" in objetivo:
        checkpoints = [
            {"nombre": "5K en Sub 23:30", "dist_min": 4.6, "dist_max": 5.4, "ritmo_max": 4.7, "detalle": "Velocidad base para media maratón sólida."},
            {"nombre": "10K en Sub 49:30", "dist_min": 9.2, "dist_max": 10.8, "ritmo_max": 4.95, "detalle": "Umbral aeróbico bien colocado."},
            {"nombre": "15K en Sub 1h16", "dist_min": 14.0, "dist_max": 16.2, "ritmo_max": 5.07, "detalle": "Confirma resistencia específica."},
        ]
    elif "hyrox" in objetivo:
        checkpoints = [
            {"nombre": "5K en Sub 25:00", "dist_min": 4.6, "dist_max": 5.4, "ritmo_max": 5.0, "detalle": "Base aeróbica para encadenar estaciones."},
            {"nombre": "2+ sesiones fuerza/semana", "dist_min": None, "dist_max": None, "ritmo_max": None, "detalle": "La fuerza sostenida es parte del objetivo."},
        ]
    else:
        checkpoints = [
            {"nombre": "5K en Sub 25:00", "dist_min": 4.6, "dist_max": 5.4, "ritmo_max": 5.0, "detalle": "Primer gran checkpoint de economía y ritmo."},
            {"nombre": "10K en Sub 52:00", "dist_min": 9.2, "dist_max": 10.8, "ritmo_max": 5.2, "detalle": "Sostener el ritmo sin deriva fuerte de fatiga."},
        ]

    actividades = df_act.copy() if not df_act.empty else pd.DataFrame()
    if not actividades.empty:
        actividades["km"] = actividades["distancia_m"].fillna(0) / 1000
        actividades["ritmo_min_km"] = pd.to_numeric(actividades.get("ritmo_medio"), errors="coerce")

    filas = []
    for cp in checkpoints:
        mejor = None
        if not actividades.empty and cp["dist_min"] is not None:
            match = actividades[
                (actividades["km"] >= cp["dist_min"]) & (actividades["km"] <= cp["dist_max"]) &
                (actividades["ritmo_min_km"].notna())
            ].sort_values("ritmo_min_km")
            if not match.empty:
                mejor = float(match.iloc[0]["ritmo_min_km"])
        logrado = mejor is not None and cp["dist_min"] is not None and mejor <= cp["ritmo_max"]
        filas.append({"checkpoint": cp["nombre"], "estado": "Hecho" if logrado else "Pendiente",
                      "detalle": cp["detalle"], "mejor_ritmo": mejor})
    return pd.DataFrame(filas)


def _fmt_tiempo_segundos(segundos):
    if segundos is None:
        return "-"
    total = int(round(float(segundos)))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


@st.cache_data(ttl=1800)
def checkpoints_objetivo_dashboard(usuario_id, objetivo_tipo=None):
    """Tarjetas de rendimiento por distancia con estado automático Hecho/Pendiente."""
    objetivo_txt = (objetivo_tipo or "").strip().lower()
    if objetivo_txt in ("ultramaraton", "ultra", "trail_ultra"):
        return []

    objetivos = [
        {
            "titulo": "5K",
            "meta_seg": 22 * 60 + 30,
            "meta_txt": "Sub 22:30",
            "dist_min_km": 4.6,
            "dist_max_km": 5.4,
            "detalle": "Demuestra la velocidad máxima necesaria",
            "accent": "#00db81",
        },
        {
            "titulo": "10K",
            "meta_seg": 46 * 60 + 30,
            "meta_txt": "Sub 46:30",
            "dist_min_km": 9.2,
            "dist_max_km": 10.8,
            "detalle": "Confirma umbral y capacidad de sostener el ritmo",
            "accent": "#1ec8ff",
        },
        {
            "titulo": "Media Maratón",
            "meta_seg": 1 * 3600 + 42 * 60,
            "meta_txt": "Sub 1h42",
            "dist_min_km": 20.0,
            "dist_max_km": 22.2,
            "detalle": "El checkpoint definitivo para el ritmo de maratón",
            "accent": "#a855f7",
        },
    ]

    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            "SELECT distancia_m, tiempo_seg, ritmo_medio, tipo_deporte "
            "FROM actividades_garmin WHERE usuario_id = ?",
            conn,
            params=(usuario_id,),
        )
    finally:
        conn.close()

    if df.empty:
        return [
            {
                **cp,
                "estado": "Pendiente",
                "hecho": False,
                "mejor_seg": None,
                "mejor_txt": "-",
                "estado_txt": "Pendiente",
                "estado_hint": "Sin registros",
            }
            for cp in objetivos
        ]

    deporte = df.get("tipo_deporte", pd.Series([""] * len(df))).fillna("").astype(str).str.lower()
    filtro_run = (
        deporte.str.contains("run")
        | deporte.str.contains("carrer")
        | deporte.str.contains("trail")
        | deporte.str.contains("tread")
    )
    if filtro_run.any():
        df = df[filtro_run].copy()
    else:
        df = df.copy()

    df["distancia_m"] = pd.to_numeric(df.get("distancia_m"), errors="coerce")
    df["tiempo_seg"] = pd.to_numeric(df.get("tiempo_seg"), errors="coerce")
    df["ritmo_medio"] = pd.to_numeric(df.get("ritmo_medio"), errors="coerce")
    df["km"] = df["distancia_m"] / 1000.0

    sin_tiempo = df["tiempo_seg"].isna() | (df["tiempo_seg"] <= 0)
    tiene_ritmo = df["ritmo_medio"].notna() & (df["ritmo_medio"] > 0)
    tiene_km = df["km"].notna() & (df["km"] > 0)
    df.loc[sin_tiempo & tiene_ritmo & tiene_km, "tiempo_seg"] = (
        df.loc[sin_tiempo & tiene_ritmo & tiene_km, "ritmo_medio"]
        * 60.0
        * df.loc[sin_tiempo & tiene_ritmo & tiene_km, "km"]
    )

    tarjetas = []
    for cp in objetivos:
        bloque = df[
            (df["km"] >= cp["dist_min_km"])
            & (df["km"] <= cp["dist_max_km"])
            & (df["tiempo_seg"].notna())
            & (df["tiempo_seg"] > 0)
        ]
        mejor_seg = float(bloque["tiempo_seg"].min()) if not bloque.empty else None
        hecho = mejor_seg is not None and mejor_seg <= float(cp["meta_seg"])
        tarjetas.append(
            {
                **cp,
                "estado": "Hecho" if hecho else "Pendiente",
                "hecho": hecho,
                "mejor_seg": mejor_seg,
                "mejor_txt": _fmt_tiempo_segundos(mejor_seg) if mejor_seg is not None else "-",
                "estado_txt": "Hecho" if hecho else "Pendiente",
                "estado_hint": "Objetivo logrado" if hecho else ("Por mejorar" if mejor_seg is not None else "Sin registros"),
            }
        )
    return tarjetas


def progreso_running(df_act):
    if df_act.empty:
        return pd.DataFrame()
    run = df_act.copy()
    run["fecha_dt"] = pd.to_datetime(run["fecha"]).dt.tz_localize(None)
    run["km"] = run["distancia_m"].fillna(0) / 1000
    run = run.sort_values("fecha_dt")
    run["week"] = run["fecha_dt"].dt.to_period("W-MON").dt.start_time
    return run.groupby("week", as_index=False).agg(km_semana=("km", "sum"), fc_media=("fc_media", "mean"), sesiones=("km", "size"))


def _mapear_grupos_musculares(texto):
    t = (texto or "").lower()
    grupos = {
        "gluteos": ["glute", "gluteo", "glúteo"],
        "espalda biceps": ["espalda", "dorsal", "remo", "dominada", "bicep", "bícep"],
        "isquios": ["isquio", "femoral", "hamstring"],
        "cuadriceps": ["cuadrice", "cuádrice", "quad"],
        "gemelos": ["gemelo", "pantorrilla", "soleo"],
        "triceps": ["tricep", "trícep"],
        "hombro": ["hombro", "delto"],
        "abdominales": ["abdominal", "core", "abs"],
    }
    encontrados = [g for g, keys in grupos.items() if any(k in t for k in keys)]
    return encontrados if encontrados else ["abdominales"]


def progreso_fuerza_grupos(df_fuerza):
    if df_fuerza.empty:
        return pd.DataFrame()
    df = df_fuerza.copy()
    df["fecha_dt"] = pd.to_datetime(df["fecha"]).dt.tz_localize(None)
    df["peso"] = pd.to_numeric(df.get("peso", 0), errors="coerce").fillna(0)
    df["series"] = pd.to_numeric(df.get("series", 0), errors="coerce").fillna(0)
    df["repeticiones"] = pd.to_numeric(df.get("repeticiones", 0), errors="coerce").fillna(0)
    df["volumen"] = (df["peso"] * df["series"] * df["repeticiones"]).clip(lower=0)
    df.loc[df["volumen"] == 0, "volumen"] = (df["series"] * df["repeticiones"]).clip(lower=0)
    filas = []
    for _, row in df.iterrows():
        for g in _mapear_grupos_musculares(row.get("musculo_principal", "")):
            filas.append({"fecha_dt": row["fecha_dt"], "grupo": g, "volumen": row["volumen"], "ejercicio": row.get("ejercicio", "")})
    if not filas:
        return pd.DataFrame()
    out = pd.DataFrame(filas)
    return out.groupby(["fecha_dt", "grupo", "ejercicio"], as_index=False).agg(volumen=("volumen", "sum")).sort_values("fecha_dt")


@st.cache_data(ttl=1800)
def resumen_semana_con_delta(usuario_id) -> dict:
    """Métricas 7d con delta — optimizado: 4 queries en 1 sola llamada HTTP a Turso."""
    f7  = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    f14 = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    uid = int(usuario_id)

    # Aggregation queries: each returns (valor_actual_7d, valor_prev_7d)
    sqls = [
        f"SELECT COALESCE(SUM(CASE WHEN fecha>='{f7}' THEN distancia_m ELSE 0 END),0),"
        f"COALESCE(SUM(CASE WHEN fecha>='{f14}' AND fecha<'{f7}' THEN distancia_m ELSE 0 END),0)"
        f" FROM actividades_garmin WHERE usuario_id={uid}",
        f"SELECT COALESCE(SUM(CASE WHEN fecha>='{f7}' THEN 1 ELSE 0 END),0),"
        f"COALESCE(SUM(CASE WHEN fecha>='{f14}' AND fecha<'{f7}' THEN 1 ELSE 0 END),0)"
        f" FROM sesiones_fuerza WHERE usuario_id={uid}",
        f"SELECT AVG(CASE WHEN fecha>='{f7}' THEN horas_totales END),"
        f"AVG(CASE WHEN fecha>='{f14}' AND fecha<'{f7}' THEN horas_totales END)"
        f" FROM datos_sueno WHERE usuario_id={uid}",
        f"SELECT AVG(CASE WHEN fecha>='{f7}' THEN hrv_ms END),"
        f"AVG(CASE WHEN fecha>='{f14}' AND fecha<'{f7}' THEN hrv_ms END)"
        f" FROM datos_biometricos_premium WHERE usuario_id={uid}",
    ]

    conn = get_db_connection()
    try:
        from src.db.db_manager import TursoHTTPConnection
        if isinstance(conn, TursoHTTPConnection):
            # 1 HTTP round-trip para las 4 queries
            raw = conn._send(sqls)
            def _parse(r):
                rows = r.get("response", {}).get("result", {}).get("rows", [])
                if not rows:
                    return None, None
                cells = rows[0]
                def _v(c):
                    if not c or c.get("type") == "null":
                        return None
                    try:
                        return float(c["value"])
                    except Exception:
                        return None
                return (_v(cells[0]) if len(cells) > 0 else None,
                        _v(cells[1]) if len(cells) > 1 else None)
            km_m, km_p_raw = _parse(raw[0])
            fc_f, fp_f     = _parse(raw[1])
            sc,   sp        = _parse(raw[2])
            hc,   hp        = _parse(raw[3])
        else:
            # SQLite — una query por tabla (4 en vez de 8)
            def _row(sql):
                r = conn.execute(sql).fetchone()
                if not r:
                    return None, None
                return r[0], (r[1] if len(r) > 1 else None)
            km_m, km_p_raw = _row(sqls[0])
            fc_f, fp_f     = _row(sqls[1])
            sc,   sp        = _row(sqls[2])
            hc,   hp        = _row(sqls[3])
    except Exception:
        km_m = km_p_raw = fc_f = fp_f = 0
        sc = sp = hc = hp = None
    finally:
        conn.close()

    km_c = (km_m or 0) / 1000
    km_p = (km_p_raw / 1000) if km_p_raw else None
    fc   = int(fc_f or 0)
    fp   = int(fp_f or 0)

    def _d(c, p): return round(c - p, 1) if c is not None and p is not None else None

    return {"km": km_c, "km_delta": _d(km_c, km_p),
            "fuerza": fc, "fuerza_delta": _d(fc, fp),
            "sueno": sc, "sueno_delta": _d(sc, sp),
            "hrv": hc, "hrv_delta": _d(hc, hp)}


@st.cache_data(ttl=300)
def metricas_garmin(usuario_id) -> dict:
    """Últimas métricas biométricas para el grid del dashboard."""
    conn = get_db_connection()
    f7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    try:
        df_b = pd.read_sql_query(
            "SELECT hrv_ms,fc_reposo,body_battery_min,body_battery_max,carga_aguda,carga_cronica,"
            "cadencia_media,estres_medio,sleep_score FROM datos_biometricos_premium "
            "WHERE usuario_id=? AND fecha>=? ORDER BY fecha DESC LIMIT 7",
            conn, params=(usuario_id, f7))
        df_s = pd.read_sql_query(
            "SELECT horas_totales,score FROM datos_sueno WHERE usuario_id=? AND fecha>=? "
            "ORDER BY fecha DESC LIMIT 1", conn, params=(usuario_id, f7))
        df_c = pd.read_sql_query(
            "SELECT cadencia_media FROM actividades_garmin WHERE usuario_id=? AND fecha>=? "
            "AND cadencia_media IS NOT NULL ORDER BY fecha DESC LIMIT 10",
            conn, params=(usuario_id, f7))
    finally:
        conn.close()

    def _m(df, col):
        if df.empty or col not in df.columns: return None
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        return round(float(s.mean()), 1) if not s.empty else None
    def _f(df, col):
        if df.empty or col not in df.columns: return None
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        return float(s.iloc[0]) if not s.empty else None

    acwr = None
    if not df_b.empty and "carga_aguda" in df_b.columns:
        ag = pd.to_numeric(df_b["carga_aguda"], errors="coerce").dropna()
        cr = pd.to_numeric(df_b["carga_cronica"], errors="coerce").dropna()
        if len(ag) and len(cr) and float(cr.iloc[0]) > 0:
            acwr = round(float(ag.iloc[0]) / float(cr.iloc[0]), 2)

    cad = _m(df_c, "cadencia_media") if not df_c.empty else _m(df_b, "cadencia_media")
    return {"hrv": _m(df_b, "hrv_ms"), "sueno_h": _f(df_s, "horas_totales"),
            "sueno_score": _f(df_s, "score"), "body_battery": None,
            "cadencia": cad, "acwr": acwr, "fc_reposo": _m(df_b, "fc_reposo"),
            "estres": _m(df_b, "estres_medio")}


@st.cache_data(ttl=1800)
def progresion_pesos_ejercicios(usuario_id) -> pd.DataFrame:
    """Últimas 2 entradas por ejercicio con orden estable y delta de peso."""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            "SELECT e.ejercicio,e.grupo_muscular,e.peso,e.series,e.repeticiones,s.fecha,"
            "s.id AS sesion_id,e.id AS ejercicio_registro_id "
            "FROM ejercicios_fuerza e JOIN sesiones_fuerza s ON s.id=e.sesion_id "
            "WHERE s.usuario_id=? ORDER BY s.fecha DESC,s.id DESC,e.id DESC LIMIT 300",
            conn, params=(usuario_id,))
    finally:
        conn.close()
    if df.empty: return pd.DataFrame()
    df["ejercicio"] = df["ejercicio"].astype(str)
    df["ejercicio_key"] = df["ejercicio"].str.strip().str.lower().str.replace(r"\s+", " ", regex=True)
    df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["peso"] = pd.to_numeric(df["peso"], errors="coerce").fillna(0)
    filas = []
    for _, grp in df.groupby("ejercicio_key", dropna=False):
        grp = grp.sort_values(["fecha_dt", "sesion_id", "ejercicio_registro_id"], ascending=False)
        u = grp.iloc[0]
        p = grp.iloc[1] if len(grp) > 1 else None
        delta = round(float(u["peso"]) - float(p["peso"]), 1) if p is not None else 0.0
        badge = f"↑ +{delta}" if delta > 0 else (f"↓ {abs(delta)}" if delta < 0 else "=")
        peso_num = float(u["peso"]) if float(u["peso"]) > 0 else 0.0
        filas.append({"Ejercicio": str(u["ejercicio"]).strip(),
                  "Grupo": str(u.get("grupo_muscular") or "Sin grupo").strip(),
                  "Peso": peso_num if peso_num > 0 else "PC",
                  "_peso_num": peso_num,
                      "S×R": f"{int(u['series'])}×{int(u['repeticiones'])}",
                      "Δ": badge,
                  "_delta_num": delta,
                      "_trend": "up" if delta > 0 else ("dn" if delta < 0 else "eq"),
                      "_orden_fecha": u["fecha_dt"],
                      "_orden_sesion": int(u["sesion_id"]),
                      "_orden_reg": int(u["ejercicio_registro_id"]),
        })
    out = pd.DataFrame(filas)
    if out.empty:
        return out
    out = out.sort_values(["_orden_fecha", "_orden_sesion", "_orden_reg"], ascending=False)
    return out.reset_index(drop=True)


def construir_calendario_semanal_actividades(df_act, df_fuerza, semana_inicio):
    semana_fin = semana_inicio + timedelta(days=6)
    out = pd.DataFrame({"fecha": pd.date_range(start=semana_inicio, end=semana_fin, freq="D")})
    out["dia"] = out["fecha"].dt.day_name().map({
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miercoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sabado", "Sunday": "Domingo"})
    out["run_desc"] = ""
    out["gym_desc"] = ""
    if not df_act.empty:
        act = df_act.copy()
        act["fecha_dt"] = pd.to_datetime(act["fecha"]).dt.tz_localize(None).dt.date
        act["km"] = act["distancia_m"].fillna(0) / 1000
        semana_act = act[(act["fecha_dt"] >= semana_inicio.date()) & (act["fecha_dt"] <= semana_fin.date())]
        if not semana_act.empty:
            for _, r in semana_act.groupby("fecha_dt", as_index=False).agg(km=("km","sum"),total=("km","size")).iterrows():
                idx = out[out["fecha"].dt.date == r["fecha_dt"]].index
                if len(idx):
                    out.loc[idx[0], "run_desc"] = f"{r['total']} run · {r['km']:.1f} km"
    if not df_fuerza.empty:
        fuer = df_fuerza.copy()
        fuer["fecha_dt"] = pd.to_datetime(fuer["fecha"]).dt.date
        semana_f = fuer[(fuer["fecha_dt"] >= semana_inicio.date()) & (fuer["fecha_dt"] <= semana_fin.date())]
        if not semana_f.empty:
            for _, r in semana_f.groupby("fecha_dt", as_index=False).agg(total=("fecha","size")).iterrows():
                idx = out[out["fecha"].dt.date == r["fecha_dt"]].index
                if len(idx):
                    out.loc[idx[0], "gym_desc"] = f"{r['total']} sesion fuerza"
    out["actividad"] = out.apply(
        lambda r: " | ".join([x for x in [r["run_desc"], r["gym_desc"]] if x]) or "Descanso / movilidad", axis=1)
    return out


@st.cache_data(ttl=300)
def cargar_plan_semana_cache(usuario_id: int, lunes_str: str) -> dict:
    """Carga el plan semanal con cache de 5 min para el dashboard."""
    from src.plan.motor import generar_plan_semana
    try:
        lunes = datetime.strptime(lunes_str, "%Y-%m-%d")
        return generar_plan_semana(usuario_id, lunes)
    except Exception:
        return {}


@st.cache_data(ttl=1800)
def cargar_km_por_semana(usuario_id: int, semanas: int = 8) -> pd.DataFrame:
    """
    Devuelve DataFrame con columnas [week_label, km_semana, sesiones]
    para las últimas N semanas de running (actividades_garmin).
    """
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            """SELECT fecha, distancia_m FROM actividades_garmin
               WHERE usuario_id=?
               AND tipo_deporte IN ('running','trail_running','treadmill_running','track_running')
               AND fecha >= date('now', '-' || ? || ' days')
               ORDER BY fecha ASC""",
            conn, params=(usuario_id, semanas * 7))
        if df.empty:
            return pd.DataFrame(columns=["week_label", "km_semana", "sesiones"])
        df["fecha_dt"] = pd.to_datetime(df["fecha"]).dt.tz_localize(None)
        df["km"]       = df["distancia_m"].fillna(0) / 1000
        df["week"]     = df["fecha_dt"].dt.to_period("W-MON").dt.start_time
        agg = df.groupby("week", as_index=False).agg(
            km_semana=("km", "sum"),
            sesiones=("km",  "size"),
        ).sort_values("week")
        # Etiqueta legible "Sem DD/MM"
        agg["week_label"] = agg["week"].dt.strftime("%-d/%m")
        return agg[["week_label", "km_semana", "sesiones"]]
    except Exception:
        return pd.DataFrame(columns=["week_label", "km_semana", "sesiones"])
    finally:
        conn.close()
