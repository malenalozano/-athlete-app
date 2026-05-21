from datetime import datetime, timedelta, date
from typing import Optional
import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from database import get_db

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
    """
    try:
        from garminconnect import Garmin
        row = conn.execute(
            "SELECT garmin_tokens FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        if not row or not row[0]:
            return None
        gc = Garmin()
        store = gc.client if hasattr(gc, "client") and gc.client is not None else None
        if store is None:
            return None
        store.loads(row[0])
        if not store.is_authenticated:
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


def _do_sync(usuario_id: int) -> dict:
    """Realiza la sincronización completa con Garmin Connect."""
    try:
        from garminconnect import Garmin
    except ImportError:
        raise HTTPException(status_code=500, detail="garminconnect no instalado en el servidor")

    conn = get_db()

    # Solo usar tokens OAuth — NUNCA intentar login con contraseña desde el cloud
    # (Garmin bloquea IPs de servidores con 403).
    # garminconnect auto-refresca el di_token usando di_refresh_token en los 401.
    client = _load_client_from_tokens(conn, usuario_id)

    if client is None:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Sesión Garmin caducada. Ejecuta desde tu PC: python scripts/garmin_login_once.py --usuario 1 (o --usuario 2 para Dani)",
        )

    from concurrent.futures import ThreadPoolExecutor, as_completed

    actividades_ok = 0
    biometrico_ok = 0
    sueno_ok = 0
    errores = []
    hoy = date.today()

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
    hace_30 = hoy - timedelta(days=30)

    with ThreadPoolExecutor(max_workers=8) as pool:
        fut_acts = pool.submit(client.get_activities, 0, 30)
        fut_dias = {pool.submit(_fetch_day, d): d for d in dias_str}

        # Actividades
        try:
            activities = fut_acts.result(timeout=20)
            for act in activities:
                fecha_raw = act.get("startTimeLocal", "")[:10]
                try:
                    if fecha_raw and date.fromisoformat(fecha_raw) >= hace_30:
                        _upsert_actividad(conn, usuario_id, act)
                        actividades_ok += 1
                except Exception:
                    pass
            conn.commit()
        except Exception as e:
            errores.append(f"Actividades: {str(e)[:100]}")

        # Datos diarios
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

    _save_tokens_to_db(conn, usuario_id, client)
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "actividades_importadas": actividades_ok,
        "dias_biometrico": biometrico_ok,
        "dias_sueno": sueno_ok,
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
    result = _do_sync(usuario_id)
    return result


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
