from datetime import datetime, timedelta

from fastapi import APIRouter

from database import get_db
from constants import RUNNING_TIPOS_SQL

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _row_to_dict(row, cols):
    if row is None:
        return None
    return dict(zip(cols, row))


@router.get("/{usuario_id}")
def dashboard(usuario_id: int):
    conn = get_db()
    hoy = datetime.now().date()
    hace_7 = (hoy - timedelta(days=7)).isoformat()
    hace_10 = (hoy - timedelta(days=10)).isoformat()
    hace_30 = (hoy - timedelta(days=30)).isoformat()
    semana_inicio = (hoy - timedelta(days=hoy.weekday())).isoformat()

    # Perfil
    row = conn.execute(
        "SELECT id, nombre, genero, objetivo, nivel, fcmax, objetivo_tipo, fecha_objetivo, fecha_inicio_entrenamiento, "
        "ritmo, fecha_objetivo_intermedio, objetivo_intermedio_nombre FROM usuarios WHERE id = ?",
        (usuario_id,),
    ).fetchone()
    perfil = dict(zip(
        ["id", "nombre", "genero", "objetivo", "nivel", "fcmax", "objetivo_tipo", "fecha_objetivo", "fecha_inicio_entrenamiento",
         "ritmo", "fecha_objetivo_intermedio", "objetivo_intermedio_nombre"],
        row or [usuario_id, "Atleta", "Mujer", "", "Intermedio", None, "maraton", None, None, None, None, None]
    ))

    # Fase macrociclo
    fase = _calcular_fase(perfil.get("objetivo_tipo"), perfil.get("fecha_objetivo"))

    # Últimas actividades Garmin (7 días)
    actividades = conn.execute(
        """SELECT fecha, tipo_deporte, distancia_m, tiempo_seg, ritmo_medio, fc_media,
                  cadencia_media, fc_max
           FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ?
           ORDER BY fecha DESC LIMIT 10""",
        (usuario_id, hace_7),
    ).fetchall()
    act_cols = ["fecha", "tipo_deporte", "distancia_m", "tiempo_seg", "ritmo_medio",
                "fc_media", "cadencia_media", "fc_max"]
    actividades = [dict(zip(act_cols, r)) for r in actividades]

    # KM semana actual (solo carrera/cinta, no bici/natación/etc.)
    km_semana = conn.execute(
        f"""SELECT COALESCE(SUM(distancia_m)/1000, 0) FROM actividades_garmin
            WHERE usuario_id = ? AND fecha >= ? AND tipo_deporte IN {RUNNING_TIPOS_SQL}""",
        (usuario_id, semana_inicio),
    ).fetchone()
    km_semana_val = round(float(km_semana[0] or 0), 1)

    # Plan KM semana (lo planificado)
    km_plan = conn.execute(
        "SELECT COALESCE(SUM(km_planificados), 0) FROM plan_entrenamiento WHERE usuario_id = ? AND semana_inicio = ?",
        (usuario_id, semana_inicio),
    ).fetchone()
    km_plan_val = round(float(km_plan[0] or 0), 1)

    # Sesiones fuerza semana: sesiones_fuerza (app) + strength_training de Garmin
    fuerza_app = conn.execute(
        "SELECT COUNT(*) FROM sesiones_fuerza WHERE usuario_id = ? AND fecha >= ?",
        (usuario_id, semana_inicio),
    ).fetchone()[0] or 0
    fuerza_garmin = conn.execute(
        """SELECT COUNT(*) FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ?
             AND tipo_deporte IN ('strength_training','strength','fuerza','gym')""",
        (usuario_id, semana_inicio),
    ).fetchone()[0] or 0
    sesiones_fuerza_semana = fuerza_app + fuerza_garmin

    # HRV últimos 14 días
    hrv_rows = conn.execute(
        """SELECT fecha, hrv_ms, fc_reposo, sleep_score, body_battery,
                  training_status, training_readiness, estres_medio
           FROM datos_biometricos_premium
           WHERE usuario_id = ? AND fecha >= ?
           ORDER BY fecha DESC LIMIT 14""",
        (usuario_id, (hoy - timedelta(days=14)).isoformat()),
    ).fetchall()
    hrv_cols = ["fecha", "hrv_ms", "fc_reposo", "sleep_score", "body_battery",
                "training_status", "training_readiness", "estres_medio"]
    hrv_data = [dict(zip(hrv_cols, r)) for r in hrv_rows]

    # Sueño últimos 10 días (margen extra para zona horaria y delay Garmin)
    sleep_rows = conn.execute(
        """SELECT fecha, horas_totales, score, sleep_profundo_horas, sleep_rem_horas
           FROM datos_sueno WHERE usuario_id = ? AND fecha >= ?
           ORDER BY fecha ASC""",
        (usuario_id, hace_10),
    ).fetchall()
    sleep_cols = ["fecha", "horas_totales", "score", "sleep_profundo_horas", "sleep_rem_horas"]
    sleep_data = [dict(zip(sleep_cols, r)) for r in sleep_rows]

    # Semáforo recuperación (último dato)
    semaforo = "verde"
    semaforo_msg = "Sin datos recientes"
    if hrv_data:
        ultimo = hrv_data[0]
        hrv_actual = ultimo.get("hrv_ms")
        sleep_score = ultimo.get("sleep_score")
        hrv_media = None
        if len(hrv_data) >= 3:
            vals = [r["hrv_ms"] for r in hrv_data[1:] if r["hrv_ms"]]
            hrv_media = sum(vals) / len(vals) if vals else None

        semaforo, semaforo_msg = _calcular_semaforo(hrv_actual, hrv_media, sleep_score,
                                                     ultimo.get("estres_medio"),
                                                     ultimo.get("body_battery"))

    # Progresión running últimas 8 semanas
    running_trend = conn.execute(
        f"""SELECT strftime('%W', fecha) as semana, SUM(distancia_m)/1000 as km
           FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ? AND tipo_deporte IN {RUNNING_TIPOS_SQL}
           GROUP BY strftime('%W', fecha)
           ORDER BY semana ASC LIMIT 8""",
        (usuario_id, (hoy - timedelta(days=56)).isoformat()),
    ).fetchall()
    running_trend = [{"semana": f"S{i+1}", "km": round(r[1] or 0, 1)} for i, r in enumerate(running_trend)]

    # Progresión de fuerza: ejercicios que subieron peso recientemente o que deben subir.
    # Fuente: historial_ejercicio + ejercicios_catalogo (sistema moderno con subir_peso).
    # Muestra solo los que:
    #   a) subir_peso = 1  → completaron la sesión anterior y deben subir carga
    #   b) último peso > penúltimo peso → acaban de subir en la sesión más reciente
    progresion_rows = conn.execute(
        """SELECT
               ec.nombre,
               ec.grupo_muscular,
               h_last.peso         AS peso_actual,
               h_prev.peso         AS peso_anterior,
               COALESCE(ec.subir_peso, 0) AS debe_subir,
               h_last.series,
               h_last.repeticiones
           FROM ejercicios_catalogo ec
           LEFT JOIN (
               SELECT h1.ejercicio_id, h1.peso, h1.series, h1.repeticiones
               FROM historial_ejercicio h1
               WHERE h1.usuario_id = ?
                 AND h1.id = (
                     SELECT id FROM historial_ejercicio
                     WHERE ejercicio_id = h1.ejercicio_id AND usuario_id = h1.usuario_id
                     ORDER BY fecha DESC, id DESC LIMIT 1
                 )
           ) h_last ON h_last.ejercicio_id = ec.id
           LEFT JOIN (
               SELECT h2.ejercicio_id, h2.peso
               FROM historial_ejercicio h2
               WHERE h2.usuario_id = ?
                 AND h2.id = (
                     SELECT id FROM historial_ejercicio
                     WHERE ejercicio_id = h2.ejercicio_id AND usuario_id = h2.usuario_id
                     ORDER BY fecha DESC, id DESC LIMIT 1 OFFSET 1
                 )
           ) h_prev ON h_prev.ejercicio_id = ec.id
           WHERE ec.usuario_id = ?
             AND (ec.archivado IS NULL OR ec.archivado = 0)
             AND h_last.peso IS NOT NULL
             AND (
                 ec.subir_peso = 1
                 OR (h_prev.peso IS NOT NULL AND h_last.peso > h_prev.peso)
             )
           ORDER BY ec.orden, ec.nombre
           LIMIT 9""",
        (usuario_id, usuario_id, usuario_id),
    ).fetchall()
    fuerza_reciente = [
        {
            "ejercicio":      r[0],
            "grupo":          r[1],
            "peso_actual":    r[2],
            "peso_anterior":  r[3],
            "debe_subir":     bool(r[4]),
            "series":         r[5],
            "repeticiones":   r[6],
        }
        for r in progresion_rows
    ]

    # Ciclo menstrual (solo mujeres / usuario 1)
    ciclo_info = None
    try:
        ultimo_ciclo = conn.execute(
            """SELECT fecha_inicio_regla, fecha_siguiente_regla, duracion_ciclo_dias
               FROM historial_ciclos_menstruales
               WHERE usuario_id = ?
               ORDER BY fecha_inicio_regla DESC LIMIT 1""",
            (usuario_id,),
        ).fetchone()
        if ultimo_ciclo:
            inicio = datetime.strptime(ultimo_ciclo[0], "%Y-%m-%d").date()
            proxima_str = ultimo_ciclo[1]
            dur_ciclo = ultimo_ciclo[2] or 28
            dia_ciclo = (hoy - inicio).days + 1
            if proxima_str:
                proxima = datetime.strptime(proxima_str, "%Y-%m-%d").date()
            else:
                proxima = inicio + timedelta(days=dur_ciclo)
            dias_para_regla = (proxima - hoy).days

            if dia_ciclo <= 5:
                fase, energia = "Menstruación", "Baja — enfócate en recuperación"
            elif dia_ciclo <= 13:
                fase, energia = "Folicular", "Alta — ideal para intensidad"
            elif dia_ciclo <= 15:
                fase, energia = "Ovulación", "Máxima — pico de fuerza"
            else:
                fase, energia = "Lútea", "Media — preferir volumen suave"

            months_es = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
            ciclo_info = {
                "fase": fase,
                "dia_ciclo": dia_ciclo,
                "duracion_ciclo": dur_ciclo,
                "dias_para_regla": dias_para_regla,
                "proxima_fecha": f"{proxima.day} {months_es[proxima.month-1]}",
                "energia": energia,
            }
    except Exception:
        pass

    # Ritmo medio semanal (últimas 8 semanas), en min/km — SOLO Tirada Larga y
    # Rodaje Base (las sesiones "aeróbicas de referencia" del plan), no cualquier
    # carrera. Se cruza con plan_entrenamiento por fecha para saber qué actividad
    # corresponde a una TL/RB real (nombres siempre empiezan por "Tirada"/"Rodaje").
    # ritmo_medio ya está en decimal min/km (calculado en _upsert_actividad como
    # (duracion_seg/60) / (distancia_m/1000)), NO dividir de nuevo.
    ritmo_rows = conn.execute(
        f"""SELECT strftime('%W', ag.fecha) as semana, AVG(ag.ritmo_medio) as ritmo
           FROM actividades_garmin ag
           WHERE ag.usuario_id = ? AND ag.fecha >= ?
             AND ag.tipo_deporte IN {RUNNING_TIPOS_SQL}
             AND ag.ritmo_medio IS NOT NULL AND ag.ritmo_medio > 0
             AND EXISTS (
                 SELECT 1 FROM plan_entrenamiento pe
                 WHERE pe.usuario_id = ag.usuario_id AND pe.fecha = ag.fecha
                   AND (pe.sesion LIKE 'Tirada%' OR pe.sesion LIKE 'Rodaje%')
             )
           GROUP BY strftime('%W', ag.fecha)
           ORDER BY semana ASC LIMIT 8""",
        (usuario_id, (hoy - timedelta(days=56)).isoformat()),
    ).fetchall()
    ritmo_trend = [
        {"semana": f"S{i+1}", "ritmo": round(r[1] or 0, 2)}
        for i, r in enumerate(ritmo_rows)
    ]

    # Cadencia media semanal (running, últimas 8 semanas)
    cadencia_rows = conn.execute(
        f"""SELECT strftime('%W', fecha) as semana, AVG(cadencia_media) as cad
           FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ?
             AND tipo_deporte IN {RUNNING_TIPOS_SQL}
             AND cadencia_media IS NOT NULL
           GROUP BY strftime('%W', fecha)
           ORDER BY semana ASC LIMIT 8""",
        (usuario_id, (hoy - timedelta(days=56)).isoformat()),
    ).fetchall()
    cadencia_trend = [
        {"semana": f"S{i+1}", "cadencia": round(r[1] or 0)}
        for i, r in enumerate(cadencia_rows)
    ]

    # Cadencia de los últimos Rodaje Base (para detectar caída sostenida) — mismo
    # cruce con plan_entrenamiento que ritmo_trend, pero por sesión, no por semana.
    cadencia_rb_rows = conn.execute(
        f"""SELECT ag.fecha, ag.cadencia_media
           FROM actividades_garmin ag
           WHERE ag.usuario_id = ?
             AND ag.tipo_deporte IN {RUNNING_TIPOS_SQL}
             AND ag.cadencia_media IS NOT NULL
             AND EXISTS (
                 SELECT 1 FROM plan_entrenamiento pe
                 WHERE pe.usuario_id = ag.usuario_id AND pe.fecha = ag.fecha
                   AND pe.sesion LIKE 'Rodaje%'
             )
           ORDER BY ag.fecha DESC LIMIT 8""",
        (usuario_id,),
    ).fetchall()
    cadencia_rb = [(r[0], r[1]) for r in reversed(cadencia_rb_rows)]  # orden ascendente

    avisos = _calcular_avisos(hrv_data, cadencia_rb)

    # ── Sesión de hoy (plan_entrenamiento) ──────────────────────────────────
    plan_hoy_row = conn.execute(
        """SELECT tipo, sesion, detalles, km_planificados
           FROM plan_entrenamiento
           WHERE usuario_id = ? AND fecha = ?
           ORDER BY id LIMIT 1""",
        (usuario_id, hoy.isoformat()),
    ).fetchone()

    sesion_hoy = None
    if plan_hoy_row:
        tipo_hoy, sesion_nombre, detalles_hoy, km_hoy = plan_hoy_row
        sesion_hoy = {
            "tipo": tipo_hoy,
            "sesion": sesion_nombre,
            "detalles": detalles_hoy,
            "km_planificados": km_hoy,
            "ejercicios_subir_peso": [],
        }

        # Si es fuerza, buscar ejercicios con subir_peso=1 del grupo correspondiente
        if tipo_hoy and "fuerza" in tipo_hoy.lower():
            grupo_hoy = None
            if sesion_nombre:
                sn = sesion_nombre.lower()
                if "push" in sn:
                    grupo_hoy = "Push"
                elif "pull" in sn:
                    grupo_hoy = "Pull"
                elif "pierna" in sn:
                    grupo_hoy = "Pierna"

            filtro_grupo = "AND LOWER(ec.grupo_muscular) = LOWER(?)" if grupo_hoy else ""
            params_subir = (usuario_id, usuario_id, grupo_hoy) if grupo_hoy else (usuario_id, usuario_id)
            ejs_rows = conn.execute(
                f"""SELECT ec.nombre, ec.grupo_muscular, h_last.peso
                    FROM ejercicios_catalogo ec
                    LEFT JOIN (
                        SELECT h1.ejercicio_id, h1.peso
                        FROM historial_ejercicio h1
                        WHERE h1.usuario_id = ?
                          AND h1.id = (
                              SELECT id FROM historial_ejercicio
                              WHERE ejercicio_id = h1.ejercicio_id AND usuario_id = h1.usuario_id
                              ORDER BY fecha DESC, id DESC LIMIT 1
                          )
                    ) h_last ON h_last.ejercicio_id = ec.id
                    WHERE ec.usuario_id = ? AND ec.subir_peso = 1
                      AND (ec.archivado IS NULL OR ec.archivado = 0)
                      {filtro_grupo}
                    ORDER BY ec.orden, ec.nombre""",
                params_subir,
            ).fetchall()
            sesion_hoy["ejercicios_subir_peso"] = [
                {"nombre": r[0], "grupo": r[1], "peso_anterior": r[2]}
                for r in ejs_rows
            ]

    conn.close()

    return {
        "perfil": perfil,
        "fase_macrociclo": fase,
        "semaforo": {"color": semaforo, "mensaje": semaforo_msg},
        "semana_actual": {
            "km_realizados": km_semana_val,
            "km_planificados": km_plan_val,
            "sesiones_fuerza": sesiones_fuerza_semana,
        },
        "actividades_recientes": actividades[:5],
        "hrv_data": hrv_data,
        "sleep_data": sleep_data,
        "ciclo": ciclo_info,
        "running_trend": running_trend,
        "ritmo_trend": ritmo_trend,
        "fuerza_reciente": fuerza_reciente,
        "cadencia_trend": cadencia_trend,
        "sesion_hoy": sesion_hoy,
        "avisos": avisos,
    }


def _calcular_fase(objetivo_tipo: str | None, fecha_objetivo: str | None) -> dict:
    hoy = datetime.now()
    mes = hoy.month
    dia = hoy.day

    tipo = (objetivo_tipo or "").lower()

    if tipo in ("ultramaraton", "ultra", "trail_ultra") and fecha_objetivo:
        try:
            fecha_carrera = datetime.strptime(fecha_objetivo, "%Y-%m-%d")
            dias = (fecha_carrera - hoy).days
            if dias < 0:
                return {"nombre": "Post-Carrera", "km_max": 40, "dias_fuerza": 2}
            if dias <= 21:
                return {"nombre": "Tapering", "km_max": 50, "dias_fuerza": 1}
            if dias <= 63:
                return {"nombre": "Pico de Forma", "km_max": 120, "dias_fuerza": 1}
            if dias <= 119:
                return {"nombre": "Preparación Específica", "km_max": 100, "dias_fuerza": 2}
            if dias <= 175:
                return {"nombre": "Preparación General", "km_max": 80, "dias_fuerza": 2}
            return {"nombre": "Acondicionamiento", "km_max": 60, "dias_fuerza": 3}
        except (ValueError, TypeError):
            pass

    # Maratón (por mes)
    if mes in [3, 4, 5]:
        return {"nombre": "Acondicionamiento", "km_max": 30, "dias_fuerza": 4}
    if mes in [6, 7, 8]:
        return {"nombre": "Preparación General", "km_max": 45, "dias_fuerza": 3}
    if mes in [9, 10, 11]:
        return {"nombre": "Preparación Específica", "km_max": 60, "dias_fuerza": 2}
    if mes == 12 or (mes == 1 and dia <= 15):
        return {"nombre": "Pico de Forma", "km_max": 75, "dias_fuerza": 2}
    if mes == 1 and dia > 15:
        return {"nombre": "Tapering", "km_max": 50, "dias_fuerza": 1}
    return {"nombre": "Tapering", "km_max": 30, "dias_fuerza": 1}


def _calcular_semaforo(hrv_actual, hrv_media, sleep_score, estres, body_battery):
    razones_rojo = []
    razones_ambar = []

    if hrv_actual is not None and hrv_media and hrv_media > 0:
        caida = (hrv_media - hrv_actual) / hrv_media
        if caida > 0.10:
            razones_rojo.append(f"HRV -{caida*100:.0f}%")
        elif caida > 0.0:
            razones_ambar.append(f"HRV ligeramente bajo")

    if sleep_score is not None:
        if sleep_score < 60:
            razones_rojo.append(f"Sleep {sleep_score}/100")
        elif sleep_score <= 80:
            razones_ambar.append(f"Sleep {sleep_score}/100")

    if estres is not None and estres > 75:
        razones_rojo.append(f"Estrés alto ({estres})")
    elif estres is not None and estres > 55:
        razones_ambar.append(f"Estrés elevado")

    if body_battery is not None and body_battery < 10:
        razones_rojo.append("Body Battery crítico")
    elif body_battery is not None and body_battery < 25:
        razones_ambar.append("Body Battery bajo")

    if razones_rojo:
        return "rojo", "Recuperación baja: " + "; ".join(razones_rojo)
    if razones_ambar:
        return "ambar", "Recuperación moderada: " + "; ".join(razones_ambar)
    return "verde", "Recuperación óptima"


# Rango HRV normal de referencia (ms) — mismo valor que usa el frontend
# (Profile.tsx / LandingPage.tsx / Home.tsx) para marcar HRV fuera de rango.
HRV_RANGO_NORMAL = (71, 92)


def _dias_consecutivos(fecha_a: str, fecha_b: str) -> bool:
    try:
        da = datetime.strptime(fecha_a, "%Y-%m-%d").date()
        db_ = datetime.strptime(fecha_b, "%Y-%m-%d").date()
        return abs((da - db_).days) == 1
    except (ValueError, TypeError):
        return False


def _calcular_avisos(hrv_data: list[dict], cadencia_rb: list[tuple]) -> list[dict]:
    """Avisos fisiológicos basados en datos de Garmin (HRV, FC reposo, cadencia).
    hrv_data viene ordenado por fecha DESC (más reciente primero)."""
    avisos = []

    # 1. Carga mal absorbida: HRV nocturna fuera de rango 2 noches seguidas
    con_hrv = [d for d in hrv_data if d.get("hrv_ms") is not None]
    activo_hrv = False
    if len(con_hrv) >= 2 and _dias_consecutivos(con_hrv[0]["fecha"], con_hrv[1]["fecha"]):
        fuera = lambda d: not (HRV_RANGO_NORMAL[0] <= d["hrv_ms"] <= HRV_RANGO_NORMAL[1])
        activo_hrv = fuera(con_hrv[0]) and fuera(con_hrv[1])
    avisos.append({"id": "carga_mal_absorbida", "activo": activo_hrv})

    # 2. Fatiga acumulada / técnica degradada: cadencia cayendo en >2 rodajes base
    # seguidos por debajo de la media personal previa (umbral 3 spm para evitar ruido).
    activo_cadencia = False
    if len(cadencia_rb) >= 5:
        valores = [c[1] for c in cadencia_rb]  # orden ascendente por fecha
        baseline = sum(valores[:-3]) / len(valores[:-3])
        recientes = valores[-3:]
        if all(v < baseline for v in recientes) and (baseline - sum(recientes) / 3) >= 3:
            activo_cadencia = True
    avisos.append({"id": "fatiga_cadencia", "activo": activo_cadencia})

    # 3. Sobreentrenamiento: FC reposo matutina +5ppm sostenida sobre la media reciente
    activo_fc = False
    con_fc = [d for d in hrv_data if d.get("fc_reposo") is not None]
    if len(con_fc) >= 6:
        recientes = con_fc[:2]
        base_pool = con_fc[2:]
        if len(base_pool) >= 4 and _dias_consecutivos(recientes[0]["fecha"], recientes[1]["fecha"]):
            media_base = sum(d["fc_reposo"] for d in base_pool) / len(base_pool)
            if all(d["fc_reposo"] >= media_base + 5 for d in recientes):
                activo_fc = True
    avisos.append({"id": "sobreentrenamiento", "activo": activo_fc})

    return avisos
