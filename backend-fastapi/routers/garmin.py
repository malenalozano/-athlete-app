from datetime import datetime, timedelta

from fastapi import APIRouter

from database import get_db

router = APIRouter(prefix="/garmin", tags=["garmin"])


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

    # Enriquecer con duración formateada y km
    for a in actividades:
        a["km"] = round((a["distancia_m"] or 0) / 1000, 2)
        seg = a["tiempo_seg"] or 0
        a["duracion_fmt"] = f"{int(seg//3600)}h {int((seg%3600)//60)}min" if seg >= 3600 else f"{int(seg//60)}min"

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

    conn.close()
    return {
        "km_semana": round(float(km_semana), 1),
        "km_mes": round(float(km_mes), 1),
        "total_actividades": total_actividades,
        "ultima_actividad": {"fecha": ultima[0], "tipo": ultima[1]} if ultima else None,
    }
