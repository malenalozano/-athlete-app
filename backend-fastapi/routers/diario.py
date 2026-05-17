from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from database import get_db

router = APIRouter(prefix="/diario", tags=["diario"])


class EntradaDiario(BaseModel):
    usuario_id: int
    fecha: Optional[str] = None
    fase_ciclo: Optional[str] = None
    fatiga_subjetiva: Optional[int] = None
    dolor_notas: Optional[str] = None
    estado_animo: Optional[str] = None
    feedback_entreno: Optional[str] = None
    sangre: Optional[str] = None
    sintomas: Optional[str] = None


class EntradaBiometrica(BaseModel):
    usuario_id: int
    fecha: Optional[str] = None
    hrv_ms: Optional[float] = None
    fc_reposo: Optional[int] = None
    sleep_score: Optional[int] = None
    horas_sueno: Optional[float] = None
    sleep_profundo_horas: Optional[float] = None
    sleep_rem_horas: Optional[float] = None
    carga_aguda: Optional[float] = None
    carga_cronica: Optional[float] = None
    estres_medio: Optional[float] = None
    body_battery: Optional[int] = None
    body_battery_min: Optional[int] = None
    body_battery_max: Optional[int] = None
    training_readiness: Optional[int] = None
    training_status: Optional[str] = None
    vo2max: Optional[float] = None


@router.get("/fisiologia/{usuario_id}")
def get_fisiologia(usuario_id: int, limit: int = 30):
    conn = get_db()
    rows = conn.execute(
        """SELECT fecha, fase_ciclo, fatiga_subjetiva, dolor_notas,
                  estado_animo, feedback_entreno, sangre, sintomas
           FROM diario_fisiologia
           WHERE usuario_id = ?
           ORDER BY fecha DESC LIMIT ?""",
        (usuario_id, limit),
    ).fetchall()
    conn.close()
    cols = ["fecha", "fase_ciclo", "fatiga_subjetiva", "dolor_notas",
            "estado_animo", "feedback_entreno", "sangre", "sintomas"]
    return [dict(zip(cols, r)) for r in rows]


@router.post("/fisiologia")
def crear_entrada(e: EntradaDiario):
    conn = get_db()
    fecha = e.fecha or datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        """INSERT OR REPLACE INTO diario_fisiologia
           (usuario_id, fecha, fase_ciclo, fatiga_subjetiva, dolor_notas,
            estado_animo, feedback_entreno, sangre, sintomas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (e.usuario_id, fecha, e.fase_ciclo, e.fatiga_subjetiva,
         e.dolor_notas, e.estado_animo, e.feedback_entreno,
         e.sangre, e.sintomas),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "fecha": fecha}


@router.get("/biometrico/{usuario_id}")
def get_biometrico(usuario_id: int, limit: int = 30):
    conn = get_db()
    rows = conn.execute(
        """SELECT b.fecha, b.hrv_ms, b.fc_reposo, b.sleep_score, b.carga_aguda, b.carga_cronica,
                  b.estres_medio, b.body_battery, b.training_readiness, b.training_status, b.vo2max,
                  s.horas_totales, s.sleep_profundo_horas, s.sleep_rem_horas
           FROM datos_biometricos_premium b
           LEFT JOIN datos_sueno s ON b.usuario_id = s.usuario_id AND b.fecha = s.fecha
           WHERE b.usuario_id = ?
           ORDER BY b.fecha DESC LIMIT ?""",
        (usuario_id, limit),
    ).fetchall()
    conn.close()
    cols = ["fecha", "hrv_ms", "fc_reposo", "sleep_score", "carga_aguda", "carga_cronica",
            "estres_medio", "body_battery", "training_readiness", "training_status", "vo2max",
            "horas_totales", "sleep_profundo_horas", "sleep_rem_horas"]
    return [dict(zip(cols, r)) for r in rows]


@router.post("/biometrico")
def crear_biometrico(e: EntradaBiometrica):
    conn = get_db()
    fecha = e.fecha or datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        """INSERT OR REPLACE INTO datos_biometricos_premium
           (usuario_id, fecha, hrv_ms, fc_reposo, sleep_score, carga_aguda, carga_cronica,
            estres_medio, body_battery, body_battery_min, body_battery_max,
            training_readiness, training_status, vo2max)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (e.usuario_id, fecha, e.hrv_ms, e.fc_reposo, e.sleep_score,
         e.carga_aguda, e.carga_cronica, e.estres_medio,
         e.body_battery, e.body_battery_min, e.body_battery_max,
         e.training_readiness, e.training_status, e.vo2max),
    )
    if e.horas_sueno is not None or e.sleep_profundo_horas is not None:
        conn.execute(
            """INSERT OR REPLACE INTO datos_sueno
               (usuario_id, fecha, horas_totales, score, sleep_profundo_horas, sleep_rem_horas)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (e.usuario_id, fecha, e.horas_sueno, e.sleep_score,
             e.sleep_profundo_horas, e.sleep_rem_horas),
        )
    conn.commit()
    conn.close()
    return {"ok": True, "fecha": fecha}
