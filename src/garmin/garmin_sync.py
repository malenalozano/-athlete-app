import os
import logging
from datetime import datetime, timedelta
from garminconnect import Garmin, GarminConnectConnectionError, GarminConnectAuthenticationError
from dotenv import load_dotenv
from src.db.db_manager import get_db_connection

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _column_exists(conn, table_name, column_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def _ensure_column(conn, table_name, column_name, column_type):
    if not _column_exists(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def _ensure_garmin_schema():
    conn = get_db_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS datos_sueno (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                fecha TEXT,
                horas_totales REAL,
                score INTEGER,
                UNIQUE(usuario_id, fecha)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS datos_biometricos_premium (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                fecha TEXT,
                hrv_ms REAL,
                fc_reposo INTEGER,
                fc_maxima INTEGER,
                cadencia_media REAL,
                longitud_zancada_m REAL,
                tiempo_contacto_ms REAL,
                oscilacion_vertical_cm REAL,
                sleep_score INTEGER,
                carga_aguda REAL,
                carga_cronica REAL,
                estres_vital INTEGER,
                rpe_sesion INTEGER,
                sensacion_notas TEXT,
                disponibilidad_min INTEGER,
                UNIQUE(usuario_id, fecha)
            )
            """
        )

        for col_name, col_type in [
            ("potencia_media_w", "REAL"),
            ("cadencia_media", "REAL"),
            ("longitud_zancada_m", "REAL"),
            ("tiempo_contacto_ms", "REAL"),
            ("oscilacion_vertical_cm", "REAL"),
            ("training_effect_aerobico", "REAL"),
            ("training_effect_anaerobico", "REAL"),
        ]:
            _ensure_column(conn, "actividades_garmin", col_name, col_type)

        for col_name, col_type in [
            ("sleep_profundo_horas", "REAL"),
            ("sleep_rem_horas", "REAL"),
            ("sleep_vigilia_horas", "REAL"),
            ("despertares", "INTEGER"),
        ]:
            _ensure_column(conn, "datos_sueno", col_name, col_type)

        for col_name, col_type in [
            ("spo2", "REAL"),
            ("potencia_media_w", "REAL"),
            ("vo2max", "REAL"),
            ("training_status", "TEXT"),
            ("body_battery_max", "INTEGER"),
            ("body_battery_min", "INTEGER"),
            ("estres_medio", "INTEGER"),
        ]:
            _ensure_column(conn, "datos_biometricos_premium", col_name, col_type)

        conn.commit()
    finally:
        conn.close()


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _search_values(obj, target_keys):
    found = []
    normalized = {k.lower() for k in target_keys}

    def _walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).lower() in normalized and value not in (None, ""):
                    found.append(value)
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(obj)
    return found


def _first_number(obj, keys):
    for value in _search_values(obj, keys):
        number = _to_float(value)
        if number is not None:
            return number
    return None


def _last_number(obj, keys):
    values = _search_values(obj, keys)
    for value in reversed(values):
        number = _to_float(value)
        if number is not None:
            return number
    return None


def _safe_api_call(fn, *args, **kwargs):
    """
    Ejecuta una llamada API de Garmin de forma segura, registrando errores.
    Retorna None si la llamada falla, pero registra qué pasó.
    """
    fn_name = getattr(fn, '__name__', str(fn))
    try:
        result = fn(*args, **kwargs)
        logger.debug(f"✅ {fn_name}({args}, {kwargs}) - OK")
        return result
    except GarminConnectAuthenticationError as e:
        logger.error(f"❌ {fn_name}: ERROR DE AUTENTICACIÓN - {e}")
        return None
    except GarminConnectConnectionError as e:
        logger.error(f"❌ {fn_name}: ERROR DE CONEXIÓN - {e}")
        return None
    except Exception as e:
        logger.warning(f"⚠️  {fn_name}({args}): {type(e).__name__}: {e}")
        return None


def _extract_activity_metrics(activity, summary, details):
    merged = {}
    for block in (activity or {}, summary or {}, details or {}):
        if isinstance(block, dict):
            merged.update(block)

    return {
        "potencia_media_w": _first_number(merged, ["averagePower", "avgPower", "power"]),
        "cadencia_media": _first_number(merged, ["averageRunCadence", "avgRunCadence", "averageCadence", "avgCadence"]),
        "longitud_zancada_m": _first_number(merged, ["avgStrideLength", "averageStrideLength", "strideLength"]),
        "tiempo_contacto_ms": _first_number(merged, ["avgGroundContactTime", "averageGroundContactTime", "groundContactTime"]),
        "oscilacion_vertical_cm": _first_number(merged, ["avgVerticalOscillation", "averageVerticalOscillation", "verticalOscillation"]),
        "training_effect_aerobico": _first_number(merged, ["aerobicTrainingEffect", "aerobicTE", "aerobicTrainingEffectLabel"]),
        "training_effect_anaerobico": _first_number(merged, ["anaerobicTrainingEffect", "anaerobicTE"]),
    }


def _extract_sleep_metrics(data, fecha_iso):
    if not data:
        return None

    score = None
    if isinstance(data.get("overallSleepScore"), dict):
        score = _to_int(data.get("overallSleepScore", {}).get("value"))

    total_seg = _first_number(data, ["sleepTimeSeconds", "totalSleepSeconds", "overallSleepDurationSeconds"])
    deep_seg = _first_number(data, ["deepSleepSeconds"])
    rem_seg = _first_number(data, ["remSleepSeconds"])
    awake_seg = _first_number(data, ["awakeSleepSeconds", "awakeSeconds", "sleepAwakeSeconds"])
    awakenings = _to_int(_first_number(data, ["awakeCount", "awakeningsCount", "restlessMomentsCount"]))

    return {
        "fecha": fecha_iso,
        "horas_totales": round((total_seg or 0) / 3600, 2),
        "score": score,
        "sleep_profundo_horas": round((deep_seg or 0) / 3600, 2),
        "sleep_rem_horas": round((rem_seg or 0) / 3600, 2),
        "sleep_vigilia_horas": round((awake_seg or 0) / 3600, 2),
        "despertares": awakenings,
    }


def _extract_daily_metrics(client, fecha_iso):
    """
    Extrae métricas diarias de Garmin para una fecha específica.
    Incluye: HRV, FC, SpO2, Stress, Body Battery, VO2max, Training Status.
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"EXTRAYENDO MÉTRICAS PARA {fecha_iso}")
    logger.info(f"{'='*70}")

    # HRV
    hrv_data = _safe_api_call(client.get_hrv_data, fecha_iso) or {}
    hrv_ms = _first_number(hrv_data, ["lastNightAverage", "averageHrv", "weeklyAverage", "hrvValue"])
    logger.info(f"  ✓ HRV: {hrv_ms} ms" if hrv_ms else "  ✗ HRV: No encontrado")

    # Heart Rates
    heart_rates = _safe_api_call(client.get_heart_rates, fecha_iso) or {}
    fc_reposo = _to_int(_first_number(heart_rates, ["restingHeartRate", "restHeartRate", "restingHR"]))
    fc_maxima = _to_int(_first_number(heart_rates, ["maxHeartRate", "maxHeartRateInBeatsPerMinute"]))
    logger.info(f"  ✓ FC Reposo: {fc_reposo}, FC Máxima: {fc_maxima}" if fc_reposo or fc_maxima else "  ✗ Heart Rates: No encontrado")

    # SpO2
    spo2_data = _safe_api_call(client.get_spo2_data, fecha_iso) or {}
    spo2 = _first_number(spo2_data, ["averageSpo2", "avgSpo2", "spo2"])
    logger.info(f"  ✓ SpO2: {spo2}" if spo2 else "  ✗ SpO2: No encontrado")

    # Stress
    stress_data = _safe_api_call(client.get_stress_data, fecha_iso) or {}
    if not stress_data:
        stress_data = _safe_api_call(getattr(client, 'get_all_day_stress', lambda x: None), fecha_iso) or {}
    estres_medio = _to_int(_first_number(stress_data, ["averageStressLevel", "avgStressLevel", "overallStressLevel"]))
    logger.info(f"  ✓ Estrés medio: {estres_medio}" if estres_medio else "  ✗ Estrés: No encontrado")

    # Body Battery
    body_battery_max = body_battery_min = None
    bb_data = _safe_api_call(getattr(client, 'get_body_battery', lambda x: None), fecha_iso)
    if bb_data:
        if isinstance(bb_data, list):
            valores = [_to_int(v) for item in bb_data for v in (_search_values(item, ["bodyBatteryLevel", "value"]) or []) if v is not None]
            if valores:
                body_battery_max = max(valores)
                body_battery_min = min(valores)
        elif isinstance(bb_data, dict):
            body_battery_max = _to_int(_first_number(bb_data, ["maxBodyBattery", "endOfDayBodyBattery"]))
            body_battery_min = _to_int(_first_number(bb_data, ["minBodyBattery"]))
    logger.info(f"  ✓ Body Battery: {body_battery_min}→{body_battery_max}" if body_battery_max else "  ✗ Body Battery: No encontrado")

    # VO2max
    vo2max = None
    max_metrics = _safe_api_call(getattr(client, 'get_max_metrics', lambda x: None), fecha_iso)
    if max_metrics:
        vo2max = _to_float(_first_number(max_metrics, ["vo2MaxValue", "vo2Max", "genericVO2MaxValue"]))
    if vo2max is None:
        # Fallback: buscar en user stats
        user_stats = _safe_api_call(getattr(client, 'get_user_summary', lambda x: None), fecha_iso) or {}
        vo2max = _to_float(_first_number(user_stats, ["vo2Max", "vo2MaxValue"]))
    logger.info(f"  ✓ VO2max: {vo2max}" if vo2max else "  ✗ VO2max: No encontrado")

    # Training Status
    training_status = None
    ts_data = _safe_api_call(getattr(client, 'get_training_status', lambda x: None), fecha_iso) or {}
    if ts_data:
        ts_raw = _search_values(ts_data, ["trainingStatusPhrase", "latestTrainingStatusPhrase", "trainingStatus"])
        if ts_raw:
            training_status = str(ts_raw[0]).lower()
    logger.info(f"  ✓ Training Status: {training_status}" if training_status else "  ✗ Training Status: No encontrado")

    logger.info(f"{'='*70}\n")

    return {
        "fecha": fecha_iso,
        "hrv_ms": hrv_ms,
        "fc_reposo": fc_reposo,
        "fc_maxima": fc_maxima,
        "spo2": spo2,
        "estres_medio": estres_medio,
        "body_battery_max": body_battery_max,
        "body_battery_min": body_battery_min,
        "vo2max": vo2max,
        "training_status": training_status,
    }


def _has_useful_daily_metrics(metrics):
    if not metrics:
        return False

    useful_keys = [
        "hrv_ms",
        "training_readiness",
        "body_battery",
        "recovery_hours",
        "fc_reposo",
        "fc_maxima",
        "estres_vital",
        "spo2",
        "sleep_score",
        "potencia_media_w",
        "cadencia_media",
        "longitud_zancada_m",
        "tiempo_contacto_ms",
        "oscilacion_vertical_cm",
    ]
    return any(metrics.get(key) is not None for key in useful_keys)


def _latest_running_metrics(client, num_actividades=10):
    actividades = _safe_api_call(client.get_activities, 0, num_actividades) or []
    resultados = []
    for actividad in actividades:
        tipo = str((actividad.get("activityType") or {}).get("typeKey", "")).lower()
        activity_id = str(actividad.get("activityId"))
        if not activity_id:
            continue
        summary = _safe_api_call(client.get_activity, activity_id) or {}
        details = _safe_api_call(client.get_activity_details, activity_id) or {}
        metrics = _extract_activity_metrics(actividad, summary, details)
        fecha = str(actividad.get("startTimeLocal", "")).split(" ", 1)[0]
        metrics["fecha"] = fecha
        metrics["tipo_deporte"] = tipo
        resultados.append(metrics)
    return resultados


def guardar_metricas_premium_db(usuario_id, datos):
    if not datos or not datos.get("fecha"):
        return

    _ensure_garmin_schema()
    conexion = get_db_connection()
    try:
        conexion.execute(
            """
            INSERT INTO datos_biometricos_premium (
                usuario_id, fecha, hrv_ms, fc_reposo, fc_maxima,
                cadencia_media, longitud_zancada_m, tiempo_contacto_ms,
                oscilacion_vertical_cm, sleep_score, spo2, potencia_media_w,
                vo2max, training_status, body_battery_max, body_battery_min, estres_medio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(usuario_id, fecha) DO UPDATE SET
                hrv_ms = COALESCE(excluded.hrv_ms, datos_biometricos_premium.hrv_ms),
                fc_reposo = COALESCE(excluded.fc_reposo, datos_biometricos_premium.fc_reposo),
                fc_maxima = COALESCE(excluded.fc_maxima, datos_biometricos_premium.fc_maxima),
                cadencia_media = COALESCE(excluded.cadencia_media, datos_biometricos_premium.cadencia_media),
                longitud_zancada_m = COALESCE(excluded.longitud_zancada_m, datos_biometricos_premium.longitud_zancada_m),
                tiempo_contacto_ms = COALESCE(excluded.tiempo_contacto_ms, datos_biometricos_premium.tiempo_contacto_ms),
                oscilacion_vertical_cm = COALESCE(excluded.oscilacion_vertical_cm, datos_biometricos_premium.oscilacion_vertical_cm),
                sleep_score = COALESCE(excluded.sleep_score, datos_biometricos_premium.sleep_score),
                spo2 = COALESCE(excluded.spo2, datos_biometricos_premium.spo2),
                potencia_media_w = COALESCE(excluded.potencia_media_w, datos_biometricos_premium.potencia_media_w),
                vo2max = COALESCE(excluded.vo2max, datos_biometricos_premium.vo2max),
                training_status = COALESCE(excluded.training_status, datos_biometricos_premium.training_status),
                body_battery_max = COALESCE(excluded.body_battery_max, datos_biometricos_premium.body_battery_max),
                body_battery_min = COALESCE(excluded.body_battery_min, datos_biometricos_premium.body_battery_min),
                estres_medio = COALESCE(excluded.estres_medio, datos_biometricos_premium.estres_medio)
            """,
            (
                usuario_id,
                datos.get("fecha"),
                datos.get("hrv_ms"),
                datos.get("fc_reposo"),
                datos.get("fc_maxima"),
                datos.get("cadencia_media"),
                datos.get("longitud_zancada_m"),
                datos.get("tiempo_contacto_ms"),
                datos.get("oscilacion_vertical_cm"),
                datos.get("sleep_score"),
                datos.get("spo2"),
                datos.get("potencia_media_w"),
                datos.get("vo2max"),
                datos.get("training_status"),
                datos.get("body_battery_max"),
                datos.get("body_battery_min"),
                datos.get("estres_medio"),
            ),
        )
        conexion.commit()
    finally:
        conexion.close()

_RUNNING_KEYWORDS = {"running", "trail", "treadmill", "indoor_running", "street_running"}

def _es_actividad_running(tipo_deporte: str) -> bool:
    t = tipo_deporte.lower()
    return any(k in t for k in _RUNNING_KEYWORDS)

def sincronizar_actividades(email, password, usuario_id, num_actividades=20):
    _ensure_garmin_schema()
    # Garantizar columna calorias antes de insertar
    conn_pre = get_db_connection()
    _ensure_column(conn_pre, "actividades_garmin", "calorias", "REAL")
    conn_pre.commit(); conn_pre.close()

    # LOGIN — propaga la excepción para que la UI la muestre
    client = iniciar_sesion_garmin(email, password)

    # FETCH actividades — sin _safe_api_call para que el error sea visible
    try:
        actividades = client.get_activities(0, num_actividades)
    except Exception as e:
        raise RuntimeError(f"Error al obtener actividades de Garmin: {e}") from e

    if not actividades:
        return "Sincronización completada: 0 actividades sincronizadas."

    actividades_sincronizadas = 0
    conexion = get_db_connection()
    cursor = conexion.cursor()
    try:
        for actividad in actividades:
            id_actividad = actividad.get("activityId")
            if not id_actividad:
                continue
            fecha = actividad.get("startTimeLocal", "")
            tipo_deporte_raw = actividad.get("activityType")
            if isinstance(tipo_deporte_raw, dict):
                tipo_deporte = tipo_deporte_raw.get("typeKey", "")
            elif isinstance(tipo_deporte_raw, list) and tipo_deporte_raw:
                tipo_deporte = tipo_deporte_raw[0].get("typeKey", "")
            else:
                tipo_deporte = str(tipo_deporte_raw or "")

            tiempo_seg = actividad.get("duration", 0)
            fc_media   = actividad.get("averageHR")
            fc_max     = actividad.get("maxHR")
            calorias   = actividad.get("calories") or actividad.get("activeKilocalories")

            es_running = _es_actividad_running(tipo_deporte)

            if es_running:
                distancia_m = actividad.get("distance", 0)
                spd = actividad.get("averageSpeed")
                ritmo_medio = round(1000 / (float(spd) * 60), 2) if spd and float(spd) > 0 else None
                summary = _safe_api_call(client.get_activity, str(id_actividad)) or {}
                details = _safe_api_call(client.get_activity_details, str(id_actividad)) or {}
                metrics = _extract_activity_metrics(actividad, summary, details)
            else:
                distancia_m = None
                ritmo_medio = None
                metrics = {k: None for k in (
                    "potencia_media_w", "cadencia_media", "longitud_zancada_m",
                    "tiempo_contacto_ms", "oscilacion_vertical_cm")}

            cursor.execute(
                """INSERT OR REPLACE INTO actividades_garmin (
                    id_actividad, usuario_id, fecha, tipo_deporte, distancia_m,
                    tiempo_seg, ritmo_medio, fc_media, fc_max, calorias,
                    potencia_media_w, cadencia_media, longitud_zancada_m,
                    tiempo_contacto_ms, oscilacion_vertical_cm,
                    training_effect_aerobico, training_effect_anaerobico
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (id_actividad, usuario_id, fecha, tipo_deporte, distancia_m,
                 tiempo_seg, ritmo_medio, fc_media, fc_max, calorias,
                 metrics.get("potencia_media_w"), metrics.get("cadencia_media"),
                 metrics.get("longitud_zancada_m"), metrics.get("tiempo_contacto_ms"),
                 metrics.get("oscilacion_vertical_cm"),
                 metrics.get("training_effect_aerobico"), metrics.get("training_effect_anaerobico")))
            actividades_sincronizadas += 1

        conexion.commit()
        return f"Sincronización completada: {actividades_sincronizadas} actividades sincronizadas."
    except Exception as e:
        conexion.rollback()
        raise RuntimeError(f"Error al guardar actividades en BD: {e}") from e
    finally:
        conexion.close()


def sincronizar_actividades_inteligente(email, password, usuario_id, num_actividades=20):
    """
    Variante compatible con la app: devuelve el numero de actividades sincronizadas.
    """
    resultado = sincronizar_actividades(email, password, usuario_id, num_actividades)
    if isinstance(resultado, str) and resultado.startswith("Sincronización completada"):
        try:
            # "Sincronización completada: X actividades sincronizadas."
            return int(resultado.split(":", 1)[1].strip().split(" ", 1)[0])
        except Exception:
            return 0
    raise RuntimeError(resultado)


GARTH_HOME = os.path.expanduser("~/.garth_athlete")


def cargar_sesion_tokens():
    """
    Carga la sesión SOLO desde tokens garth guardados en disco.
    NO hace login SSO. NO toca las credenciales.
    Devuelve el cliente Garmin si los tokens existen, o None si no hay tokens.
    El cliente usa el refresh_token automáticamente si el access_token expiró.
    """
    if not os.path.exists(GARTH_HOME) or not os.listdir(GARTH_HOME):
        return None
    try:
        client = Garmin()
        client.garth.load(GARTH_HOME)
        logger.debug("✓ Sesión cargada desde tokens de disco")
        return client
    except Exception as e:
        logger.warning(f"No se pudo cargar sesión desde tokens: {e}")
        return None


def sincronizar_actividades_con_sesion(gc, usuario_id: int, num_actividades: int = 20) -> int:
    """
    Sincroniza usando un cliente Garmin ya autenticado.
    Devuelve el número de actividades sincronizadas.
    Propaga excepciones para que la UI las muestre.
    """
    _ensure_garmin_schema()
    conn_pre = get_db_connection()
    _ensure_column(conn_pre, "actividades_garmin", "calorias", "REAL")
    conn_pre.commit(); conn_pre.close()

    try:
        actividades = gc.get_activities(0, num_actividades)
    except Exception as e:
        raise RuntimeError(f"Error al obtener actividades: {e}") from e

    if not actividades:
        return 0

    actividades_sincronizadas = 0
    conexion = get_db_connection()
    cursor = conexion.cursor()
    try:
        for actividad in actividades:
            id_actividad = actividad.get("activityId")
            if not id_actividad:
                continue
            fecha = actividad.get("startTimeLocal", "")
            tipo_deporte_raw = actividad.get("activityType")
            if isinstance(tipo_deporte_raw, dict):
                tipo_deporte = tipo_deporte_raw.get("typeKey", "")
            elif isinstance(tipo_deporte_raw, list) and tipo_deporte_raw:
                tipo_deporte = tipo_deporte_raw[0].get("typeKey", "")
            else:
                tipo_deporte = str(tipo_deporte_raw or "")

            tiempo_seg = actividad.get("duration", 0)
            fc_media   = actividad.get("averageHR")
            fc_max     = actividad.get("maxHR")
            calorias   = actividad.get("calories") or actividad.get("activeKilocalories")
            es_running = _es_actividad_running(tipo_deporte)

            if es_running:
                distancia_m = actividad.get("distance", 0)
                spd = actividad.get("averageSpeed")
                ritmo_medio = round(1000 / (float(spd) * 60), 2) if spd and float(spd) > 0 else None
                summary = _safe_api_call(gc.get_activity, str(id_actividad)) or {}
                details = _safe_api_call(gc.get_activity_details, str(id_actividad)) or {}
                metrics = _extract_activity_metrics(actividad, summary, details)
            else:
                distancia_m = None
                ritmo_medio = None
                metrics = {k: None for k in (
                    "potencia_media_w", "cadencia_media", "longitud_zancada_m",
                    "tiempo_contacto_ms", "oscilacion_vertical_cm")}

            cursor.execute(
                """INSERT OR REPLACE INTO actividades_garmin (
                    id_actividad, usuario_id, fecha, tipo_deporte, distancia_m,
                    tiempo_seg, ritmo_medio, fc_media, fc_max, calorias,
                    potencia_media_w, cadencia_media, longitud_zancada_m,
                    tiempo_contacto_ms, oscilacion_vertical_cm,
                    training_effect_aerobico, training_effect_anaerobico
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (id_actividad, usuario_id, fecha, tipo_deporte, distancia_m,
                 tiempo_seg, ritmo_medio, fc_media, fc_max, calorias,
                 metrics.get("potencia_media_w"), metrics.get("cadencia_media"),
                 metrics.get("longitud_zancada_m"), metrics.get("tiempo_contacto_ms"),
                 metrics.get("oscilacion_vertical_cm"),
                 metrics.get("training_effect_aerobico"), metrics.get("training_effect_anaerobico")))
            actividades_sincronizadas += 1

        conexion.commit()
        return actividades_sincronizadas
    except Exception as e:
        conexion.rollback()
        raise RuntimeError(f"Error al guardar en BD: {e}") from e
    finally:
        conexion.close()


def iniciar_sesion_garmin(email, password):
    """
    Login con prioridad a tokens OAuth guardados (~/.garth_athlete).
    - Si hay tokens válidos → carga sin tocar SSO (evita 429).
    - Si no hay tokens → login con credenciales y guarda tokens.
    Ejecutar scripts/garmin_login_once.py una vez para inicializar tokens.
    """
    # 1. Intentar con tokens pre-guardados por garmin_login_once.py
    if os.path.exists(GARTH_HOME) and os.listdir(GARTH_HOME):
        try:
            client = Garmin()
            client.garth.load(GARTH_HOME)
            client.get_full_name()   # prueba rápida de sesión válida
            logger.debug("✓ Login via GARTH_HOME OK")
            return client
        except Exception as e:
            logger.warning(f"Tokens expirados ({type(e).__name__}), haciendo login fresco...")

    # 2. Login fresco con credenciales
    client = Garmin(email=email, password=password)
    try:
        client.login()
        os.makedirs(GARTH_HOME, exist_ok=True)
        client.garth.dump(GARTH_HOME)
        logger.debug(f"✓ Tokens guardados en {GARTH_HOME}")
        return client
    except GarminConnectAuthenticationError as e:
        logger.error(f"❌ Autenticación fallida: {e}")
        raise
    except GarminConnectConnectionError as e:
        logger.error(f"❌ Conexión fallida: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado: {type(e).__name__}: {e}")
        raise


def obtener_datos_sueno(client, fecha):
    """
    Recupera datos de sueño para una fecha dada. Si no hay datos o falla, devuelve None.
    Con logging detallado.
    """
    fecha_iso = fecha.strftime("%Y-%m-%d")
    logger.debug(f"  → Obteniendo datos de sueño para {fecha_iso}...")
    try:
        data = client.get_sleep_data(fecha_iso)
        if data:
            logger.debug(f"    ✓ Datos de sueño recibidos (keys: {list(data.keys())[:5]}...)")
        else:
            logger.debug(f"    ℹ Sin datos de sueño para esta fecha")
    except Exception as e:
        logger.warning(f"    ⚠️  Error al obtener datos de sueño: {type(e).__name__}: {e}")
        return None
    
    result = _extract_sleep_metrics(data, fecha_iso)
    if result:
        logger.debug(f"    ✓ Sueño extraído: {result.get('horas_totales')} h, Score: {result.get('score')}")
    return result



def guardar_sueno_db(usuario_id, datos_sueno):
    _ensure_garmin_schema()
    conexion = get_db_connection()
    cursor = conexion.cursor()
    cursor.execute(
        """
        INSERT INTO datos_sueno (
            usuario_id, fecha, horas_totales, score,
            sleep_profundo_horas, sleep_rem_horas, sleep_vigilia_horas, despertares
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(usuario_id, fecha) DO UPDATE SET
            horas_totales = COALESCE(excluded.horas_totales, datos_sueno.horas_totales),
            score = COALESCE(excluded.score, datos_sueno.score),
            sleep_profundo_horas = COALESCE(excluded.sleep_profundo_horas, datos_sueno.sleep_profundo_horas),
            sleep_rem_horas = COALESCE(excluded.sleep_rem_horas, datos_sueno.sleep_rem_horas),
            sleep_vigilia_horas = COALESCE(excluded.sleep_vigilia_horas, datos_sueno.sleep_vigilia_horas),
            despertares = COALESCE(excluded.despertares, datos_sueno.despertares)
        """,
        (
            usuario_id,
            datos_sueno.get("fecha"),
            datos_sueno.get("horas_totales"),
            datos_sueno.get("score"),
            datos_sueno.get("sleep_profundo_horas"),
            datos_sueno.get("sleep_rem_horas"),
            datos_sueno.get("sleep_vigilia_horas"),
            datos_sueno.get("despertares"),
        ),
    )
    conexion.commit()
    conexion.close()


def sincronizar_biometricos_garmin(email, password, usuario_id, dias=7):
    """
    Sincroniza biométricos y recuperación directamente desde Garmin para los últimos `dias`.
    Con logging detallado para diagnosticar problemas.
    """
    logger.info(f"\n{'#'*80}")
    logger.info(f"INICIANDO SINCRONIZACIÓN BIOMÉTRICA - usuario_id={usuario_id}, días={dias}")
    logger.info(f"{'#'*80}")
    
    try:
        _ensure_garmin_schema()
        logger.info("✓ Schema Garmin verificado")
        
        logger.info("→ Iniciando sesión en Garmin...")
        client = iniciar_sesion_garmin(email, password)
        logger.info("✓ Sesión iniciada exitosamente")
        
        logger.info("→ Buscando actividades de running recientes...")
        latest_running_list = _latest_running_metrics(client, num_actividades=12)
        latest_running = latest_running_list[0] if latest_running_list and isinstance(latest_running_list, list) and len(latest_running_list) > 0 else None
        if latest_running and latest_running.get("fecha"):
            logger.info(f"  ✓ Actividad running encontrada: {latest_running.get('fecha')}")
        else:
            logger.info(f"  ℹ No hay actividades de running recientes")
        
        target_days = max(1, int(dias))
        max_scan_days = min(60, max(14, target_days * 4))
        dias_sincronizados = 0
        dias_vacios = 0

        for i in range(max_scan_days):
            if dias_sincronizados >= target_days:
                break

            fecha = (datetime.now() - timedelta(days=i)).date()
            fecha_iso = fecha.strftime("%Y-%m-%d")
            logger.info(f"\n[{i+1}/{max_scan_days}] Procesando {fecha_iso}...")
            
            # Obtener y guardar sueño
            try:
                sleep_metrics = obtener_datos_sueno(client, fecha)
                if sleep_metrics:
                    guardar_sueno_db(usuario_id, sleep_metrics)
                    logger.info(f"  ✓ Sueño: {sleep_metrics.get('horas_totales')} h, Score: {sleep_metrics.get('score')}")
                else:
                    logger.info(f"  ℹ Sueño: No hay datos")
            except Exception as e:
                logger.warning(f"  ⚠️  Error al obtener sueño: {e}")
                sleep_metrics = None
            
            # Obtener métricas diarias
            try:
                daily_metrics = _extract_daily_metrics(client, fecha_iso)
                if sleep_metrics:
                    daily_metrics["sleep_score"] = sleep_metrics.get("score")
                
                # Agregar métricas de running si coinciden la fecha
                if latest_running and latest_running.get("fecha") == fecha_iso:
                    logger.info(f"  ↳ Agregando métricas de actividad running")
                    daily_metrics.update({
                        "potencia_media_w": latest_running.get("potencia_media_w"),
                        "cadencia_media": latest_running.get("cadencia_media"),
                        "longitud_zancada_m": latest_running.get("longitud_zancada_m"),
                        "tiempo_contacto_ms": latest_running.get("tiempo_contacto_ms"),
                        "oscilacion_vertical_cm": latest_running.get("oscilacion_vertical_cm"),
                    })
                
                if not _has_useful_daily_metrics(daily_metrics):
                    dias_vacios += 1
                    logger.info("  ℹ Día sin métricas útiles (todo nulo): se omite para evitar ruido en el entrenador.")
                    continue

                # Guardar en BD
                guardar_metricas_premium_db(usuario_id, daily_metrics)
                logger.info(f"  ✓ Métricas guardadas en BD")
                dias_sincronizados += 1
                
            except Exception as e:
                logger.error(f"  ✗ Error al guardar métricas: {e}")
                import traceback
                logger.debug(traceback.format_exc())
        
        # Guardar última actividad running si aplica
        if latest_running and latest_running.get("fecha"):
            try:
                guardar_metricas_premium_db(usuario_id, latest_running)
                logger.info(f"✓ Última actividad running guardada")
            except Exception as e:
                logger.warning(f"⚠️  Error al guardar última actividad: {e}")
        
        if dias_sincronizados < target_days:
            logger.warning(
                f"⚠ Solo se encontraron {dias_sincronizados}/{target_days} días con datos útiles "
                f"(días vacíos omitidos: {dias_vacios})."
            )

        logger.info(f"\n{'#'*80}")
        logger.info(
            f"✓ SINCRONIZACIÓN COMPLETADA: {dias_sincronizados} días útiles guardados "
            f"(objetivo={target_days}, vacíos={dias_vacios})"
        )
        logger.info(f"{'#'*80}\n")
        
        return dias_sincronizados
        
    except GarminConnectAuthenticationError as e:
        logger.error(f"\n❌ ERROR DE AUTENTICACIÓN: {e}\n")
        raise RuntimeError(f"Error de autenticación Garmin: {e}")
    except GarminConnectConnectionError as e:
        logger.error(f"\n❌ ERROR DE CONEXIÓN: {e}\n")
        raise RuntimeError(f"Error de conexión con Garmin: {e}")
    except Exception as e:
        logger.error(f"\n❌ ERROR INESPERADO: {e}\n")
        import traceback
        logger.debug(traceback.format_exc())
        raise


def sincronizar_todo_con_sesion(gc, usuario_id: int, dias: int = 7) -> dict:
    """
    Sincronización completa usando sesión ya autenticada (sin SSO).
    Solo sincroniza actividades/días no guardados aún.
    Devuelve dict con claves 'actividades' y 'dias_bio'.
    """
    _ensure_garmin_schema()
    conn_pre = get_db_connection()
    _ensure_column(conn_pre, "actividades_garmin", "calorias", "REAL")
    conn_pre.commit(); conn_pre.close()

    fecha_limite = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")

    # ── 1. Actividades nuevas de los últimos `dias` días ─────────────────
    conn_check = get_db_connection()
    try:
        ids_existentes = set(
            row[0] for row in conn_check.execute(
                "SELECT id_actividad FROM actividades_garmin WHERE usuario_id=? AND fecha>=?",
                (usuario_id, fecha_limite)
            ).fetchall()
        )
    finally:
        conn_check.close()

    try:
        todas = gc.get_activities(0, 50) or []
    except Exception as e:
        raise RuntimeError(f"Error al obtener actividades: {e}") from e

    actividades_nuevas = [
        a for a in todas
        if a.get("activityId") not in ids_existentes
        and (a.get("startTimeLocal") or "")[:10] >= fecha_limite
    ]

    act_guardadas = 0
    if actividades_nuevas:
        conexion = get_db_connection()
        cursor = conexion.cursor()
        try:
            for actividad in actividades_nuevas:
                id_actividad = actividad.get("activityId")
                if not id_actividad:
                    continue
                fecha = actividad.get("startTimeLocal", "")
                tipo_deporte_raw = actividad.get("activityType")
                if isinstance(tipo_deporte_raw, dict):
                    tipo_deporte = tipo_deporte_raw.get("typeKey", "")
                else:
                    tipo_deporte = str(tipo_deporte_raw or "")

                tiempo_seg = actividad.get("duration", 0)
                fc_media   = actividad.get("averageHR")
                fc_max     = actividad.get("maxHR")
                calorias   = actividad.get("calories") or actividad.get("activeKilocalories")
                es_running = _es_actividad_running(tipo_deporte)

                if es_running:
                    distancia_m = actividad.get("distance", 0)
                    spd = actividad.get("averageSpeed")
                    ritmo_medio = round(1000 / (float(spd) * 60), 2) if spd and float(spd) > 0 else None
                    summary = _safe_api_call(gc.get_activity, str(id_actividad)) or {}
                    details = _safe_api_call(gc.get_activity_details, str(id_actividad)) or {}
                    metrics = _extract_activity_metrics(actividad, summary, details)
                else:
                    distancia_m = None
                    ritmo_medio = None
                    metrics = {k: None for k in (
                        "potencia_media_w", "cadencia_media", "longitud_zancada_m",
                        "tiempo_contacto_ms", "oscilacion_vertical_cm")}

                cursor.execute(
                    """INSERT OR REPLACE INTO actividades_garmin (
                        id_actividad, usuario_id, fecha, tipo_deporte, distancia_m,
                        tiempo_seg, ritmo_medio, fc_media, fc_max, calorias,
                        potencia_media_w, cadencia_media, longitud_zancada_m,
                        tiempo_contacto_ms, oscilacion_vertical_cm,
                        training_effect_aerobico, training_effect_anaerobico
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (id_actividad, usuario_id, fecha, tipo_deporte, distancia_m,
                     tiempo_seg, ritmo_medio, fc_media, fc_max, calorias,
                     metrics.get("potencia_media_w"), metrics.get("cadencia_media"),
                     metrics.get("longitud_zancada_m"), metrics.get("tiempo_contacto_ms"),
                     metrics.get("oscilacion_vertical_cm"),
                     metrics.get("training_effect_aerobico"), metrics.get("training_effect_anaerobico")))
                act_guardadas += 1
            conexion.commit()
        except Exception as e:
            conexion.rollback()
            raise RuntimeError(f"Error al guardar actividades: {e}") from e
        finally:
            conexion.close()

    # ── 2. Biométricos y sueño de los últimos `dias` días ───────────────
    latest_running_list = _safe_api_call(_latest_running_metrics, gc, 12) or []
    latest_running = latest_running_list[0] if latest_running_list else None

    dias_bio = 0
    for i in range(dias):
        fecha = (datetime.now() - timedelta(days=i)).date()
        fecha_iso = fecha.strftime("%Y-%m-%d")

        # Sueño
        try:
            sleep_metrics = obtener_datos_sueno(gc, fecha)
            if sleep_metrics:
                guardar_sueno_db(usuario_id, sleep_metrics)
        except Exception:
            sleep_metrics = None

        # Métricas diarias
        try:
            daily_metrics = _extract_daily_metrics(gc, fecha_iso)
            if sleep_metrics:
                daily_metrics["sleep_score"] = sleep_metrics.get("score")
            if latest_running and latest_running.get("fecha") == fecha_iso:
                daily_metrics.update({
                    "potencia_media_w": latest_running.get("potencia_media_w"),
                    "cadencia_media": latest_running.get("cadencia_media"),
                    "longitud_zancada_m": latest_running.get("longitud_zancada_m"),
                    "tiempo_contacto_ms": latest_running.get("tiempo_contacto_ms"),
                    "oscilacion_vertical_cm": latest_running.get("oscilacion_vertical_cm"),
                })
            if _has_useful_daily_metrics(daily_metrics):
                guardar_metricas_premium_db(usuario_id, daily_metrics)
                dias_bio += 1
        except Exception:
            pass

    return {"actividades": act_guardadas, "dias_bio": dias_bio}


if __name__ == "__main__":
    # Ejemplo de uso
    email = input("Introduce tu correo de Garmin: ")
    password = input("Introduce tu contraseña de Garmin: ")
    usuario_id = int(input("Introduce tu ID de usuario (ej. 1): "))
    resultado = sincronizar_actividades(email, password, usuario_id)
    print(resultado)
