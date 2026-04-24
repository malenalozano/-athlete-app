"""
src/plan/adaptador_semanal.py
Adaptador inteligente del plan semanal.

Reglas (sintetizadas de soymaratonista.com):
1. Tras sesión dura → suave o descanso.
2. No velocidad/series el día previo a la tirada larga.
3. Si se pierde 1 día: continuar plan tal cual.
4. Si se pierden 2+ días seguidos: retomar con rodaje suave, no con calidad.
5. Priorizar: Tirada Larga > Ritmo Maratón/Tempo > Series/VO2 > Rodajes.
6. Si se pierde la tirada larga: intentar meterla en los días restantes reduciendo km.
7. Separar sesiones de calidad con 48h.
8. 80/20: máximo 2-3 días de calidad por semana.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Dict, Any

TIPOS_CARRERA = {
    "Tirada Larga", "Progresiva", "Carrera Z2", "Regenerativo",
    "Tempo (umbral)", "Intervalos VO2max", "Rodaje Corto",
    "Fartlek", "Sustitución", "Calidad",
}
TIPOS_FUERZA = {
    "Fuerza", "Fuerza Activ.", "Fuerza Tren Superior",
    "Fuerza Push", "Fuerza Pull", "Fuerza Pierna", "Movilidad",
}
TIPOS_CALIDAD = {"Tempo (umbral)", "Intervalos VO2max", "Progresiva", "Fartlek", "Calidad"}
TIPOS_SUAVE = {"Carrera Z2", "Regenerativo", "Rodaje Corto"}

PRIORIDAD = {
    "Tirada Larga": 100,
    "Tempo (umbral)": 80,
    "Progresiva": 75,
    "Intervalos VO2max": 70,
    "Fartlek": 65,
    "Calidad": 60,
    "Carrera Z2": 40,
    "Fuerza Pierna": 35,
    "Fuerza Push": 30,
    "Fuerza Pull": 30,
    "Fuerza": 25,
    "Rodaje Corto": 20,
    "Fuerza Tren Superior": 18,
    "Regenerativo": 15,
    "Movilidad": 10,
    "Descanso": 0,
    "Sustitución": 5,
}


def _tipo_es_calidad(tipo: str) -> bool:
    return any(k in tipo for k in TIPOS_CALIDAD) or "Calidad" in tipo


def _tipo_es_fuerza_pierna(tipo: str) -> bool:
    t = str(tipo or "").lower()
    return "pierna" in t or ("fuerza" in t and "superior" not in t and "pull" not in t and "push" not in t)


def _tipo_es_dura(tipo: str) -> bool:
    return _tipo_es_calidad(tipo) or tipo == "Tirada Larga" or _tipo_es_fuerza_pierna(tipo)


def _tipo_es_suave(tipo: str) -> bool:
    return tipo in TIPOS_SUAVE or tipo in ("Descanso", "Movilidad", "Regenerativo", "Fuerza Tren Superior")


def _dia_fue_dia_duro_completado(dia: Dict[str, Any]) -> bool:
    """Un día pasado marcado como 'realizado' y con sesión dura."""
    if not dia.get("realizado"):
        return False
    return _tipo_es_dura(str(dia.get("tipo", "")))


def _cuenta_dias_perdidos_seguidos(dias_pasados: List[Dict[str, Any]]) -> int:
    """Cuenta días consecutivos SIN entrenamiento al final del tramo pasado."""
    seguidos = 0
    for d in reversed(dias_pasados):
        if d.get("realizado"):
            break
        # Si el plan era descanso, no cuenta como "perdido"
        if str(d.get("tipo", "")) in ("Descanso", "Movilidad"):
            break
        seguidos += 1
    return seguidos


def _tirada_larga_se_perdio(dias_pasados: List[Dict[str, Any]]) -> bool:
    """¿El plan original tenía TL en días pasados y no se realizó?"""
    for d in dias_pasados:
        tipo_original = str(d.get("_tipo_original") or d.get("tipo", ""))
        if tipo_original == "Tirada Larga" and not d.get("realizado"):
            return True
    return False


def _calidad_se_perdio(dias_pasados: List[Dict[str, Any]]) -> bool:
    for d in dias_pasados:
        tipo_original = str(d.get("_tipo_original") or d.get("tipo", ""))
        if _tipo_es_calidad(tipo_original) and not d.get("realizado"):
            return True
    return False


def adaptar_plan_restante(
    plan_completo: List[Dict[str, Any]],
    hoy: datetime,
) -> List[Dict[str, Any]]:
    """
    Adapta los días futuros del plan según lo realizado/perdido en días pasados.

    plan_completo: lista de 7 días ya procesados (incluyen 'realizado': bool).
                   Cada día pasado tiene 'realizado' y tipo real; los futuros tienen el plan original.
    hoy: datetime de hoy.

    Devuelve la lista modificada (no muta).
    """
    if not plan_completo:
        return plan_completo

    hoy_date = hoy.date()
    dias_pasados = []
    dias_futuros = []
    for d in plan_completo:
        try:
            fd = datetime.fromisoformat(str(d.get("fecha", ""))[:10]).date()
        except Exception:
            fd = hoy_date
        if fd < hoy_date:
            dias_pasados.append(d)
        else:
            dias_futuros.append(d)

    if not dias_futuros:
        return plan_completo

    # Copia profunda simple de los futuros
    futuros = [dict(d) for d in dias_futuros]

    # ---------------------------------------------------------------
    # Regla 4: Si perdió 2+ días seguidos recientes → primer día futuro = rodaje suave
    # ---------------------------------------------------------------
    perdidos_seguidos = _cuenta_dias_perdidos_seguidos(dias_pasados)
    if perdidos_seguidos >= 2 and futuros:
        primer_dia = futuros[0]
        tipo_orig = str(primer_dia.get("tipo", ""))
        if _tipo_es_dura(tipo_orig) and tipo_orig != "Tirada Larga":
            # Degradar a Z2/rodaje suave
            primer_dia["_tipo_original"] = tipo_orig
            primer_dia["tipo"] = "Carrera Z2"
            km_orig = float(primer_dia.get("km") or 0)
            primer_dia["km"] = round(max(km_orig * 0.6, 4), 1) if km_orig > 0 else 6
            primer_dia["duracion_min"] = int(primer_dia["km"] * 6.5) if primer_dia["km"] > 0 else 40
            primer_dia["intensidad"] = "Baja"
            primer_dia["alerta"] = f"🧠 Retomando tras {perdidos_seguidos} días parados → Z2 suave"

    # ---------------------------------------------------------------
    # Regla 6: Si se perdió la tirada larga y aún hay fin de semana → reubicar
    # ---------------------------------------------------------------
    if _tirada_larga_se_perdio(dias_pasados):
        # Buscar primer día futuro que sea fin de semana (sáb/dom) o el último disponible
        candidatos_tl = []
        for i, d in enumerate(futuros):
            try:
                fd = datetime.fromisoformat(str(d.get("fecha", ""))[:10])
                dow = fd.weekday()  # 0=lun, 6=dom
                if dow in (5, 6):  # sábado o domingo
                    candidatos_tl.append(i)
            except Exception:
                pass

        # Si no hay fin de semana disponible, usar último día futuro
        if not candidatos_tl and futuros:
            candidatos_tl = [len(futuros) - 1]

        if candidatos_tl:
            idx_tl = candidatos_tl[-1]
            # Buscar los km originales de la TL en días pasados
            km_tl_orig = 0.0
            for d in dias_pasados:
                if str(d.get("_tipo_original") or d.get("tipo", "")) == "Tirada Larga":
                    km_tl_orig = float(d.get("km") or 0)
                    break
            # Reducir 15% por retraso
            km_tl = round(km_tl_orig * 0.85, 1) if km_tl_orig > 0 else 14
            dia_tl = futuros[idx_tl]
            dia_tl["_tipo_original"] = str(dia_tl.get("tipo", ""))
            dia_tl["tipo"] = "Tirada Larga"
            dia_tl["km"] = km_tl
            dia_tl["duracion_min"] = int(km_tl * 6.5)
            dia_tl["intensidad"] = "Baja"
            dia_tl["alerta"] = f"🧠 TL reubicada (se perdió el día original) · {km_tl} km"

            # Regla 2: el día anterior a la TL NO debe ser velocidad/series
            if idx_tl > 0:
                dia_prev = futuros[idx_tl - 1]
                if _tipo_es_calidad(str(dia_prev.get("tipo", ""))):
                    dia_prev["_tipo_original"] = str(dia_prev.get("tipo", ""))
                    dia_prev["tipo"] = "Carrera Z2"
                    km_p = float(dia_prev.get("km") or 0)
                    dia_prev["km"] = round(max(km_p * 0.7, 4), 1) if km_p > 0 else 6
                    dia_prev["duracion_min"] = int(dia_prev["km"] * 6.5)
                    dia_prev["intensidad"] = "Baja"
                    dia_prev["alerta"] = "🧠 Z2 suave antes de TL"

    # ---------------------------------------------------------------
    # Regla 1: tras sesión dura completada ayer → hoy debe ser suave
    # ---------------------------------------------------------------
    if dias_pasados and futuros:
        ultimo_pasado = dias_pasados[-1]
        if _dia_fue_dia_duro_completado(ultimo_pasado):
            primer_futuro = futuros[0]
            if _tipo_es_dura(str(primer_futuro.get("tipo", ""))) and str(primer_futuro.get("tipo", "")) != "Tirada Larga":
                primer_futuro["_tipo_original"] = str(primer_futuro.get("tipo", ""))
                primer_futuro["tipo"] = "Regenerativo"
                km_p = float(primer_futuro.get("km") or 0)
                primer_futuro["km"] = round(max(km_p * 0.5, 3), 1) if km_p > 0 else 5
                primer_futuro["duracion_min"] = int(primer_futuro["km"] * 7) if primer_futuro["km"] > 0 else 30
                primer_futuro["intensidad"] = "Muy baja"
                ya_alerta = primer_futuro.get("alerta", "")
                primer_futuro["alerta"] = (ya_alerta + " · " if ya_alerta else "") + "🧠 Regenerativo (ayer fue duro)"

    # ---------------------------------------------------------------
    # Regla 7: no dos días de calidad seguidos en el futuro
    # ---------------------------------------------------------------
    for i in range(len(futuros) - 1):
        a = str(futuros[i].get("tipo", ""))
        b = str(futuros[i + 1].get("tipo", ""))
        if _tipo_es_calidad(a) and _tipo_es_calidad(b):
            # Degradar el de menor prioridad
            if PRIORIDAD.get(a, 0) <= PRIORIDAD.get(b, 0):
                futuros[i]["_tipo_original"] = a
                futuros[i]["tipo"] = "Carrera Z2"
                km_p = float(futuros[i].get("km") or 0)
                futuros[i]["km"] = round(max(km_p * 0.7, 5), 1) if km_p > 0 else 6
                futuros[i]["duracion_min"] = int(futuros[i]["km"] * 6.5)
                futuros[i]["intensidad"] = "Baja"
                futuros[i]["alerta"] = "🧠 Z2 para separar sesiones de calidad"
            else:
                futuros[i + 1]["_tipo_original"] = b
                futuros[i + 1]["tipo"] = "Carrera Z2"
                km_p = float(futuros[i + 1].get("km") or 0)
                futuros[i + 1]["km"] = round(max(km_p * 0.7, 5), 1) if km_p > 0 else 6
                futuros[i + 1]["duracion_min"] = int(futuros[i + 1]["km"] * 6.5)
                futuros[i + 1]["intensidad"] = "Baja"
                futuros[i + 1]["alerta"] = "🧠 Z2 para separar sesiones de calidad"

    # ---------------------------------------------------------------
    # Regla 8: máximo 3 días de calidad por semana (incluyendo TL como dura)
    # ---------------------------------------------------------------
    dias_calidad_total = [d for d in (dias_pasados + futuros) if _tipo_es_dura(str(d.get("tipo", "")))]
    if len(dias_calidad_total) > 4:  # TL + 2-3 calidad
        # Degradar la de menor prioridad en futuros
        candidatos = [
            (i, PRIORIDAD.get(str(futuros[i].get("tipo", "")), 0))
            for i in range(len(futuros))
            if _tipo_es_dura(str(futuros[i].get("tipo", "")))
            and str(futuros[i].get("tipo", "")) != "Tirada Larga"
        ]
        candidatos.sort(key=lambda x: x[1])
        exceso = len(dias_calidad_total) - 4
        for idx, _ in candidatos[:exceso]:
            futuros[idx]["_tipo_original"] = str(futuros[idx].get("tipo", ""))
            futuros[idx]["tipo"] = "Carrera Z2"
            km_p = float(futuros[idx].get("km") or 0)
            futuros[idx]["km"] = round(max(km_p * 0.7, 5), 1) if km_p > 0 else 6
            futuros[idx]["duracion_min"] = int(futuros[idx]["km"] * 6.5)
            futuros[idx]["intensidad"] = "Baja"
            futuros[idx]["alerta"] = "🧠 Volumen suave — ya hubo bastante calidad esta semana"

    return dias_pasados + futuros
