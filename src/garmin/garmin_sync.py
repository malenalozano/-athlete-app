import os
import logging
from datetime import datetime, timedelta
from garminconnect import Garmin, GarminConnectConnectionError, GarminConnectAuthenticationError
from dotenv import load_dotenv
from db.db_manager import get_db_connection

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
    Registra el estado de cada métrica mientras la obtiene.
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"EXTRAYENDO MÉTRICAS PARA {fecha_iso}")
    logger.info(f"{'='*70}")
    
    # HRV
    logger.debug(f"  → Obteniendo HRV...")
    hrv_data = _safe_api_call(client.get_hrv_data, fecha_iso) or {}
    hrv_ms = _first_number(hrv_data, ["lastNightAverage", "averageHrv", "weeklyAverage", "hrvValue"])
    logger.info(f"  ✓ HRV: {hrv_ms} ms" if hrv_ms else f"  ✗ HRV: No encontrado")

    # Training Readiness
    logger.debug(f"  → Obteniendo Training Readiness...")
    readiness_data = _safe_api_call(getattr(client, 'get_training_readiness', lambda x: None), fecha_iso) or {}

    # Body Battery

    # Recovery Hours
    recovery_hours = _first_number(readiness_data, ["recoveryTime", "recoveryTimeHours", "recoveryHours"])
    logger.info(f"  ✓ Recovery Hours: {recovery_hours}" if recovery_hours else f"  ✗ Recovery Hours: No encontrado")
    
    # Stress Data
    logger.debug(f"  → Obteniendo Stress Data...")
    stress_data = _safe_api_call(client.get_stress_data, fecha_iso) or {}
    if not stress_data:
        logger.debug(f"  → Fallback: Obteniendo All Day Stress...")
        stress_data = _safe_api_call(client.get_all_day_stress, fecha_iso) or {}
    # Eliminados: training_readiness, body_battery, estres_vital
    
    # SpO2
    logger.debug(f"  → Obteniendo SpO2...")
    spo2_data = _safe_api_call(client.get_spo2_data, fecha_iso) or {}
    spo2 = _first_number(spo2_data, ["averageSpo2", "avgSpo2", "spo2"])
    logger.info(f"  ✓ SpO2: {spo2}" if spo2 else f"  ✗ SpO2: No encontrado")
    
    # Heart Rates
    logger.debug(f"  → Obteniendo Heart Rates...")
    heart_rates = _safe_api_call(client.get_heart_rates, fecha_iso) or {}
    fc_reposo = _to_int(_first_number(heart_rates, ["restingHeartRate", "restHeartRate", "restingHR"]))
    fc_maxima = _to_int(_first_number(heart_rates, ["maxHeartRate", "maxHeartRateInBeatsPerMinute"]))
    logger.info(f"  ✓ FC Reposo: {fc_reposo}, FC Máxima: {fc_maxima}" if fc_reposo or fc_maxima else f"  ✗ Heart Rates: No encontrado")
    
    logger.info(f"{'='*70}\n")
    
    return {
        "fecha": fecha_iso,
        "hrv_ms": hrv_ms,
        "fc_reposo": fc_reposo,
        "fc_maxima": fc_maxima,
        "spo2": spo2,
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
                oscilacion_vertical_cm, sleep_score, spo2, potencia_media_w
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                potencia_media_w = COALESCE(excluded.potencia_media_w, datos_biometricos_premium.potencia_media_w)
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
            ),
        )
        conexion.commit()
    finally:
        conexion.close()

def sincronizar_actividades(email, password, usuario_id, num_actividades=20):
    """
    Sincroniza las últimas actividades de Garmin con la base de datos.
    """
    _ensure_garmin_schema()
    try:
        # Inicializar cliente Garmin y realizar login
        client = Garmin(email, password)
        client.login()
    except GarminConnectAuthenticationError:
        return "Error: Credenciales de Garmin incorrectas."
    except GarminConnectConnectionError:
        return "Error: No se pudo conectar con Garmin Connect."
    except Exception as e:
        return f"Error inesperado: {e}"

    try:
        # Obtener las últimas actividades según el número especificado
        actividades = client.get_activities(0, num_actividades)
        actividades_sincronizadas = 0

        # Conectar a la base de datos
        conexion = get_db_connection()
        cursor = conexion.cursor()

        for actividad in actividades:
            # Extraer y mapear campos clave
            id_actividad = actividad["activityId"]
            fecha = actividad["startTimeLocal"]
            tipo_deporte = actividad["activityType"]["typeKey"]
            distancia_m = actividad.get("distance", 0)
            tiempo_seg = actividad.get("duration", 0)
            ritmo_medio = 1000 / (actividad.get("averageSpeed", 1) * 60) if actividad.get("averageSpeed") else None
            fc_media = actividad.get("averageHR")
            fc_max = actividad.get("maxHR")
            summary = _safe_api_call(client.get_activity, str(id_actividad)) or {}
            details = _safe_api_call(client.get_activity_details, str(id_actividad)) or {}
            metrics = _extract_activity_metrics(actividad, summary, details)

            # Insertar o reemplazar en la base de datos
            cursor.execute('''
                INSERT OR REPLACE INTO actividades_garmin (
                    id_actividad, usuario_id, fecha, tipo_deporte, distancia_m, tiempo_seg, ritmo_medio, fc_media, fc_max,
                    potencia_media_w, cadencia_media, longitud_zancada_m, tiempo_contacto_ms, oscilacion_vertical_cm
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                id_actividad, usuario_id, fecha, tipo_deporte, distancia_m, tiempo_seg, ritmo_medio, fc_media, fc_max,
                metrics.get("potencia_media_w"), metrics.get("cadencia_media"), metrics.get("longitud_zancada_m"),
                metrics.get("tiempo_contacto_ms"), metrics.get("oscilacion_vertical_cm")
            ))

            actividades_sincronizadas += 1

        # Guardar cambios y cerrar conexión
        conexion.commit()
        conexion.close()

        return f"Sincronización completada: {actividades_sincronizadas} actividades sincronizadas."
    except Exception as e:
        if "database" in str(e).lower():
            return f"Error de base de datos: {e}"
        return f"Error inesperado durante la sincronización: {e}"


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


def iniciar_sesion_garmin(email, password):
    """Inicia sesión en Garmin Connect con manejo de errores."""
    logger.debug("→ Iniciando línea Garmin...")
    try:
        client = Garmin(email, password)
        logger.debug("  → Ejecutando login()...")
        client.login()
        logger.debug("  ✓ Login exitoso")
        return client
    except GarminConnectAuthenticationError as e:
        logger.error(f"  ❌ Error de autenticación: {e}")
        raise
    except GarminConnectConnectionError as e:
        logger.error(f"  ❌ Error de conexión: {e}")
        raise
    except Exception as e:
        logger.error(f"  ❌ Error inesperado: {type(e).__name__}: {e}")
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
        latest_running = _latest_running_metrics(client, num_actividades=12)
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


if __name__ == "__main__":
    # Ejemplo de uso
    email = input("Introduce tu correo de Garmin: ")
    password = input("Introduce tu contraseña de Garmin: ")
    usuario_id = int(input("Introduce tu ID de usuario (ej. 1): "))
    resultado = sincronizar_actividades(email, password, usuario_id)
    print(resultado)
