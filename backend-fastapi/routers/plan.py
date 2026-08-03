import sys
import os
import re
import csv
import io
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from database import get_db
from constants import RUNNING_TIPOS, RUNNING_TIPOS_SQL

# Intentar importar reglas desde la carpeta src/ (que está un nivel arriba del backend)
try:
    _src_path = os.path.join(os.path.dirname(__file__), "..", "..", "src")
    if _src_path not in sys.path:
        sys.path.insert(0, _src_path)
    from plan.reglas import calcular_semaforo, controlar_distribucion_intensidad
    _REGLAS_DISPONIBLES = True
except Exception:
    _REGLAS_DISPONIBLES = False

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
    incluir_calidad: bool = True  # Si es False, las sesiones de calidad se sustituyen por Rodaje Base
    incluir_fuerza: bool = False  # Si es False (por defecto), no se generan sesiones de Fuerza esta semana
    dry_run: bool = False  # Si es True, solo calcula y devuelve las sesiones, no las guarda
    ciclo_override: Optional[str] = None  # "carga1" | "carga2" | "carga3" | "descarga" — fuerza el tipo de semana


class AplicarSemanaRequest(BaseModel):
    fecha_inicio: str
    sesiones: list[dict]


class RegenerarTotalRequest(BaseModel):
    semanas: int = 4  # Cuántas semanas futuras regenerar (incluye la actual)
    incluir_fuerza: bool = False  # Si es False (por defecto), no se generan sesiones de Fuerza


FARTLEK_REPS_MAX = 10  # Máximo absoluto de reps según NORMAS ENTRENAMIENTO.pdf

# Ciclo de 4 semanas: Carga 1 → Carga 2 → Carga 3 → Descarga → Carga 1…
# Anclado a una semana de referencia conocida como Carga 1 (lunes 2026-07-27),
# para que la etiqueta que ve el usuario no dependa de la semana ISO del año.
CICLO_CARGA_ANCLA = datetime(2026, 7, 27)


def _posicion_ciclo(fecha_inicio: datetime) -> int:
    """0=Carga1, 1=Carga2, 2=Carga3, 3=Descarga."""
    semanas = (fecha_inicio - CICLO_CARGA_ANCLA).days // 7
    return semanas % 4


def _etiqueta_ciclo(pos: int) -> str:
    return "Descarga" if pos == 3 else f"Carga {pos + 1}"


def _calcular_macrociclo_v2(
    fecha_inicio: datetime,
    plan_start_str: str | None,
    f_inter_str: str | None,
    f_final_str: str | None,
) -> dict | None:
    """Calendario de macrociclos de NORMAS_ENTRENAMIENTO_v2 (dos carreras: una
    intermedia de test — ej. media maratón — y el maratón final). Devuelve None si
    el usuario no tiene configurada la carrera intermedia, para que el caller use la
    lógica antigua de un solo objetivo (por mes).

    M1 = semanas 1-4 del plan (fijo). M2 = desde semana 5 hasta el taper de la
    intermedia. M3 = desde la semana siguiente a la intermedia hasta el taper del
    objetivo final. M4 = las 3 semanas de taper antes del objetivo final.
    """
    if not f_final_str or not f_inter_str:
        return None
    try:
        f_final = datetime.strptime(f_final_str, "%Y-%m-%d")
        f_inter = datetime.strptime(f_inter_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None

    plan_start = None
    if plan_start_str:
        try:
            plan_start = datetime.strptime(plan_start_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            plan_start = None
    if not plan_start:
        plan_start = f_inter - timedelta(weeks=14)  # fallback: 14 semanas de base a la intermedia

    monday_plan_start = plan_start - timedelta(days=plan_start.weekday())
    semana_num = max(1, (fecha_inicio - monday_plan_start).days // 7 + 1)

    dias_inter = (f_inter - fecha_inicio).days
    dias_final = (f_final - fecha_inicio).days

    macrociclo: int
    sub_fase: str | None = None
    proximo_hito: str | None = None
    semanas_hasta_hito: int | None = None

    if dias_inter >= 0:
        proximo_hito, semanas_hasta_hito = "intermedia", dias_inter // 7
        if dias_inter <= 6:
            macrociclo, sub_fase = 2, "Semana de carrera"
        elif dias_inter <= 13:
            macrociclo, sub_fase = 2, "Taper corto"
        elif semana_num <= 4:
            macrociclo = 1
        else:
            macrociclo = 2
    elif dias_final >= 0:
        proximo_hito, semanas_hasta_hito = "final", dias_final // 7
        if dias_final <= 6:
            macrociclo, sub_fase = 4, "Semana de carrera"
        elif dias_final <= 13:
            macrociclo, sub_fase = 4, "Taper -2"
        elif dias_final <= 20:
            macrociclo, sub_fase = 4, "Taper -3"
        else:
            macrociclo = 3
    else:
        macrociclo, sub_fase = 4, "Semana de carrera"  # objetivo final ya pasado

    if macrociclo == 1:
        semana_en_macro = semana_num
    elif macrociclo == 2:
        semana_en_macro = max(1, semana_num - 4)
    elif macrociclo == 3:
        semana_en_macro = max(1, (fecha_inicio - f_inter).days // 7 + 1)
    else:
        semana_en_macro = 1

    if macrociclo == 3:
        # Ciclo especial 2 semanas de carga + 1 de descarga
        pos = (semana_en_macro - 1) % 3
        es_descarga = pos == 2
        ciclo_label = "Descarga" if es_descarga else f"Carga {pos + 1}"
    elif macrociclo == 4:
        es_descarga = False
        ciclo_label = sub_fase or "Tapering"
    else:
        pos = (semana_num - 1) % 4
        es_descarga = pos == 3
        ciclo_label = "Descarga" if es_descarga else f"Carga {pos + 1}"

    # Duración total de cada macrociclo (en semanas), para la barra de progreso.
    # M1 y M4 son fijos; M2/M3 dependen de la distancia real entre las dos carreras.
    race_week_monday = f_inter - timedelta(days=f_inter.weekday())
    taper3_start_monday = f_final - timedelta(days=f_final.weekday()) - timedelta(weeks=3)
    semanas_m2 = max(1, (race_week_monday - monday_plan_start).days // 7 + 1 - 4)
    semanas_m3 = max(1, (taper3_start_monday - (race_week_monday + timedelta(weeks=1))).days // 7 + 1)
    semanas_por_macrociclo = {1: 4, 2: semanas_m2, 3: semanas_m3, 4: 3}

    return {
        "macrociclo": macrociclo,
        "sub_fase": sub_fase,
        "es_descarga": es_descarga,
        "ciclo_label": ciclo_label,
        "semana_num": semana_num,
        "semana_en_macro": semana_en_macro,
        "semanas_totales_macrociclo": semanas_por_macrociclo[macrociclo],
        "semanas_por_macrociclo": semanas_por_macrociclo,
        "proximo_hito": proximo_hito,
        "semanas_hasta_hito": semanas_hasta_hito,
    }


def _migrar_progresiva_legacy(conn, sesiones: list) -> list:
    """Detecta sesiones Progresiva con bloque_min incorrecto (calculado con semana ISO en
    lugar de semanas dentro del Mac1) y las corrige en la BD + en la lista devuelta.

    Señal de sesión incorrecta:
    - sesion == 'Progresiva' y detalles contiene un bloque Z4 > 5 min en Mac1 semana ≤4
      (el código viejo usaba semana ISO → bloque_min podía ser 15 cuando debería ser 5).
    - También captura el bug matemático: Z4_min a 4:55/km > km_planificados total.

    Corrección: bloque_min = 5 (inicio del Mac1), km_real calculado desde los tiempos.
    """
    PROG_BLOQUE_MIN_INICIO = 5  # NORMAS: bloque Z4 empieza en 5 min

    for s in sesiones:
        if s.get("tipo") != "Carrera":
            continue
        sesion_name = s.get("sesion", "") or ""
        if "Progresiva" not in sesion_name:
            continue

        detalles = s.get("detalles", "") or ""
        km_actual = s.get("km_planificados") or 0

        # Extraer bloque_min del texto actual: "Xer tercio Z4 (N min a 4:55min/km)"
        match = re.search(r"Z4\s*\((\d+)\s*min", detalles)
        bloque_min_actual = int(match.group(1)) if match else None

        if bloque_min_actual is None:
            continue  # descripción desconocida, no tocar

        # Detectar inconsistencia matemática: Z4 solo ya supera km_total
        # (bloque_min / 4.917 > km_planificados → imposible)
        km_solo_z4 = bloque_min_actual / 4.917
        es_inconsistente = km_actual > 0 and km_solo_z4 > km_actual * 0.9

        if not es_inconsistente and bloque_min_actual <= PROG_BLOQUE_MIN_INICIO:
            continue  # ya es correcto o ya fue migrado

        # Corregir: bloque_min = 5 min (inicio Mac1), km_real desde los tiempos
        bm = PROG_BLOQUE_MIN_INICIO
        km_z1 = round(bm / 7.5, 2)    # Z1: ~7:30/km
        km_z2 = round(bm / 6.5, 2)    # Z2: ~6:30/km
        km_z4 = round(bm / 4.917, 2)  # Z4: ~4:55/km
        km_real = round(km_z1 + km_z2 + km_z4, 1)

        nuevos_detalles = (
            f"{bm} min Z1 (suave, ~7:30/km) · {bm} min Z2 (~6:30/km) · {bm} min Z4 (@4:55min/km). "
            f"Total ~{km_real} km en {bm * 3} min. "
            f"Progresión: bloque Z4 empieza {bm} min, +2 min cada ciclo de 4 semanas."
        )

        conn.execute(
            "UPDATE plan_entrenamiento SET sesion='Progresiva', detalles=?, km_planificados=? WHERE id=?",
            (nuevos_detalles, km_real, s["id"]),
        )
        s["sesion"] = "Progresiva"
        s["detalles"] = nuevos_detalles
        s["km_planificados"] = km_real

    conn.commit()
    return sesiones


def _migrar_fartlek_legacy(conn, sesiones: list) -> list:
    """Detecta sesiones Fartlek con reps incorrectas (código viejo o por encima del cap)
    y las corrige en la BD + en la lista devuelta, sin regenerar el plan completo.

    Señales de sesión incorrecta:
    - sesion contiene 'Mac' (e.g. 'Fartlek Mac1') → nombre antiguo
    - km_planificados < 5.0 → km muy bajos (formato viejo)
    - reps extraídas de detalles > FARTLEK_REPS_MAX → reps por encima del cap de seguridad
      (esto captura sesiones generadas antes de que se aplicara el cap, e.g. 11 reps)
    """
    km_warmup  = round(15 / 6.33, 1)          # ~2.4 km
    km_per_rep = round(1 / 4.917 + 2 / 6.5, 2)  # ~0.51 km/rep
    km_cool    = round(5 / 7.0, 1)             # ~0.7 km

    for s in sesiones:
        if s.get("tipo") != "Carrera":
            continue
        sesion_name = s.get("sesion", "") or ""
        if "Fartlek" not in sesion_name:
            continue

        km_actual = s.get("km_planificados") or 0
        is_legacy_name = "Mac" in sesion_name or "mac" in sesion_name
        is_low_km = km_actual > 0 and km_actual < 5.0

        # Extraer reps ANTES del filtro para poder verificar el cap
        detalles = s.get("detalles", "") or ""
        match = re.search(r"(\d+)[×x]\(", detalles)
        reps_extraidas = int(match.group(1)) if match else None
        is_reps_over_cap = reps_extraidas is not None and reps_extraidas > FARTLEK_REPS_MAX

        if not (is_legacy_name or is_low_km or is_reps_over_cap):
            continue  # sesión moderna y dentro del rango permitido, nada que hacer

        # Determinar reps correctas:
        # - Si las reps estaban por encima del cap → capear a FARTLEK_REPS_MAX
        # - Si el formato era legacy sin reps → arrancar en 6 (inicio de progresión)
        if reps_extraidas is not None:
            reps = min(reps_extraidas, FARTLEK_REPS_MAX)
        else:
            reps = 6  # valor de inicio según NORMAS ENTRENAMIENTO.pdf

        km_real = round(km_warmup + reps * km_per_rep + km_cool, 1)
        nuevos_detalles = (
            f"15' calentamiento Z2 + {reps}×(1'@4:55min/km + 2' Z1) + 5' Z1. "
            f"Total ~{km_real} km. Progresión: comenzar con 6 reps, +1 rep cada ciclo de 4 semanas."
        )

        # Actualizar BD
        conn.execute(
            "UPDATE plan_entrenamiento SET sesion='Fartlek', detalles=?, km_planificados=? WHERE id=?",
            (nuevos_detalles, km_real, s["id"]),
        )
        # Actualizar objeto en memoria
        s["sesion"] = "Fartlek"
        s["detalles"] = nuevos_detalles
        s["km_planificados"] = km_real

    conn.commit()
    return sesiones


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

    # Auto-migrar sesiones Fartlek antiguas (nombre "Fartlek MacX" o km erróneo)
    sesiones = _migrar_fartlek_legacy(conn, sesiones)
    # Auto-migrar sesiones Progresiva antiguas (bloque Z4 imposible: > km total)
    sesiones = _migrar_progresiva_legacy(conn, sesiones)

    # Ritmo/FC objetivo (extraídos de "detalles") y, para la Tirada Larga, la FC de
    # reposo del día siguiente — para la tab Comparar (real vs esperado).
    for s in sesiones:
        s["ritmo_esperado"], s["fc_esperado"] = _parse_ritmo_fc(s.get("detalles"))
        s["fc_reposo_dia_siguiente"] = None
        if (s.get("sesion") or "").startswith("Tirada"):
            try:
                dia_siguiente = (datetime.strptime(s["fecha"], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                row = conn.execute(
                    """SELECT fc_reposo FROM datos_biometricos_premium
                       WHERE usuario_id = ? AND fecha = ? AND fc_reposo IS NOT NULL LIMIT 1""",
                    (usuario_id, dia_siguiente),
                ).fetchone()
                if row:
                    s["fc_reposo_dia_siguiente"] = row[0]
            except Exception:
                pass

    # Estadísticas semana
    km_plan = sum(s["km_planificados"] or 0 for s in sesiones)
    km_real = sum(s["km_realizados"] or 0 for s in sesiones)
    completadas = sum(1 for s in sesiones if s["completado"])

    # Actividades Garmin de la semana (para km reales si no hay km_realizados)
    garmin_rows = conn.execute(
        """SELECT id_actividad, fecha, tipo_deporte, distancia_m, tiempo_seg, ritmo_medio, fc_media, subtipo_manual
           FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ? AND fecha <= ?
           ORDER BY fecha ASC""",
        (usuario_id, fecha_inicio, fin),
    ).fetchall()
    garmin_cols = ["id_actividad", "fecha", "tipo_deporte", "distancia_m", "tiempo_seg", "ritmo_medio", "fc_media", "subtipo_manual"]
    actividades_garmin = [dict(zip(garmin_cols, r)) for r in garmin_rows]

    # Si no hay km_real en plan pero hay Garmin, usar Garmin — solo carrera/cinta,
    # no bici/natación/etc.
    if km_real == 0 and actividades_garmin:
        km_real = round(
            sum(a["distancia_m"] or 0 for a in actividades_garmin
                if (a["tipo_deporte"] or "").lower() in RUNNING_TIPOS) / 1000,
            1,
        )

    # Coach recommendation
    perfil_row = conn.execute(
        """SELECT objetivo_tipo, fecha_objetivo, fcmax, fecha_inicio_entrenamiento,
                  fecha_objetivo_intermedio, objetivo_intermedio_nombre
           FROM usuarios WHERE id = ?""",
        (usuario_id,),
    ).fetchone()

    # Distribución 80/20 Z1+Z2 de la semana (aviso, no corrige automáticamente)
    distribucion_msg = None
    if _REGLAS_DISPONIBLES and sesiones:
        try:
            _, distribucion_msg = controlar_distribucion_intensidad(
                [{"tipo": s["tipo"], "intensidad": s["intensidad"], "km_planificados": s["km_planificados"]} for s in sesiones]
            )
        except Exception:
            pass

    conn.close()

    objetivo_tipo = perfil_row[0] if perfil_row else "maraton"
    fecha_objetivo = perfil_row[1] if perfil_row else None
    objetivo_intermedio_nombre = perfil_row[5] if perfil_row else None
    fase = _calcular_fase_nombre(objetivo_tipo, fecha_objetivo)

    # Ciclo Carga1/Carga2/Carga3/Descarga + macrociclo — informativo, para que el
    # usuario sepa en qué tipo de semana y macrociclo está. Camino v2 (dos carreras)
    # si está configurado, si no ciclo genérico anclado + macrociclo antiguo por mes.
    v2_info = _calcular_macrociclo_v2(
        inicio,
        perfil_row[3] if perfil_row else None,
        perfil_row[4] if perfil_row else None,
        fecha_objetivo,
    )
    if v2_info:
        ciclo_label = v2_info["ciclo_label"]
        es_descarga = v2_info["es_descarga"]
        macrociclo_num = v2_info["macrociclo"]
        semana_num = v2_info["semana_num"]
        semana_en_macro = v2_info["semana_en_macro"]
        semanas_por_macrociclo = v2_info["semanas_por_macrociclo"]
        proximo_hito = v2_info["proximo_hito"]
        semanas_hasta_hito = v2_info["semanas_hasta_hito"]
    else:
        semana_en_macro = None
        semanas_por_macrociclo = None
        pos_ciclo = _posicion_ciclo(inicio)
        ciclo_label = _etiqueta_ciclo(pos_ciclo)
        es_descarga = (pos_ciclo == 3)
        mes = inicio.month
        if mes in (5, 6, 7, 8):
            macrociclo_num = 1
        elif mes in (9, 10, 11):
            macrociclo_num = 2
        elif mes in (12, 1):
            macrociclo_num = 3
        else:
            macrociclo_num = 1
        if fecha_objetivo:
            try:
                dias_obj = (datetime.strptime(fecha_objetivo, "%Y-%m-%d") - inicio).days
                if 0 <= dias_obj <= 21:
                    macrociclo_num = 4
            except (ValueError, TypeError):
                pass
        semana_num = None
        proximo_hito = None
        semanas_hasta_hito = None

    proximo_hito_nombre = None
    if proximo_hito == "intermedia":
        proximo_hito_nombre = objetivo_intermedio_nombre or "carrera intermedia"
    elif proximo_hito == "final":
        proximo_hito_nombre = "objetivo final"

    return {
        "semana_inicio": fecha_inicio,
        "sesiones": sesiones,
        "actividades_garmin": actividades_garmin,
        "ciclo_label": ciclo_label,
        "macrociclo_label": f"M{macrociclo_num}",
        "semana_num": semana_num,
        "semana_en_macro": semana_en_macro,
        "semanas_por_macrociclo": semanas_por_macrociclo,
        "proximo_hito": proximo_hito,
        "proximo_hito_nombre": proximo_hito_nombre,
        "semanas_hasta_hito": semanas_hasta_hito,
        "distribucion_intensidad": distribucion_msg,
        "stats": {
            "km_planificados": round(km_plan, 1),
            "km_realizados": round(km_real, 1),
            "sesiones_completadas": completadas,
            "total_sesiones": len(sesiones),
        },
        "es_descarga": es_descarga,
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


@router.get("/{usuario_id}/completo")
def get_plan_completo(usuario_id: int):
    """Plan de carrera completo, semana por semana, solo con tipo de sesión y km
    (resumen ligero para la vista 'Plan' — sin cruce con Garmin ni cálculo de fase).
    Solo desde el inicio real del plan (fecha_inicio_entrenamiento) — las semanas
    anteriores pueden contener datos de pruebas antiguas (formato legacy) que ya
    no reflejan el plan real. Si no hay fecha de inicio guardada, se muestra todo."""
    conn = get_db()
    perfil_row = conn.execute(
        "SELECT fecha_inicio_entrenamiento FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()
    fecha_inicio_plan = perfil_row[0] if perfil_row else None

    if fecha_inicio_plan:
        rows = conn.execute(
            """SELECT fecha, tipo, sesion, km_planificados, semana_inicio
               FROM plan_entrenamiento
               WHERE usuario_id = ? AND fecha >= ?
               ORDER BY fecha ASC""",
            (usuario_id, fecha_inicio_plan),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT fecha, tipo, sesion, km_planificados, semana_inicio
               FROM plan_entrenamiento
               WHERE usuario_id = ?
               ORDER BY fecha ASC""",
            (usuario_id,),
        ).fetchall()
    conn.close()

    semanas: dict[str, dict] = {}
    for fecha, tipo, sesion, km_planificados, semana_inicio in rows:
        semana = semanas.setdefault(semana_inicio, {"semana_inicio": semana_inicio, "sesiones": [], "km_planificados": 0.0})
        semana["sesiones"].append({
            "fecha": fecha,
            "tipo": tipo,
            "sesion": sesion,
            "km_planificados": km_planificados,
        })
        semana["km_planificados"] += km_planificados or 0

    lista = sorted(semanas.values(), key=lambda w: w["semana_inicio"])
    for w in lista:
        w["km_planificados"] = round(w["km_planificados"], 1)
    return {"semanas": lista}


def _calcular_semanas_en_macro(fecha: datetime, macrociclo: int) -> int:
    """Calcula semanas transcurridas desde el INICIO del macrociclo actual.

    Mac1 (May-Ago):  inicio = 1 mayo del año en curso
    Mac2 (Sep-Nov):  inicio = 1 septiembre del año en curso
    Mac3 (Dic-Ene):  inicio = 1 diciembre del año anterior (si estamos en enero)
                              o 1 diciembre del año en curso (si estamos en diciembre)
    Mac4 (Tapering): no tiene progresión de reps → devuelve 1

    IMPORTANTE: esto garantiza que en la 1ª semana de Mac1 tengamos siempre 6 reps,
    independientemente del número de semana ISO del año.
    """
    año = fecha.year
    if macrociclo == 1:
        inicio = datetime(año, 5, 1)
    elif macrociclo == 2:
        inicio = datetime(año, 9, 1)
    elif macrociclo == 3:
        # Mac3 cruza año: si estamos en enero, el inicio fue el 1 dic del año anterior
        inicio = datetime(año - 1 if fecha.month == 1 else año, 12, 1)
    else:
        return 1  # Tapering: sin progresión, reps fijas en mínimo
    semanas = max(1, (fecha - inicio).days // 7 + 1)
    return semanas


@router.post("/{usuario_id}/generar-semana")
def generar_semana(usuario_id: int, body: GenerarSemanaRequest):
    """Genera y guarda las 7 sesiones de la semana siguiendo las NORMAS DE ENTRENAMIENTO."""
    try:
        fecha_inicio = datetime.strptime(body.fecha_inicio, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato fecha inválido (YYYY-MM-DD)")

    conn = get_db()

    # ── 1. Borrar sesiones existentes de esa semana (salvo dry_run: solo previsualiza) ──
    fecha_fin = (fecha_inicio + timedelta(days=6)).strftime("%Y-%m-%d")
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
    if not body.dry_run:
        conn.execute(
            "DELETE FROM plan_entrenamiento WHERE usuario_id = ? AND fecha >= ? AND fecha <= ?",
            (usuario_id, fecha_inicio_str, fecha_fin),
        )

    # ── 2. Obtener perfil del usuario (fecha objetivo + lesiones) ──
    perfil_row = conn.execute(
        """SELECT objetivo_tipo, fecha_objetivo, fcmax, fecha_inicio_entrenamiento,
                  fecha_objetivo_intermedio
           FROM usuarios WHERE id = ?""",
        (usuario_id,),
    ).fetchone()
    fecha_objetivo_str = perfil_row[1] if perfil_row else None
    fecha_inicio_entreno_str = perfil_row[3] if perfil_row else None
    fecha_objetivo_intermedio_str = perfil_row[4] if perfil_row else None

    # Verificar lesiones activas ANTES de calcular volumen
    lesiones_activas_count = 0
    try:
        lesiones_activas_count = conn.execute(
            "SELECT COUNT(*) FROM lesiones WHERE usuario_id = ? AND activa = 1",
            (usuario_id,),
        ).fetchone()[0] or 0
    except Exception:
        pass

    # ── 3. Calcular km semana anterior ──
    semana_ant_inicio = (fecha_inicio - timedelta(days=7)).strftime("%Y-%m-%d")
    semana_ant_fin = (fecha_inicio - timedelta(days=1)).strftime("%Y-%m-%d")

    km_ant_plan = conn.execute(
        """SELECT COALESCE(SUM(km_planificados), 0)
           FROM plan_entrenamiento
           WHERE usuario_id = ? AND fecha >= ? AND fecha <= ? AND tipo != 'Fuerza'""",
        (usuario_id, semana_ant_inicio, semana_ant_fin),
    ).fetchone()[0]

    km_ant_garmin = conn.execute(
        f"""SELECT COALESCE(SUM(distancia_m)/1000, 0)
           FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ? AND fecha <= ?
             AND tipo_deporte IN {RUNNING_TIPOS_SQL}""",
        (usuario_id, semana_ant_inicio, semana_ant_fin),
    ).fetchone()[0]

    km_semana_ant = float(km_ant_garmin) if km_ant_garmin > 0 else float(km_ant_plan)
    if km_semana_ant < 1:
        # Sin historial: usar 15 km como base conservadora de inicio.
        # 20 km era demasiado alto para alguien que acaba de empezar a correr
        # (la TL resultante sería ~6.6 km + calidad + 3 sesiones más = riesgo de lesión).
        # Con 15 km: TL ~5 km, RB ~5.6 km, RG ~1.7 km, Fartlek ~6.2 km (6 reps).
        km_semana_ant = 15.0

    # ── 4-5. Macrociclo + ciclo carga/descarga ──
    # Camino v2 (dos carreras: intermedia + final) si el usuario la tiene configurada;
    # si no, camino antiguo por mes con un único objetivo (compatibilidad Dani/otros).
    semana_iso = fecha_inicio.isocalendar()[1]
    volumen_congelado = False
    v2_info = _calcular_macrociclo_v2(
        fecha_inicio, fecha_inicio_entreno_str, fecha_objetivo_intermedio_str, fecha_objetivo_str
    )
    dias_hasta_objetivo = None  # usado en el texto de tapering del camino antiguo

    if v2_info:
        macrociclo = v2_info["macrociclo"]
        es_descarga = v2_info["es_descarga"]
        ciclo_label = v2_info["ciclo_label"]
        semanas_desde_descarga = v2_info["semana_en_macro"]
        semanas_en_macro = v2_info["semana_en_macro"]
        if macrociclo in (1, 4):
            sesion_calidad_impar, sesion_calidad_par = "Fartlek", "Progresiva"
        elif macrociclo == 2:
            sesion_calidad_impar, sesion_calidad_par = "Intervalos", "Tempo"
        else:
            sesion_calidad_impar, sesion_calidad_par = "Intervalos_VO2max", "Tempo_Largo"
        tipo_calidad = sesion_calidad_impar if semanas_en_macro % 2 != 0 else sesion_calidad_par
    else:
        pos_ciclo = _posicion_ciclo(fecha_inicio)
        es_descarga = (pos_ciclo == 3)
        semanas_desde_descarga = pos_ciclo + 1
        ciclo_label = _etiqueta_ciclo(pos_ciclo)

        mes = fecha_inicio.month
        if fecha_objetivo_str:
            try:
                dias_hasta_objetivo = (datetime.strptime(fecha_objetivo_str, "%Y-%m-%d") - fecha_inicio).days
            except (ValueError, TypeError):
                pass

        if dias_hasta_objetivo is not None and 0 <= dias_hasta_objetivo <= 21:
            macrociclo = 4
            sesion_calidad_impar, sesion_calidad_par = "Fartlek", "Progresiva"
        elif mes in [5, 6, 7, 8]:
            macrociclo = 1
            sesion_calidad_impar, sesion_calidad_par = "Fartlek", "Progresiva"
        elif mes in [9, 10, 11]:
            macrociclo = 2
            sesion_calidad_impar, sesion_calidad_par = "Intervalos", "Tempo"
        elif mes in [12, 1]:
            macrociclo = 3
            sesion_calidad_impar, sesion_calidad_par = "Intervalos_VO2max", "Tempo_Largo"
        else:  # Feb-Abr (post-maratón o sin fecha objetivo)
            macrociclo = 1
            sesion_calidad_impar, sesion_calidad_par = "Fartlek", "Progresiva"

        tipo_calidad = sesion_calidad_impar if semana_iso % 2 != 0 else sesion_calidad_par

        # Mac3 (camino antiguo): ciclo especial 2+1 en lugar del 3+1 genérico
        if macrociclo == 3:
            inicio_mac3 = datetime(
                fecha_inicio.year if fecha_inicio.month == 12 else fecha_inicio.year - 1,
                12, 1
            )
            semanas_en_mac3 = max(1, ((fecha_inicio - inicio_mac3).days // 7) + 1)
            pos_mac3 = (semanas_en_mac3 - 1) % 3
            es_descarga = pos_mac3 == 2
            ciclo_label = "Descarga" if es_descarga else f"Carga {pos_mac3 + 1}"

    # Override manual del tipo de semana (selector "Carga1/Carga2/Carga3/Descarga" en Rehacer plan)
    if body.ciclo_override:
        override = body.ciclo_override.strip().lower()
        if override == "descarga":
            es_descarga, ciclo_label = True, "Descarga"
        elif override in ("carga1", "carga2", "carga3"):
            es_descarga, ciclo_label = False, f"Carga {override[-1]}"
        semanas_desde_descarga = int(override[-1]) if override[-1].isdigit() else 1

    # Si el usuario ha especificado km_total manualmente, usarlo directamente
    if body.km_total is not None and body.km_total > 0:
        km_total = round(float(body.km_total), 1)
        es_descarga = False
    elif lesiones_activas_count > 0:
        # Lesiones activas → congelar volumen en el nivel anterior
        km_total = round(km_semana_ant, 1)
        es_descarga = False
        volumen_congelado = True
    elif v2_info and macrociclo == 4 and not body.ciclo_override:
        # Tapering M4 (v2): reducción sobre el PICO de km alcanzado en M3, no sobre
        # el volumen de la semana anterior (que ya está bajando).
        pico_row = conn.execute(
            """SELECT MAX(semana_km) FROM (
                 SELECT semana_inicio, SUM(km_planificados) AS semana_km
                 FROM plan_entrenamiento
                 WHERE usuario_id = ? AND tipo = 'Carrera' AND fecha < ?
                 GROUP BY semana_inicio
               )""",
            (usuario_id, fecha_inicio_str),
        ).fetchone()
        pico = float(pico_row[0]) if pico_row and pico_row[0] else km_semana_ant
        sub_fase = v2_info.get("sub_fase")
        if sub_fase == "Taper -3":
            km_total = round(pico * 0.75, 1)
        elif sub_fase == "Taper -2":
            km_total = round(pico * 0.50, 1)
        else:  # Semana de carrera: mínimo, sesiones fijas cortas
            km_total = 5.0
        es_descarga = False
    elif es_descarga:
        km_total = round(km_semana_ant * 0.70, 1)
    else:
        km_total = round(km_semana_ant * 1.10, 1)

    # ── 6-7-9. Reparto de km (TL/RG/calidad/RB) y construcción de sesiones ──
    # (compartido con _generar_semana_interna vía _distribuir_km_y_construir_sesiones)
    if not v2_info:
        semanas_en_macro = _calcular_semanas_en_macro(fecha_inicio, macrociclo)

    # ── 8. Semáforo HRV (advisory) — añadir nota a sesiones de calidad si rojo ──
    semaforo_info = {"color": "verde", "mensaje": "Sin datos biométricos.", "nota": None}
    if _REGLAS_DISPONIBLES:
        try:
            bio_row = conn.execute(
                """SELECT hrv_ms, sleep_score, estres_medio, body_battery
                   FROM diario_biometrico
                   WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 1""",
                (usuario_id,),
            ).fetchone()
            if bio_row:
                hrv_hoy = bio_row[0]
                sleep_score_hoy = bio_row[1]
                estres_hoy = bio_row[2]
                bb_hoy = bio_row[3]
                # Media HRV 7 días
                hrv_media = conn.execute(
                    """SELECT AVG(hrv_ms) FROM diario_biometrico
                       WHERE usuario_id = ? AND fecha >= ? AND hrv_ms IS NOT NULL""",
                    (usuario_id, (fecha_inicio - timedelta(days=7)).strftime("%Y-%m-%d")),
                ).fetchone()[0]
                semaforo_info = calcular_semaforo(
                    hrv_actual=hrv_hoy, hrv_media_7d=hrv_media,
                    sleep_score=sleep_score_hoy, estres_medio=estres_hoy,
                    body_battery_min=bb_hoy,
                )
        except Exception:
            pass

    # ── 8b. FC post-TL semana anterior ──
    fc_post_tl_nota = None
    try:
        # Buscar TL de la semana anterior (sábado, día 5 de la semana anterior)
        tl_fecha = (fecha_inicio - timedelta(days=2)).strftime("%Y-%m-%d")  # sábado anterior
        tl_act = conn.execute(
            f"""SELECT fc_media, distancia_m FROM actividades_garmin
               WHERE usuario_id = ? AND fecha = ?
                 AND tipo_deporte IN {RUNNING_TIPOS_SQL}
               ORDER BY distancia_m DESC LIMIT 1""",
            (usuario_id, tl_fecha),
        ).fetchone()
        if tl_act and tl_act[1] and float(tl_act[1]) > 8000:
            # Tirada larga detectada — buscar FC reposo el día siguiente (domingo)
            dia_post_tl = (datetime.strptime(tl_fecha, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            fc_post_row = conn.execute(
                """SELECT fc_reposo FROM datos_biometricos_premium
                   WHERE usuario_id = ? AND fecha = ? AND fc_reposo IS NOT NULL
                   LIMIT 1""",
                (usuario_id, dia_post_tl),
            ).fetchone()
            if fc_post_row and fc_post_row[0]:
                fc_tl = round(float(tl_act[0])) if tl_act[0] else None
                fc_rep = int(fc_post_row[0])
                nota_fc = f"FC post-TL semana pasada: media {fc_tl} bpm durante TL — reposo siguiente mañana {fc_rep} bpm."
                if fc_rep > 62:
                    nota_fc += " FC reposo elevada, prioriza recuperación activa esta semana."
                fc_post_tl_nota = nota_fc
    except Exception:
        pass

    # ── 8c. Mac2: alerta si ritmos Z4/Z5 no alcanzados dos semanas seguidas ──
    mac2_alerta_z4 = None
    if macrociclo == 2:
        try:
            pace_objetivo_mac2 = 4.75  # 4:45/km en decimal min/km
            semana_2ant_inicio = (fecha_inicio - timedelta(days=14)).strftime("%Y-%m-%d")
            ultimas_calidad = conn.execute(
                f"""SELECT ritmo_medio FROM actividades_garmin
                   WHERE usuario_id = ? AND fecha >= ? AND fecha < ?
                     AND tipo_deporte IN {RUNNING_TIPOS_SQL}
                     AND distancia_m BETWEEN 3000 AND 12000
                   ORDER BY fecha DESC LIMIT 4""",
                (usuario_id, semana_2ant_inicio, fecha_inicio_str),
            ).fetchall()
            if len(ultimas_calidad) >= 2:
                paces = [r[0] for r in ultimas_calidad if r[0] and float(r[0]) > 0]
                if paces and all(p > pace_objetivo_mac2 + 0.15 for p in paces[:2]):
                    mac2_alerta_z4 = (
                        f"⚠️ Últimas 2 semanas no se han alcanzado ritmos Z4/Z5 (objetivo <4:45/km). "
                        f"Ritmos registrados: {', '.join(f'{p:.2f} min/km' for p in paces[:2])}. "
                        f"Revisa recuperación, calzado o reduce intensidad del siguiente bloque."
                    )
        except Exception:
            pass

    # ── 9. Reparto de km + construir sesiones ──
    sesiones_plan, km_tl, km_rg, km_calidad, km_rb = _distribuir_km_y_construir_sesiones(
        conn, usuario_id, fecha_inicio, macrociclo, km_total, tipo_calidad,
        semana_ant_inicio, semana_ant_fin, semanas_en_macro,
        v2_info.get("sub_fase") if v2_info else None,
        incluir_fuerza=body.incluir_fuerza,
    )

    # Si semáforo rojo, añadir advertencia a sesiones de calidad
    if semaforo_info.get("color") == "rojo":
        for s in sesiones_plan:
            if s["tipo"] == "Carrera" and s["intensidad"] == "Alta":
                aviso = f"\n⚠️ HRV baja hoy ({semaforo_info['mensaje']}). Valora reducir intensidad a Z2."
                s["detalles"] = (s["detalles"] or "") + aviso

    # Nota de motivo de reducción en sesiones de baja intensidad
    if volumen_congelado:
        motivo = f"Volumen congelado por {lesiones_activas_count} lesión(es) activa(s). No aumentes carga."
        for s in sesiones_plan:
            if s["intensidad"] in ("Baja", "Muy baja", "Media"):
                s["detalles"] = (s["detalles"] or "") + f"\n📌 {motivo}"
                break  # Solo en la primera sesión suave

    # FC post-TL: añadir al regenerativo del domingo
    if fc_post_tl_nota:
        for s in sesiones_plan:
            if "Regenerativo" in (s.get("sesion") or "") or s.get("intensidad") == "Muy baja":
                s["detalles"] = (s["detalles"] or "") + f"\nℹ️ {fc_post_tl_nota}"
                break

    # Mac2 alerta Z4: añadir a sesión de calidad de esta semana
    if mac2_alerta_z4:
        for s in sesiones_plan:
            if s["intensidad"] == "Alta":
                s["detalles"] = (s["detalles"] or "") + f"\n{mac2_alerta_z4}"
                break

    # ── 9b. Sin sesión de calidad: sustituir por Rodaje Base (mismo km) ──
    if not body.incluir_calidad:
        for s in sesiones_plan:
            if s["tipo"] == "Carrera" and s["intensidad"] == "Alta":
                km_sustituido = s["km_planificados"] or 0
                s["sesion"] = "Rodaje Base Z2"
                s["detalles"] = f"Rodaje Base Z2 — {km_sustituido} km. Ritmo 6:20-6:50min/km. FC 134-143 ppm. (Sustituye sesión de calidad por indicación del usuario.)"
                s["intensidad"] = "Baja"
                s["duracion_min"] = round(km_sustituido * 6.5)

    # ── 10. Validar distribución 80/20 Z1+Z2 ──
    distribucion_msg = None
    if _REGLAS_DISPONIBLES:
        try:
            _, distribucion_msg = controlar_distribucion_intensidad(sesiones_plan)
        except Exception:
            pass

    if not body.dry_run:
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

    # ── 11. Construir coach_tip ──
    conn.close()

    if volumen_congelado:
        tipo_semana = "Semana Congelada (Lesión)"
        tip_semana = (
            f"Volumen congelado por {lesiones_activas_count} lesión(es) activa(s): {km_total:.0f} km. "
            f"No aumentes el volumen. Prioriza recuperación y sesiones de bajo impacto."
        )
    elif macrociclo == 4:
        if v2_info:
            sem_antes = (v2_info["semanas_hasta_hito"] or 0) + 1
            sub_fase = v2_info.get("sub_fase") or "Tapering"
            tipo_semana = f"{sub_fase} — {sem_antes} semana(s) para el objetivo final"
        else:
            sem_antes = (dias_hasta_objetivo // 7) + 1 if dias_hasta_objetivo is not None else "?"
            tipo_semana = f"Tapering — {sem_antes} semana(s) para el maratón"
        tip_semana = f"Tapering: reduce volumen, mantén algo de intensidad. Piernas frescas para el día D. {km_total:.0f} km esta semana."
    elif es_descarga:
        tipo_semana = "Semana de Descarga"
        tip_semana = f"Descansa y asimila. Volumen reducido al 70%: {km_semana_ant:.0f} km → {km_total:.0f} km."
    else:
        n = semanas_desde_descarga
        tipo_semana = f"Semana de Aumento {n}"
        tip_semana = f"Progresión +10%: {km_semana_ant:.0f} km → {km_total:.0f} km. Macrociclo {macrociclo} — {tipo_calidad}."

    # Añadir semáforo al tip si no está verde
    if semaforo_info.get("color") in ("ambar", "rojo"):
        tip_semana += f" | {semaforo_info['mensaje']}"
    if distribucion_msg and "⚠️" in distribucion_msg:
        tip_semana += f" | {distribucion_msg}"
    if mac2_alerta_z4:
        tip_semana += f" | {mac2_alerta_z4}"

    return {
        "ok": True,
        "dry_run": body.dry_run,
        "semana_inicio": fecha_inicio_str,
        "km_total": km_total,
        "tipo_semana": tipo_semana,
        "es_descarga": es_descarga,
        "ciclo_label": ciclo_label,
        "macrociclo_label": f"M{macrociclo}",
        "semana_num": v2_info["semana_num"] if v2_info else None,
        "proximo_hito": v2_info["proximo_hito"] if v2_info else None,
        "semanas_hasta_hito": v2_info["semanas_hasta_hito"] if v2_info else None,
        "coach_tip": tip_semana,
        "macrociclo": macrociclo,
        "semaforo": {"color": semaforo_info.get("color", "verde"), "mensaje": semaforo_info.get("mensaje", "")},
        "distribucion_intensidad": distribucion_msg,
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


@router.post("/{usuario_id}/aplicar-semana")
def aplicar_semana(usuario_id: int, body: AplicarSemanaRequest):
    """Aplica una lista de sesiones de Carrera (previsualizadas y opcionalmente editadas
    por el usuario tras /generar-semana con dry_run=true), sustituyendo únicamente las
    sesiones de tipo Carrera de esa semana. Las sesiones de Fuerza no se tocan."""
    try:
        fecha_inicio = datetime.strptime(body.fecha_inicio, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato fecha inválido (YYYY-MM-DD)")
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin = (fecha_inicio + timedelta(days=6)).strftime("%Y-%m-%d")

    sesiones_carrera = [s for s in body.sesiones if (s.get("tipo") or "Carrera") == "Carrera"]
    if not sesiones_carrera:
        raise HTTPException(status_code=400, detail="No hay sesiones de Carrera para aplicar")

    conn = get_db()
    conn.execute(
        "DELETE FROM plan_entrenamiento WHERE usuario_id = ? AND fecha >= ? AND fecha <= ? AND tipo = 'Carrera'",
        (usuario_id, fecha_inicio_str, fecha_fin),
    )
    ahora = datetime.now().isoformat()
    for s in sesiones_carrera:
        conn.execute(
            """INSERT INTO plan_entrenamiento
               (usuario_id, semana_inicio, fecha, tipo, sesion, detalles, duracion_min,
                intensidad, km_planificados, creado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (usuario_id, fecha_inicio_str, s.get("fecha"), "Carrera", s.get("sesion"),
             s.get("detalles"), s.get("duracion_min"), s.get("intensidad"),
             s.get("km_planificados"), ahora),
        )
    conn.commit()
    conn.close()
    return {"ok": True, "sesiones_aplicadas": len(sesiones_carrera)}


CSV_COLUMNAS_REQUERIDAS = ["Día del mes", "Día de la semana", "Sesión Planificada", "Tipo de Sesión"]

# Tipo de Sesión (columna del CSV) -> (tipo interno, etiqueta de sesión)
_CSV_TIPO_MAP = {
    "descanso": ("Descanso", "Descanso"),
    "rodaje base": ("Carrera", "Rodaje Base"),
    "tirada larga": ("Carrera", "Tirada Larga"),
    "fuerza": ("Fuerza", "Fuerza"),
    "calidad": ("Carrera", "Calidad"),
    "series": ("Carrera", "Series"),
    "intervalos": ("Carrera", "Intervalos"),
    "umbral": ("Carrera", "Umbral"),
    "tempo": ("Carrera", "Tempo"),
    "fartlek": ("Carrera", "Fartlek"),
}

_KM_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:-\s*(\d+(?:[.,]\d+)?)\s*)?km", re.IGNORECASE)


def _parse_km_planificados(texto: str) -> float | None:
    if not texto:
        return None
    m = _KM_RE.search(texto)
    if not m:
        return None
    a = float(m.group(1).replace(",", "."))
    b = float(m.group(2).replace(",", ".")) if m.group(2) else None
    return round((a + b) / 2, 2) if b is not None else a


def _mapear_tipo_sesion(tipo_csv: str, sesion_planificada: str) -> tuple[str, str]:
    tipo, sesion = _CSV_TIPO_MAP.get((tipo_csv or "").strip().lower(), (None, None))
    if tipo is not None:
        return tipo, sesion
    # Tipo no reconocido: se guarda tal cual como sesión de tipo "Carrera"
    return "Carrera", (tipo_csv or sesion_planificada or "Sesión").strip()


def _parsear_csv_plan(contenido: str, fecha_inicio: str) -> list[dict]:
    contenido = contenido.lstrip("﻿")
    try:
        reader = csv.DictReader(io.StringIO(contenido))
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el CSV")

    headers = [h.strip() for h in (reader.fieldnames or [])]
    faltantes = [c for c in CSV_COLUMNAS_REQUERIDAS if c not in headers]
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"Faltan columnas en el CSV: {', '.join(faltantes)}. "
                   f"Columnas requeridas: {', '.join(CSV_COLUMNAS_REQUERIDAS)}",
        )

    try:
        fecha_actual = datetime.strptime(fecha_inicio, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha_inicio inválido (YYYY-MM-DD)")

    sesiones: list[dict] = []
    for row in reader:
        sesion_planificada = (row.get("Sesión Planificada") or "").strip()
        tipo_csv = (row.get("Tipo de Sesión") or "").strip()
        if not sesion_planificada and not tipo_csv:
            continue  # fila vacía

        tipo, sesion = _mapear_tipo_sesion(tipo_csv, sesion_planificada)
        km_planificados = _parse_km_planificados(sesion_planificada) if tipo != "Descanso" else None

        sesiones.append({
            "fecha": fecha_actual.strftime("%Y-%m-%d"),
            "tipo": tipo,
            "sesion": sesion,
            "detalles": sesion_planificada or None,
            "duracion_min": None,
            "intensidad": None,
            "km_planificados": km_planificados,
        })
        fecha_actual += timedelta(days=1)

    if not sesiones:
        raise HTTPException(status_code=400, detail="El CSV no contiene sesiones")
    return sesiones


@router.post("/{usuario_id}/importar-csv")
async def importar_plan_csv(
    usuario_id: int,
    fecha_inicio: str = Form(...),
    dry_run: bool = Form(False),
    file: UploadFile = File(...),
):
    """Importa un plan de entrenamiento desde un CSV (ver formato en CSV_COLUMNAS_REQUERIDAS).
    La primera fila de datos se asigna a fecha_inicio y cada fila siguiente al día siguiente.
    Con dry_run=true solo se devuelve la previsualización, sin guardar nada."""
    crudo = await file.read()
    try:
        contenido = crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        contenido = crudo.decode("latin-1")

    sesiones = _parsear_csv_plan(contenido, fecha_inicio)

    if dry_run:
        return {"ok": True, "sesiones": sesiones}

    conn = get_db()
    ahora = datetime.now().isoformat()
    for s in sesiones:
        semana_inicio = _inicio_semana(s["fecha"])
        conn.execute(
            """INSERT INTO plan_entrenamiento
               (usuario_id, semana_inicio, fecha, tipo, sesion, detalles, duracion_min,
                intensidad, km_planificados, creado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (usuario_id, semana_inicio, s["fecha"], s["tipo"], s["sesion"],
             s["detalles"], s["duracion_min"], s["intensidad"], s["km_planificados"], ahora),
        )
    conn.commit()
    conn.close()
    return {"ok": True, "sesiones_importadas": len(sesiones)}


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
        f"""SELECT COALESCE(SUM(distancia_m)/1000, 0)
           FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ?
             AND tipo_deporte IN {RUNNING_TIPOS_SQL}""",
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

    # ── 2. Obtener fechas objetivo del usuario (final + intermedia opcional) ──
    perfil_row_regen = conn.execute(
        "SELECT fecha_objetivo, fecha_inicio_entrenamiento, fecha_objetivo_intermedio FROM usuarios WHERE id = ?",
        (usuario_id,),
    ).fetchone()
    fecha_objetivo_regen = perfil_row_regen[0] if perfil_row_regen else None
    fecha_inicio_entreno_regen = perfil_row_regen[1] if perfil_row_regen else None
    fecha_inter_regen = perfil_row_regen[2] if perfil_row_regen else None

    # ── 3. Generar N semanas desde la semana actual ──
    semanas_generadas = []
    dias_hasta_lunes = hoy.weekday()
    semana_actual = hoy - timedelta(days=dias_hasta_lunes)

    for n in range(body.semanas):
        fecha_sem_dt = semana_actual + timedelta(weeks=n)
        fecha_sem = fecha_sem_dt.strftime("%Y-%m-%d")
        v2_info = _calcular_macrociclo_v2(fecha_sem_dt, fecha_inicio_entreno_regen, fecha_inter_regen, fecha_objetivo_regen)

        if v2_info:
            es_descarga = v2_info["es_descarga"]
            if v2_info["macrociclo"] == 4:
                sub_fase = v2_info.get("sub_fase")
                if sub_fase == "Taper -3":
                    km_sem = round(km_base * 0.75, 1)
                elif sub_fase == "Taper -2":
                    km_sem = round(km_base * 0.50, 1)
                else:
                    km_sem = 5.0
            elif es_descarga:
                km_sem = round(km_base * 0.70, 1)
            elif n == 0:
                km_sem = round(km_base, 1)
            else:
                km_sem = round(km_base * (1.10 ** n), 1)
        else:
            es_descarga = (_posicion_ciclo(fecha_sem_dt) == 3)
            dias_obj = None
            if fecha_objetivo_regen:
                try:
                    dias_obj = (datetime.strptime(fecha_objetivo_regen, "%Y-%m-%d") - fecha_sem_dt).days
                except (ValueError, TypeError):
                    pass
            es_tapering = dias_obj is not None and 0 <= dias_obj <= 21

            if es_tapering:
                km_sem = round(km_base * 0.50, 1)  # Tapering: 50% del volumen base
            elif es_descarga:
                km_sem = round(km_base * 0.70, 1)
            elif n == 0:
                km_sem = round(km_base, 1)
            else:
                km_sem = round(km_base * (1.10 ** n), 1)

        km_sem = min(km_sem, 80.0)

        _generar_semana_interna(conn, usuario_id, fecha_sem, km_sem, fecha_objetivo_str=fecha_objetivo_regen, v2_info=v2_info, incluir_fuerza=body.incluir_fuerza)
        semanas_generadas.append({"semana_inicio": fecha_sem, "km_total": km_sem, "descarga": es_descarga})

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "km_base_real": round(km_base, 1),
        "semanas_regeneradas": len(semanas_generadas),
        "detalle": semanas_generadas,
    }


def _generar_semana_interna(
    conn, usuario_id: int, fecha_inicio_str: str, km_total: float,
    fecha_objetivo_str: str | None = None, v2_info: dict | None = None,
    incluir_fuerza: bool = True,
):
    """Genera y guarda las sesiones de una semana con km_total dado, sin commit.
    Si v2_info viene dado (calendario NORMAS_ENTRENAMIENTO_v2 de dos carreras), se usa
    su macrociclo/sub_fase en vez de detectarlo por mes."""
    fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d")
    fecha_fin = (fecha_inicio + timedelta(days=6)).strftime("%Y-%m-%d")

    # Borrar sesiones existentes
    conn.execute(
        "DELETE FROM plan_entrenamiento WHERE usuario_id = ? AND fecha >= ? AND fecha <= ?",
        (usuario_id, fecha_inicio_str, fecha_fin),
    )

    semana_iso = fecha_inicio.isocalendar()[1]
    mes = fecha_inicio.month
    sub_fase = None

    if v2_info:
        macrociclo = v2_info["macrociclo"]
        sub_fase = v2_info.get("sub_fase")
        semanas_en_macro_v2 = v2_info["semana_en_macro"]
        if macrociclo in (1, 4):
            sesion_calidad_impar, sesion_calidad_par = "Fartlek", "Progresiva"
        elif macrociclo == 2:
            sesion_calidad_impar, sesion_calidad_par = "Intervalos", "Tempo"
        else:
            sesion_calidad_impar, sesion_calidad_par = "Intervalos_VO2max", "Tempo_Largo"
        tipo_calidad = sesion_calidad_impar if semanas_en_macro_v2 % 2 != 0 else sesion_calidad_par
    else:
        # Detectar tapering por fecha objetivo (camino antiguo, un solo objetivo)
        dias_hasta_objetivo = None
        if fecha_objetivo_str:
            try:
                dias_hasta_objetivo = (datetime.strptime(fecha_objetivo_str, "%Y-%m-%d") - fecha_inicio).days
            except (ValueError, TypeError):
                pass

        if dias_hasta_objetivo is not None and 0 <= dias_hasta_objetivo <= 21:
            macrociclo = 4
            sesion_calidad_impar = "Fartlek"
            sesion_calidad_par = "Progresiva"
        elif mes in [5, 6, 7, 8]:
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

    semana_ant_inicio = (fecha_inicio - timedelta(days=7)).strftime("%Y-%m-%d")
    semana_ant_fin = (fecha_inicio - timedelta(days=1)).strftime("%Y-%m-%d")
    semanas_en_macro = v2_info["semana_en_macro"] if v2_info else _calcular_semanas_en_macro(fecha_inicio, macrociclo)

    sesiones_plan, km_tl, km_rg, km_calidad, km_rb = _distribuir_km_y_construir_sesiones(
        conn, usuario_id, fecha_inicio, macrociclo, km_total, tipo_calidad,
        semana_ant_inicio, semana_ant_fin, semanas_en_macro, sub_fase,
        incluir_fuerza=incluir_fuerza,
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


def _detalles_calidad_mac1(tipo: str, km: float, reps: int, bloque_min: int) -> tuple[str, str, float]:
    """Devuelve (sesion_nombre, detalles, km_real) para sesiones de calidad del Mac1.
    km_real se calcula desde la estructura real de la sesión, no como % del total."""
    if tipo == "Fartlek":
        # 15' Z2 a 6:20/km ≈ 2.4km + reps×(1'@4:55 + 2' Z1) + 5' Z1
        km_warmup = round(15 / 6.33, 1)   # 15' a ~6:20/km
        km_per_rep = round(1 / 4.917 + 2 / 6.5, 2)  # 1'@4:55 + 2' Z2
        km_cool = round(5 / 7.0, 1)
        km_real = round(km_warmup + reps * km_per_rep + km_cool, 1)
        return (
            "Fartlek",
            f"15' calentamiento Z2 + {reps}×(1'@4:55min/km + 2' Z1) + 5' Z1. Total ~{km_real} km. "
            f"Progresión: comenzar con 6 reps, +1 rep cada ciclo de 4 semanas.",
            km_real,
        )
    else:  # Progresiva
        # FIX: km_real se calcula DESDE los tiempos, no como % del volumen semanal.
        # Así Z4(bloque_min min) + Z2(bloque_min min) + Z1(bloque_min min) son coherentes
        # con el km total y con lo que dice el PDF ("bloque Z4 empieza 5 min").
        km_z1 = round(bloque_min / 7.5, 2)    # Z1: ~7:30/km
        km_z2 = round(bloque_min / 6.5, 2)    # Z2: ~6:30/km
        km_z4 = round(bloque_min / 4.917, 2)  # Z4: ~4:55/km
        km_real = round(km_z1 + km_z2 + km_z4, 1)
        dur_total = bloque_min * 3
        return (
            "Progresiva",
            f"{bloque_min} min Z1 (suave, ~7:30/km) · {bloque_min} min Z2 (~6:30/km) · "
            f"{bloque_min} min Z4 (@4:55min/km). "
            f"Total ~{km_real} km en {dur_total} min. "
            f"Progresión: bloque Z4 empieza 5 min, +2 min cada ciclo de 4 semanas.",
            km_real,
        )


def _detalles_calidad_mac2(tipo: str, km: float, semana_iso: int) -> tuple[str, str]:
    """Devuelve (sesion_nombre, detalles) para sesiones de calidad del Mac2.
    Progressión series: sep=3×2000m, oct=4×2000m, nov=5×2000m
    Progressión tempo: sep=6km, oct=8km, nov=10-12km
    """
    mes_est = 9 if semana_iso < 40 else (10 if semana_iso < 44 else 11)
    if tipo == "Intervalos":
        series = {9: 3, 10: 4, 11: 5}.get(mes_est, 3)
        return (
            "Intervalos Largos 2000m",
            f"3 km calentamiento Z2 + {series}×(2000m @4:40-4:45min/km + 2' Z1) + 2 km Z1. "
            f"Total ~{km} km. Ritmo Zona 5 — si la última serie es >5s más lenta que la 1ª, parar.",
        )
    else:  # Tempo
        km_tempo = {9: 6, 10: 8, 11: 10}.get(mes_est, 6)
        return (
            "Tempo Run",
            f"2 km Z2 calentamiento + {km_tempo} km @5:10-5:15min/km (justo sobre ritmo maratón, Z4) + 2 km Z1. "
            f"Total ~{km} km. Objetivo: completar el bloque sin agotamiento máximo.",
        )


def _detalles_calidad_mac3(tipo: str, km: float) -> tuple[str, str]:
    """Devuelve (sesion_nombre, detalles) para sesiones de calidad del Mac3."""
    if tipo == "Intervalos_VO2max":
        return (
            "Intervalos VO2max",
            f"3 km calentamiento Z2 + series de 800-1000m @4:25-4:35min/km (Z5 pura) + 90s-2' recuperación pasiva + 2 km Z1. "
            f"Total ~{km} km. Objetivo: que 5:00/km se sienta mecánicamente 'lento'.",
        )
    else:  # Tempo_Largo
        return (
            "Tempo Largo",
            f"Carrera continua {km} km @5:05-5:10min/km (Z4 sostenida). "
            f"Sin calentamiento largo — ritmo desde el primer km. Resistencia al umbral de lactato.",
        )


def _detalles_tl(macrociclo: int, km_tl: float) -> str:
    """Genera los detalles de la Tirada Larga según el macrociclo (normas PDF)."""
    if macrociclo == 1:
        return (
            f"Tirada Larga Z2 — {km_tl} km. Ritmo 6:20-6:50min/km. FC 134-143 ppm. "
            f"100% Z2 — base aeróbica. Toma nota de tu FC al levantarte al día siguiente."
        )
    elif macrociclo == 2:
        z2_km = round(km_tl * 0.60, 1)
        z4_km = round(km_tl * 0.20, 1)
        return (
            f"Tirada Larga con Bloque Maratón — {km_tl} km. "
            f"Estructura: {z2_km} km Z2 + {z4_km} km @5:00min/km (Z4) + {round(km_tl - z2_km - z4_km, 1)} km Z2. "
            f"La TL debe representar el 30-35% del volumen semanal. "
            f"NUTRICIÓN: practica beber agua/bebida isotónica cada 20-25 min."
        )
    elif macrociclo == 3:
        z2_ini = round(km_tl * 0.33, 1)
        bloque_z4 = min(round(km_tl * 0.50, 1), 18.0)
        z2_fin = round(km_tl - z2_ini - bloque_z4, 1)
        return (
            f"Tirada Larga Específica (Ensayo General) — {km_tl} km. "
            f"Estructura: {z2_ini} km Z2 + {bloque_z4} km @4:55-5:00min/km + {z2_fin} km Z2. "
            f"NUTRICIÓN OBLIGATORIA: 60-90g carbohidratos/hora. Ensaya los geles que usarás en el maratón. "
            f"Si el bloque Z4 falla por fatiga: el objetivo sub-5:00 está en riesgo — priorizar descanso."
        )
    else:  # Tapering
        return (
            f"Rodaje Suave — {km_tl} km. Ritmo libre y cómodo, Z1-Z2. "
            f"Tapering: el objetivo es llegar con piernas frescas al maratón."
        )


def _fuerza_por_macrociclo(macrociclo: int, fecha_dia: str, dia_semana: int) -> dict | None:
    """Genera la sesión de fuerza correcta según el macrociclo y día.
    Mac1: Pull(Lun) / Push(Mié) / Pierna(Vie)
    Mac2: Pierna Pesada(Lun) / Core+TS(Mié) — sin viernes fuerza
    Mac3: Pierna Ligera(Lun) — solo 1 día
    Mac4: Sin fuerza
    """
    if macrociclo == 1:
        if dia_semana == 0:  # Lunes
            return {"sesion": "Fuerza Tren Superior Pull", "intensidad": "Moderada",
                    "detalles": "Dominadas 4×6, Remo con barra 4×8, Curl bíceps 3×12, Face Pull 3×15. Mac1: 65-70% 1RM, hipertrofia base.", "duracion_min": 55}
        if dia_semana == 2:  # Miércoles
            return {"sesion": "Fuerza Tren Superior Push", "intensidad": "Moderada",
                    "detalles": "Press banca 4×6, Press militar 4×8, Fondos 3×12, Extensión tríceps 3×15. Mac1: 65-70% 1RM.", "duracion_min": 55}
        if dia_semana == 4:  # Viernes
            return {"sesion": "Fuerza Pierna", "intensidad": "Alta",
                    "detalles": "Sentadilla 4×8 @75%1RM, Peso muerto rumano 3×10, Zancada búlgara 3×12, Hip Thrust 3×15. Mac1: hipertrofia funcional.", "duracion_min": 65}
    elif macrociclo == 2:
        if dia_semana == 0:  # Lunes — único día de pierna pesado
            return {"sesion": "Fuerza Pierna (Pesada)", "intensidad": "Alta",
                    "detalles": "Sentadilla 4×6 @85% 1RM, Peso muerto 4×5 @85%, Prensa 45° 4×8. Mac2: 1 día pesado por semana — da prioridad a la recuperación de Intervalos y Tempo.", "duracion_min": 65}
        if dia_semana == 2:  # Miércoles — Core + Tren Superior
            return {"sesion": "Core + Tren Superior", "intensidad": "Moderada",
                    "detalles": "Plancha 3×45s, Dead Bug 3×12, Jalón al pecho 4×8, Remo en polea 3×12, Press militar 3×10. Mac2: fuerza sin fatigar piernas.", "duracion_min": 50}
        return None  # Viernes: sin fuerza en Mac2
    elif macrociclo == 3:
        if dia_semana == 0:  # Lunes — único día, pierna LIGERA
            return {"sesion": "Fuerza Pierna Ligera (Pliometría)", "intensidad": "Moderada",
                    "detalles": "Saltos al cajón 4×8, Skipping 3×20m, Zancadas con salto 3×8/pierna, Hip Thrust ligero 3×15. Mac3: velocidad de ejecución alta, cargas bajas — mantener chispa sin fatiga muscular.", "duracion_min": 40}
        return None  # Resto días: sin fuerza en Mac3
    return None  # Mac4: sin fuerza


def _distribuir_km_y_construir_sesiones(
    conn, usuario_id: int, fecha_inicio: datetime,
    macrociclo: int, km_total: float, tipo_calidad: str,
    semana_ant_inicio: str, semana_ant_fin: str,
    semana_en_macro: int, sub_fase: str | None,
    incluir_fuerza: bool = True,
) -> tuple[list, float, float, float, float]:
    """Reparte el volumen semanal en TL/RG/calidad/RB y construye las 7 sesiones de
    la semana. Compartido por generar_semana y _generar_semana_interna (regenerar-total)
    para que un ajuste a las reglas de reparto no se pueda olvidar en una de las dos copias.
    Devuelve (sesiones_plan, km_tl, km_rg, km_calidad, km_rb)."""
    # TL: 30-35% del volumen semanal, tope absoluto 32 km. Mac1: crece un 8% respecto
    # a la TL de la semana anterior (NORMAS v2 1.2). Si el cálculo se sale de la banda
    # 30-35%/32km, se recorta y el resto se reparte en Rodaje Base (residuo km_rb).
    km_tl_calculado = min(round(km_total * 0.33, 1), 32.0)
    if macrociclo == 1:
        km_tl_ant_row = conn.execute(
            """SELECT km_planificados FROM plan_entrenamiento
               WHERE usuario_id = ? AND fecha >= ? AND fecha <= ?
                 AND (sesion LIKE 'Tirada%' OR sesion = 'Tirada Larga')
               ORDER BY fecha DESC LIMIT 1""",
            (usuario_id, semana_ant_inicio, semana_ant_fin),
        ).fetchone()
        if km_tl_ant_row and km_tl_ant_row[0]:
            km_tl = min(round(float(km_tl_ant_row[0]) * 1.08, 1), 32.0)
        else:
            km_tl = km_tl_calculado
    else:
        km_tl = km_tl_calculado
    # Mínimo proporcional: no forzar 8 km si el volumen semanal es bajo. El tope
    # absoluto de 32km (o el 35%) SIEMPRE gana si choca con el mínimo del 30% —
    # "nunca se sobrepasa esa distancia en todo el plan" (NORMAS v2, Parte 7).
    km_tl_min = max(round(km_total * 0.30, 1), 4.0)
    km_tl_max = min(round(km_total * 0.35, 1), 32.0)
    km_tl = min(max(km_tl, km_tl_min), km_tl_max)

    km_rg = round(km_tl / 3, 1)

    # Calidad: nunca más del 20% del volumen semanal — sea 1 sesión (Mac1/Mac4) o 2
    # (Mac2: Intervalos+Tempo a partes iguales; Mac3: VO2max+Tempo Largo manteniendo
    # la proporción 1:1.3 pero repartiendo ese 20% total entre ambas).
    km_calidad = round(km_total * 0.20, 1)
    if macrociclo == 2:
        km_calidad_sesion = round(km_calidad / 2, 1)
    elif macrociclo == 3:
        km_calidad_sesion = round(km_calidad / 2.3, 1)  # la Tempo Larga usa ×1.3 de este valor
    else:
        km_calidad_sesion = km_calidad

    km_rb = round(km_total - km_tl - km_rg - km_calidad, 1)
    if km_rb < 3:
        km_rb = 3.0

    # Reps de fartlek: 6 + 1 por cada 4 semanas desde el INICIO del macrociclo actual.
    # Cap de seguridad: máximo 10 reps para prevenir sobrecarga.
    ciclo_num = max(0, (semana_en_macro - 1) // 4)
    fartlek_reps = min(6 + ciclo_num, FARTLEK_REPS_MAX)
    prog_bloque_min = 5 + ciclo_num * 2

    sesiones_plan = _construir_sesiones(
        fecha_inicio, tipo_calidad, macrociclo, km_calidad_sesion, km_rb, km_rg, km_tl,
        fartlek_reps, prog_bloque_min, sub_fase=sub_fase, incluir_fuerza=incluir_fuerza
    )

    # Mac1: Fartlek/Progresiva calculan su km real desde la estructura de la sesión
    # (reps × ritmo), no directamente desde km_calidad_sesion — con reps altas puede
    # superar el 20% del volumen semanal. Recortar al tope y pasar el sobrante a RB.
    if macrociclo == 1:
        for s in sesiones_plan:
            if s["tipo"] == "Carrera" and s["intensidad"] == "Alta" and (s["km_planificados"] or 0) > km_calidad:
                sobrante = round(s["km_planificados"] - km_calidad, 1)
                s["km_planificados"] = km_calidad
                for rb in sesiones_plan:
                    if rb["tipo"] == "Carrera" and "Rodaje Base" in (rb["sesion"] or ""):
                        rb["km_planificados"] = round((rb["km_planificados"] or 0) + sobrante, 1)
                        rb["duracion_min"] = round(rb["km_planificados"] * 6.5)
                        break

    return sesiones_plan, km_tl, km_rg, km_calidad, km_rb


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
    sub_fase: str | None = None,
    incluir_fuerza: bool = True,
) -> list:
    """Construye la lista de sesiones para una semana según las NORMAS DE ENTRENAMIENTO:
    Mac1: Lun=Pull · Mar=Calidad · Mié=Push · Jue=RB · Vie=Pierna · Sáb=TL · Dom=RG
    Mac2: Lun=PiernaP · Mar=Core+TS · Mié=Intervalos · Jue=Tempo · Vie=RB · Sáb=TL · Dom=RG
          (NORMA: Pierna Lun → Core+TS Mar (no calidad ✓) → Intervalos Mié (48h ✓))
    Mac3: Lun=PiernaL · Mar=VO2max · Mié=RB · Jue=TempoL · Vie=— · Sáb=TL · Dom=RG
    Mac4: Tapering — sesiones reducidas
    """
    semana_iso = fecha_inicio.isocalendar()[1]
    sesiones = []

    for offset in range(7):
        fecha_dia = (fecha_inicio + timedelta(days=offset)).strftime("%Y-%m-%d")
        dia_semana = offset  # 0=Lun, 1=Mar, ..., 6=Dom

        if macrociclo == 1:
            # ── MAC 1: distribución fija estándar ──
            if dia_semana == 0:
                sesiones.append({"fecha": fecha_dia, "tipo": "Fuerza", "sesion": "Fuerza Tren Superior Pull",
                    "detalles": "Dominadas 4×6, Remo con barra 4×8, Curl bíceps 3×12, Face Pull 3×15. 65-70% 1RM.",
                    "duracion_min": 55, "intensidad": "Moderada", "km_planificados": None})
            elif dia_semana == 1:
                nombre, det, km_real_cal = _detalles_calidad_mac1(tipo_calidad, km_calidad, fartlek_reps, prog_bloque_min)
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": nombre, "detalles": det,
                    "duracion_min": round(km_real_cal * 6.0), "intensidad": "Alta", "km_planificados": km_real_cal})
            elif dia_semana == 2:
                sesiones.append({"fecha": fecha_dia, "tipo": "Fuerza", "sesion": "Fuerza Tren Superior Push",
                    "detalles": "Press banca 4×6, Press militar 4×8, Fondos 3×12, Extensión tríceps 3×15. 65-70% 1RM.",
                    "duracion_min": 55, "intensidad": "Moderada", "km_planificados": None})
            elif dia_semana == 3:
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Rodaje Base Z2",
                    "detalles": f"Rodaje Base Z2 — {km_rb} km. Ritmo 6:20-6:50min/km. FC 134-143 ppm.",
                    "duracion_min": round(km_rb * 6.5), "intensidad": "Baja", "km_planificados": km_rb})
            elif dia_semana == 4:
                sesiones.append({"fecha": fecha_dia, "tipo": "Fuerza", "sesion": "Fuerza Pierna",
                    "detalles": "Sentadilla 4×8 @75%1RM, Peso muerto rumano 3×10, Zancada búlgara 3×12, Hip Thrust 3×15.",
                    "duracion_min": 65, "intensidad": "Alta", "km_planificados": None})
            elif dia_semana == 5:
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Tirada Larga",
                    "detalles": _detalles_tl(1, km_tl),
                    "duracion_min": round(km_tl * 6.5), "intensidad": "Moderada-Alta", "km_planificados": km_tl})
            elif dia_semana == 6:
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Regenerativo Z1",
                    "detalles": f"Regenerativo Z1 — {km_rg} km. Ritmo muy suave >7:00min/km. FC <133 ppm.",
                    "duracion_min": round(km_rg * 7.5), "intensidad": "Muy baja", "km_planificados": km_rg})

        elif macrociclo == 2:
            # ── MAC 2: 2 sesiones de calidad (Intervalos + Tempo) ──
            # NORMA: Pierna → día siguiente NO puede ser Fartlek/Tempo/Intervalos.
            # NORMA: las dos sesiones de calidad deben ir separadas por al menos 48h.
            # Pierna(Lun) → Core+TS(Mar, no calidad ✓) → Intervalos(Mié, 48h de Pierna) →
            # RB(Jue) → Tempo(Vie, 48h de Intervalos ✓) → TL(Sáb) → RG(Dom)
            # Distribución: Lun=PiernaP · Mar=Core+TS · Mié=Intervalos · Jue=RB · Vie=Tempo · Sáb=TL · Dom=RG
            nombre_int, det_int = _detalles_calidad_mac2("Intervalos", km_calidad, semana_iso)
            nombre_tmp, det_tmp = _detalles_calidad_mac2("Tempo", km_calidad, semana_iso)
            if dia_semana == 0:
                sesiones.append({"fecha": fecha_dia, "tipo": "Fuerza", "sesion": "Fuerza Pierna (Pesada)",
                    "detalles": "Sentadilla 4×6 @85% 1RM, Peso muerto 4×5 @85%, Prensa 45° 4×8. Mac2: 1 día pesado.",
                    "duracion_min": 65, "intensidad": "Alta", "km_planificados": None})
            elif dia_semana == 1:
                sesiones.append({"fecha": fecha_dia, "tipo": "Fuerza", "sesion": "Core + Tren Superior",
                    "detalles": "Plancha 3×45s, Dead Bug 3×12, Jalón 4×8, Remo en polea 3×12, Press militar 3×10. Recuperación activa tras Pierna.",
                    "duracion_min": 50, "intensidad": "Moderada", "km_planificados": None})
            elif dia_semana == 2:
                # Intervalos a 48h de Pierna ✓
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": nombre_int, "detalles": det_int,
                    "duracion_min": 70, "intensidad": "Alta", "km_planificados": km_calidad})
            elif dia_semana == 3:
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Rodaje Base Z2",
                    "detalles": f"Rodaje Base Z2 — {km_rb} km. Ritmo 6:10-6:40min/km. FC 134-143 ppm.",
                    "duracion_min": round(km_rb * 6.2), "intensidad": "Baja", "km_planificados": km_rb})
            elif dia_semana == 4:
                # Tempo a 48h de Intervalos ✓
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": nombre_tmp, "detalles": det_tmp,
                    "duracion_min": 70, "intensidad": "Alta", "km_planificados": km_calidad})
            elif dia_semana == 5:
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Tirada Larga con Bloque Maratón",
                    "detalles": _detalles_tl(2, km_tl),
                    "duracion_min": round(km_tl * 6.2), "intensidad": "Moderada-Alta", "km_planificados": km_tl})
            elif dia_semana == 6:
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Regenerativo Z1",
                    "detalles": f"Regenerativo Z1 — {km_rg} km. Ritmo muy suave >7:00min/km. FC <133 ppm.",
                    "duracion_min": round(km_rg * 7.5), "intensidad": "Muy baja", "km_planificados": km_rg})

        elif macrociclo == 3:
            # ── MAC 3: TL específica, VO2max + Tempo Largo, fuerza mínima ──
            # NORMA: la TL Específica debe estar separada de cualquier sesión de calidad
            # por al menos 72h → Tempo Largo va el miércoles (72h antes de la TL del
            # sábado), Rodaje Base pasa al jueves.
            nombre_vo2, det_vo2 = _detalles_calidad_mac3("Intervalos_VO2max", km_calidad)
            nombre_tl2, det_tl2 = _detalles_calidad_mac3("Tempo_Largo", round(km_calidad * 1.3, 1))
            if dia_semana == 0:
                sesiones.append({"fecha": fecha_dia, "tipo": "Fuerza", "sesion": "Fuerza Pierna Ligera (Pliometría)",
                    "detalles": "Saltos al cajón 4×8, Skipping 3×20m, Zancadas con salto 3×8/pierna, Hip Thrust 3×15 (ligero). Velocidad de ejecución alta.",
                    "duracion_min": 40, "intensidad": "Moderada", "km_planificados": None})
            elif dia_semana == 1:
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": nombre_vo2, "detalles": det_vo2,
                    "duracion_min": 70, "intensidad": "Alta", "km_planificados": km_calidad})
            elif dia_semana == 2:
                # Tempo Largo a 72h de la TL del sábado ✓
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": nombre_tl2, "detalles": det_tl2,
                    "duracion_min": 90, "intensidad": "Alta", "km_planificados": round(km_calidad * 1.3, 1)})
            elif dia_semana == 3:
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Rodaje Base Z2",
                    "detalles": f"Rodaje Base Z2 — {km_rb} km. Ritmo suave. FC 134-143 ppm. Recuperación activa entre sesiones de calidad.",
                    "duracion_min": round(km_rb * 6.2), "intensidad": "Baja", "km_planificados": km_rb})
            elif dia_semana == 4:
                sesiones.append({"fecha": fecha_dia, "tipo": "Descanso", "sesion": "Descanso Activo",
                    "detalles": "Descanso o movilidad/estiramientos 20-30 min. No correr. La TL específica requiere 72h de separación.",
                    "duracion_min": 25, "intensidad": "Muy baja", "km_planificados": None})
            elif dia_semana == 5:
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Tirada Larga Específica",
                    "detalles": _detalles_tl(3, km_tl),
                    "duracion_min": round(km_tl * 6.0), "intensidad": "Alta", "km_planificados": km_tl})
            elif dia_semana == 6:
                sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Regenerativo Z1",
                    "detalles": f"Regenerativo Z1 — {km_rg} km. Ritmo muy suave >7:00min/km. FC <133 ppm. Recuperación post-TL específica.",
                    "duracion_min": round(km_rg * 7.5), "intensidad": "Muy baja", "km_planificados": km_rg})

        else:  # Mac4 — Tapering (plantilla según sub-fase, NORMAS v2 Parte 6)
            if sub_fase == "Semana de carrera":
                # Plantilla fija literal del doc: Lunes 20'Z2, Miércoles 15'+4 rectas, Domingo carrera.
                if dia_semana == 0:
                    sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Activación Z2",
                        "detalles": "20 min Z2. Muy suave, piernas frescas.",
                        "duracion_min": 20, "intensidad": "Muy baja", "km_planificados": round(20 / 7.0, 1)})
                elif dia_semana == 2:
                    sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Activación + Rectas",
                        "detalles": "15 min Z2 + 4 rectas de 100 m (progresivas, no al máximo). Activar sin fatigar.",
                        "duracion_min": 20, "intensidad": "Baja", "km_planificados": round(15 / 7.0 + 0.4, 1)})
                elif dia_semana == 6:
                    sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "MARATÓN DE SEVILLA",
                        "detalles": "Día D — Maratón de Sevilla. ¡A por ello!",
                        "duracion_min": None, "intensidad": "Alta", "km_planificados": 42.2})
            elif sub_fase == "Taper -2":
                # -50% del pico, solo rodajes suaves + bloque a ritmo maratón, sin calidad dura.
                if dia_semana == 2:
                    sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Rodaje Suave",
                        "detalles": f"Rodaje suave — {km_rb} km. Z1-Z2. Sin esfuerzo. Piernas frescas.",
                        "duracion_min": round(km_rb * 6.5), "intensidad": "Baja", "km_planificados": km_rb})
                elif dia_semana == 4:
                    sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Bloque Ritmo Maratón",
                        "detalles": "15' Z2 + 5 km @5:00min/km (ritmo maratón) + 10' Z1. Sensaciones, sin fatiga.",
                        "duracion_min": 50, "intensidad": "Moderada", "km_planificados": round(5 + 25 / 7.0, 1)})
                elif dia_semana == 6:
                    sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Rodaje Suave",
                        "detalles": f"Rodaje suave — {round(km_rb * 0.6, 1)} km. Z1-Z2.",
                        "duracion_min": round(km_rb * 0.6 * 6.5), "intensidad": "Baja", "km_planificados": round(km_rb * 0.6, 1)})
            else:  # "Taper -3": -25% del pico, mantiene 1 sesión corta de intervalos
                if dia_semana == 1:
                    sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Intervalos Cortos Tapering",
                        "detalles": f"15' Z2 + 4×(400m @ritmo 5K + 2' recuperación) + 10' Z1. ~{km_calidad} km. Mantener chispa sin fatiga.",
                        "duracion_min": 45, "intensidad": "Alta", "km_planificados": km_calidad})
                elif dia_semana == 3:
                    sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Rodaje Suave",
                        "detalles": f"Rodaje suave — {km_rb} km. Z1-Z2. Sin esfuerzo. Piernas frescas.",
                        "duracion_min": round(km_rb * 6.5), "intensidad": "Baja", "km_planificados": km_rb})
                elif dia_semana == 5:
                    sesiones.append({"fecha": fecha_dia, "tipo": "Carrera", "sesion": "Rodaje con Bloque Ritmo",
                        "detalles": f"20' Z2 + 5 km @5:00min/km (ritmo maratón) + 10' Z1. Confirmar sensaciones. Total ~{round(km_calidad * 0.8, 1)} km.",
                        "duracion_min": 55, "intensidad": "Moderada", "km_planificados": round(km_calidad * 0.8, 1)})
                elif dia_semana == 6:
                    sesiones.append({"fecha": fecha_dia, "tipo": "Descanso", "sesion": "Descanso",
                        "detalles": "Descanso total o caminata suave. Pies frescos para mañana.",
                        "duracion_min": 0, "intensidad": "Muy baja", "km_planificados": None})

    if not incluir_fuerza:
        sesiones = [s for s in sesiones if s["tipo"] != "Fuerza"]

    return sesiones


def _inicio_semana(fecha_str: str) -> str:
    d = datetime.strptime(fecha_str, "%Y-%m-%d")
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")


def _parse_ritmo_fc(detalles: str | None) -> tuple[str | None, str | None]:
    """Extrae el ritmo y la FC objetivo del texto de 'detalles' de una sesión (ya
    generado por _detalles_tl / _detalles_calidad_* con ese formato consistente),
    para exponerlos como campos estructurados en vez de tener que reparsear texto
    libre en el frontend."""
    if not detalles:
        return None, None
    ritmo = None
    m = re.search(r'([<>]?\d:\d{2}(?:-\d:\d{2})?)\s*min/km', detalles)
    if m:
        ritmo = f"{m.group(1)} min/km"
    fc = None
    m = re.search(r'FC\s*([<>]?\d+(?:-\d+)?)\s*ppm', detalles)
    if m:
        fc = f"{m.group(1)} ppm"
    return ritmo, fc


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
