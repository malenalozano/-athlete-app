from datetime import datetime, timedelta

from fastapi import APIRouter

from database import get_db

router = APIRouter(prefix="/entrenador", tags=["entrenador"])


@router.get("/{usuario_id}/resumen")
def resumen_entrenador(usuario_id: int):
    """Resumen semanal para el entrenador virtual."""
    conn = get_db()
    hoy = datetime.now().date()
    semana_inicio = (hoy - timedelta(days=hoy.weekday())).isoformat()
    hace_7 = (hoy - timedelta(days=7)).isoformat()

    # Actividades semana
    actividades = conn.execute(
        """SELECT fecha, tipo_deporte, distancia_m, tiempo_seg, fc_media, ritmo_medio
           FROM actividades_garmin WHERE usuario_id = ? AND fecha >= ?
           ORDER BY fecha DESC""",
        (usuario_id, semana_inicio),
    ).fetchall()

    # Último biométrico
    biom = conn.execute(
        """SELECT hrv_ms, sleep_score, training_readiness, training_status,
                  body_battery, estres_medio, vo2max
           FROM datos_biometricos_premium WHERE usuario_id = ?
           ORDER BY fecha DESC LIMIT 1""",
        (usuario_id,),
    ).fetchone()

    # Sesiones fuerza semana
    sesiones_fuerza = conn.execute(
        "SELECT COUNT(*) FROM sesiones_fuerza WHERE usuario_id = ? AND fecha >= ?",
        (usuario_id, semana_inicio),
    ).fetchone()[0]

    # Lesiones activas
    lesiones = conn.execute(
        "SELECT tipo, grado FROM lesiones WHERE usuario_id = ? AND activa = 1",
        (usuario_id,),
    ).fetchall()

    conn.close()

    km_semana = round(sum((a[2] or 0) / 1000 for a in actividades), 1)
    biom_dict = {}
    if biom:
        cols = ["hrv_ms", "sleep_score", "training_readiness", "training_status",
                "body_battery", "estres_medio", "vo2max"]
        biom_dict = dict(zip(cols, biom))

    recomendaciones = _generar_recomendaciones(km_semana, sesiones_fuerza, biom_dict, lesiones)

    return {
        "km_semana": km_semana,
        "sesiones_fuerza": sesiones_fuerza,
        "actividades_count": len(actividades),
        "biometrico": biom_dict,
        "lesiones_activas": [{"tipo": l[0], "grado": l[1]} for l in lesiones],
        "recomendaciones": recomendaciones,
    }


def _generar_recomendaciones(km: float, fuerza: int, biom: dict, lesiones: list) -> list[str]:
    tips = []

    training_readiness = biom.get("training_readiness")
    hrv = biom.get("hrv_ms")
    sleep = biom.get("sleep_score")

    if training_readiness is not None:
        if training_readiness < 40:
            tips.append("Training Readiness bajo — prioriza recuperación hoy.")
        elif training_readiness > 70:
            tips.append(f"Training Readiness alto ({training_readiness}) — buen momento para sesión de calidad.")

    if sleep is not None and sleep < 65:
        tips.append(f"Sueño subóptimo ({sleep}/100) — reduce intensidad.")

    if km > 0 and fuerza == 0:
        tips.append("Sin sesiones de fuerza esta semana — añade una sesión de glúteo/core.")

    if lesiones:
        for l in lesiones:
            tips.append(f"⚠️ {l[0]} (grado {l[1]}) activa — adapta el plan.")

    if not tips:
        tips.append("Todo en orden. Sigue el plan y escucha tu cuerpo.")

    return tips
