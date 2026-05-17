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


def _do_sync(usuario_id: int) -> dict:
    """Realiza la sincronización completa con Garmin Connect."""
    try:
        from garminconnect import Garmin
    except ImportError:
        raise HTTPException(status_code=500, detail="garminconnect no instalado en el servidor")

    conn = get_db()
    email, password = _get_credentials(conn, usuario_id)

    try:
        client = Garmin(email, password)
        client.login()
    except Exception as e:
        conn.close()
        msg = str(e)
        if "2FA" in msg or "MFA" in msg or "factor" in msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Garmin requiere verificación en dos pasos (2FA). Desactívala temporalmente en tu cuenta Garmin Connect.",
            )
        raise HTTPException(status_code=400, detail=f"Error al conectar con Garmin: {msg[:200]}")

    actividades_ok = 0
    biometrico_ok = 0
    sueno_ok = 0
    errores = []

    # ── Actividades (últimos 30 días) ──────────────────────────────────────────
    try:
        activities = client.get_activities(0, 50)
        hoy = date.today()
        hace_30 = hoy - timedelta(days=30)
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

    # ── Datos diarios (últimos 14 días): sueño, HRV, body battery, estrés ─────
    hoy = date.today()
    for delta in range(14):
        dia = hoy - timedelta(days=delta)
        dia_str = dia.isoformat()

        # Sueño
        try:
            sleep = client.get_sleep_data(dia_str)
            daily = (sleep or {}).get("dailySleepDTO") or {}
            horas_totales = None
            if daily.get("sleepTimeSeconds"):
                horas_totales = round(daily["sleepTimeSeconds"] / 3600, 2)
            score = daily.get("sleepScores", {}).get("overall", {}).get("value") if isinstance(daily.get("sleepScores"), dict) else None
            if score is None:
                score = daily.get("sleepScore")
            profundo = round(daily.get("deepSleepSeconds", 0) / 3600, 2) if daily.get("deepSleepSeconds") else None
            rem = round(daily.get("remSleepSeconds", 0) / 3600, 2) if daily.get("remSleepSeconds") else None
            if horas_totales or score:
                _upsert_sueno(conn, usuario_id, dia_str,
                              horas_totales=horas_totales, score=score,
                              sleep_profundo_horas=profundo, sleep_rem_horas=rem)
                sueno_ok += 1
        except Exception as e:
            if delta == 0:
                errores.append(f"Sueño: {str(e)[:80]}")

        # HRV
        try:
            hrv_data = client.get_hrv_data(dia_str)
            hrv_summary = (hrv_data or {}).get("hrvSummary") or {}
            hrv_ms = hrv_summary.get("lastNight") or hrv_summary.get("weeklyAvg")
            if hrv_ms:
                _upsert_biometrico(conn, usuario_id, dia_str, hrv_ms=hrv_ms)
                biometrico_ok += 1
        except Exception:
            pass

        # Stats diarias (FC reposo, estrés, body battery, VO2max, etc.)
        try:
            stats = client.get_stats(dia_str)
            fc_rep = stats.get("restingHeartRate")
            estres = stats.get("averageStressLevel")
            body_bat_end = stats.get("bodyBatteryChargedValue") or stats.get("bodyBatteryHighValue")
            body_bat_min = stats.get("bodyBatteryDrainedValue") or stats.get("bodyBatteryLowValue")
            vo2max = stats.get("vo2MaxValue")
            _upsert_biometrico(conn, usuario_id, dia_str,
                               fc_reposo=fc_rep,
                               estres_medio=estres,
                               body_battery=body_bat_end,
                               body_battery_min=body_bat_min,
                               vo2max=vo2max)
            biometrico_ok += 1
        except Exception as e:
            if delta == 0:
                errores.append(f"Stats: {str(e)[:80]}")

        # Training readiness / training status
        try:
            tr = client.get_training_readiness(dia_str)
            readiness = None
            status = None
            if isinstance(tr, dict):
                readiness = tr.get("score") or tr.get("trainingReadiness")
                status = tr.get("trainingStatus") or tr.get("status")
            elif isinstance(tr, list) and tr:
                readiness = tr[0].get("score")
                status = tr[0].get("trainingStatus")
            if readiness or status:
                _upsert_biometrico(conn, usuario_id, dia_str,
                                   training_readiness=readiness,
                                   training_status=status)
        except Exception:
            pass

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
