"""
src/plan/helpers.py
Carga de datos desde BD y distribución semanal de sesiones.
Extraído de motor.py para mantenerlo bajo 200 líneas.
"""

import pandas as pd
from datetime import datetime, timedelta

from src.db.db_manager import get_db_connection

_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Template por fase: 7 slots, uno por día de semana (L→D).
# "calidad" = sesión de calidad según fase. "tl" = tirada larga. "regen" = regenerativo.
_TEMPLATES = {
    "Acondicionamiento": [
        {"tipo": "Fuerza",          "carrera": False, "fuerza_p": True,  "intensidad": "Media",     "km_base": 0},
        {"tipo": "Carrera Z2",      "carrera": True,  "fuerza_p": False, "intensidad": "Baja",      "km_base": 5},
        {"tipo": "Fuerza",          "carrera": False, "fuerza_p": True,  "intensidad": "Media",     "km_base": 0},
        {"tipo": "Calidad",         "carrera": True,  "fuerza_p": False, "intensidad": "Media-Alta","km_base": 6},
        {"tipo": "Fuerza",          "carrera": False, "fuerza_p": True,  "intensidad": "Media",     "km_base": 0},
        {"tipo": "Tirada Larga",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",      "km_base": 0, "tl": True},
        {"tipo": "Regenerativo",    "carrera": True,  "fuerza_p": False, "intensidad": "Muy baja",  "km_base": 0, "regen": True},
    ],
    "Preparación General": [
        {"tipo": "Regenerativo",    "carrera": True,  "fuerza_p": False, "intensidad": "Muy baja",  "km_base": 0, "regen": True},
        {"tipo": "Fuerza",          "carrera": False, "fuerza_p": True,  "intensidad": "Alta",      "km_base": 0},
        {"tipo": "Carrera Z2",      "carrera": True,  "fuerza_p": False, "intensidad": "Baja",      "km_base": 7},
        {"tipo": "Fuerza",          "carrera": False, "fuerza_p": True,  "intensidad": "Alta",      "km_base": 0},
        {"tipo": "Calidad",         "carrera": True,  "fuerza_p": False, "intensidad": "Alta",      "km_base": 8},
        {"tipo": "Fuerza",          "carrera": False, "fuerza_p": True,  "intensidad": "Media",     "km_base": 0},
        {"tipo": "Tirada Larga",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",      "km_base": 0, "tl": True},
    ],
    "Preparación Específica": [
        {"tipo": "Regenerativo",    "carrera": True,  "fuerza_p": False, "intensidad": "Muy baja",  "km_base": 0, "regen": True},
        {"tipo": "Carrera Z2",      "carrera": True,  "fuerza_p": False, "intensidad": "Baja",      "km_base": 8},
        {"tipo": "Fuerza",          "carrera": False, "fuerza_p": True,  "intensidad": "Media",     "km_base": 0},
        {"tipo": "Calidad",         "carrera": True,  "fuerza_p": False, "intensidad": "Alta",      "km_base": 10},
        {"tipo": "Carrera Z2",      "carrera": True,  "fuerza_p": False, "intensidad": "Baja",      "km_base": 8},
        {"tipo": "Fuerza",          "carrera": False, "fuerza_p": True,  "intensidad": "Media",     "km_base": 0},
        {"tipo": "Tirada Larga",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",      "km_base": 0, "tl": True},
    ],
    "Pico de Forma": [
        {"tipo": "Regenerativo",    "carrera": True,  "fuerza_p": False, "intensidad": "Muy baja",  "km_base": 0, "regen": True},
        {"tipo": "Carrera Z2",      "carrera": True,  "fuerza_p": False, "intensidad": "Baja",      "km_base": 10},
        {"tipo": "Fuerza",          "carrera": False, "fuerza_p": True,  "intensidad": "Media",     "km_base": 0},
        {"tipo": "Calidad",         "carrera": True,  "fuerza_p": False, "intensidad": "Alta",      "km_base": 12},
        {"tipo": "Carrera Z2",      "carrera": True,  "fuerza_p": False, "intensidad": "Baja",      "km_base": 10},
        {"tipo": "Fuerza",          "carrera": False, "fuerza_p": True,  "intensidad": "Media",     "km_base": 0},
        {"tipo": "Tirada Larga",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",      "km_base": 0, "tl": True},
    ],
    "Tapering": [
        {"tipo": "Descanso",        "carrera": False, "fuerza_p": False, "intensidad": "—",         "km_base": 0},
        {"tipo": "Carrera Z2",      "carrera": True,  "fuerza_p": False, "intensidad": "Baja",      "km_base": 5},
        {"tipo": "Fuerza Activ.",   "carrera": False, "fuerza_p": False, "intensidad": "Baja",      "km_base": 0},
        {"tipo": "Calidad",         "carrera": True,  "fuerza_p": False, "intensidad": "Media",     "km_base": 6},
        {"tipo": "Descanso",        "carrera": False, "fuerza_p": False, "intensidad": "—",         "km_base": 0},
        {"tipo": "Rodaje Corto",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",      "km_base": 4},
        {"tipo": "Tirada Larga",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",      "km_base": 0, "tl": True},
    ],
}

_NOMBRE_CALIDAD = {
    "progresiva": "Progresiva",
    "intervalos_vo2max": "Intervalos VO2max",
    "tempo": "Tempo (umbral)",
}

# Templates específicos para ultramaratón (más volumen, back-to-back sábado+domingo)
_TEMPLATES_ULTRA = {
    "Acondicionamiento": [
        {"tipo": "Fuerza",        "carrera": False, "fuerza_p": True,  "intensidad": "Media",    "km_base": 0},
        {"tipo": "Carrera Z2",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 8},
        {"tipo": "Fuerza",        "carrera": False, "fuerza_p": True,  "intensidad": "Media",    "km_base": 0},
        {"tipo": "Calidad",       "carrera": True,  "fuerza_p": False, "intensidad": "Media-Alta","km_base": 10},
        {"tipo": "Fuerza",        "carrera": False, "fuerza_p": True,  "intensidad": "Media",    "km_base": 0},
        {"tipo": "Tirada Larga",  "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 0, "tl": True},
        {"tipo": "Regenerativo",  "carrera": True,  "fuerza_p": False, "intensidad": "Muy baja", "km_base": 0, "regen": True},
    ],
    "Preparación General": [
        {"tipo": "Regenerativo",  "carrera": True,  "fuerza_p": False, "intensidad": "Muy baja", "km_base": 0, "regen": True},
        {"tipo": "Carrera Z2",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 12},
        {"tipo": "Fuerza",        "carrera": False, "fuerza_p": True,  "intensidad": "Alta",     "km_base": 0},
        {"tipo": "Calidad",       "carrera": True,  "fuerza_p": False, "intensidad": "Alta",     "km_base": 12},
        {"tipo": "Fuerza",        "carrera": False, "fuerza_p": True,  "intensidad": "Alta",     "km_base": 0},
        {"tipo": "Tirada Larga",  "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 0, "tl": True},
        {"tipo": "Back-to-Back",  "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 0, "regen": True},
    ],
    "Preparación Específica": [
        {"tipo": "Regenerativo",  "carrera": True,  "fuerza_p": False, "intensidad": "Muy baja", "km_base": 0, "regen": True},
        {"tipo": "Carrera Z2",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 14},
        {"tipo": "Fuerza",        "carrera": False, "fuerza_p": True,  "intensidad": "Media",    "km_base": 0},
        {"tipo": "Calidad",       "carrera": True,  "fuerza_p": False, "intensidad": "Alta",     "km_base": 14},
        {"tipo": "Carrera Z2",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 12},
        {"tipo": "Tirada Larga",  "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 0, "tl": True},
        {"tipo": "Back-to-Back",  "carrera": True,  "fuerza_p": False, "intensidad": "Muy baja", "km_base": 0, "regen": True},
    ],
    "Pico de Forma": [
        {"tipo": "Regenerativo",  "carrera": True,  "fuerza_p": False, "intensidad": "Muy baja", "km_base": 0, "regen": True},
        {"tipo": "Carrera Z2",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 16},
        {"tipo": "Fuerza",        "carrera": False, "fuerza_p": True,  "intensidad": "Media",    "km_base": 0},
        {"tipo": "Calidad",       "carrera": True,  "fuerza_p": False, "intensidad": "Alta",     "km_base": 16},
        {"tipo": "Carrera Z2",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 14},
        {"tipo": "Tirada Larga",  "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 0, "tl": True},
        {"tipo": "Back-to-Back",  "carrera": True,  "fuerza_p": False, "intensidad": "Muy baja", "km_base": 0, "regen": True},
    ],
    "Tapering": [
        {"tipo": "Descanso",      "carrera": False, "fuerza_p": False, "intensidad": "—",        "km_base": 0},
        {"tipo": "Carrera Z2",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 8},
        {"tipo": "Fuerza Activ.", "carrera": False, "fuerza_p": False, "intensidad": "Baja",     "km_base": 0},
        {"tipo": "Calidad",       "carrera": True,  "fuerza_p": False, "intensidad": "Media",    "km_base": 8},
        {"tipo": "Descanso",      "carrera": False, "fuerza_p": False, "intensidad": "—",        "km_base": 0},
        {"tipo": "Rodaje Corto",  "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 6},
        {"tipo": "Regenerativo",  "carrera": True,  "fuerza_p": False, "intensidad": "Muy baja", "km_base": 0, "regen": True},
    ],
    "Post-Carrera": [
        {"tipo": "Descanso",      "carrera": False, "fuerza_p": False, "intensidad": "—",        "km_base": 0},
        {"tipo": "Movilidad",     "carrera": False, "fuerza_p": False, "intensidad": "Muy baja", "km_base": 0},
        {"tipo": "Regenerativo",  "carrera": True,  "fuerza_p": False, "intensidad": "Muy baja", "km_base": 0, "regen": True},
        {"tipo": "Movilidad",     "carrera": False, "fuerza_p": False, "intensidad": "Muy baja", "km_base": 0},
        {"tipo": "Descanso",      "carrera": False, "fuerza_p": False, "intensidad": "—",        "km_base": 0},
        {"tipo": "Carrera Z2",    "carrera": True,  "fuerza_p": False, "intensidad": "Baja",     "km_base": 6},
        {"tipo": "Regenerativo",  "carrera": True,  "fuerza_p": False, "intensidad": "Muy baja", "km_base": 0, "regen": True},
    ],
}


def cargar_datos_plan(usuario_id: int) -> dict:
    """
    Carga TODOS los datos relevantes para generar el plan semanal:
    HRV, sueño (score + breakdown), lesiones, km, cadencia, ACWR,
    métricas running específicas, ciclo menstrual, stress, body battery,
    VO2max, training status + perfil del usuario (género, fecha_objetivo, objetivo_tipo).
    """
    from src.db.db_manager import obtener_perfil
    perfil_usuario = obtener_perfil(usuario_id) or {}

    conn = get_db_connection()
    fecha_7d = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    fecha_28d = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")
    fecha_60d = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    try:
        df_bio = pd.read_sql_query(
            """SELECT fecha, hrv_ms, fc_reposo, sleep_score, spo2, estres_medio,
                      body_battery, body_battery_max, body_battery_min, training_status
               FROM datos_biometricos_premium
               WHERE usuario_id=? AND fecha>=? ORDER BY fecha DESC""",
            conn, params=(usuario_id, fecha_7d))

        df_sueno = pd.read_sql_query(
            """SELECT fecha, score, horas_totales, sleep_profundo_horas,
                      sleep_rem_horas, sleep_vigilia_horas, despertares
               FROM datos_sueno WHERE usuario_id=? AND fecha>=? ORDER BY fecha DESC""",
            conn, params=(usuario_id, fecha_7d))

        try:
            df_lesiones = pd.read_sql_query(
                "SELECT tipo AS zona, grado FROM lesiones WHERE usuario_id=? AND activa=1",
                conn, params=(usuario_id,))
        except Exception:
            df_lesiones = pd.DataFrame(columns=["zona", "grado"])

        try:
            df_lesiones_hist = pd.read_sql_query(
                "SELECT zona, tipo, grado FROM historial_lesiones WHERE usuario_id=? AND activa=1",
                conn, params=(usuario_id,))
        except Exception:
            df_lesiones_hist = pd.DataFrame(columns=["zona", "tipo", "grado"])

        # FIX: filtrar solo actividades de carrera para no contaminar km/cadencia con ciclismo/natación
        _TIPOS_CARRERA = "('running', 'trail_running', 'treadmill', 'indoor_running', 'track_running', 'road_running')"
        df_act = pd.read_sql_query(
            f"""SELECT fecha, distancia_m, cadencia_media, ritmo_medio, fc_media, fc_max,
                      potencia_media_w, longitud_zancada_m, tiempo_contacto_ms,
                      oscilacion_vertical_cm, training_effect_aerobico, training_effect_anaerobico
               FROM actividades_garmin
               WHERE usuario_id=? AND fecha>=?
               AND (tipo_deporte IN {_TIPOS_CARRERA} OR tipo_deporte IS NULL)
               ORDER BY fecha DESC""",
            conn, params=(usuario_id, fecha_7d))

        df_act_28d = pd.read_sql_query(
            f"SELECT fecha, distancia_m FROM actividades_garmin "
            f"WHERE usuario_id=? AND fecha>=?"
            f" AND (tipo_deporte IN {_TIPOS_CARRERA} OR tipo_deporte IS NULL)",
            conn, params=(usuario_id, fecha_28d))

        df_carga = pd.read_sql_query(
            "SELECT carga_aguda, carga_cronica FROM datos_biometricos_premium "
            "WHERE usuario_id=? AND fecha>=? AND carga_aguda IS NOT NULL ORDER BY fecha DESC LIMIT 1",
            conn, params=(usuario_id, fecha_28d))

        df_z2 = pd.read_sql_query(
            f"SELECT fecha, ritmo_medio, fc_media FROM actividades_garmin "
            f"WHERE usuario_id=? AND fecha>=? AND fc_media BETWEEN 120 AND 150"
            f" AND (tipo_deporte IN {_TIPOS_CARRERA} OR tipo_deporte IS NULL)",
            conn, params=(usuario_id, fecha_28d))

        # Ciclo menstrual — usar último registro y, si existe historial, inferir fase actual
        fase_ciclo = None
        try:
            row_ciclo = conn.execute(
                "SELECT fase_ciclo, fecha, fatiga_subjetiva, estado_animo "
                "FROM diario_fisiologia WHERE usuario_id=? AND fase_ciclo IS NOT NULL "
                "ORDER BY fecha DESC LIMIT 1",
                (usuario_id,)).fetchone()
            if row_ciclo:
                fase_ciclo = {
                    "fase": row_ciclo[0],
                    "fecha": row_ciclo[1],
                    "fatiga_subjetiva": row_ciclo[2],
                    "estado_animo": row_ciclo[3],
                    "origen": "Registrado",
                }

            df_ciclo_hist = pd.read_sql_query(
                "SELECT fecha, fase_ciclo, sangre FROM diario_fisiologia "
                "WHERE usuario_id=? AND fecha>=? ORDER BY fecha ASC",
                conn, params=(usuario_id, fecha_28d))
            if not df_ciclo_hist.empty:
                from datetime import date
                from src.core.ciclo_helpers import predecir_fases_ciclo

                ciclo_df, _ = predecir_fases_ciclo(df_ciclo_hist, horizonte_dias=40)
                hoy = date.today()
                fila_hoy = ciclo_df[ciclo_df["fecha"] == hoy]
                if not fila_hoy.empty:
                    fase_hoy = str(fila_hoy.iloc[0].get("fase_ciclo") or "").strip()
                    origen_hoy = str(fila_hoy.iloc[0].get("origen") or "Predicho").strip()
                    if fase_hoy:
                        if fase_ciclo is None:
                            fase_ciclo = {}
                        fase_ciclo["fase"] = fase_hoy
                        fase_ciclo["origen"] = origen_hoy
        except Exception:
            pass

        # --- FC Reposo fallback: buscar en 28d si no encontró en 7d ---
        df_bio_28d = None
        try:
            df_bio_28d = pd.read_sql_query(
                """SELECT fc_reposo FROM datos_biometricos_premium
                   WHERE usuario_id=? AND fecha>=? AND fc_reposo IS NOT NULL
                   ORDER BY fecha DESC LIMIT 3""",
                conn, params=(usuario_id, fecha_28d))
        except Exception:
            pass

    finally:
        conn.close()

    # --- HRV ---
    hrv_actual = hrv_media = hrv_media_60d = None
    if not df_bio.empty:
        df_h = df_bio.dropna(subset=["hrv_ms"])
        if not df_h.empty:
            hrv_actual = float(df_h.iloc[0]["hrv_ms"])
            hrv_media = float(df_h["hrv_ms"].mean())

    # --- HRV 60-day baseline (Bevel-style) ---
    try:
        df_bio_60d = pd.read_sql_query(
            """SELECT hrv_ms FROM datos_biometricos_premium
               WHERE usuario_id=? AND fecha>=? AND hrv_ms IS NOT NULL
               ORDER BY fecha DESC""",
            conn, params=(usuario_id, fecha_60d))
        if not df_bio_60d.empty:
            hrv_media_60d = float(df_bio_60d["hrv_ms"].mean())
    except Exception:
        pass

    # --- FC Reposo (buscar en últimos 7d, luego fallback a 28d) ---
    fc_reposo = None
    if not df_bio.empty and "fc_reposo" in df_bio.columns:
        df_fc = df_bio.dropna(subset=["fc_reposo"])
        if not df_fc.empty:
            # Si hay múltiples registros, usar el promedio de los últimos 3 días
            fc_reposo_values = df_fc["fc_reposo"].head(3).values
            if len(fc_reposo_values) > 0:
                fc_reposo = int(round(float(fc_reposo_values.mean())))

    # Si no encontró en 7d, buscar en 28d (ya cargado en el try block)
    if fc_reposo is None and df_bio_28d is not None and not df_bio_28d.empty:
        fc_reposo = int(round(float(df_bio_28d["fc_reposo"].mean())))

    # --- Sleep score ---
    sleep_score = None
    # Primero buscar en datos_sueno.score (más confiable)
    if not df_sueno.empty:
        df_s = df_sueno.dropna(subset=["score"])
        if not df_s.empty:
            sleep_score = float(df_s.iloc[0]["score"])
    # Fallback a datos_biometricos_premium.sleep_score
    if sleep_score is None and not df_bio.empty:
        df_s2 = df_bio.dropna(subset=["sleep_score"])
        if not df_s2.empty:
            sleep_score = float(df_s2.iloc[0]["sleep_score"])

    # --- Sleep breakdown (último disponible) ---
    sleep_breakdown = {}
    if not df_sueno.empty:
        ultimo = df_sueno.iloc[0]
        sleep_breakdown = {
            "horas_totales": ultimo.get("horas_totales"),
            "profundo_h": ultimo.get("sleep_profundo_horas"),
            "rem_h": ultimo.get("sleep_rem_horas"),
            "vigilia_h": ultimo.get("sleep_vigilia_horas"),
            "despertares": ultimo.get("despertares"),
        }

    # --- Lesiones ---
    lesiones = []
    if not df_lesiones.empty:
        lesiones = [{"zona": r["zona"], "grado": int(r["grado"] or 1)} for _, r in df_lesiones.iterrows()]
    elif not df_lesiones_hist.empty:
        lesiones = [{"zona": r.get("zona") or r.get("tipo", ""), "grado": int(r["grado"] or 1)}
                    for _, r in df_lesiones_hist.iterrows()]

    # --- Km semana (solo carrera, filtrado en query) ---
    km_anterior = float(df_act["distancia_m"].fillna(0).sum() / 1000) if not df_act.empty else 0.0
    if km_anterior == 0.0 and not df_act_28d.empty:
        # df_act_28d ahora cubre 28d completos; calcular promedio semanal (4 semanas)
        km_anterior = float(df_act_28d["distancia_m"].fillna(0).sum() / 1000 / 4)

    # --- Cadencia ---
    cadencia = None
    if not df_act.empty and "cadencia_media" in df_act.columns:
        c = df_act.dropna(subset=["cadencia_media"])
        if not c.empty:
            cadencia = float(c["cadencia_media"].mean())

    # --- ACWR (Acute/Chronic Workload Ratio) ---
    acwr = 1.0
    if not df_carga.empty:
        ag, cr = df_carga.iloc[0]["carga_aguda"], df_carga.iloc[0]["carga_cronica"]
        if ag and cr and float(cr) > 0:
            acwr = round(float(ag) / float(cr), 2)

    # --- Métricas running específicas (promedios últimos 7d) ---
    metricas_running = {}
    if not df_act.empty:
        cols_run = ["potencia_media_w", "longitud_zancada_m", "tiempo_contacto_ms",
                    "oscilacion_vertical_cm", "training_effect_aerobico", "training_effect_anaerobico"]
        for col in cols_run:
            if col in df_act.columns:
                serie = df_act[col].dropna()
                if not serie.empty:
                    metricas_running[col] = round(float(serie.mean()), 2)
        # Ritmo y FC medios en carreras recientes
        if "ritmo_medio" in df_act.columns:
            rm = df_act["ritmo_medio"].dropna()
            if not rm.empty:
                metricas_running["ritmo_medio"] = round(float(rm.mean()), 2)
        if "fc_media" in df_act.columns:
            fm = df_act["fc_media"].dropna()
            if not fm.empty:
                metricas_running["fc_media"] = round(float(fm.mean()), 1)

    # --- Stress, Body Battery, VO2max, Training Status (último disponible) ---
    estres_medio = body_battery = body_battery_max = body_battery_min = vo2max = training_status = None
    if not df_bio.empty:
        for col, var in [("estres_medio", "estres_medio"), ("body_battery", "body_battery"), ("body_battery_max", "body_battery_max"),
                         ("body_battery_min", "body_battery_min"), ("vo2max", "vo2max")]:
            if col in df_bio.columns:
                s = df_bio[col].dropna()
                if not s.empty:
                    val = float(s.iloc[0])
                    if col == "estres_medio":
                        estres_medio = int(val)
                    elif col == "body_battery":
                        body_battery = int(val)
                    elif col == "body_battery_max":
                        body_battery_max = int(val)
                    elif col == "body_battery_min":
                        body_battery_min = int(val)
                    elif col == "vo2max":
                        vo2max = val
    # Compatibilidad entre fuentes Garmin: usar body_battery simple si no hay min/max.
    if body_battery is not None:
        if body_battery_min is None:
            body_battery_min = body_battery
        if body_battery_max is None:
            body_battery_max = body_battery
        if "training_status" in df_bio.columns:
            ts_s = df_bio["training_status"].dropna()
            if not ts_s.empty:
                training_status = str(ts_s.iloc[0])

    z2_list = df_z2.to_dict("records") if not df_z2.empty else []

    # Últimas 3 actividades para análisis Training Effect
    ultimas_3_act = []
    if not df_act.empty:
        cols_te = ["training_effect_aerobico", "training_effect_anaerobico"]
        for i, (_, row) in enumerate(df_act.head(3).iterrows()):
            if i >= 3:
                break
            ultimas_3_act.append({
                "fecha": row.get("fecha"),
                "training_effect_aerobico": row.get("training_effect_aerobico"),
                "training_effect_anaerobico": row.get("training_effect_anaerobico"),
            })

    # --- HRV Recovery Evaluation ---
    from src.plan.reglas import evaluar_hrv_recovery, calcular_target_intensidad_bevel
    hrv_list = df_bio["hrv_ms"].dropna().tolist() if not df_bio.empty else []
    hrv_recovery = evaluar_hrv_recovery(
        hrv_data=hrv_list,
        sleep_score=sleep_score,
        estres_medio=estres_medio,
        body_battery_min=body_battery_min,
        body_battery_max=body_battery_max,
        carga_aguda=df_carga["carga_aguda"].iloc[0] if not df_carga.empty else None,
        carga_cronica=df_carga["carga_cronica"].iloc[0] if not df_carga.empty else None,
    )

    # --- Target Intensity (Bevel: HRV vs 60-day baseline) ---
    target_intensidad = calcular_target_intensidad_bevel(hrv_actual, hrv_media_60d)

    return {
        "hrv_actual": hrv_actual,
        "hrv_media_7d": hrv_media,
        "hrv_media_60d": hrv_media_60d,
        "hrv_recovery": hrv_recovery,
        "target_intensidad": target_intensidad,
        "fc_reposo": fc_reposo,
        "sleep_score": sleep_score,
        "sleep_breakdown": sleep_breakdown,
        "lesiones_activas": lesiones,
        "km_semana_anterior": km_anterior,
        "cadencia_media": cadencia,
        "acwr": acwr,
        "actividades_z2": z2_list,
        "metricas_running": metricas_running,
        "fase_ciclo": fase_ciclo,
        "ciclo_menstrual": fase_ciclo,
        "estres_medio": estres_medio,
        "body_battery": body_battery,
        "body_battery_max": body_battery_max,
        "body_battery_min": body_battery_min,
        "vo2max": vo2max,
        "training_status": training_status,
        "ultimas_3_actividades": ultimas_3_act,
        # Perfil del usuario
        "genero": perfil_usuario.get("genero", "Mujer"),
        "fecha_objetivo": perfil_usuario.get("fecha_objetivo"),
        "objetivo_tipo": perfil_usuario.get("objetivo_tipo", "maraton"),
        "nombre": perfil_usuario.get("nombre", "Atleta"),
    }


def distribuir_semana(fase: dict, km_objetivo: float, semaforo: dict,
                      restricciones: dict, fecha_inicio, cadencia_eval: dict = None,
                      sleep_breakdown: dict = None, objetivo_tipo: str = "maraton") -> list:
    """Construye los 7 días aplicando templates, semáforo y restricciones de lesión.
    Si cadencia < 170 spm: inserta 5min de drills técnica antes de carreras Z2.
    Si sleep profundo < 45 min: reduce series a Z2.
    objetivo_tipo: 'maraton' usa _TEMPLATES; 'ultramaraton'/'ultra' usa _TEMPLATES_ULTRA.
    """
    fase_nombre = fase["fase_nombre"]
    es_ultra = str(objetivo_tipo).lower() in ("ultramaraton", "ultra", "trail_ultra")
    catalogo = _TEMPLATES_ULTRA if es_ultra else _TEMPLATES
    tkey = next((k for k in catalogo if k in fase_nombre), "Acondicionamiento")
    template = catalogo[tkey]
    nombre_calidad = _NOMBRE_CALIDAD.get(fase.get("sesion_calidad", "progresiva"), "Calidad")

    if cadencia_eval is None:
        cadencia_eval = {"necesita_drills": False}

    # Detectar si sleep profundo es insuficiente (<45 min)
    sleep_insuficiente = False
    if sleep_breakdown and sleep_breakdown.get("profundo_h") is not None:
        if sleep_breakdown["profundo_h"] < 0.75:  # 45 min = 0.75 h
            sleep_insuficiente = True

    km_base_total = sum(t["km_base"] for t in template)
    km_tl = max(round(km_objetivo - km_base_total, 1), 6.0)
    km_regen = round(km_tl / 3, 1)

    dias = []
    for i, tpl in enumerate(template):
        fecha_dia = fecha_inicio + timedelta(days=i)
        tipo = tpl["tipo"]
        if tipo == "Calidad":
            tipo = nombre_calidad

        km = tpl["km_base"]
        if tpl.get("tl"):
            km = km_tl
        elif tpl.get("regen"):
            km = km_regen

        # FIX: ritmo estimado según intensidad de sesión (min/km), no fijo a 7
        _RITMO_MIN_KM = {"Muy baja": 7.5, "Baja": 6.5, "Media": 6.0,
                         "Media-Alta": 5.5, "Alta": 5.0, "—": 0}
        ritmo_est = _RITMO_MIN_KM.get(tpl["intensidad"], 6.5)
        dur = int(km * ritmo_est) if (tpl["carrera"] and km > 0) else (
            60 if not tpl["carrera"] and tpl["fuerza_p"] else 30)

        alerta = ""
        # Semáforo ROJO — solo advertencia, no modifica el plan
        if semaforo["color"] == "rojo" and tipo not in ("Descanso", "Regenerativo"):
            if tpl["carrera"]:
                alerta = "⛔ Semáforo rojo — considera bajar intensidad"
            elif tpl["fuerza_p"]:
                alerta = "⛔ Semáforo rojo — considera movilidad en vez de fuerza"

        # Semáforo ÁMBAR: no calidad — FIX: parentizar correctamente el `or`
        elif semaforo["color"] == "ambar" and (
                "Calidad" in tipo or tipo in ("Intervalos VO2max", "Tempo (umbral)", "Progresiva")):
            tipo, alerta = "Carrera Z2", "⚠️ Semáforo ámbar → cambiado a Z2"

        # Sleep profundo insuficiente: reducir series
        if sleep_insuficiente and tipo in ("Intervalos VO2max", "Tempo (umbral)", nombre_calidad, "Progresiva"):
            tipo, alerta = "Carrera Z2", "😴 Sleep profundo < 45 min → series reducidas a Z2"


        # Restricción carrera
        if restricciones["bloqueo_carrera"] and tpl["carrera"]:
            sustit = restricciones["sustituciones"][0] if restricciones["sustituciones"] else "Bici Z2 45min"
            tipo, km, dur, alerta = "Sustitución", 0, 45, f"🚫 Carrera bloqueada — {sustit}"

        # Restricción piernas
        if restricciones["bloqueo_piernas"] and tpl["fuerza_p"]:
            tipo, alerta = "Fuerza Tren Superior", "🚫 Piernas bloqueadas → tren superior"

        # Prohibir series
        if restricciones["prohibir_series"] and tipo in ("Intervalos VO2max", "Tempo (umbral)", nombre_calidad):
            tipo, alerta = "Carrera Z2", "⚠️ Series prohibidas por lesión → Z2"

        # Drills de cadencia: insertar 5min antes de carreras Z2 si cadencia < 170
        drill_info = ""
        if cadencia_eval.get("necesita_drills") and tipo == "Carrera Z2" and km > 0:
            drill_info = " + 5min drills técnica (cadencia)"
            if not alerta:
                alerta = f"📊 Cadencia baja: incluir drills técnicos"

        dias.append({"dia": _DIAS[i], "fecha": fecha_dia.strftime("%Y-%m-%d"),
                     "tipo": tipo + drill_info, "intensidad": tpl["intensidad"],
                     "km": km, "duracion_min": dur, "alerta": alerta})
    return dias
