from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_db

router = APIRouter(prefix="/plan", tags=["plan"])


class SesionUpdate(BaseModel):
    completado: Optional[bool] = None
    km_realizados: Optional[float] = None
    notas: Optional[str] = None
    sesion: Optional[str] = None
    tipo: Optional[str] = None
    detalles: Optional[str] = None
    duracion_min: Optional[int] = None
    intensidad: Optional[str] = None
    km_planificados: Optional[float] = None
    fecha: Optional[str] = None


class SesionCreate(BaseModel):
    usuario_id: int
    fecha: str
    tipo: str
    sesion: str
    detalles: Optional[str] = None
    duracion_min: Optional[int] = None
    intensidad: Optional[str] = None
    km_planificados: Optional[float] = None


class GenerarSemanaRequest(BaseModel):
    fecha_inicio: str
    km_total: Optional[float] = None  # Si se proporciona, sobreescribe el cálculo automático


class RegenerarTotalRequest(BaseModel):
    semanas: int = 4  # Cuántas semanas futuras regenerar (incluye la actual)


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
    fields: dict = {}
    if update.completado is not None:
        fields["completado"] = 1 if update.completado else 0
    if update.km_realizados is not None:
        fields["km_realizados"] = update.km_realizados
    if update.sesion is not None:
        fields["sesion"] = update.sesion
    if update.tipo is not None:
        fields["tipo"] = update.tipo
    if update.detalles is not None:
        fields["detalles"] = update.detalles
    if update.duracion_min is not None:
        fields["duracion_min"] = update.duracion_min
    if update.intensidad is not None:
        fields["intensidad"] = update.intensidad
    if update.km_planificados is not None:
        fields["km_planificados"] = update.km_planificados
    if update.fecha is not None:
        fields["fecha"] = update.fecha
        fields["semana_inicio"] = _inicio_semana(update.fecha)
    if fields:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE plan_entrenamiento SET {set_clause} WHERE id = ?",
            (*fields.values(), sesion_id),
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


@router.post("/{usuario_id}/generar-semana")
def generar_semana(usuario_id: int, body: GenerarSemanaRequest):
    """Genera y guarda las 7 sesiones de la semana siguiendo las NORMAS DE ENTRENAMIENTO."""
    try:
        fecha_inicio = datetime.strptime(body.fecha_inicio, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato fecha inválido (YYYY-MM-DD)")

    conn = get_db()

    # ── 1. Borrar sesiones existentes de esa semana ──
    fecha_fin = (fecha_inicio + timedelta(days=6)).strftime("%Y-%m-%d")
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
    conn.execute(
        "DELETE FROM plan_entrenamiento WHERE usuario_id = ? AND fecha >= ? AND fecha <= ?",
        (usuario_id, fecha_inicio_str, fecha_fin),
    )

    # ── 2. Calcular km semana anterior ──
    semana_ant_inicio = (fecha_inicio - timedelta(days=7)).strftime("%Y-%m-%d")
    semana_ant_fin = (fecha_inicio - timedelta(days=1)).strftime("%Y-%m-%d")

    km_ant_plan = conn.execute(
        """SELECT COALESCE(SUM(km_planificados), 0)
           FROM plan_entrenamiento
           WHERE usuario_id = ? AND fecha >= ? AND fecha <= ? AND tipo != 'Fuerza'""",
        (usuario_id, semana_ant_inicio, semana_ant_fin),
    ).fetchone()[0]

    km_ant_garmin = conn.execute(
        """SELECT COALESCE(SUM(distancia_m)/1000, 0)
           FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ? AND fecha <= ?""",
        (usuario_id, semana_ant_inicio, semana_ant_fin),
    ).fetchone()[0]

    km_semana_ant = float(km_ant_garmin) if km_ant_garmin > 0 else float(km_ant_plan)
    if km_semana_ant < 1:
        km_semana_ant = 20.0  # arrancar con 20 km si no hay historial

    # ── 3. Determinar si es semana de descarga (cada 4a semana del año) ──
    semana_iso = fecha_inicio.isocalendar()[1]
    es_descarga = (semana_iso % 4 == 0)
    semanas_desde_descarga = semana_iso % 4

    # Si el usuario ha especificado km_total manualmente, usarlo directamente
    if body.km_total is not None and body.km_total > 0:
        km_total = round(float(body.km_total), 1)
        es_descarga = False  # No aplicar descarga cuando el usuario define el volumen
    elif es_descarga:
        km_total = round(km_semana_ant * 0.70, 1)
    else:
        km_total = round(km_semana_ant * 1.10, 1)

    # ── 4. Macrociclo según mes ──
    mes = fecha_inicio.month
    if mes in [5, 6, 7, 8]:
        macrociclo = 1
        sesion_calidad_impar = "Fartlek"
        sesion_calidad_par = "Progresiva"
    elif mes in [9, 10, 11]:
        macrociclo = 2
        sesion_calidad_impar = "Intervalos"
        sesion_calidad_par = "Tempo"
    elif mes in [12, 1]:
        macrociclo = 3
        sesion_calidad_impar = "Intervalos_VO2max"
        sesion_calidad_par = "Tempo_Largo"
    else:  # Feb-Abr
        macrociclo = 1
        sesion_calidad_impar = "Fartlek"
        sesion_calidad_par = "Progresiva"

    tipo_calidad = sesion_calidad_impar if semana_iso % 2 != 0 else sesion_calidad_par

    # ── 5. Distribución de km ──
    km_tl = min(round(km_total * 0.33, 1), 32.0)
    km_tl = max(km_tl, 8.0)
    km_rg = round(km_tl / 3, 1)
    km_calidad = round(km_total * 0.17, 1)
    km_rb = round(km_total - km_tl - km_rg - km_calidad, 1)
    if km_rb < 3:
        km_rb = 3.0

    # ── 6. Ciclos de progresión para fartlek/progresiva ──
    # Reps de fartlek: 6 + 1 por cada 4 semanas completadas desde inicio
    ciclo_num = max(0, (semana_iso - 1) // 4)
    fartlek_reps = 6 + ciclo_num
    prog_bloque_min = 5 + ciclo_num * 2

    # ── 7. Construir sesiones según distribución NORMAS ENTRENAMIENTO ──
    sesiones_plan = _construir_sesiones(
        fecha_inicio, tipo_calidad, macrociclo, km_calidad, km_rb, km_rg, km_tl,
        fartlek_reps, prog_bloque_min
    )

    # ── 8. Guardar en BD ──
    ahora = datetime.now().isoformat()
    for s in sesiones_plan:
        conn.execute(
            """INSERT INTO plan_entrenamiento
               (usuario_id, semana_inicio, fecha, tipo, sesion, detalles, duracion_min,
                intensidad, km_planificados, creado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (usuario_id, fecha_inicio_str, s["fecha"], s["tipo"], s["sesion"],
             s["detalles"], s["duracion_min"], s["intensidad"], s["km_planificados"], ahora),
        )
    conn.commit()

    # ── 9. Construir coach_tip ──
    lesiones_activas = conn.execute(
        """SELECT COUNT(*) FROM lesiones_activas WHERE usuario_id = ? AND activa = 1""",
        (usuario_id,),
    ).fetchone()
    # La tabla puede no existir; ignorar errores
    conn.close()

    if es_descarga:
        tipo_semana = "Semana de Descarga"
        tip_semana = f"Descansa y asimila. Volumen reducido al 70%: {km_semana_ant:.0f} km → {km_total:.0f} km."
    else:
        n = semanas_desde_descarga
        tipo_semana = f"Semana de Aumento {n}"
        tip_semana = f"Progresión +10%: {km_semana_ant:.0f} km → {km_total:.0f} km. Macrociclo {macrociclo} — {tipo_calidad}."

    return {
        "ok": True,
        "semana_inicio": fecha_inicio_str,
        "km_total": km_total,
        "tipo_semana": tipo_semana,
        "coach_tip": tip_semana,
        "macrociclo": macrociclo,
        "sesiones": [
            {
                "fecha": s["fecha"],
                "tipo": s["tipo"],
                "sesion": s["sesion"],
                "detalles": s["detalles"],
                "km_planificados": s["km_planificados"],
                "duracion_min": s["duracion_min"],
                "intensidad": s["intensidad"],
            }
            for s in sesiones_plan
        ],
    }


@router.post("/{usuario_id}/regenerar-total")
def regenerar_total(usuario_id: int, body: RegenerarTotalRequest):
    """Regenera el plan completo desde la semana actual hacia adelante.
    Usa los km reales de Garmin de las últimas 4 semanas como base.
    Útil cuando el atleta ha quedado por debajo del plan y hay que readaptar."""
    conn = get_db()
    hoy = datetime.now()

    # ── 1. Calcular km reales promedio de las últimas 4 semanas ──
    hace_28 = (hoy - timedelta(days=28)).strftime("%Y-%m-%d")
    km_reales_4sem = conn.execute(
        """SELECT COALESCE(SUM(distancia_m)/1000, 0)
           FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ?""",
        (usuario_id, hace_28),
    ).fetchone()[0]

    km_base = float(km_reales_4sem) / 4  # promedio semanal real
    if km_base < 5:
        # Si no hay datos Garmin, usar el plan de la última semana
        inicio_sem_ant = (hoy - timedelta(days=7 + hoy.weekday())).strftime("%Y-%m-%d")
        fin_sem_ant = (hoy - timedelta(days=hoy.weekday() + 1)).strftime("%Y-%m-%d")
        km_plan_ant = conn.execute(
            """SELECT COALESCE(SUM(km_planificados), 0)
               FROM plan_entrenamiento
               WHERE usuario_id = ? AND fecha >= ? AND fecha <= ? AND tipo != 'Fuerza'""",
            (usuario_id, inicio_sem_ant, fin_sem_ant),
        ).fetchone()[0]
        km_base = float(km_plan_ant) if km_plan_ant > 5 else 20.0

    # ── 2. Generar N semanas desde la semana actual ──
    semanas_generadas = []
    # Inicio de la semana actual (lunes)
    dias_hasta_lunes = hoy.weekday()
    semana_actual = hoy - timedelta(days=dias_hasta_lunes)

    for n in range(body.semanas):
        fecha_sem = (semana_actual + timedelta(weeks=n)).strftime("%Y-%m-%d")
        semana_iso = (semana_actual + timedelta(weeks=n)).isocalendar()[1]
        es_descarga = (semana_iso % 4 == 0)

        if es_descarga:
            km_sem = round(km_base * 0.70, 1)
        elif n == 0:
            km_sem = round(km_base, 1)  # semana actual: no subir, usar base real
        else:
            km_sem = round(km_base * (1.10 ** n), 1)

        km_sem = min(km_sem, 80.0)  # tope de seguridad

        _generar_semana_interna(conn, usuario_id, fecha_sem, km_sem)
        semanas_generadas.append({"semana_inicio": fecha_sem, "km_total": km_sem, "descarga": es_descarga})

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "km_base_real": round(km_base, 1),
        "semanas_regeneradas": len(semanas_generadas),
        "detalle": semanas_generadas,
    }


def _generar_semana_interna(conn, usuario_id: int, fecha_inicio_str: str, km_total: float):
    """Genera y guarda las sesiones de una semana con km_total dado, sin commit."""
    fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d")
    fecha_fin = (fecha_inicio + timedelta(days=6)).strftime("%Y-%m-%d")

    # Borrar sesiones existentes
    conn.execute(
        "DELETE FROM plan_entrenamiento WHERE usuario_id = ? AND fecha >= ? AND fecha <= ?",
        (usuario_id, fecha_inicio_str, fecha_fin),
    )

    semana_iso = fecha_inicio.isocalendar()[1]
    mes = fecha_inicio.month

    if mes in [5, 6, 7, 8]:
        macrociclo = 1
        sesion_calidad_impar = "Fartlek"
        sesion_calidad_par = "Progresiva"
    elif mes in [9, 10, 11]:
        macrociclo = 2
        sesion_calidad_impar = "Intervalos"
        sesion_calidad_par = "Tempo"
    elif mes in [12, 1]:
        macrociclo = 3
        sesion_calidad_impar = "Intervalos_VO2max"
        sesion_calidad_par = "Tempo_Largo"
    else:
        macrociclo = 1
        sesion_calidad_impar = "Fartlek"
        sesion_calidad_par = "Progresiva"

    tipo_calidad = sesion_calidad_impar if semana_iso % 2 != 0 else sesion_calidad_par

    km_tl = min(round(km_total * 0.33, 1), 32.0)
    km_tl = max(km_tl, 8.0)
    km_rg = round(km_tl / 3, 1)
    km_calidad = round(km_total * 0.17, 1)
    km_rb = max(round(km_total - km_tl - km_rg - km_calidad, 1), 3.0)

    ciclo_num = max(0, (semana_iso - 1) // 4)
    fartlek_reps = 6 + ciclo_num
    prog_bloque_min = 5 + ciclo_num * 2

    sesiones_plan = _construir_sesiones(
        fecha_inicio, tipo_calidad, macrociclo, km_calidad, km_rb, km_rg, km_tl,
        fartlek_reps, prog_bloque_min
    )

    ahora = datetime.now().isoformat()
    for s in sesiones_plan:
        conn.execute(
            """INSERT INTO plan_entrenamiento
               (usuario_id, semana_inicio, fecha, tipo, sesion, detalles, duracion_min,
                intensidad, km_planificados, creado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (usuario_id, fecha_inicio_str, s["fecha"], s["tipo"], s["sesion"],
             s["detalles"], s["duracion_min"], s["intensidad"], s["km_planificados"], ahora),
        )


def _construir_sesiones(
    fecha_inicio: datetime,
    tipo_calidad: str,
    macrociclo: int,
    km_calidad: float,
    km_rb: float,
    km_rg: float,
    km_tl: float,
    fartlek_reps: int,
    prog_bloque_min: int,
) -> list:
    """Construye la lista de sesiones para una semana según las NORMAS DE ENTRENAMIENTO:
    Lun=Pull · Mar=Calidad · Mié=Push · Jue=RB · Vie=Pierna · Sáb=RG · Dom=TL"""
    sesiones = []
    for offset in range(7):
        fecha_dia = (fecha_inicio + timedelta(days=offset)).strftime("%Y-%m-%d")

        if offset == 0:  # Lunes — Fuerza Pull
            sesiones.append({
                "fecha": fecha_dia, "tipo": "Fuerza",
                "sesion": "Fuerza Tren Superior Pull",
                "detalles": "Dominadas 4×6, Remo con barra 4×8, Curl bíceps 3×12, Face Pull 3×15",
                "duracion_min": 55, "intensidad": "Moderada", "km_planificados": None,
            })

        elif offset == 1:  # Martes — Calidad
            if tipo_calidad == "Fartlek":
                sesion_nombre = f"Fartlek Mac{macrociclo}"
                detalles = f"15' Z2 + {fartlek_reps}×(1'@4:55 + 2' Z1) + 5' Z1. Total ~{km_calidad} km"
            elif tipo_calidad == "Progresiva":
                sesion_nombre = f"Progresiva Mac{macrociclo}"
                detalles = (f"{km_calidad} km — 1/3 Z1 / 1/3 Z2 / 1/3 Z4. "
                            f"Último tercio: {prog_bloque_min} min a 4:55 min/km")
            elif tipo_calidad == "Intervalos":
                sesion_nombre = "Intervalos Umbral"
                detalles = f"15' calentamiento + 5×(5' @umbral + 3' Z1) + 10' vuelta calma. ~{km_calidad} km"
            elif tipo_calidad == "Tempo":
                sesion_nombre = "Tempo Run"
                detalles = f"10' Z1 + {km_calidad} km @ritmo umbral (5:00-5:10 min/km) + 10' Z1"
            else:
                sesion_nombre = tipo_calidad
                detalles = f"Sesión de calidad — {km_calidad} km"
            sesiones.append({
                "fecha": fecha_dia, "tipo": "Carrera",
                "sesion": sesion_nombre, "detalles": detalles,
                "duracion_min": 65, "intensidad": "Alta", "km_planificados": km_calidad,
            })

        elif offset == 2:  # Miércoles — Fuerza Push
            sesiones.append({
                "fecha": fecha_dia, "tipo": "Fuerza",
                "sesion": "Fuerza Tren Superior Push",
                "detalles": "Press banca 4×6, Press militar 4×8, Fondos 3×12, Extensión tríceps 3×15",
                "duracion_min": 55, "intensidad": "Moderada", "km_planificados": None,
            })

        elif offset == 3:  # Jueves — Rodaje Base Z2
            sesiones.append({
                "fecha": fecha_dia, "tipo": "Carrera",
                "sesion": "Rodaje Base Z2",
                "detalles": f"Rodaje Base Z2 — {km_rb} km. Ritmo 6:20-6:50 min/km. FC 130-150 ppm.",
                "duracion_min": round(km_rb * 6.5), "intensidad": "Baja", "km_planificados": km_rb,
            })

        elif offset == 4:  # Viernes — Fuerza Pierna
            sesiones.append({
                "fecha": fecha_dia, "tipo": "Fuerza",
                "sesion": "Fuerza Pierna",
                "detalles": "Sentadilla 4×8 @75%1RM, Peso muerto rumano 3×10, Zancada búlgara 3×12, Hip Thrust 3×15",
                "duracion_min": 65, "intensidad": "Alta", "km_planificados": None,
            })

        elif offset == 5:  # Sábado — Regenerativo (≈ 1/3 de TL)
            sesiones.append({
                "fecha": fecha_dia, "tipo": "Carrera",
                "sesion": "Regenerativo Z1",
                "detalles": f"Regenerativo Z1 — {km_rg} km. Ritmo muy suave >7:00 min/km. FC <130 ppm.",
                "duracion_min": round(km_rg * 7.5), "intensidad": "Muy baja", "km_planificados": km_rg,
            })

        elif offset == 6:  # Domingo — Tirada Larga (30-35% volumen)
            sesiones.append({
                "fecha": fecha_dia, "tipo": "Carrera",
                "sesion": "Tirada Larga Z2",
                "detalles": f"Tirada Larga Z2 — {km_tl} km. Ritmo 6:20-6:50 min/km. FC 130-150 ppm.",
                "duracion_min": round(km_tl * 6.5), "intensidad": "Moderada-Alta", "km_planificados": km_tl,
            })

    return sesiones


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
