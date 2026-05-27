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
    # UNION: días con biométrico (con o sin sueño) + días con sólo sueño
    # Así nunca se pierde un día que tiene sueño pero no tiene HRV/stats.
    rows = conn.execute(
        """SELECT b.fecha,
                  b.hrv_ms, b.fc_reposo,
                  COALESCE(b.sleep_score, s.score) AS sleep_score,
                  b.carga_aguda, b.carga_cronica,
                  b.estres_medio, b.body_battery,
                  b.training_readiness, b.training_status, b.vo2max,
                  s.horas_totales, s.sleep_profundo_horas, s.sleep_rem_horas
           FROM datos_biometricos_premium b
           LEFT JOIN datos_sueno s
             ON b.usuario_id = s.usuario_id AND b.fecha = s.fecha
           WHERE b.usuario_id = ?

           UNION

           SELECT s.fecha,
                  NULL, NULL, s.score,
                  NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                  s.horas_totales, s.sleep_profundo_horas, s.sleep_rem_horas
           FROM datos_sueno s
           LEFT JOIN datos_biometricos_premium b
             ON b.usuario_id = s.usuario_id AND b.fecha = s.fecha
           WHERE s.usuario_id = ? AND b.fecha IS NULL

           ORDER BY fecha DESC LIMIT ?""",
        (usuario_id, usuario_id, limit),
    ).fetchall()
    conn.close()
    cols = ["fecha", "hrv_ms", "fc_reposo", "sleep_score", "carga_aguda", "carga_cronica",
            "estres_medio", "body_battery", "training_readiness", "training_status", "vo2max",
            "horas_totales", "sleep_profundo_horas", "sleep_rem_horas"]
    return [dict(zip(cols, r)) for r in rows]


class SweatRateTest(BaseModel):
    usuario_id: int
    fecha: Optional[str] = None
    peso_inicial_kg: float
    peso_final_kg: float
    liquidos_ml: float
    tiempo_min: float
    temperatura_c: Optional[float] = None
    humedad_pct: Optional[float] = None
    notas: Optional[str] = None


@router.get("/sweat-rate/{usuario_id}")
def get_sweat_rate(usuario_id: int, limit: int = 50):
    conn = get_db()
    rows = conn.execute(
        """SELECT id, fecha, peso_inicial_kg, peso_final_kg, liquidos_ml,
                  tiempo_min, temperatura_c, humedad_pct, tasa_sudoracion_lh, notas, creado_en
           FROM sweat_rate_tests
           WHERE usuario_id = ?
           ORDER BY fecha DESC LIMIT ?""",
        (usuario_id, limit),
    ).fetchall()
    conn.close()
    cols = ["id", "fecha", "peso_inicial_kg", "peso_final_kg", "liquidos_ml",
            "tiempo_min", "temperatura_c", "humedad_pct", "tasa_sudoracion_lh", "notas", "creado_en"]
    return [dict(zip(cols, r)) for r in rows]


@router.post("/sweat-rate")
def crear_sweat_rate(e: SweatRateTest):
    # Cálculo: Tasa (L/h) = (peso_inicial - peso_final + liquidos_ml/1000) / (tiempo_min/60)
    perdida_kg = e.peso_inicial_kg - e.peso_final_kg
    liquidos_l = e.liquidos_ml / 1000.0
    tiempo_h = e.tiempo_min / 60.0
    if tiempo_h <= 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="El tiempo debe ser mayor que 0")
    tasa = (perdida_kg + liquidos_l) / tiempo_h

    conn = get_db()
    fecha = e.fecha or datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        """INSERT INTO sweat_rate_tests
           (usuario_id, fecha, peso_inicial_kg, peso_final_kg, liquidos_ml,
            tiempo_min, temperatura_c, humedad_pct, tasa_sudoracion_lh, notas, creado_en)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (e.usuario_id, fecha, e.peso_inicial_kg, e.peso_final_kg,
         e.liquidos_ml, e.tiempo_min, e.temperatura_c, e.humedad_pct,
         round(tasa, 3), e.notas, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "fecha": fecha, "tasa_sudoracion_lh": round(tasa, 3)}


@router.delete("/sweat-rate/{test_id}")
def eliminar_sweat_rate(test_id: int):
    conn = get_db()
    conn.execute("DELETE FROM sweat_rate_tests WHERE id = ?", (test_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ── Intra-Entreno ────────────────────────────────────────────────────────────

class IntraEntrenoTest(BaseModel):
    usuario_id: int
    fecha: Optional[str] = None
    duracion_min: float
    alimentos: str
    tipo_fuente: str          # 'gel' | 'solido' | 'liquido' | 'mixto'
    cho_total_g: float
    malestar: int             # 1-10
    notas: Optional[str] = None


@router.get("/intra-entreno/{usuario_id}")
def get_intra_entreno(usuario_id: int, limit: int = 100):
    conn = get_db()
    rows = conn.execute(
        """SELECT id, fecha, duracion_min, alimentos, tipo_fuente,
                  cho_total_g, cho_g_hora, malestar, notas, creado_en
           FROM intra_entreno_tests
           WHERE usuario_id = ?
           ORDER BY fecha DESC LIMIT ?""",
        (usuario_id, limit),
    ).fetchall()
    conn.close()
    cols = ["id", "fecha", "duracion_min", "alimentos", "tipo_fuente",
            "cho_total_g", "cho_g_hora", "malestar", "notas", "creado_en"]
    return [dict(zip(cols, r)) for r in rows]


@router.post("/intra-entreno")
def crear_intra_entreno(e: IntraEntrenoTest):
    if e.duracion_min <= 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="La duración debe ser mayor que 0")
    if not 1 <= e.malestar <= 10:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="El malestar debe estar entre 1 y 10")

    cho_g_hora = round(e.cho_total_g / (e.duracion_min / 60.0), 2)

    conn = get_db()
    fecha = e.fecha or datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        """INSERT INTO intra_entreno_tests
           (usuario_id, fecha, duracion_min, alimentos, tipo_fuente,
            cho_total_g, cho_g_hora, malestar, notas, creado_en)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (e.usuario_id, fecha, e.duracion_min, e.alimentos, e.tipo_fuente,
         e.cho_total_g, cho_g_hora, e.malestar,
         e.notas, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "fecha": fecha, "cho_g_hora": cho_g_hora}


@router.delete("/intra-entreno/{test_id}")
def eliminar_intra_entreno(test_id: int):
    conn = get_db()
    conn.execute("DELETE FROM intra_entreno_tests WHERE id = ?", (test_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/intra-entreno/{usuario_id}/analisis")
def analizar_intra_entreno(usuario_id: int, objetivo_gh: float = 90.0):
    """
    Detecta patrones de malestar por fuente de carbohidratos.
    Compara entradas 'solido'/'mixto' buscando el umbral donde malestar >= 6.
    Sugiere complementar con líquido para alcanzar el objetivo_gh.
    """
    conn = get_db()

    # Todas las entradas con sólidos o mixto
    rows_solido = conn.execute(
        """SELECT cho_g_hora, malestar FROM intra_entreno_tests
           WHERE usuario_id = ? AND tipo_fuente IN ('solido', 'mixto')
           ORDER BY fecha DESC""",
        (usuario_id,),
    ).fetchall()

    # Todas las entradas con geles (referencia)
    rows_gel = conn.execute(
        """SELECT cho_g_hora, malestar FROM intra_entreno_tests
           WHERE usuario_id = ? AND tipo_fuente IN ('gel', 'liquido')
           ORDER BY fecha DESC""",
        (usuario_id,),
    ).fetchall()

    conn.close()

    resultado = {
        "suficientes_datos": False,
        "n_solido": len(rows_solido),
        "n_gel": len(rows_gel),
        "alerta": None,
        "resumen": None,
    }

    if len(rows_solido) < 2:
        return resultado

    resultado["suficientes_datos"] = True

    # Calcular promedios y detectar patrón
    ok_solido = [r[0] for r in rows_solido if r[1] <= 4]    # malestar tolerable
    mal_solido = [r[0] for r in rows_solido if r[1] >= 6]   # malestar alto

    # Media general de malestar
    media_malestar = round(sum(r[1] for r in rows_solido) / len(rows_solido), 1)
    media_cho = round(sum(r[0] for r in rows_solido) / len(rows_solido), 1)

    resultado["resumen"] = {
        "media_malestar": media_malestar,
        "media_cho_gh": media_cho,
        "n_total": len(rows_solido),
    }

    # Solo alertar si hay suficientes muestras con malestar alto (≥2)
    if len(mal_solido) < 2:
        return resultado

    # Límite = máximo CHO donde todavía hay tolerancia (o mínimo problemático - 10 si no hay OK)
    if ok_solido:
        limite = max(ok_solido)
    else:
        limite = min(mal_solido) - 10 if min(mal_solido) > 10 else 30.0

    diferencia = max(0.0, objetivo_gh - limite)

    resultado["alerta"] = {
        "limite_solidos_gh": round(limite, 1),
        "objetivo_gh": objetivo_gh,
        "diferencia_liquido_gh": round(diferencia, 1),
        "muestras_mal": len(mal_solido),
        "mensaje": (
            f"Tu límite de absorción con sólidos está en {round(limite)}g/h. "
            f"Para llegar a los {round(objetivo_gh)}g/h necesarios, "
            f"la app sugiere añadir {round(diferencia)}g/h en formato líquido en los bidones."
        ),
    }

    return resultado


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
