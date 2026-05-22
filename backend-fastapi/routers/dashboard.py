from datetime import datetime, timedelta

from fastapi import APIRouter

from database import get_db

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
        "SELECT id, nombre, genero, objetivo, nivel, fcmax, objetivo_tipo, fecha_objetivo, fecha_inicio_entrenamiento FROM usuarios WHERE id = ?",
        (usuario_id,),
    ).fetchone()
    perfil = dict(zip(
        ["id", "nombre", "genero", "objetivo", "nivel", "fcmax", "objetivo_tipo", "fecha_objetivo", "fecha_inicio_entrenamiento"],
        row or [usuario_id, "Atleta", "Mujer", "", "Intermedio", None, "maraton", None, None]
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

    # KM semana actual
    km_semana = conn.execute(
        "SELECT COALESCE(SUM(distancia_m)/1000, 0) FROM actividades_garmin WHERE usuario_id = ? AND fecha >= ?",
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
        """SELECT strftime('%W', fecha) as semana, SUM(distancia_m)/1000 as km
           FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ? AND tipo_deporte IN ('running','trail_running','correr','carrera')
           GROUP BY strftime('%W', fecha)
           ORDER BY semana ASC LIMIT 8""",
        (usuario_id, (hoy - timedelta(days=56)).isoformat()),
    ).fetchall()
    running_trend = [{"semana": f"S{i+1}", "km": round(r[1] or 0, 1)} for i, r in enumerate(running_trend)]

    # Última sesión fuerza (ejercicios)
    last_fuerza = conn.execute(
        """SELECT ef.ejercicio, ef.peso, ef.series, ef.repeticiones
           FROM ejercicios_fuerza ef
           JOIN sesiones_fuerza sf ON sf.id = ef.sesion_id
           WHERE sf.usuario_id = ?
           ORDER BY sf.fecha DESC, sf.id DESC LIMIT 6""",
        (usuario_id,),
    ).fetchall()
    fuerza_reciente = [
        {"ejercicio": r[0], "peso": r[1], "series": r[2], "repeticiones": r[3]}
        for r in last_fuerza
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

    # Ritmo medio semanal running (últimas 8 semanas), en min/km
    ritmo_rows = conn.execute(
        """SELECT strftime('%W', fecha) as semana, AVG(ritmo_medio) as ritmo
           FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ?
             AND tipo_deporte IN ('running','trail_running','correr','carrera')
             AND ritmo_medio IS NOT NULL AND ritmo_medio > 0
           GROUP BY strftime('%W', fecha)
           ORDER BY semana ASC LIMIT 8""",
        (usuario_id, (hoy - timedelta(days=56)).isoformat()),
    ).fetchall()
    ritmo_trend = [
        {"semana": f"S{i+1}", "ritmo": round((r[1] or 0) / 60, 2)}
        for i, r in enumerate(ritmo_rows)
    ]

    # Cadencia media semanal (running, últimas 8 semanas)
    cadencia_rows = conn.execute(
        """SELECT strftime('%W', fecha) as semana, AVG(cadencia_media) as cad
           FROM actividades_garmin
           WHERE usuario_id = ? AND fecha >= ?
             AND tipo_deporte IN ('running','trail_running','correr','carrera')
             AND cadencia_media IS NOT NULL
           GROUP BY strftime('%W', fecha)
           ORDER BY semana ASC LIMIT 8""",
        (usuario_id, (hoy - timedelta(days=56)).isoformat()),
    ).fetchall()
    cadencia_trend = [
        {"semana": f"S{i+1}", "cadencia": round(r[1] or 0)}
        for i, r in enumerate(cadencia_rows)
    ]

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
