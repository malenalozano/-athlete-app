"""
src/plan/nutrition_recommendations.py
Recomendaciones nutricionales basadas en tipo de entrenamiento, duración y objetivos.
Integrado con plan semanal.
"""


def obtener_macros_objetivo(objetivo_tipo: str = "maraton", genero: str = "mujer") -> dict:
    """
    Retorna distribución macro estándar para entrenamiento de maratón.

    Para mujer 21 años entrenando híbrido (fuerza + carrera):
    - Carbohidratos: 60-65% (fuel principal)
    - Proteínas: 15-20% (crítico para mantenimiento muscular en carrera)
    - Grasas: 20-30% (hormonal, absorción vitaminas)

    Retorna: {"carbos_pct": 65, "protein_pct": 18, "grasas_pct": 17, "descripcion": str}
    """
    es_mujer = genero.lower() in ("mujer", "female", "f", "w")

    if objetivo_tipo.lower() in ("maraton", "marathon"):
        if es_mujer:
            return {
                "carbos_pct": 65,
                "protein_pct": 18,
                "grasas_pct": 17,
                "descripcion": "Maratón mujer: énfasis en proteína para mantenimiento muscular + carrera.",
                "protein_g_per_kg": 1.6,  # 1.6 g/kg peso corporal
            }
        else:
            return {
                "carbos_pct": 60,
                "protein_pct": 15,
                "grasas_pct": 25,
                "descripcion": "Maratón hombre: distribución clásica.",
                "protein_g_per_kg": 1.4,
            }
    else:  # Ultra
        return {
            "carbos_pct": 62,
            "protein_pct": 16,
            "grasas_pct": 22,
            "descripcion": "Ultramaratón: balance carbos-proteína.",
            "protein_g_per_kg": 1.5,
        }


def recomendar_nutri_pre_entrenamiento(
    tipo_entrenamiento: str,
    duracion_min: int | None = None,
    intensidad: str = "Z2",  # Z1, Z2, Z3, Z4, Z5
) -> dict:
    """
    Retorna recomendación nutricional PRE-entrenamiento.

    Retorna: {"carbos_g": int, "protein_g": int, "timing_min": int, "descripcion": str}
    """

    tipo_lower = str(tipo_entrenamiento).lower()

    # Z2 y regenerativo: sin necesidad de nutrición específica pre
    if "z2" in tipo_lower or "regenerat" in tipo_lower:
        return {
            "carbos_g": 0,
            "protein_g": 0,
            "timing_min": 0,
            "descripcion": "✅ Z2: sin nutrición específica pre-requerida.",
        }

    # Carrera de calidad (Tempo, Intervalos, Progresiva, Fartlek)
    if any(x in tipo_lower for x in ("intervalo", "tempo", "progresiva", "fartlek", "calidad")):
        return {
            "carbos_g": 45,
            "protein_g": 15,
            "timing_min": 45,  # 45 min antes
            "descripcion": "Carrera de calidad: 45g carbos + 15g proteína (ratio 3:1) 45 min antes.",
        }

    # Fuerza pesada (3-6 reps)
    if "fuerza" in tipo_lower and ("pesada" in tipo_lower or "3-6" in tipo_lower):
        return {
            "carbos_g": 40,
            "protein_g": 20,
            "timing_min": 60,
            "descripcion": "Fuerza pesada: 40g carbos + 20g proteína 60 min antes.",
        }

    # Fuerza estándar (8-12 reps)
    if "fuerza" in tipo_lower:
        return {
            "carbos_g": 30,
            "protein_g": 15,
            "timing_min": 60,
            "descripcion": "Fuerza: 30g carbos + 15g proteína 60 min antes.",
        }

    return {
        "carbos_g": 0,
        "protein_g": 0,
        "timing_min": 0,
        "descripcion": "Sin recomendación específica.",
    }


def recomendar_nutri_durante_entrenamiento(
    tipo_entrenamiento: str,
    duracion_min: int | None = None,
) -> dict:
    """
    Retorna recomendación nutricional DURANTE entrenamiento.

    Crítico para sesiones >40 min para evitar catabolismo muscular.

    Retorna: {"carbos_g_hora": int, "electrolitos": bool, "hidratacion_ml": int, "descripcion": str}
    """

    tipo_lower = str(tipo_entrenamiento).lower()
    duracion = duracion_min or 0

    # Sesiones cortas (<40 min): solo agua
    if duracion < 40:
        return {
            "carbos_g_hora": 0,
            "electrolitos": False,
            "hidratacion_ml": 150,
            "descripcion": "✅ Sesión corta: agua ad libitum (~150-200 ml/15 min).",
        }

    # Z2 larga (40-90 min): carbos bajos
    if "z2" in tipo_lower or "regenerat" in tipo_lower:
        if 40 <= duracion <= 60:
            return {
                "carbos_g_hora": 30,
                "electrolitos": True,
                "hidratacion_ml": 500,
                "descripcion": "Z2 media (40-60 min): 30g carbos/hora + electrolitos.",
            }
        else:  # >60 min
            return {
                "carbos_g_hora": 60,
                "electrolitos": True,
                "hidratacion_ml": 600,
                "descripcion": "Z2 larga (>60 min): 60g carbos/hora + electrolitos.",
            }

    # Carrera de calidad o fuerza: máximo carbos
    if any(x in tipo_lower for x in ("intervalo", "tempo", "progresiva", "fartlek", "fuerza")):
        return {
            "carbos_g_hora": 60 if duracion < 90 else 90,
            "electrolitos": True,
            "hidratacion_ml": 600,
            "descripcion": f"Alta intensidad (>40 min): {60 if duracion < 90 else 90}g carbos/hora + electrolitos.",
        }

    return {
        "carbos_g_hora": 30,
        "electrolitos": True,
        "hidratacion_ml": 500,
        "descripcion": "Plan estándar: 30g carbos/hora + electrolitos.",
    }


def recomendar_nutri_post_entrenamiento(
    tipo_entrenamiento: str,
    duracion_min: int | None = None,
) -> dict:
    """
    Retorna recomendación nutricional POST-entrenamiento (ventana 30-60 min).

    Crucial para recuperación y evitar catabolismo.

    Retorna: {"carbos_g": int, "protein_g": int, "timing_min": int, "descripcion": str}
    """

    tipo_lower = str(tipo_entrenamiento).lower()

    # Fuerza pesada: máxima prioridad recuperación proteína
    if "fuerza" in tipo_lower and any(x in tipo_lower for x in ("pesada", "pierna")):
        return {
            "carbos_g": 50,
            "protein_g": 30,
            "timing_min": 30,
            "descripcion": "💪 Post-fuerza: 50g carbos + 30g proteína en 30 min. Ratio 1:1 carbos:proteína.",
        }

    # Carrera larga (>60 min): recuperación carbos + proteína
    if ("z2" in tipo_lower or any(x in tipo_lower for x in ("tirada", "carrera"))) and duracion and duracion > 60:
        return {
            "carbos_g": 60,
            "protein_g": 20,
            "timing_min": 30,
            "descripcion": "🏃 Post-carrera larga: 60g carbos + 20g proteína en 30 min (ratio 3:1).",
        }

    # Carrera de calidad (Tempo, Intervalos): proteína importante
    if any(x in tipo_lower for x in ("intervalo", "tempo", "progresiva", "fartlek")):
        return {
            "carbos_g": 45,
            "protein_g": 20,
            "timing_min": 30,
            "descripcion": "⚡ Post-calidad: 45g carbos + 20g proteína en 30 min.",
        }

    # Z2 corta: sin recomendación especial
    return {
        "carbos_g": 0,
        "protein_g": 0,
        "timing_min": 0,
        "descripcion": "✅ Z2 corta: sin recomendación post específica.",
    }


def generar_alerta_nutricional_sesion(
    tipo: str,
    duracion_min: int | None = None,
    ciclo_fase: str | None = None,
) -> list[str]:
    """
    Retorna lista de alertas nutricionales para una sesión específica.
    """
    alertas = []
    duracion = duracion_min or 0

    # Catabolismo por duración
    if duracion >= 40 and duracion < 50:
        alertas.append("⚠️ NUTRICIÓN: Sesión >40 min. Consumir 30-60g carbos cada hora para evitar catabolismo.")
    elif duracion >= 50:
        alertas.append("🚨 NUTRICIÓN: Sesión >50 min. OBLIGATORIO: 60-90g carbos/hora + electrolitos. PROTEGE MÚSCULO.")

    # Menstruación
    if ciclo_fase and ciclo_fase.lower() in ("menstruacion", "menstruation"):
        alertas.append("💧 CICLO: Menstruación. Aumentar ingesta de agua +500ml + electrolitos + hierro (carne roja, espinaca).")

    # Post-entreno
    tipo_lower = str(tipo).lower()
    if "fuerza" in tipo_lower:
        alertas.append("💪 POST: Proteína en 30 min post-fuerza (huevo, pollo, yogur griego).")
    if duracion > 60:
        alertas.append("🏃 POST: Recuperación carbos-proteína en 30 min (plátano + yogur, o batido).")

    return alertas
