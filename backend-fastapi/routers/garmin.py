from datetime import datetime, timedelta, date
from typing import Optional
import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from database import get_db
from constants import es_actividad_running

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/garmin", tags=["garmin"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_credentials(conn, usuario_id: int) -> tuple[str, str]:
    row = conn.execute(
        "SELECT email_garmin, password_garmin_enc FROM usuarios WHERE id = ?",
        (usuario_id,),
    ).fetchone()
    if not row or not row[0] or not row[1]:
        raise HTTPException(
            status_code=400,
            detail="No hay credenciales Garmin configuradas. Ve a Perfil → Sincronización para añadirlas.",
        )
    return row[0], row[1]


def _upsert_actividad(conn, usuario_id: int, act: dict):
    act_id = str(act.get("activityId", ""))
    if not act_id:
        return

    tipo_raw = (act.get("activityType", {}) or {}).get("typeKey", "") or ""
    tipo = tipo_raw.lower().replace(" ", "_")

    distancia = act.get("distance") or 0
    duracion = act.get("duration") or 0
    ritmo = (duracion / 60) / (distancia / 1000) if distancia and duracion else None
    fc_media = act.get("averageHR")
    fc_max = act.get("maxHR")
    cadencia = act.get("averageRunningCadenceInStepsPerMinute")
    fecha_raw = act.get("startTimeLocal") or act.get("startTimeGMT") or ""
    fecha = fecha_raw[:10] if fecha_raw else None

    conn.execute(
        """INSERT OR REPLACE INTO actividades_garmin
           (id_actividad, usuario_id, fecha, tipo_deporte, distancia_m, tiempo_seg,
            ritmo_medio, fc_media, fc_max, cadencia_media)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (act_id, usuario_id, fecha, tipo, distancia, duracion,
         ritmo, fc_media, fc_max, cadencia),
    )


def _upsert_biometrico(conn, usuario_id: int, fecha: str, **kwargs):
    existing = conn.execute(
        "SELECT id FROM datos_biometricos_premium WHERE usuario_id = ? AND fecha = ?",
        (usuario_id, fecha),
    ).fetchone()

    fields = {k: v for k, v in kwargs.items() if v is not None}
    if not fields:
        return

    if existing:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE datos_biometricos_premium SET {set_clause} WHERE usuario_id = ? AND fecha = ?",
            (*fields.values(), usuario_id, fecha),
        )
    else:
        cols = ["usuario_id", "fecha"] + list(fields.keys())
        placeholders = ", ".join(["?"] * len(cols))
        conn.execute(
            f"INSERT INTO datos_biometricos_premium ({', '.join(cols)}) VALUES ({placeholders})",
            (usuario_id, fecha, *fields.values()),
        )


def _upsert_sueno(conn, usuario_id: int, fecha: str, **kwargs):
    fields = {k: v for k, v in kwargs.items() if v is not None}
    if not fields:
        return
    existing = conn.execute(
        "SELECT id FROM datos_sueno WHERE usuario_id = ? AND fecha = ?",
        (usuario_id, fecha),
    ).fetchone()
    if existing:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE datos_sueno SET {set_clause} WHERE usuario_id = ? AND fecha = ?",
            (*fields.values(), usuario_id, fecha),
        )
    else:
        cols = ["usuario_id", "fecha"] + list(fields.keys())
        placeholders = ", ".join(["?"] * len(cols))
        conn.execute(
            f"INSERT INTO datos_sueno ({', '.join(cols)}) VALUES ({placeholders})",
            (usuario_id, fecha, *fields.values()),
        )


def _load_client_from_tokens(conn, usuario_id: int):
    """Carga cliente Garmin desde tokens OAuth guardados en BD.
    No hace login ni llama a la API — la renovación de token ocurre
    automáticamente en el primer 401 mediante di_refresh_token.
    Soporta tanto gc.client (versiones antiguas) como gc.garth (versiones nuevas).
    """
    try:
        from garminconnect import Garmin
        row = conn.execute(
            "SELECT garmin_tokens FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        if not row or not row[0]:
            return None
        gc = Garmin()
        # Detectar dónde vive el store OAuth según la versión de garminconnect
        store = None
        if hasattr(gc, "garth") and gc.garth is not None:
            store = gc.garth
        elif hasattr(gc, "client") and gc.client is not None:
            store = gc.client
        if store is None:
            return None
        store.loads(row[0])
        # Algunos stores no tienen is_authenticated; si cargó sin excepción, lo damos por válido
        if hasattr(store, "is_authenticated") and not store.is_authenticated:
            return None
        return gc
    except Exception:
        return None


def _save_tokens_to_db(conn, usuario_id: int, gc):
    """Guarda los tokens actualizados de vuelta a la BD tras una sync exitosa."""
    try:
        store = None
        if hasattr(gc, "garth") and gc.garth is not None:
            store = gc.garth
        elif hasattr(gc, "client") and gc.client is not None:
            store = gc.client
        if store and hasattr(store, "dumps"):
            token_json = store.dumps()
            conn.execute(
                "UPDATE usuarios SET garmin_tokens = ? WHERE id = ?",
                (token_json, usuario_id),
            )
    except Exception:
        pass


def _bootstrap_client_from_credentials(conn, usuario_id: int):
    """Genera tokens OAuth desde credenciales guardadas (one-time bootstrap)."""
    try:
        from garminconnect import Garmin
    except ImportError:
        return None

    row = conn.execute(
        "SELECT email_garmin, password_garmin_enc FROM usuarios WHERE id = ?",
        (usuario_id,),
    ).fetchone()
    if not row or not row[0] or not row[1]:
        return None

    email = row[0]
    password = row[1]
    try:
        gc = Garmin(email=email, password=password)
        gc.login()
        _save_tokens_to_db(conn, usuario_id, gc)
        conn.commit()
        return gc
    except Exception as e:
        logger.warning(f"No se pudo bootstrap Garmin con credenciales para usuario {usuario_id}: {e}")
        return None


# Palabras clave para clasificar el tipo de actividad de Garmin y poder
# auto-completar sesiones del plan cuando coinciden con lo realizado.
# RUNNING_TIPOS viene de constants.py (compartida con plan.py/dashboard.py) para
# que "qué cuenta como carrera" no se desincronice entre sitios.
STRENGTH_KEYWORDS = (
    "strength_training", "indoor_cardio", "hiit", "indoor_climbing", "cross_training",
    "yoga", "pilates", "bouldering", "cardio",
)


def _es_actividad_running(tipo_deporte: str) -> bool:
    return es_actividad_running(tipo_deporte)


def _es_actividad_fuerza(tipo_deporte: str) -> bool:
    t = (tipo_deporte or "").lower()
    return any(k in t for k in STRENGTH_KEYWORDS)


def _auto_completar_sesiones_por_garmin(conn, usuario_id: int, desde: str) -> int:
    """Marca como completadas las sesiones del plan que ya tienen una actividad
    Garmin compatible ese mismo día (carrera→actividad de running, fuerza→actividad
    de fuerza/cross). No inventa datos: si no hay actividad compatible, no toca nada.
    Devuelve el número de sesiones marcadas.
    """
    sesiones = conn.execute(
        """SELECT id, fecha, tipo FROM plan_entrenamiento
           WHERE usuario_id = ? AND fecha >= ? AND completado = 0""",
        (usuario_id, desde),
    ).fetchall()
    if not sesiones:
        return 0

    actividades = conn.execute(
        """SELECT fecha, tipo_deporte, distancia_m FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ?""",
        (usuario_id, desde),
    ).fetchall()
    por_fecha: dict = {}
    for fecha, tipo_deporte, distancia_m in actividades:
        por_fecha.setdefault(fecha, []).append((tipo_deporte or "", distancia_m or 0))

    marcadas = 0
    for sesion_id, fecha, tipo in sesiones:
        acts = por_fecha.get(fecha)
        if not acts:
            continue
        es_carrera = (tipo or "").lower() == "carrera"
        km_real = 0.0
        match = False
        for tipo_deporte, distancia_m in acts:
            if es_carrera and _es_actividad_running(tipo_deporte):
                match = True
                km_real += distancia_m / 1000
            elif not es_carrera and _es_actividad_fuerza(tipo_deporte):
                match = True
        if not match:
            continue
        if es_carrera and km_real > 0:
            conn.execute(
                "UPDATE plan_entrenamiento SET completado = 1, km_realizados = ? WHERE id = ?",
                (round(km_real, 2), sesion_id),
            )
        else:
            conn.execute(
                "UPDATE plan_entrenamiento SET completado = 1 WHERE id = ?",
                (sesion_id,),
            )
        marcadas += 1
    return marcadas


def _do_sync(usuario_id: int) -> dict:
    """Realiza la sincronización completa con Garmin Connect.

    Maneja automáticamente tokens expirados: si los tokens guardados fallan con 401,
    intenta bootstrap con credenciales como fallback. Nunca deja una excepción sin
    capturar (timeouts, 429, errores de red) para que una sync fallida no tumbe el
    endpoint ni deje la conexión de BD abierta.
    """
    try:
        from garminconnect import Garmin
    except ImportError:
        raise HTTPException(status_code=500, detail="garminconnect no instalado en el servidor")

    conn = get_db()
    try:
        return _do_sync_inner(conn, usuario_id)
    finally:
        conn.close()


def _do_sync_inner(conn, usuario_id: int) -> dict:
    from garminconnect import Garmin

    # Preferimos tokens OAuth. Si no existen, hacemos bootstrap one-time con
    # credenciales guardadas para no obligar al usuario a ejecutar scripts manuales.
    client = _load_client_from_tokens(conn, usuario_id)

    if client is None:
        logger.info(f"Sin tokens OAuth para usuario {usuario_id}, intentando bootstrap con credenciales...")
        client = _bootstrap_client_from_credentials(conn, usuario_id)

    if client is None:
        raise HTTPException(
            status_code=400,
            detail="No se pudo iniciar sesión en Garmin con las credenciales guardadas. Revisa email/password en Perfil y vuelve a sincronizar.",
        )

    # Algunas versiones de garminconnect requieren cargar el perfil antes de get_stats/get_sleep
    # para rellenar el display_name interno. Lo hacemos en segundo plano silenciosamente.
    try:
        client.get_full_name()
    except Exception:
        try:
            client.get_user_profile()
        except Exception:
            pass  # No es crítico — seguimos

    from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError

    actividades_ok = 0
    biometrico_ok = 0
    sueno_ok = 0
    sesiones_auto_completadas = 0
    errores = []
    hoy = date.today()
    # Extendemos la ventana a 90 días para no perder actividades de hace más de un mes
    hace_90 = hoy - timedelta(days=90)

    def _fetch_day(dia_str: str) -> dict:
        """Descarga todos los datos de un día en paralelo (se ejecuta en hilo)."""
        result = {"fecha": dia_str, "sueno": None, "hrv": None, "stats": None, "readiness": None}
        try:
            sleep = client.get_sleep_data(dia_str)
            daily = (sleep or {}).get("dailySleepDTO") or {}
            horas = round(daily["sleepTimeSeconds"] / 3600, 2) if daily.get("sleepTimeSeconds") else None
            score = (daily.get("sleepScores", {}) or {}).get("overall", {}).get("value") if isinstance(daily.get("sleepScores"), dict) else daily.get("sleepScore")
            profundo = round(daily.get("deepSleepSeconds", 0) / 3600, 2) if daily.get("deepSleepSeconds") else None
            rem = round(daily.get("remSleepSeconds", 0) / 3600, 2) if daily.get("remSleepSeconds") else None
            if horas or score:
                result["sueno"] = {"horas_totales": horas, "score": score, "sleep_profundo_horas": profundo, "sleep_rem_horas": rem}
        except Exception:
            pass
        try:
            hrv_data = client.get_hrv_data(dia_str)
            hrv_summary = (hrv_data or {}).get("hrvSummary") or {}
            hrv_ms = hrv_summary.get("lastNight") or hrv_summary.get("weeklyAvg")
            if hrv_ms:
                result["hrv"] = hrv_ms
        except Exception:
            pass
        try:
            stats = client.get_stats(dia_str)
            result["stats"] = {
                "fc_reposo": stats.get("restingHeartRate"),
                "estres_medio": stats.get("averageStressLevel"),
                "body_battery": stats.get("bodyBatteryChargedValue") or stats.get("bodyBatteryHighValue"),
                "body_battery_min": stats.get("bodyBatteryDrainedValue") or stats.get("bodyBatteryLowValue"),
                "vo2max": stats.get("vo2MaxValue"),
            }
        except Exception:
            pass
        try:
            tr = client.get_training_readiness(dia_str)
            readiness = status = None
            if isinstance(tr, dict):
                readiness = tr.get("score") or tr.get("trainingReadiness")
                status = tr.get("trainingStatus") or tr.get("status")
            elif isinstance(tr, list) and tr:
                readiness = tr[0].get("score")
                status = tr[0].get("trainingStatus")
            if readiness or status:
                result["readiness"] = {"training_readiness": readiness, "training_status": status}
        except Exception:
            pass
        return result

    # ── Actividades + datos diarios en paralelo ────────────────────────────────
    dias = [hoy - timedelta(days=d) for d in range(7)]
    dias_str = [d.isoformat() for d in dias]

    with ThreadPoolExecutor(max_workers=8) as pool:
        # Pedimos hasta 50 actividades para no perder nada reciente
        fut_acts = pool.submit(client.get_activities, 0, 50)
        fut_dias = {pool.submit(_fetch_day, d): d for d in dias_str}

        # Actividades
        try:
            activities = fut_acts.result(timeout=20)
            for act in activities:
                fecha_raw = act.get("startTimeLocal", "")[:10]
                try:
                    # Aceptar actividades de los últimos 90 días
                    if fecha_raw and date.fromisoformat(fecha_raw) >= hace_90:
                        _upsert_actividad(conn, usuario_id, act)
                        actividades_ok += 1
                except Exception:
                    pass
            conn.commit()
        except Exception as e:
            err_str = str(e)
            # Un 429 (rate limit) NO debe reintentar con login por contraseña: reintentar
            # login durante un bloqueo de Garmin es justo lo que agrava/alarga el bloqueo
            # (ver GARMIN_429_COMPLETE_GUIDE.md). Nos limitamos a registrar el error.
            if "429" in err_str or "Too Many Requests" in err_str:
                logger.warning(f"Garmin rate-limit (429) para usuario {usuario_id}. No se reintenta login.")
                errores.append("Actividades: Garmin está limitando peticiones (429). Se reintentará en la próxima sync.")
            elif "401" in err_str or "Authentication failed" in err_str:
                logger.warning(f"Tokens expirados para usuario {usuario_id} (401). Reintentando con credenciales...")
                client = _bootstrap_client_from_credentials(conn, usuario_id)
                if client is not None:
                    try:
                        activities = client.get_activities(0, 50)
                        for act in activities:
                            fecha_raw = act.get("startTimeLocal", "")[:10]
                            try:
                                if fecha_raw and date.fromisoformat(fecha_raw) >= hace_90:
                                    _upsert_actividad(conn, usuario_id, act)
                                    actividades_ok += 1
                            except Exception:
                                pass
                        conn.commit()
                        logger.info(f"Reintento exitoso para usuario {usuario_id}: {actividades_ok} actividades")
                    except Exception as e2:
                        errores.append(f"Actividades (reintento fallido): {str(e2)[:100]}")
                else:
                    errores.append(f"Actividades: Tokens expirados, no se pudo renovar con credenciales")
            else:
                errores.append(f"Actividades: {err_str[:100]}")

        # Datos diarios — un timeout global de as_completed() no debe tumbar toda la
        # sync (las actividades ya están guardadas); los días que no lleguen a tiempo
        # simplemente se omiten y se recuperan en la siguiente sincronización.
        try:
            for fut in as_completed(fut_dias, timeout=25):
                try:
                    day = fut.result()
                    dia_str = day["fecha"]
                    if day["sueno"]:
                        _upsert_sueno(conn, usuario_id, dia_str, **day["sueno"])
                        sueno_ok += 1
                        # Guardar sleep_score en biometrico para que el LEFT JOIN
                        # del endpoint /diario/biometrico siempre devuelva esta fila
                        if day["sueno"].get("score"):
                            _upsert_biometrico(conn, usuario_id, dia_str, sleep_score=day["sueno"]["score"])
                    if day["hrv"]:
                        _upsert_biometrico(conn, usuario_id, dia_str, hrv_ms=day["hrv"])
                        biometrico_ok += 1
                    if day["stats"]:
                        _upsert_biometrico(conn, usuario_id, dia_str, **day["stats"])
                        biometrico_ok += 1
                    if day["readiness"]:
                        _upsert_biometrico(conn, usuario_id, dia_str, **day["readiness"])
                except Exception:
                    pass
        except FutureTimeoutError:
            logger.warning(f"Timeout esperando datos biométricos diarios para usuario {usuario_id} — continuando.")
            errores.append("Datos biométricos: algunos días no llegaron a tiempo, se reintentarán en la próxima sync.")

    try:
        _save_tokens_to_db(conn, usuario_id, client)
        conn.commit()
    except Exception as e:
        logger.warning(f"No se pudieron guardar tokens/commit final para usuario {usuario_id}: {e}")

    # Auto-completar sesiones del plan que ya coinciden con actividades importadas
    # (últimos 14 días — suficiente para "esta semana" y la anterior).
    try:
        desde = (hoy - timedelta(days=14)).isoformat()
        sesiones_auto_completadas = _auto_completar_sesiones_por_garmin(conn, usuario_id, desde)
        conn.commit()
    except Exception as e:
        logger.warning(f"No se pudo auto-completar sesiones para usuario {usuario_id}: {e}")

    return {
        "ok": True,
        "actividades_importadas": actividades_ok,
        "dias_biometrico": biometrico_ok,
        "dias_sueno": sueno_ok,
        "sesiones_completadas_auto": sesiones_auto_completadas,
        "advertencias": errores if errores else None,
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/{usuario_id}/actividades")
def get_actividades(usuario_id: int, dias: int = 30):
    conn = get_db()
    desde = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
    rows = conn.execute(
        """SELECT id_actividad, fecha, tipo_deporte, distancia_m, tiempo_seg,
                  ritmo_medio, fc_media, fc_max, cadencia_media,
                  longitud_zancada_m, tiempo_contacto_ms, oscilacion_vertical_cm
           FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ?
           ORDER BY fecha DESC""",
        (usuario_id, desde),
    ).fetchall()
    conn.close()
    cols = ["id", "fecha", "tipo_deporte", "distancia_m", "tiempo_seg",
            "ritmo_medio", "fc_media", "fc_max", "cadencia_media",
            "longitud_zancada_m", "tiempo_contacto_ms", "oscilacion_vertical_cm"]
    actividades = [dict(zip(cols, r)) for r in rows]

    for a in actividades:
        a["km"] = round((a["distancia_m"] or 0) / 1000, 2)
        seg = a["tiempo_seg"] or 0
        a["duracion_fmt"] = (
            f"{int(seg//3600)}h {int((seg%3600)//60)}min" if seg >= 3600
            else f"{int(seg//60)}min"
        )
    return actividades


@router.get("/{usuario_id}/stats")
def get_stats(usuario_id: int):
    conn = get_db()
    hoy = datetime.now().date()
    semana_inicio = (hoy - timedelta(days=hoy.weekday())).isoformat()
    mes_inicio = hoy.replace(day=1).isoformat()

    km_semana = conn.execute(
        "SELECT COALESCE(SUM(distancia_m)/1000,0) FROM actividades_garmin WHERE usuario_id = ? AND fecha >= ?",
        (usuario_id, semana_inicio),
    ).fetchone()[0]

    km_mes = conn.execute(
        "SELECT COALESCE(SUM(distancia_m)/1000,0) FROM actividades_garmin WHERE usuario_id = ? AND fecha >= ?",
        (usuario_id, mes_inicio),
    ).fetchone()[0]

    total_actividades = conn.execute(
        "SELECT COUNT(*) FROM actividades_garmin WHERE usuario_id = ?",
        (usuario_id,),
    ).fetchone()[0]

    ultima = conn.execute(
        "SELECT fecha, tipo_deporte FROM actividades_garmin WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 1",
        (usuario_id,),
    ).fetchone()

    ultimo_biom = conn.execute(
        "SELECT fecha FROM datos_biometricos_premium WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 1",
        (usuario_id,),
    ).fetchone()

    conn.close()
    return {
        "km_semana": round(float(km_semana), 1),
        "km_mes": round(float(km_mes), 1),
        "total_actividades": total_actividades,
        "ultima_actividad": {"fecha": ultima[0], "tipo": ultima[1]} if ultima else None,
        "ultima_sync_biometrico": ultimo_biom[0] if ultimo_biom else None,
    }


@router.post("/{usuario_id}/sync")
def sync_garmin(usuario_id: int):
    """Sincroniza actividades y datos biométricos desde Garmin Connect."""
    from notifications import send_notification
    try:
        result = _do_sync(usuario_id)
        acts = result.get("actividades_importadas", 0)
        advertencias = result.get("advertencias")
        if advertencias:
            send_notification(
                f"Sync completada con advertencias: {', '.join(advertencias[:2])}",
                title="🟡 Garmin sincronizado",
                tags=["warning"],
                priority="default",
            )
        else:
            send_notification(
                f"Garmin sync OK — {acts} actividad(es) importada(s). ✅",
                title="Garmin sincronizado",
                tags=["white_check_mark", "runner"],
                priority="default",
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        send_notification(
            f"Error al sincronizar Garmin: {str(e)[:120]}",
            title="❌ Error sync Garmin",
            tags=["x", "warning"],
            priority="high",
        )
        raise HTTPException(status_code=502, detail=f"No se pudo sincronizar con Garmin: {str(e)[:150]}")


class TokensPayload(BaseModel):
    tokens_json: str


@router.post("/{usuario_id}/upload-tokens")
def upload_tokens(usuario_id: int, body: TokensPayload):
    """Guarda tokens OAuth de Garmin en la BD (llamado desde el script local)."""
    conn = get_db()
    conn.execute(
        "UPDATE usuarios SET garmin_tokens = ? WHERE id = ?",
        (body.tokens_json, usuario_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "message": f"Tokens guardados para usuario {usuario_id}"}


@router.get("/{usuario_id}/token-status")
def token_status(usuario_id: int):
    """Comprueba si hay tokens Garmin guardados para el usuario."""
    conn = get_db()
    row = conn.execute(
        "SELECT garmin_tokens IS NOT NULL AND garmin_tokens != '' FROM usuarios WHERE id = ?",
        (usuario_id,),
    ).fetchone()
    conn.close()
    tiene_tokens = bool(row and row[0])
    return {"usuario_id": usuario_id, "tiene_tokens": tiene_tokens}


@router.get("/{usuario_id}/diagnostico")
def diagnostico_garmin(usuario_id: int):
    """
    Diagnóstico detallado: prueba cada paso del sync por separado.
    Útil para depurar por qué sync devuelve 0 actividades.
    """
    from datetime import date
    diag = {
        "usuario_id": usuario_id,
        "pasos": [],
        "error_fatal": None,
    }

    # 1. DB + tokens
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT garmin_tokens, email_garmin FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
        if not row:
            diag["error_fatal"] = "Usuario no encontrado en BD"
            return diag
        tokens_len = len(row[0]) if row[0] else 0
        diag["pasos"].append({
            "paso": "tokens_en_bd",
            "ok": tokens_len > 0,
            "detalle": f"len={tokens_len}, email={row[1]}",
        })
        if tokens_len == 0:
            diag["error_fatal"] = "Sin tokens en BD. Ejecuta garmin_login_once.py"
            conn.close()
            return diag
    except Exception as e:
        diag["error_fatal"] = f"Error BD: {e}"
        return diag

    # 2. Cargar client
    try:
        from garminconnect import Garmin
        gc = Garmin()
        has_client = hasattr(gc, "client") and gc.client is not None
        has_garth = hasattr(gc, "garth") and gc.garth is not None
        diag["pasos"].append({
            "paso": "garmin_obj",
            "ok": True,
            "detalle": f"has_client={has_client}, has_garth={has_garth}",
        })

        # Intentar cargar tokens en el store correcto
        store = None
        store_name = None
        if has_client:
            store = gc.client
            store_name = "client"
        elif has_garth:
            store = gc.garth
            store_name = "garth"

        if store is None:
            diag["pasos"].append({"paso": "load_store", "ok": False, "detalle": "No hay store (ni client ni garth)"})
            diag["error_fatal"] = "No se puede cargar el store de tokens"
            conn.close()
            return diag

        store.loads(row[0])
        is_auth = store.is_authenticated if hasattr(store, "is_authenticated") else "unknown"
        diag["pasos"].append({
            "paso": "load_tokens",
            "ok": bool(is_auth) if isinstance(is_auth, bool) else True,
            "detalle": f"store={store_name}, is_authenticated={is_auth}",
        })
    except Exception as e:
        diag["pasos"].append({"paso": "load_client", "ok": False, "detalle": str(e)})
        diag["error_fatal"] = f"Error cargando client: {e}"
        conn.close()
        return diag

    # 3. Llamada a get_activities
    try:
        acts = gc.get_activities(0, 5)
        fechas = [a.get("startTimeLocal", "?")[:10] for a in (acts or [])]
        diag["pasos"].append({
            "paso": "get_activities",
            "ok": True,
            "detalle": f"total={len(acts or [])}, fechas={fechas}",
        })
    except Exception as e:
        diag["pasos"].append({"paso": "get_activities", "ok": False, "detalle": str(e)[:200]})

    # 4. get_stats de ayer
    try:
        ayer = (date.today().replace(day=date.today().day - 1)).isoformat()
        stats = gc.get_stats(ayer)
        diag["pasos"].append({
            "paso": "get_stats",
            "ok": bool(stats),
            "detalle": f"fecha={ayer}, keys={list((stats or {}).keys())[:5]}",
        })
    except Exception as e:
        diag["pasos"].append({"paso": "get_stats", "ok": False, "detalle": str(e)[:200]})

    conn.close()
    return diag
