import os
import logging
import re
import json
from datetime import datetime, timedelta
from threading import Thread
from pathlib import Path

try:
    from garminconnect import Garmin, GarminConnectConnectionError, GarminConnectAuthenticationError
except ImportError:
    Garmin = None
    GarminConnectConnectionError = Exception
    GarminConnectAuthenticationError = Exception
from dotenv import load_dotenv
from src.db.db_manager import get_db_connection

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Archivo de bloqueo 429
_BLOCKADE_FILE = os.path.expanduser("~/.garth_athlete/.blockade.json")


def check_garmin_blockade():
    """
    Verifica si hay un bloqueo 429 activo de Garmin.
    Devuelve dict con info del bloqueo, o None si no hay bloqueo.
    """
    if not os.path.exists(_BLOCKADE_FILE):
        return None
    
    try:
        with open(_BLOCKADE_FILE, 'r') as f:
            data = json.load(f)
        
        blocked_until_str = data.get('blocked_until')
        if not blocked_until_str:
            return None
        
        blocked_until_dt = datetime.fromisoformat(blocked_until_str)
        now = datetime.now()
        
        if now < blocked_until_dt:
            remaining = blocked_until_dt - now
            return {
                'is_blocked': True,
                'remaining_seconds': remaining.total_seconds(),
                'remaining_hours': remaining.total_seconds() / 3600,
                'blocked_until': blocked_until_str,
                'reason': data.get('reason', 'Unknown')
            }
        else:
            # Bloqueo ha expirado, limpiar
            try:
                os.remove(_BLOCKADE_FILE)
            except Exception:
                pass
            return None
    except Exception as e:
        logger.debug(f"Error verificando bloqueo: {e}")
        return None


def _record_429_blockade(hours=48):
    """Registra un bloqueo 429 por N horas."""
    blocked_until = datetime.now() + timedelta(hours=hours)
    os.makedirs(os.path.dirname(_BLOCKADE_FILE), exist_ok=True)
    
    try:
        with open(_BLOCKADE_FILE, 'w') as f:
            json.dump({
                'blocked_until': blocked_until.isoformat(),
                'reason': '429 Too Many Requests from Garmin',
                'created_at': datetime.now().isoformat()
            }, f)
        logger.warning(f"Bloqueo registrado hasta: {blocked_until.isoformat()}")
    except Exception as e:
        logger.warning(f"No se pudo guardar bloqueo: {e}")


def _clear_blockade_record():
    """Limpia el registro local de bloqueo 429, si existe."""
    try:
        if os.path.exists(_BLOCKADE_FILE):
            os.remove(_BLOCKADE_FILE)
    except Exception as e:
        logger.debug(f"No se pudo limpiar bloqueo local: {e}")


def _token_store(client):
    """
    Devuelve el backend de tokens compatible con la versión instalada.
    Soporta tanto `gc.garth` como `gc.client`.
    """
    if hasattr(client, "garth") and getattr(client, "garth", None) is not None:
        return client.garth
    if hasattr(client, "client") and getattr(client, "client", None) is not None:
        return client.client
    return None


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
    Incluye timeout de 15 segundos para evitar cuelgues.
    Retorna None si la llamada falla, pero registra qué pasó.
    """
    fn_name = getattr(fn, '__name__', str(fn))
    timeout_sec = 15
    result_container = [None]
    exception_container = [None]
    
    def _call_with_result():
        try:
            result_container[0] = fn(*args, **kwargs)
        except Exception as e:
            exception_container[0] = e
    
    thread = Thread(target=_call_with_result, daemon=True)
    thread.start()
    thread.join(timeout=timeout_sec)
    
    if thread.is_alive():
        logger.error(f"❌ {fn_name}: TIMEOUT después de {timeout_sec}s")
        return None
    
    if exception_container[0]:
        e = exception_container[0]
        if isinstance(e, GarminConnectAuthenticationError):
            logger.error(f"❌ {fn_name}: ERROR DE AUTENTICACIÓN - {e}")
        elif isinstance(e, GarminConnectConnectionError):
            logger.error(f"❌ {fn_name}: ERROR DE CONEXIÓN - {e}")
        else:
            logger.warning(f"⚠️  {fn_name}({args}): {type(e).__name__}: {e}")
        return None
    
    logger.debug(f"✅ {fn_name}({args}, {kwargs}) - OK")
    return result_container[0]


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


def _extract_sleep_score(data):
    def _find_sleep_score_recursive(obj, depth=0, max_depth=10):
        """Búsqueda recursiva en el objeto para encontrar un sleep score válido (70-100)."""
        if depth > max_depth or obj is None:
            return None

        if isinstance(obj, dict):
            for key, val in obj.items():
                # Buscar en nombres de claves que sugieran score
                key_lower = str(key).lower()
                if any(k in key_lower for k in ["score", "quality", "overall"]):
                    if isinstance(val, (int, float)):
                        score = _to_int(val)
                        if score and 40 < score <= 100:
                            logger.debug(f"    [FOUND RECURSIVE] {key}={score}")
                            return score
                    elif isinstance(val, dict):
                        if "value" in val:
                            score = _to_int(val["value"])
                            if score and 40 < score <= 100:
                                logger.debug(f"    [FOUND RECURSIVE] {key}.value={score}")
                                return score

                # Recursión
                result = _find_sleep_score_recursive(val, depth + 1, max_depth)
                if result is not None:
                    return result

        elif isinstance(obj, list):
            for item in obj:
                result = _find_sleep_score_recursive(item, depth + 1, max_depth)
                if result is not None:
                    return result

        return None

    def _score_from_block(block):
        if not isinstance(block, dict):
            return None

        # Loguear estructura para debug
        try:
            logger.debug(f"    [DEBUG sleep_score] Keys en block: {list(block.keys())[:10]}")
        except:
            pass

        # Formato frecuente: {"overallSleepScore": {"value": 82}}
        overall = block.get("overallSleepScore")
        if isinstance(overall, dict):
            score = _to_int(overall.get("value"))
            if score is not None:
                logger.debug(f"    [DEBUG] Found score {score} in overallSleepScore.value")
                return score
        elif overall is not None:
            score = _to_int(overall)
            if score is not None:
                logger.debug(f"    [DEBUG] Found score {score} in overallSleepScore direct")
                return score

        # Formato alternativo: {"sleepScores": [{"qualifierKey": "OVERALL", "value": 82}, ...]}
        sleep_scores = block.get("sleepScores")
        if isinstance(sleep_scores, list):
            for item in sleep_scores:
                if not isinstance(item, dict):
                    continue
                qualifier = str(item.get("qualifierKey", "")).upper()
                if qualifier in {"OVERALL", "SLEEP_SCORE", "TOTAL"}:
                    score = _to_int(item.get("value"))
                    if score is not None:
                        logger.debug(f"    [DEBUG] Found score {score} in sleepScores[{qualifier}]")
                        return score

            # Fallback de la lista: tomar el máximo valor válido (normalmente 0-100).
            values = [_to_int(item.get("value")) for item in sleep_scores if isinstance(item, dict)]
            values = [v for v in values if v is not None and 0 < v <= 100]
            if values:
                max_score = max(values)
                logger.debug(f"    [DEBUG] Found score {max_score} from sleepScores max")
                return max_score

        # Otros nombres vistos en integraciones/SDKs.
        # Buscar directamente en campos simples
        for key in ["sleepScore", "sleepQualityScore", "overallScore", "score", "overall", "qualityScore", "score24h"]:
            val = block.get(key)
            if val is not None:
                score = _to_int(val)
                if score is not None and 0 < score <= 100:
                    logger.debug(f"    [DEBUG] Found score {score} in {key}")
                    return score

        # Búsqueda profunda por nombres parciales
        fallback = _to_int(_last_number(block, ["sleepScore", "sleepQualityScore", "overallScore", "score", "overall"]))
        if fallback is not None:
            logger.debug(f"    [DEBUG] Found fallback score {fallback} from _last_number")
            return fallback

        # ÚLTIMO RECURSO: búsqueda recursiva
        recursive = _find_sleep_score_recursive(block)
        if recursive is not None:
            return recursive

        return None

    logger.debug(f"  [DEBUG sleep] Extrayendo score de datos tipo: {type(data)}")
    # Algunos payloads traen datos al tope; otros bajo dailySleepDTO.
    for block_name, block in [("data_root", data), ("dailySleepDTO", data.get("dailySleepDTO") if isinstance(data, dict) else None)]:
        if block is None:
            continue
        logger.debug(f"    [DEBUG] Buscando en {block_name}")
        score = _score_from_block(block)
        if score is not None:
            logger.debug(f"  ✓ Sleep score extraído: {score}")
            return score

    # Último fallback global, por si la estructura cambia.
    fallback = _to_int(_last_number(data, ["sleepScore", "sleepQualityScore", "overallScore", "score", "overall"]))
    if fallback is not None:
        logger.debug(f"  [DEBUG] Fallback final: {fallback}")
    return fallback


def _extract_sleep_metrics(data, fecha_iso):
    if not data:
        return None

    score = _extract_sleep_score(data)
    score_original = score  # Guardar score original de Garmin
    if score is not None and score <= 0:
        score = None

    total_seg = _first_number(data, ["sleepTimeSeconds", "totalSleepSeconds", "overallSleepDurationSeconds"])
    deep_seg = _first_number(data, ["deepSleepSeconds"])
    rem_seg = _first_number(data, ["remSleepSeconds"])
    awake_seg = _first_number(data, ["awakeSleepSeconds", "awakeSeconds", "sleepAwakeSeconds"])
    awakenings = _to_int(_first_number(data, ["awakeCount", "awakeningsCount", "restlessMomentsCount"]))

    def _hours_or_none(seconds_value):
        val = _to_float(seconds_value)
        if val is None or val <= 0:
            return None
        return round(val / 3600, 2)

    horas_totales = _hours_or_none(total_seg)
    sleep_profundo_horas = _hours_or_none(deep_seg)
    sleep_rem_horas = _hours_or_none(rem_seg)
    sleep_vigilia_horas = _hours_or_none(awake_seg)

    if awakenings is not None and awakenings <= 0:
        awakenings = None

    # Si todo viene vacío/cero, Garmin aún no ha publicado los datos del día.
    if not any([
        horas_totales is not None,
        score is not None,
        sleep_profundo_horas is not None,
        sleep_rem_horas is not None,
        sleep_vigilia_horas is not None,
        awakenings is not None,
    ]):
        return None

    # IMPORTANTE: Solo estimar score si Garmin definitivamente NO lo proporciona
    # y tenemos datos de sueño profundo. NO reemplazar el score de Garmin.
    if score is None and sleep_profundo_horas is not None:
        # Estimación simple: base 60 + bonificación por profundo/REM
        base = 60
        if horas_totales:
            # Añadir puntos por duración total (hasta +10, máx 8h)
            duracion_bonus = min(10, int(horas_totales * 1.25))
            base += duracion_bonus
        if sleep_profundo_horas:
            # Profundo: óptimo 2-2.5h, añadir +15 si está en rango
            if 1.5 <= sleep_profundo_horas <= 2.5:
                base += 15
            elif sleep_profundo_horas > 1.0:
                base += 10
        if sleep_rem_horas:
            # REM: óptimo 1.5-2h, añadir +5 si está en rango
            if 1.0 <= sleep_rem_horas <= 2.5:
                base += 5
        if awakenings and awakenings > 0:
            # Despenalizar por despertares (-5 por despertar excesivo)
            base -= min(10, awakenings * 2)
        score = max(40, min(100, base))  # Clamped entre 40-100
        logger.debug(f"  ℹ Score de sueño estimado {fecha_iso}: {_to_int(score)}/100 (Garmin no proporcionó score)")
    else:
        logger.debug(f"  ✓ Score de sueño {fecha_iso}: {score}/100 (de Garmin)")

    return {
        "fecha": fecha_iso,
        "horas_totales": horas_totales,
        "score": _to_int(score) if score is not None else None,
        "sleep_profundo_horas": sleep_profundo_horas,
        "sleep_rem_horas": sleep_rem_horas,
        "sleep_vigilia_horas": sleep_vigilia_horas,
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

    # Training Load (ACWR - Acute/Chronic Workload)
    carga_aguda = carga_cronica = None
    tl_data = _safe_api_call(getattr(client, 'get_training_load_balance', lambda x: None), fecha_iso) or {}
    if tl_data:
        carga_aguda = _to_float(_first_number(tl_data, ["acuteLoadValue", "acute", "acuteLoad"]))
        carga_cronica = _to_float(_first_number(tl_data, ["chronicLoadValue", "chronic", "chronicLoad"]))
    logger.info(f"  ✓ Training Load: Acute={carga_aguda}, Chronic={carga_cronica}" if carga_aguda or carga_cronica else "  ✗ Training Load: No encontrado")

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
        "carga_aguda": carga_aguda,
        "carga_cronica": carga_cronica,
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
                vo2max, training_status, body_battery_max, body_battery_min, estres_medio,
                carga_aguda, carga_cronica
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                estres_medio = COALESCE(excluded.estres_medio, datos_biometricos_premium.estres_medio),
                carga_aguda = COALESCE(excluded.carga_aguda, datos_biometricos_premium.carga_aguda),
                carga_cronica = COALESCE(excluded.carga_cronica, datos_biometricos_premium.carga_cronica)
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
                datos.get("carga_aguda"),
                datos.get("carga_cronica"),
            ),
        )
        conexion.commit()
    finally:
        conexion.close()


def _calcular_acwr(usuario_id: int, fecha_referencia: str) -> tuple:
    """
    Calcula ACWR (Acute/Chronic Workload Ratio) basado en Training Effect acumulado.

    Carga aguda: suma de TE de los últimos 7 días
    Carga crónica: suma de TE de los últimos 28 días
    ACWR = carga_aguda / carga_crónica

    Returns: (carga_aguda, carga_cronica, acwr)
    """
    conn = get_db_connection()
    try:
        # Últimos 7 días
        fecha_7d = (datetime.strptime(fecha_referencia, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(COALESCE(training_effect_aerobico, 0) + COALESCE(training_effect_anaerobico, 0)), 0)
            FROM actividades_garmin
            WHERE usuario_id=? AND fecha >= ? AND fecha <= ?
        """, (usuario_id, fecha_7d, fecha_referencia))
        carga_aguda = float(cursor.fetchone()[0] or 0)

        # Últimos 28 días
        fecha_28d = (datetime.strptime(fecha_referencia, "%Y-%m-%d") - timedelta(days=28)).strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT COALESCE(SUM(COALESCE(training_effect_aerobico, 0) + COALESCE(training_effect_anaerobico, 0)), 0)
            FROM actividades_garmin
            WHERE usuario_id=? AND fecha >= ? AND fecha <= ?
        """, (usuario_id, fecha_28d, fecha_referencia))
        carga_cronica = float(cursor.fetchone()[0] or 0)

        acwr = carga_aguda / carga_cronica if carga_cronica > 0 else 1.0

        return round(carga_aguda, 2), round(carga_cronica, 2), round(acwr, 2)
    finally:
        conn.close()


def _guardar_acwr_diario(usuario_id: int, fecha_referencia: str) -> None:
    """
    Calcula ACWR y lo guarda en datos_biometricos_premium para la fecha.
    """
    carga_aguda, carga_cronica, acwr = _calcular_acwr(usuario_id, fecha_referencia)

    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO datos_biometricos_premium (usuario_id, fecha, carga_aguda, carga_cronica)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(usuario_id, fecha) DO UPDATE SET
                carga_aguda = COALESCE(excluded.carga_aguda, datos_biometricos_premium.carga_aguda),
                carga_cronica = COALESCE(excluded.carga_cronica, datos_biometricos_premium.carga_cronica)
        """, (usuario_id, fecha_referencia, carga_aguda if carga_aguda > 0 else None, carga_cronica if carga_cronica > 0 else None))
        conn.commit()
    finally:
        conn.close()


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
    client = iniciar_sesion_garmin(email, password, usuario_id=usuario_id)

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


def _safe_email_slug(email: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "_", str(email or "").strip().lower())


def _token_homes(email: str | None = None):
    """
    Construye rutas candidatas de tokens.
    - Preferimos un directorio por cuenta para soportar multiusuario.
    - Mantenemos compatibilidad con el path antiguo (~/.garth_athlete).
    """
    homes = []
    if email:
        homes.append(os.path.join(GARTH_HOME, _safe_email_slug(email)))
    homes.append(GARTH_HOME)
    return homes


def _load_valid_client_from_home(home: str):
    """Carga tokens DI (garminconnect >= 0.3) desde disco."""
    token_file = Path(home).expanduser() / "garmin_tokens.json"
    if not token_file.exists():
        return None
    try:
        gc = Garmin()
        store = _token_store(gc)
        if store is None:
            return None
        store.load(str(Path(home).expanduser()))
        if hasattr(store, "is_authenticated") and not store.is_authenticated:
            return None
        logger.debug(f"✓ Tokens cargados desde disco: {home}")
        return gc
    except Exception as e:
        logger.warning(f"Tokens inválidos en {home}: {type(e).__name__}: {e}")
        return None


def _guardar_tokens_db(usuario_id: int, token_json: str):
    """Persiste el JSON de tokens garth en la columna garmin_tokens de usuarios."""
    try:
        conn = get_db_connection()
        conn.execute(
            "UPDATE usuarios SET garmin_tokens=? WHERE id=?",
            (token_json, usuario_id))
        conn.commit()
        conn.close()
        logger.debug(f"✓ Tokens Garmin guardados en BD para usuario {usuario_id}")
    except Exception as e:
        logger.warning(f"No se pudieron guardar tokens en BD: {e}")


def _cargar_tokens_db(usuario_id: int):
    """Carga tokens DI (garminconnect >= 0.3) desde la BD."""
    try:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT garmin_tokens FROM usuarios WHERE id=?", (usuario_id,)
        ).fetchone()
        conn.close()
        if not row or not row[0]:
            return None
        token_json = row[0]
        gc = Garmin()
        store = _token_store(gc)
        if store is None:
            return None
        store.loads(token_json)
        if hasattr(store, "is_authenticated") and not store.is_authenticated:
            return None
        logger.debug(f"✓ Tokens Garmin cargados desde BD para usuario {usuario_id}")
        return gc
    except Exception as e:
        logger.warning(f"Tokens BD inválidos para usuario {usuario_id}: {type(e).__name__}: {e}")
        return None


def _parchar_garth_sin_refresh(gc):
    """
    Garminconnect >= 0.3 usa tokens DI propios que se refrescan sin SSO.
    No se necesita monkey-patch; esta función es un no-op por compatibilidad.
    """
    return gc


def cargar_sesion_tokens(email: str | None = None, usuario_id: int | None = None):
    """
    Carga la sesión SOLO desde tokens garth (disco primero, BD como fallback).
    NO hace login SSO. NO toca las credenciales.
    Devuelve el cliente Garmin si los tokens existen, o None si no hay tokens.
    El cliente usa el refresh_token automáticamente si el access_token expiró.
    """
    # 1. Intentar desde archivos en disco (funciona en local)
    for home in _token_homes(email):
        client = _load_valid_client_from_home(home)
        if client is not None:
            return client
    # 2. Fallback: tokens guardados en BD (funciona en Streamlit Cloud)
    if usuario_id is not None:
        client = _cargar_tokens_db(usuario_id)
        if client is not None:
            return client
    return None


def sincronizar_actividades_con_sesion(gc, usuario_id: int, num_actividades: int = 20) -> int:
    """
    Sincroniza usando un cliente Garmin ya autenticado.
    Devuelve el número de actividades sincronizadas.
    Propaga excepciones para que la UI las muestre.
    
    Nota: Si el cliente es None o inválido, lanza RuntimeError.
    """
    if gc is None:
        raise RuntimeError("⚠️  Cliente Garmin no autenticado. Conecta tu cuenta nuevamente.")
    
    # Parchear garth para evitar refresh_oauth2 automático (previene 429 en cloud)
    gc = _parchar_garth_sin_refresh(gc)
    
    # Validar que el token sea fresco antes de empezar
    if not _check_token_freshness(gc):
        raise RuntimeError(
            "🔑 Token expirado o inválido. La sesión ha caducado. "
            "Desconecta y vuelve a conectar tu cuenta Garmin para refrescar los tokens."
        )
    
    _ensure_garmin_schema()
    conn_pre = get_db_connection()
    _ensure_column(conn_pre, "actividades_garmin", "calorias", "REAL")
    conn_pre.commit(); conn_pre.close()

    try:
        actividades = gc.get_activities(0, num_actividades)
    except GarminConnectAuthenticationError as e:
        logger.error(f"❌ Error de autenticación en get_activities: {e}")
        raise RuntimeError(
            "🔑 Error de autenticación con Garmin. Tu sesión ha expirado. "
            "Desconecta y vuelve a conectar tu cuenta."
        ) from e
    except GarminConnectConnectionError as e:
        logger.error(f"❌ Error de conexión en get_activities: {e}")
        raise RuntimeError(f"❌ Error de conexión con Garmin: {e}") from e
    except Exception as e:
        logger.error(f"❌ Error al obtener actividades: {type(e).__name__}: {e}")
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
        logger.error(f"❌ Error al guardar actividades: {e}")
        raise RuntimeError(f"Error al guardar actividades en BD: {e}") from e
    finally:
        conexion.close()


def _check_token_freshness(gc):
    """
    Verifica si el cliente tiene un token válido (al menos 5 min de validez).
    Devuelve True si el token es válido, False si expira pronto.
    """
    if not gc:
        return False
    try:
        store = _token_store(gc)
        if store is None:
            return False
        oauth2 = getattr(store, "oauth2_token", None)
        if oauth2 is None:
            # Si no hay metadatos de expiración, permitimos seguir y que la API confirme validez.
            return True
        # Si ya está marcado como expirado
        if getattr(oauth2, "expired", False):
            return False
        # Validar tiempo de expiración (más de 5 minutos)
        expires_at = getattr(oauth2, "expires_at", None)
        if expires_at is None:
            return True  # Sin info de expiración, asumir válido
        import time
        tiempo_restante = expires_at - int(time.time())
        return tiempo_restante > 300  # Más de 5 minutos
    except Exception as e:
        logger.debug(f"Error verificando token: {e}")
        return False


def iniciar_sesion_garmin(email, password, usuario_id: int | None = None, force_fresh_login: bool = False):
    """
    Login con prioridad a tokens OAuth guardados (disco o BD).
    - Si hay tokens válidos → carga sin tocar SSO (evita 429).
    - Si no hay tokens válidos → login con credenciales, guarda tokens en disco y en BD.
    
    Args:
        email: Email de Garmin
        password: Contraseña de Garmin
        usuario_id: ID de usuario para guardar tokens en BD
        force_fresh_login: Si True, ignora tokens existentes y hace login fresco
    
    Ejecutar scripts/garmin_login_once.py una vez para inicializar tokens.
    """
    # 1. Verificar si hay bloqueo 429 activo
    blockade = check_garmin_blockade()
    if blockade and blockade['is_blocked']:
        hours = int(blockade['remaining_hours'])
        minutes = int((blockade['remaining_hours'] % 1) * 60)
        msg = (
            f"🚫 Garmin está bloqueando las peticiones desde esta IP (error 429).\n\n"
            f"⏳ Tiempo restante de bloqueo: {hours}h {minutes}m\n"
            f"   (hasta {blockade['blocked_until']})\n\n"
            f"📍 Para resolver:\n"
            f"   1. Espera el tiempo indicado arriba\n"
            f"   2. NO intentes ejecutar este script antes (alargaría el bloqueo)\n"
            f"   3. Cuando pase el tiempo, vuelve a ejecutar en terminal:\n"
            f"      python scripts/garmin_login_once.py"
        )
        raise RuntimeError(msg)
    
    # 2. Intentar con tokens de esta cuenta PRIMERO (disco primero, BD como fallback)
    if not force_fresh_login:
        client = cargar_sesion_tokens(email, usuario_id=usuario_id)
        if client is not None and _check_token_freshness(client):
            logger.debug("✅ Token válido cargado desde almacenamiento")
            return client
        elif client is not None:
            logger.debug("⚠️  Token expirado, realizando login fresco")
    
    # 3. Login fresco con credenciales (solo si es necesario)
    logger.info(f"🔑 Iniciando login fresco para {email}...")
    client = Garmin(email=email, password=password)
    try:
        # Login con timeout
        login_container = [False]
        exception_container = [None]
        
        def _login():
            try:
                client.login()
                login_container[0] = True
            except Exception as e:
                exception_container[0] = e
        
        thread = Thread(target=_login, daemon=True)
        thread.start()
        thread.join(timeout=20)  # 20 segundos para login
        
        if not login_container[0]:
            if exception_container[0]:
                raise exception_container[0]
            else:
                raise TimeoutError("Login en Garmin expiró (timeout)")
        
        logger.info("✅ Login exitoso en Garmin")
        
        # Guardar en disco (local)
        token_home = os.path.join(GARTH_HOME, _safe_email_slug(email)) if email else GARTH_HOME
        try:
            os.makedirs(token_home, exist_ok=True)
            store = _token_store(client)
            if store is None:
                raise RuntimeError("No se encontró backend de tokens en cliente Garmin")
            store.dump(token_home)
            logger.info(f"✓ Tokens guardados en disco: {token_home}")
        except Exception as e:
            logger.warning(f"No se pudieron guardar tokens en disco: {e}")
        
        # Guardar en BD (persiste en cloud)
        if usuario_id is not None:
            try:
                store = _token_store(client)
                if store is None:
                    raise RuntimeError("No se encontró backend de tokens en cliente Garmin")
                _guardar_tokens_db(usuario_id, store.dumps())
                logger.info(f"✓ Tokens guardados en BD para usuario {usuario_id}")
            except Exception as e:
                logger.warning(f"No se pudieron guardar tokens en BD: {e}")
        _clear_blockade_record()
        
        return client
    except GarminConnectAuthenticationError as e:
        logger.error(f"❌ Autenticación fallida: {e}")
        msg = str(e)
        
        # Detectar y registrar bloqueo 429
        if "429" in msg or "rate" in msg.lower() or "Too Many Requests" in msg:
            _record_429_blockade(hours=48)
            raise RuntimeError(
                "🚫 Garmin ha bloqueado las peticiones por demasiados intentos (Error 429).\n\n"
                "⏳ Bloqueo activo durante 48 horas.\n\n"
                "📍 No hagas nada por ahora:\n"
                "   • Espera 48 horas completas\n"
                "   • NO intentes ejecutar este script de nuevo\n"
                "   • La app en Cloud seguirá funcionando con tokens ya guardados\n\n"
                "🔄 Cuando pasen 48 horas, ejecuta en terminal:\n"
                "   python scripts/garmin_login_once.py"
            ) from e
        
        raise RuntimeError(f"Error de autenticación: {e}") from e
    except GarminConnectConnectionError as e:
        logger.error(f"❌ Conexión fallida: {e}")
        raise RuntimeError(f"Error de conexión con Garmin: {e}") from e
    except TimeoutError as e:
        logger.error(f"❌ Timeout en login: {e}")
        raise RuntimeError(f"El login tardó demasiado. Intenta más tarde: {e}") from e
    except Exception as e:
        logger.error(f"❌ Error inesperado: {type(e).__name__}: {e}")
        
        # Si es error de red, posiblemente sea también bloqueo
        msg = str(e)
        if "429" in msg or "Too Many Requests" in msg:
            _record_429_blockade(hours=48)
        
        raise RuntimeError(f"Error al realizar login: {type(e).__name__}: {e}") from e


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
        client = iniciar_sesion_garmin(email, password, usuario_id=usuario_id)
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


def _persistir_tokens_si_cambiaron(gc, usuario_id: int):
    """Re-guarda tokens DI en BD tras sync por si se refrescaron."""
    try:
        store = _token_store(gc)
        if store is None:
            return
        _guardar_tokens_db(usuario_id, store.dumps())
    except Exception as e:
        logger.warning(f"No se pudieron re-persistir tokens tras sync: {e}")


def sincronizar_todo_con_sesion(gc, usuario_id: int, dias: int = 7) -> dict:
    """
    Sincronización completa usando sesión ya autenticada (sin SSO).
    Solo sincroniza actividades/días no guardados aún.
    Devuelve dict con claves 'actividades' y 'dias_bio'.
    """
    if gc is None:
        raise RuntimeError("⚠️  Cliente Garmin no autenticado. Conecta tu cuenta nuevamente.")
    
    # Validar que el token sea fresco antes de empezar
    if not _check_token_freshness(gc):
        raise RuntimeError(
            "🔑 Token expirado o inválido. La sesión ha caducado. "
            "Desconecta y vuelve a conectar tu cuenta Garmin para refrescar los tokens."
        )
    
    # Parchear garth para evitar refresh_oauth2 automático (previene 429 en cloud)
    gc = _parchar_garth_sin_refresh(gc)
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
    except GarminConnectAuthenticationError as e:
        logger.error(f"❌ Error de autenticación: {e}")
        raise RuntimeError(
            "🔑 Error de autenticación con Garmin. Tu sesión ha expirado. "
            "Desconecta y vuelve a conectar tu cuenta."
        ) from e
    except GarminConnectConnectionError as e:
        logger.error(f"❌ Error de conexión: {e}")
        raise RuntimeError(f"❌ Error de conexión con Garmin: {e}") from e
    except Exception as e:
        logger.error(f"❌ Error al obtener actividades: {type(e).__name__}: {e}")
        raise RuntimeError(f"Error al obtener actividades: {e}") from e

    actividades_nuevas = [
        a for a in todas
        if a.get("activityId") not in ids_existentes
        and (a.get("startTimeLocal") or "")[:10] >= fecha_limite
    ]

    act_guardadas = 0
    actividades_importadas = []
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
                actividades_importadas.append({
                    "id_actividad": id_actividad,
                    "fecha": fecha,
                    "tipo_deporte": tipo_deporte,
                    "km": round((distancia_m or 0) / 1000, 2) if distancia_m is not None else None,
                    "min": round((tiempo_seg or 0) / 60, 1) if tiempo_seg is not None else None,
                    "fc_media": fc_media,
                })
            conexion.commit()
        except Exception as e:
            conexion.rollback()
            logger.error(f"❌ Error al guardar actividades: {e}")
            raise RuntimeError(f"Error al guardar actividades: {e}") from e
        finally:
            conexion.close()

    # ── 2. Biométricos y sueño de los últimos `dias` días ───────────────
    latest_running_list = _safe_api_call(_latest_running_metrics, gc, 12) or []
    latest_running = latest_running_list[0] if latest_running_list else None

    dias_bio = 0
    dias_sueno = 0
    biometricos_importados = []
    sueno_importado = []
    for i in range(dias):
        fecha = (datetime.now() - timedelta(days=i)).date()
        fecha_iso = fecha.strftime("%Y-%m-%d")

        # Sueño
        try:
            sleep_metrics = obtener_datos_sueno(gc, fecha)
            if sleep_metrics:
                guardar_sueno_db(usuario_id, sleep_metrics)
                dias_sueno += 1
                sueno_importado.append({
                    "fecha": fecha_iso,
                    "horas_totales": sleep_metrics.get("horas_totales"),
                    "score": sleep_metrics.get("score"),
                    "sleep_profundo_horas": sleep_metrics.get("sleep_profundo_horas"),
                    "sleep_rem_horas": sleep_metrics.get("sleep_rem_horas"),
                })
        except GarminConnectAuthenticationError:
            logger.warning(f"Token expiró al obtener sueño para {fecha_iso}")
            raise RuntimeError(
                "🔑 Token expirado durante la sincronización. "
                "Desconecta y vuelve a conectar tu cuenta."
            )
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
                biometricos_importados.append(daily_metrics)
        except GarminConnectAuthenticationError:
            logger.warning(f"Token expiró al obtener métricas para {fecha_iso}")
            raise RuntimeError(
                "🔑 Token expirado durante la sincronización. "
                "Desconecta y vuelve a conectar tu cuenta."
            )
        except Exception as e:
            logger.warning(f"Error al obtener métricas para {fecha_iso}: {e}")

    logger.info(f"✅ Sincronización completa: {act_guardadas} actividades, {dias_bio} días bio, {dias_sueno} días sueño")
    return {
        "actividades": act_guardadas,
        "dias_bio": dias_bio,
        "dias_sueno": dias_sueno,
        "actividades_importadas": actividades_importadas,
        "biometricos_importados": biometricos_importados,
        "sueno_importado": sueno_importado,
    }


if __name__ == "__main__":
    # Ejemplo de uso
    email = input("Introduce tu correo de Garmin: ")
    password = input("Introduce tu contraseña de Garmin: ")
    usuario_id = int(input("Introduce tu ID de usuario (ej. 1): "))
    resultado = sincronizar_actividades(email, password, usuario_id)
    print(resultado)
