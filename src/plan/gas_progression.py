"""
src/plan/gas_progression.py
Módulo de Síndrome General de Adaptación (GAS)
Evalúa las 3 fases: Alarma, Resistencia, Agotamiento
Basado en: HRV, sueño, estrés, recuperación
"""

from datetime import datetime, timedelta


def evaluar_fase_gas(
    hrv_actual: float | None,
    hrv_media_7d: float | None,
    sleep_score: float | None,
    sleep_breakdown: dict | None,
    estres_medio: float | None,
    body_battery_min: float | None,
    dias_desde_estimulo_duro: int = 0,
) -> dict:
    """
    Evalúa la fase actual del GAS basada en señales fisiológicas.

    GAS Phases:
    1. ALARMA (0-48h post-estímulo): HRV baja, sleep disrupted, estrés alto
    2. RESISTENCIA (2-7 días): HRV en recuperación, sleep normalizándose
    3. AGOTAMIENTO (>7 días sin descanso): HRV persistentemente baja, sleep <60, fatiga crónica

    Retorna:
    {
        "fase": "alarma" | "resistencia" | "agotamiento",
        "severidad": 1-10 (1=leve, 10=crítico),
        "dias_estimulo": int,
        "recomendacion": str,
        "riesgo_lesion": float (0.0-1.0),
        "permitir_calidad": bool,
        "multiplicador_volumen": float,
    }
    """

    # Defaults seguros si no hay datos
    if not hrv_actual or not hrv_media_7d or not sleep_score:
        return {
            "fase": "resistencia",
            "severidad": 3,
            "dias_estimulo": 0,
            "recomendacion": "Datos insuficientes. Plan base aplicado.",
            "riesgo_lesion": 0.1,
            "permitir_calidad": True,
            "multiplicador_volumen": 1.0,
        }

    sleep_breakdown = sleep_breakdown or {}
    sleep_profundo_h = sleep_breakdown.get("profundo_h", 0)
    hrv_caida_pct = ((hrv_media_7d - hrv_actual) / hrv_media_7d) * 100 if hrv_media_7d > 0 else 0

    # ---- FASE DE ALARMA ----
    if hrv_caida_pct > 15 or sleep_score < 60 or sleep_profundo_h < 0.5:
        return {
            "fase": "alarma",
            "severidad": min(10, int(hrv_caida_pct / 2 + (100 - sleep_score) / 10)),
            "dias_estimulo": dias_desde_estimulo_duro,
            "recomendacion": "🚨 FASE DE ALARMA: Cuerpo bajo estrés. Reducir volumen, priorizar Z2, dormir 1h extra.",
            "riesgo_lesion": 0.6,
            "permitir_calidad": False,
            "multiplicador_volumen": 0.7,
        }

    # ---- FASE DE AGOTAMIENTO (>7 días de estrés persistente) ----
    if (
        dias_desde_estimulo_duro > 7
        and hrv_caida_pct > 10
        and sleep_score < 70
        and estres_medio and estres_medio > 70
    ):
        return {
            "fase": "agotamiento",
            "severidad": min(10, int(hrv_caida_pct / 2 + (100 - sleep_score) / 8)),
            "dias_estimulo": dias_desde_estimulo_duro,
            "recomendacion": "⚠️ FASE DE AGOTAMIENTO: Riesgo overtraining crítico. DESCANSO OBLIGATORIO 3-5 días.",
            "riesgo_lesion": 0.9,
            "permitir_calidad": False,
            "multiplicador_volumen": 0.4,
        }

    # ---- FASE DE RESISTENCIA (adaptación en curso) ----
    return {
        "fase": "resistencia",
        "severidad": max(1, int(hrv_caida_pct / 5 + (100 - sleep_score) / 20)),
        "dias_estimulo": dias_desde_estimulo_duro,
        "recomendacion": "✅ FASE DE RESISTENCIA: Cuerpo adaptándose. Plan normal aplicado.",
        "riesgo_lesion": 0.2,
        "permitir_calidad": True,
        "multiplicador_volumen": 1.0,
    }


def calcular_dias_desde_estimulo(
    ultimas_3_actividades: list | None,
) -> int:
    """
    Calcula días desde la última actividad de alta intensidad (Intervalos, Tempo, Progresiva).
    Si última actividad fue hace 2 días @ Z4, retorna 2.

    Usado para determinar si estamos en fase de Alarma (0-2 días post-estimulo) o Resistencia.
    """
    if not ultimas_3_actividades:
        return 7  # Asumir recuperada si no hay datos

    for act in ultimas_3_actividades:
        tipo = str(act.get("tipo", "")).lower()
        if any(k in tipo for k in ("intervalo", "tempo", "progresiva", "fartlek", "calidad")):
            fecha_actividad = act.get("fecha")
            if fecha_actividad:
                try:
                    fecha_act_obj = datetime.fromisoformat(str(fecha_actividad))
                    dias_diff = (datetime.now() - fecha_act_obj).days
                    return max(0, dias_diff)
                except (ValueError, TypeError):
                    pass
    return 7


def recomendar_descanso_gas(gas_phase: dict) -> bool:
    """
    Retorna True si se recomienda DESCANSO TOTAL (no entrenar).
    Solo en fase de agotamiento severo (severidad >= 8).
    """
    return gas_phase["fase"] == "agotamiento" and gas_phase["severidad"] >= 8


def mensaje_educativo_gas(gas_phase: dict, ciclo_fase: str | None = None) -> str:
    """
    Retorna mensaje educativo sobre GAS + ciclo menstrual (si aplica).
    """
    base = f"\n**GAS Status**: {gas_phase['recomendacion']}\n"

    if ciclo_fase:
        if ciclo_fase.lower() in ("menstruacion", "menstruation"):
            base += f"\n🩸 **Ciclo Menstrual**: Menstruación detectada.\n"
            base += f"   → El cuerpo está en doble estrés (GAS {gas_phase['fase'].upper()} + estrés hormonal)\n"
            base += f"   → Usar slider para ajustar volumen según disponibilidad de energía\n"
        elif ciclo_fase.lower() in ("ovulacion", "ovulation"):
            base += f"\n🔴 **Ciclo Menstrual**: Ovulación.\n"
            base += f"   → Mejor tolerancia al dolor + mejor rendimiento\n"
            base += f"   → Óptimo para test o sesiones de calidad\n"

    return base
