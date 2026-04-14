"""
src/plan/entrenador.py — Motor de entrenamiento IA+código.
Python decide la ESTRUCTURA. La IA solo redacta descripciones.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from src.plan.motor import generar_plan_semana
from src.plan.helpers import cargar_datos_plan
from src.plan.reglas import obtener_fase_macrociclo, calcular_semaforo
from src.db.db_manager import get_db_connection


# ---------------------------------------------------------------------------
# Público
# ---------------------------------------------------------------------------

def generar_entrenamiento_semana(usuario_id: int, fecha_inicio=None) -> dict:
    """
    Motor principal. Combina:
    1. Python puro: decide estructura (tipo de sesión, volumen, intensidad)
    2. IA (Gemini): redacta descripción personalizada de cada sesión
    Devuelve el mismo formato que generar_plan_semana + campo 'descripcion_ia' en cada día.
    """
    if fecha_inicio is None:
        hoy = datetime.now()
        fecha_inicio = hoy - __import__("datetime").timedelta(days=hoy.weekday())

    try:
        # PARTE 1 — Python genera la estructura completa
        plan = generar_plan_semana(usuario_id, fecha_inicio)
        
        # DEBUG: verificar que tipos de sesión se generaron
        tipos_generados = [dia.get("tipo", "?") for dia in plan.get("dias", [])]
        import sys
        print(f"[DEBUG] Tipos generados: {tipos_generados}", file=sys.stderr)
        
    except Exception as e:
        import traceback
        error_msg = f"Error generando plan: {str(e)}\n{traceback.format_exc()}"
        raise RuntimeError(error_msg) from e

    try:
        # PARTE 2 — Construir contexto completo del atleta
        datos = cargar_datos_plan(usuario_id)
        fase = plan["fase"]
        semaforo = plan["semaforo"]
        contexto = _construir_contexto_atleta(usuario_id, fase, semaforo, datos)

        # PARTE 3 — IA redacta descripción de cada sesión no-descanso
        for dia in plan["dias"]:
            if dia["tipo"] in ("Descanso",):
                dia["descripcion_ia"] = "Día de descanso. Recuperación activa opcional: caminar, estirar."
            else:
                try:
                    dia["descripcion_ia"] = _pedir_descripcion_ia(dia, contexto)
                except Exception as e:
                    # Si falla la IA, mantenemosla sesión como está pero sin descripción
                    dia["descripcion_ia"] = f"[Sin descripción IA]"

        plan["contexto_ia"] = contexto  # para debug/display en UI
        plan["nutricion"] = _generar_recomendaciones_nutricion(datos, plan)
        plan["reporte_semanal"] = _generar_reporte_semanal(datos, plan)
        return plan
    except Exception as e:
        import traceback
        error_msg = f"Error en contexto IA: {str(e)}\n{traceback.format_exc()}"
        raise RuntimeError(error_msg) from e


# ---------------------------------------------------------------------------
# Construcción del contexto
# ---------------------------------------------------------------------------

def _construir_contexto_atleta(usuario_id: int, fase: dict, semaforo: dict, datos: dict) -> str:
    """
    Construye el contexto COMPLETO para la IA con TODOS los datos disponibles:
    HRV, sueño (score + breakdown), stress, body battery, VO2max, training status,
    ciclo menstrual, métricas running específicas, lesiones, pesos, nutrición.
    """
    lineas = [
        "═══════════════════════════════════════",
        "ATLETA: Malena, 21 años, 55 kg, mujer.",
        "OBJETIVO: Maratón Sub 3:30 — 21 febrero 2027.",
        "PERFIL: Atleta híbrida running + fuerza. Historial periostitis tibia.",
        "═══════════════════════════════════════",
        "",
        f"FASE MACROCICLO: {fase.get('fase_nombre','?')}",
        f"  Enfoque running: {fase.get('enfoque_running','')}",
        f"  Enfoque fuerza: {fase.get('enfoque_fuerza','')}",
        f"  Sesión de calidad esta fase: {fase.get('sesion_calidad','')}",
        f"  Km máx. esta fase: {fase.get('km_semanales_max','')} km/semana",
        "",
        f"SEMÁFORO RECUPERACIÓN: {semaforo.get('color','?').upper()}",
        f"  → {semaforo.get('mensaje','')}",
    ]

    # — HRV —
    hrv = datos.get("hrv_actual")
    hrv_med = datos.get("hrv_media_7d")
    if hrv:
        hrv_txt = f"  HRV: {hrv:.0f} ms (media 7d: {hrv_med:.0f} ms)" if hrv_med else f"  HRV: {hrv:.0f} ms"
        lineas.append(hrv_txt)

    # — Sueño —
    sleep = datos.get("sleep_score")
    if sleep:
        lineas.append(f"  Sleep score: {sleep:.0f}/100")
    sb = datos.get("sleep_breakdown", {})
    if sb:
        partes = []
        if sb.get("horas_totales"):
            partes.append(f"{sb['horas_totales']:.1f}h totales")
        if sb.get("profundo_h") is not None:
            partes.append(f"{sb['profundo_h']*60:.0f}min profundo")
        if sb.get("rem_h") is not None:
            partes.append(f"{sb['rem_h']:.1f}h REM")
        if sb.get("despertares") is not None:
            partes.append(f"{sb['despertares']} despertares")
        if partes:
            lineas.append(f"  Sueño anoche: {', '.join(partes)}")

    # — Estrés y Body Battery —
    estres = datos.get("estres_medio")
    if estres is not None:
        lineas.append(f"  Estrés Garmin: {estres}/100 {'⚠️ MUY ALTO' if estres > 70 else ''}")
    bb_max = datos.get("body_battery_max")
    bb_min = datos.get("body_battery_min")
    if bb_max is not None:
        lineas.append(f"  Body Battery: {bb_min}→{bb_max} (mín→máx del día)")

    # — VO2max y Training Status —
    vo2 = datos.get("vo2max")
    if vo2:
        lineas.append(f"  VO2max estimado: {vo2:.1f} ml/kg/min")
    ts = datos.get("training_status")
    if ts:
        lineas.append(f"  Garmin Training Status: {ts}")

    # — ACWR y volumen —
    acwr = datos.get("acwr", 1.0)
    km_ant = datos.get("km_semana_anterior", 0)
    lineas.append(f"  ACWR: {acwr:.2f} {'⚠️ ZONA DE RIESGO' if acwr > 1.4 else '✓ OK'}")
    if km_ant:
        lineas.append(f"  Km semana anterior: {km_ant:.1f} km")

    # — Ciclo menstrual —
    lineas.append("")
    fc = datos.get("fase_ciclo")
    if fc and fc.get("fase"):
        lineas.append(f"CICLO MENSTRUAL: {fc['fase']} (último registro: {fc.get('fecha','')})")
        if fc.get("fatiga_subjetiva"):
            lineas.append(f"  Fatiga subjetiva registrada: {fc['fatiga_subjetiva']}/10")
        if fc.get("estado_animo"):
            lineas.append(f"  Estado de ánimo: {fc['estado_animo']}")
    else:
        fase_ciclo_txt = _obtener_fase_ciclo(usuario_id)
        lineas.append(f"CICLO MENSTRUAL: {fase_ciclo_txt}")

    # — Métricas de carrera específicas —
    mrun = datos.get("metricas_running", {})
    if mrun:
        lineas.append("")
        lineas.append("MÉTRICAS RUNNING (media últimos 7 días):")
        if mrun.get("cadencia_media"):  # viene de datos generales
            pass  # ya está en cadencia_media de datos
        if mrun.get("potencia_media_w"):
            lineas.append(f"  Potencia media: {mrun['potencia_media_w']:.0f} W")
        if mrun.get("longitud_zancada_m"):
            lineas.append(f"  Longitud zancada: {mrun['longitud_zancada_m']:.2f} m")
        if mrun.get("tiempo_contacto_ms"):
            lineas.append(f"  Tiempo contacto suelo (GCT): {mrun['tiempo_contacto_ms']:.0f} ms "
                          f"{'⚠️ ALTO' if mrun['tiempo_contacto_ms'] > 270 else ''}")
        if mrun.get("oscilacion_vertical_cm"):
            lineas.append(f"  Oscilación vertical: {mrun['oscilacion_vertical_cm']:.1f} cm "
                          f"{'⚠️ ALTA' if mrun['oscilacion_vertical_cm'] > 9 else ''}")
        if mrun.get("training_effect_aerobico"):
            lineas.append(f"  Training Effect aeróbico medio: {mrun['training_effect_aerobico']:.1f}/5")
        if mrun.get("training_effect_anaerobico"):
            lineas.append(f"  Training Effect anaeróbico medio: {mrun['training_effect_anaerobico']:.1f}/5")
        cad = datos.get("cadencia_media")
        if cad:
            lineas.append(f"  Cadencia media: {cad:.0f} spm {'✓' if cad >= 170 else '⚠️ <170 añadir drills'}")

    # — Lesiones activas —
    lesiones = datos.get("lesiones_activas", [])
    lineas.append("")
    if lesiones:
        lineas.append("LESIONES ACTIVAS:")
        for l in lesiones:
            lineas.append(f"  - {l.get('zona','?')} grado {l.get('grado',1)}")
    else:
        lineas.append("LESIONES ACTIVAS: ninguna")

    # — Últimas sesiones de fuerza —
    ultimas = _obtener_ultimas_sesiones(usuario_id, n=3)
    if ultimas:
        lineas.append("")
        lineas.append("ÚLTIMAS SESIONES FUERZA:")
        for s in ultimas:
            lineas.append(f"  {s['fecha']}  {s['tipo_registro']}  — {s['resumen']}")

    # — Pesos actuales —
    pesos = _obtener_pesos_actuales(usuario_id)
    if pesos:
        lineas.append("")
        lineas.append("PESOS ACTUALES:")
        for nombre, peso in list(pesos.items())[:8]:
            lineas.append(f"  {nombre}: {peso} kg")

    # — Reglas del entrenamiento —
    lineas += [
        "",
        "REGLAS ENTRENAMIENTO (INAMOVIBLES):",
        "  80/20: 80% Z1-Z2, 20% alta intensidad.",
        "  Regla 10%: volumen no supera km_anterior × 1.1.",
        "  Ciclo lúteo/premenstrual: -15% volumen, sin intensidad máxima.",
        "  Ciclo ovulatorio: ventana de máximo rendimiento.",
        "  Fuerza piernas SIEMPRE antes de carrera (o 6h separación).",
        "  No fuerza piernas + series el mismo día (mínimo 48h).",
        "  Regenerativo = tirada_larga / 3 km.",
        "",
        "NUTRICIÓN (protocolo Maratón):",
        "  Proteína objetivo: 2g/kg → 110g/día.",
        "  Pre-entreno: carbos + proteína (ratio 3:1).",
        "  Durante carrera >60min: 30-90g carbos/hora.",
        "  Si estrés Garmin >50 o hay sesión sauna: duplicar electrolitos.",
        "  Hidratación extra en fase lútea/premenstrual.",
    ]

    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Llamada a IA
# ---------------------------------------------------------------------------

def _pedir_descripcion_ia(sesion: dict, contexto: str) -> str:
    """
    Llama a Gemini para que redacte 2-3 líneas de descripción de UNA sesión.
    Si falla, devuelve descripción genérica.
    """
    try:
        from src.core.ai_coach import _inicializar_modelo
        modelo = _inicializar_modelo()
        if modelo is None:
            return _descripcion_generica(sesion)

        tipo     = sesion.get("tipo", "")
        km       = sesion.get("km", 0)
        dur      = sesion.get("duracion_min", 0)
        intens   = sesion.get("intensidad", "")
        dia      = sesion.get("dia", "")

        prompt = f"""Eres el entrenador personal de Malena, atleta híbrida de 21 años entrenando para Maratón Sub 3:30. \
Sé conciso, directo y motivador. USA los datos del contexto para personalizar (no repitas todo el contexto).

CONTEXTO ATLETA:
{contexto}

SESIÓN ASIGNADA: {dia} — {tipo}
Distancia/Duración: {f'{km} km' if km else f'{dur} min'}
Intensidad: {intens}

Redacta EN 2-3 LÍNEAS MÁXIMO:
1. Por qué ESTA sesión tiene sentido HOY (menciona 1-2 datos concretos del contexto si son relevantes).
2. Cómo ejecutarla: zonas de FC, ritmo o sensación objetivo.
3. Si aplica: 1 consejo nutricional/hidratación específico para esta sesión.
Sin inventar datos. Sin encabezados. Solo el texto directo en español."""

        respuesta = modelo.generate_content(
            prompt,
            generation_config={"temperature": 0.3, "max_output_tokens": 150}
        ).text.strip()
        return respuesta if respuesta else _descripcion_generica(sesion)
    except Exception:
        return _descripcion_generica(sesion)


def _descripcion_generica(sesion: dict) -> str:
    tipo = sesion.get("tipo", "")
    km   = sesion.get("km", 0)
    dur  = sesion.get("duracion_min", 0)
    dist = f"{km} km" if km else f"{dur} min"
    msgs = {
        "Tirada Larga":    f"Carrera larga {dist} en Z2. Mantén conversación, no te pases de ritmo.",
        "Regenerativo":    f"Rodaje suave {dist} a baja intensidad para recuperar activamente.",
        "Carrera Z2":      f"Rodaje Z2 {dist}. Frecuencia cardíaca 120-145 bpm, pace cómodo.",
        "Fuerza":          f"Sesión de fuerza {dur} min. Sigue el plan de ejercicios de la semana.",
        "Tempo (umbral)":  f"Carrera a ritmo umbral {dist}. Zona 4, esfuerzo sostenible ~20 min.",
        "Intervalos VO2max": f"Series VO2max {dist}. Esfuerzo 95% FCmax, recuperación completa.",
        "Progresiva":      f"Carrera progresiva {dist}. Empieza suave y termina en zona 4.",
        "Descanso":        "Descanso activo. Caminar, estirar o nada.",
    }
    return msgs.get(tipo, f"Sesión de {tipo} — {dist}. Ejecuta según tus sensaciones del día.")


# ---------------------------------------------------------------------------
# Helpers BD
# ---------------------------------------------------------------------------

def _obtener_fase_ciclo(usuario_id: int) -> str:
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT fase_ciclo, fecha FROM diario_fisiologia "
            "WHERE usuario_id=? ORDER BY fecha DESC LIMIT 1",
            (usuario_id,)).fetchone()
    except Exception:
        row = None
    finally:
        conn.close()
    if row:
        return f"{row[0]} (último registro: {row[1]})"
    return "Sin datos de ciclo"


def _obtener_ultimas_sesiones(usuario_id: int, n: int = 3) -> list:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT fecha, tipo_registro, resumen FROM sesiones_fuerza "
            "WHERE usuario_id=? ORDER BY fecha DESC LIMIT ?",
            (usuario_id, n)).fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()
    return [{"fecha": r[0], "tipo_registro": r[1] or "general", "resumen": r[2] or ""} for r in rows]


def _obtener_pesos_actuales(usuario_id: int) -> dict:
    """Devuelve {nombre_ejercicio: último_peso} desde historial_ejercicio."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """SELECT eb.nombre, he.peso
               FROM historial_ejercicio he
               JOIN ejercicios_biblioteca eb ON he.ejercicio_id = eb.id
               WHERE he.usuario_id=?
               GROUP BY he.ejercicio_id
               HAVING he.fecha = MAX(he.fecha)
               ORDER BY eb.nombre""",
            (usuario_id,)).fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()
    return {r[0]: r[1] for r in rows if r[1]}


# ---------------------------------------------------------------------------
# Nutrición y Reporte semanal
# ---------------------------------------------------------------------------

def _generar_recomendaciones_nutricion(datos: dict, plan: dict) -> dict:
    """
    Genera recomendaciones nutricionales adaptadas a los datos del atleta y la semana.
    Basado en el Bloque 7 del protocolo Malena.
    """
    peso_kg = 55  # Malena
    proteina_g = round(peso_kg * 2)  # 2g/kg → 110g/día

    rec = {
        "proteina_diaria_g": proteina_g,
        "hidratacion_extra": False,
        "electrolitos_extra": False,
        "notas": [],
    }

    # Fase del ciclo → hidratación extra
    fc = datos.get("fase_ciclo", {})
    if fc and fc.get("fase"):
        fase = str(fc["fase"]).lower()
        if any(k in fase for k in ("lutea", "premenstrual", "menstruac")):
            rec["hidratacion_extra"] = True
            rec["notas"].append("Fase del ciclo: aumentar ingesta de agua y electrolitos (sodio, magnesio).")

    # Estrés Garmin > 50 → electrolitos
    estres = datos.get("estres_medio")
    if estres and estres > 50:
        rec["electrolitos_extra"] = True
        rec["notas"].append(f"Estrés Garmin {estres} → duplicar electrolitos en bebida de entrenamiento.")

    # Km elevados → carbos periéntrenamiento
    km_sem = plan.get("km_totales", 0)
    if km_sem > 40:
        rec["notas"].append(f"Semana de {km_sem} km → priorizar 30-60g carbos/hora en rodajes >60 min.")

    # Tirada larga en el plan
    tiene_tl = any("Tirada Larga" in d.get("tipo", "") for d in plan.get("dias", []))
    if tiene_tl:
        rec["notas"].append("Tirada larga: 30-90g carbos/hora + 500ml agua/hora. Pre: arroz/plátano 2h antes.")

    # Semana de calidad/intensidad
    tiene_vo2 = any("VO2max" in d.get("tipo", "") or "Intervalos" in d.get("tipo", "") for d in plan.get("dias", []))
    if tiene_vo2:
        rec["notas"].append("Día de intervalos: comer 3-4h antes. Post: proteína + carbos en 30min (ratio 3:1).")

    # Sleep bajo → proteína extra
    sleep = datos.get("sleep_score")
    if sleep and sleep < 70:
        rec["notas"].append(f"Sleep score {sleep:.0f} — incluir caseína antes de dormir para mejorar recuperación muscular.")

    return rec


def _generar_reporte_semanal(datos: dict, plan: dict) -> dict:
    """
    Genera el reporte semanal estructurado (Bloque 5 del protocolo).
    Incluye: lesiones, métricas Garmin, eficiencia aeróbica, fase macrociclo, nutrición.
    """
    fase = plan.get("fase", {})
    semaforo = plan.get("semaforo", {})
    km_ant = datos.get("km_semana_anterior", 0)
    km_max = round(km_ant * 1.10, 1) if km_ant else "—"
    mrun = datos.get("metricas_running", {})

    reporte = {
        "fase_macrociclo": fase.get("fase_nombre", "—"),
        "semaforo": semaforo.get("color", "verde"),
        "km_totales_plan": plan.get("km_totales", 0),
        "km_maximo_seguro": km_max,
        "acwr": plan.get("acwr", 1.0),
        "training_status": datos.get("training_status", "Sin datos"),
        "vo2max": datos.get("vo2max"),
        "secciones": [],
    }

    # Lesiones
    lesiones = datos.get("lesiones_activas", [])
    if lesiones:
        reporte["secciones"].append({
            "titulo": "⚠️ Lesiones Activas",
            "items": [f"{l['zona']} grado {l['grado']}" for l in lesiones],
        })

    # Métricas Garmin
    metricas_items = []
    hrv = datos.get("hrv_actual")
    if hrv:
        metricas_items.append(f"HRV: {hrv:.0f} ms (media 7d: {datos.get('hrv_media_7d', 0):.0f} ms)")
    sleep = datos.get("sleep_score")
    if sleep:
        metricas_items.append(f"Sleep score: {sleep:.0f}/100")
    sb = datos.get("sleep_breakdown", {})
    if sb.get("profundo_h") is not None:
        metricas_items.append(f"Sueño profundo: {sb['profundo_h']*60:.0f} min")
    if sb.get("rem_h") is not None:
        metricas_items.append(f"REM: {sb['rem_h']:.1f} h")
    estres = datos.get("estres_medio")
    if estres:
        metricas_items.append(f"Estrés medio: {estres}/100")
    bb = datos.get("body_battery_max")
    bb_min = datos.get("body_battery_min")
    if bb:
        metricas_items.append(f"Body Battery: {bb_min}→{bb} (mín→máx)")
    if reporte["vo2max"]:
        metricas_items.append(f"VO2max: {reporte['vo2max']:.1f} ml/kg/min")
    if metricas_items:
        reporte["secciones"].append({"titulo": "📊 Métricas Garmin", "items": metricas_items})

    # Métricas running
    run_items = []
    if mrun.get("potencia_media_w"):
        run_items.append(f"Potencia media: {mrun['potencia_media_w']:.0f} W")
    if mrun.get("tiempo_contacto_ms"):
        gct = mrun["tiempo_contacto_ms"]
        run_items.append(f"GCT: {gct:.0f} ms {'⚠️ mejorar técnica' if gct > 270 else '✓'}")
    if mrun.get("oscilacion_vertical_cm"):
        osc = mrun["oscilacion_vertical_cm"]
        run_items.append(f"Oscilación: {osc:.1f} cm {'⚠️ trabajar cadera' if osc > 9 else '✓'}")
    cad = datos.get("cadencia_media")
    if cad:
        run_items.append(f"Cadencia: {cad:.0f} spm {'⚠️ añadir drills' if cad < 170 else '✓'}")
    if run_items:
        reporte["secciones"].append({"titulo": "👟 Eficiencia de Carrera", "items": run_items})

    # Ciclo menstrual
    fc = datos.get("fase_ciclo", {})
    if fc and fc.get("fase"):
        reporte["secciones"].append({
            "titulo": "🩸 Ciclo Menstrual",
            "items": [f"Fase: {fc['fase']}",
                      f"Registro: {fc.get('fecha', '—')}"],
        })

    # Próxima semana
    reporte["secciones"].append({
        "titulo": "📋 Límites Semana Siguiente",
        "items": [
            f"Máximo km seguros: {km_max} km (km_ant × 1.10)",
            f"Fase macrociclo: {fase.get('fase_nombre', '—')} (máx. {fase.get('km_semanales_max', '—')} km)",
            f"Días de fuerza recomendados: {fase.get('dias_fuerza', '—')}",
            f"Enfoque fuerza: {fase.get('enfoque_fuerza', '—')}",
        ],
    })

    return reporte
