from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_db

router = APIRouter(prefix="/plan", tags=["plan"])


class SesionUpdate(BaseModel):
    completado: bool
    km_realizados: Optional[float] = None
    notas: Optional[str] = None


class SesionCreate(BaseModel):
    usuario_id: int
    fecha: str
    tipo: str
    sesion: str
    detalles: Optional[str] = None
    duracion_min: Optional[int] = None
    intensidad: Optional[str] = None
    km_planificados: Optional[float] = None


@router.get("/{usuario_id}/semana/{fecha_inicio}")
def get_plan_semana(usuario_id: int, fecha_inicio: str):
    """Devuelve el plan de la semana. Si no hay sesiones genera un plan básico."""
    conn = get_db()

    # Calcular fin de semana
    try:
        inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato fecha inválido (YYYY-MM-DD)")
    fin = (inicio + timedelta(days=6)).strftime("%Y-%m-%d")

    rows = conn.execute(
        """SELECT id, fecha, tipo, sesion, detalles, duracion_min, intensidad,
                  completado, km_planificados, km_realizados, semana_inicio
           FROM plan_entrenamiento
           WHERE usuario_id = ? AND fecha >= ? AND fecha <= ?
           ORDER BY fecha ASC""",
        (usuario_id, fecha_inicio, fin),
    ).fetchall()
    cols = ["id", "fecha", "tipo", "sesion", "detalles", "duracion_min", "intensidad",
            "completado", "km_planificados", "km_realizados", "semana_inicio"]
    sesiones = [dict(zip(cols, r)) for r in rows]

    # Estadísticas semana
    km_plan = sum(s["km_planificados"] or 0 for s in sesiones)
    km_real = sum(s["km_realizados"] or 0 for s in sesiones)
    completadas = sum(1 for s in sesiones if s["completado"])

    # Actividades Garmin de la semana (para km reales si no hay km_realizados)
    garmin_rows = conn.execute(
        """SELECT fecha, tipo_deporte, distancia_m, tiempo_seg, ritmo_medio, fc_media
           FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ? AND fecha <= ?
           ORDER BY fecha ASC""",
        (usuario_id, fecha_inicio, fin),
    ).fetchall()
    garmin_cols = ["fecha", "tipo_deporte", "distancia_m", "tiempo_seg", "ritmo_medio", "fc_media"]
    actividades_garmin = [dict(zip(garmin_cols, r)) for r in garmin_rows]

    # Si no hay km_real en plan pero hay Garmin, usar Garmin
    if km_real == 0 and actividades_garmin:
        km_real = round(sum(a["distancia_m"] or 0 for a in actividades_garmin) / 1000, 1)

    # Coach recommendation
    perfil_row = conn.execute(
        "SELECT objetivo_tipo, fecha_objetivo, fcmax FROM usuarios WHERE id = ?",
        (usuario_id,),
    ).fetchone()
    conn.close()

    objetivo_tipo = perfil_row[0] if perfil_row else "maraton"
    fecha_objetivo = perfil_row[1] if perfil_row else None
    fase = _calcular_fase_nombre(objetivo_tipo, fecha_objetivo)

    return {
        "semana_inicio": fecha_inicio,
        "sesiones": sesiones,
        "actividades_garmin": actividades_garmin,
        "stats": {
            "km_planificados": round(km_plan, 1),
            "km_realizados": round(km_real, 1),
            "sesiones_completadas": completadas,
            "total_sesiones": len(sesiones),
        },
        "fase": fase,
        "coach_tip": _coach_tip(fase, km_real, len(sesiones)),
    }


@router.patch("/sesion/{sesion_id}")
def actualizar_sesion(sesion_id: int, update: SesionUpdate):
    conn = get_db()
    conn.execute(
        "UPDATE plan_entrenamiento SET completado = ?, km_realizados = ? WHERE id = ?",
        (1 if update.completado else 0, update.km_realizados, sesion_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@router.post("/sesion")
def crear_sesion(s: SesionCreate):
    conn = get_db()
    semana_inicio = _inicio_semana(s.fecha)
    ahora = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO plan_entrenamiento
           (usuario_id, semana_inicio, fecha, tipo, sesion, detalles, duracion_min,
            intensidad, km_planificados, creado_en)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (s.usuario_id, semana_inicio, s.fecha, s.tipo, s.sesion,
         s.detalles, s.duracion_min, s.intensidad, s.km_planificados, ahora),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@router.delete("/sesion/{sesion_id}")
def borrar_sesion(sesion_id: int):
    conn = get_db()
    conn.execute("DELETE FROM plan_entrenamiento WHERE id = ?", (sesion_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


def _inicio_semana(fecha_str: str) -> str:
    d = datetime.strptime(fecha_str, "%Y-%m-%d")
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")


def _calcular_fase_nombre(objetivo_tipo: str | None, fecha_objetivo: str | None) -> str:
    hoy = datetime.now()
    mes = hoy.month
    dia = hoy.day
    tipo = (objetivo_tipo or "").lower()

    if tipo in ("ultramaraton", "ultra") and fecha_objetivo:
        try:
            dias = (datetime.strptime(fecha_objetivo, "%Y-%m-%d") - hoy).days
            if dias <= 21:
                return "Tapering"
            if dias <= 63:
                return "Pico de Forma"
            if dias <= 119:
                return "Preparación Específica"
            if dias <= 175:
                return "Preparación General"
            return "Acondicionamiento"
        except (ValueError, TypeError):
            pass

    if mes in [3, 4, 5]:
        return "Acondicionamiento"
    if mes in [6, 7, 8]:
        return "Preparación General"
    if mes in [9, 10, 11]:
        return "Preparación Específica"
    if mes == 12 or (mes == 1 and dia <= 15):
        return "Pico de Forma"
    return "Tapering"


def _coach_tip(fase: str, km_real: float, n_sesiones: int) -> str:
    if fase == "Acondicionamiento":
        return "Fase de base: prioriza Z2 y construcción de fuerza. No subas más del 10% de volumen."
    if fase == "Preparación General":
        return "Construye resistencia aeróbica. Introduce progresivamente sesiones de calidad."
    if fase == "Preparación Específica":
        return "Ritmos de competición. Simula condiciones de carrera. Cuida la recuperación."
    if fase == "Pico de Forma":
        return "Tiradas largas y consolidación. Mantén la intensidad, no subas volumen."
    if fase == "Tapering":
        return "Reduce volumen, mantén intensidad. Prioriza el descanso y la supercompensación."
    return "Sigue el plan y escucha tu cuerpo."
