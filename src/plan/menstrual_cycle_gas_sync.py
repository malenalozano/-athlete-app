"""
src/plan/menstrual_cycle_gas_sync.py
Sincronización Ciclo Menstrual + GAS (Síndrome General de Adaptación)
Modelo flexible con SLIDER para que usuaria controle volumen según disponibilidad.

El sistema SUGIERE reducción basada en ciencia, pero ELLA DECIDE.
"""


def evaluar_ciclo_gas_sinergia(
    fase_ciclo: str | None,
    gas_fase: str,
    gas_severidad: int,  # 1-10
) -> dict:
    """
    Evalúa interacción ciclo menstrual + GAS.
    Si ciclo + GAS bajo = doble estrés fisiológico.

    Retorna:
    {
        "doble_estres": bool,
        "multiplicador_base": float (ej: 0.8 para -20% volumen),
        "recomendacion_slider": str (ej: "Sugerir reducir a 68 km de 85 km"),
        "mensaje_educativo": str,
        "permite_override": bool,
    }
    """

    fase_ciclo = str(fase_ciclo or "").lower().strip()

    # ---- MENSTRUACIÓN + CUALQUIER GAS ----
    if "menstruacion" in fase_ciclo or "menses" in fase_ciclo:
        if gas_fase == "agotamiento" or gas_severidad >= 7:
            return {
                "doble_estres": True,
                "multiplicador_base": 0.6,
                "recomendacion_slider": "🩸 Menstruación + GAS agotamiento. Sugerir volumen al 60% (máximo riesgo).",
                "mensaje_educativo": (
                    "Menstruación = bajos estrógeno/progesterona → peor tolerancia al estrés.\n"
                    "GAS agotamiento = cuerpo sin capacidad de adaptación.\n"
                    "Combinación = alto riesgo overtraining. **Usa slider para ajustar según cómo te sientas**."
                ),
                "permite_override": True,
            }
        elif gas_fase == "alarma":
            return {
                "doble_estres": True,
                "multiplicador_base": 0.75,
                "recomendacion_slider": "🩸 Menstruación + GAS alarma. Sugerir volumen al 75% (riesgo moderado).",
                "mensaje_educativo": (
                    "Menstruación: fase hormonalmente sensible.\n"
                    "GAS alarma: cuerpo procesando estímulo duro.\n"
                    "Recomendación: reducir volumen. Pero **si te sientes fuerte, usa el slider**."
                ),
                "permite_override": True,
            }
        else:  # GAS Resistencia
            return {
                "doble_estres": False,
                "multiplicador_base": 0.9,
                "recomendacion_slider": "🩸 Menstruación pero GAS en resistencia. Sugerir volumen al 90%.",
                "mensaje_educativo": (
                    "Menstruación: baja tolerancia al dolor.\n"
                    "GAS resistencia: cuerpo adaptándose bien.\n"
                    "Puede ser un día bueno para entrenar. **Ajusta con slider según disponibilidad**."
                ),
                "permite_override": True,
            }

    # ---- OVULACIÓN (Pico hormonal) ----
    elif "ovulacion" in fase_ciclo or "ovulation" in fase_ciclo:
        return {
            "doble_estres": False,
            "multiplicador_base": 1.1,  # +10% volumen posible
            "recomendacion_slider": "🔴 Ovulación: mejor rendimiento. Volumen +10% opcional (110%).",
            "mensaje_educativo": (
                "Ovulación: estrógeno y progesterona en pico.\n"
                "Mejor tolerancia al dolor, mejor VO2max esperado.\n"
                "**VENTANA DE ORO PARA TEST O SESIONES DIFÍCILES**.\n"
                "Usa slider para aprovechar este día si lo necesitas."
            ),
            "permite_override": True,
        }

    # ---- LUTEAL (Post-ovulación) ----
    elif "luteal" in fase_ciclo or "post-ovulacion" in fase_ciclo or "post-ovulatory" in fase_ciclo:
        if gas_fase == "agotamiento" or gas_severidad >= 7:
            return {
                "doble_estres": True,
                "multiplicador_base": 0.75,
                "recomendacion_slider": "Fase luteal + GAS agotamiento. Sugerir 75% volumen.",
                "mensaje_educativo": (
                    "Fase luteal: progesterona alta → fatiga aumentada.\n"
                    "GAS agotamiento: cuerpo sin buffer de recuperación.\n"
                    "Recomendación: descanso. Usa slider para ajustar.\n"
                ),
                "permite_override": True,
            }
        else:
            return {
                "doble_estres": False,
                "multiplicador_base": 0.95,
                "recomendacion_slider": "Fase luteal. Volumen 95% (ligera reducción por progesterona).",
                "mensaje_educativo": (
                    "Fase luteal: menor energía disponible (progesterona ↑).\n"
                    "Considera entrenamientos más cortos pero intensos.\n"
                    "Usa slider para ajustar según cómo te sientas."
                ),
                "permite_override": True,
            }

    # ---- FOLICULAR (post-menstruación) ----
    elif "folicular" in fase_ciclo or "follicular" in fase_ciclo:
        return {
            "doble_estres": False,
            "multiplicador_base": 1.0,
            "recomendacion_slider": "Fase folicular. Volumen normal (100%).",
            "mensaje_educativo": (
                "Fase folicular: estrógeno ↑, energía ↑.\n"
                "Óptimo para volumen de entrenamiento.\n"
                "Usa slider si necesitas ajustar por GAS o disponibilidad."
            ),
            "permite_override": True,
        }

    # ---- SIN DATOS DE CICLO ----
    return {
        "doble_estres": False,
        "multiplicador_base": 1.0,
        "recomendacion_slider": "Sin datos ciclo. Volumen basado solo en GAS.",
        "mensaje_educativo": "Añade tu ciclo en Diario para recomendaciones más precisas.",
        "permite_override": True,
    }


def calcular_volumen_con_slider(
    km_objetivo_base: float,
    multiplicador_ciclo_gas: float,
    slider_porcentaje: float = 100,  # 0-100
) -> dict:
    """
    Calcula volumen final con slider (0-100%).

    slider_porcentaje=100 → volumen 100% (sin reducción)
    slider_porcentaje=75  → volumen 75% (reducción -25%)
    slider_porcentaje=110 → volumen 110% (aumento +10%)

    Retorna:
    {
        "km_base_recomendado": float,
        "km_final_con_slider": float,
        "porcentaje_slider": float,
        "reduccion_km": float,
        "mensaje": str,
    }
    """

    # Volumen recomendado (después de aplicar ciclo + GAS)
    km_recomendado = km_objetivo_base * multiplicador_ciclo_gas

    # Volumen con slider
    km_final = km_recomendado * (slider_porcentaje / 100.0)

    reduccion = km_objetivo_base - km_final

    return {
        "km_base_recomendado": round(km_recomendado, 1),
        "km_final_con_slider": round(km_final, 1),
        "porcentaje_slider": slider_porcentaje,
        "reduccion_km": round(reduccion, 1),
        "mensaje": (
            f"Volumen base: {km_objetivo_base:.1f} km\n"
            f"Recomendado (ciclo+GAS): {km_recomendado:.1f} km ({multiplicador_ciclo_gas*100:.0f}%)\n"
            f"**Tu ajuste (slider): {km_final:.1f} km ({slider_porcentaje:.0f}%)**"
        ),
    }


def generar_alertas_ciclo_gas(
    fase_ciclo: str | None,
    gas_fase: str,
    gas_severidad: int,
    sinergia: dict,
) -> list[str]:
    """
    Retorna lista de alertas específicas ciclo + GAS.
    """
    alertas = []

    if sinergia["doble_estres"]:
        alertas.append(f"🩸 DOBLE ESTRÉS: Ciclo menstrual + GAS {gas_fase}. Usa slider para ajustar volumen.")

    if gas_severidad >= 8:
        alertas.append(f"🚨 GAS SEVERO: Severidad {gas_severity}/10. Considera descanso 3-5 días.")

    if "menstruacion" in str(fase_ciclo or "").lower():
        alertas.append("💧 Aumentar hidratación +500ml/día + electrolitos + hierro (carnes rojas, espinaca).")
        alertas.append("⚠️ Menstruación: dolor puede ser mayor. Escucha a tu cuerpo en el slider.")

    if "ovulacion" in str(fase_ciclo or "").lower():
        alertas.append("🔴 OVULACIÓN: Mejor rendimiento hoy. Ventana para test o PR si lo necesitas.")

    return [a for a in alertas if a]  # Remove empty strings


def validar_slider_seguridad(
    slider_porcentaje: float,
    gas_fase: str,
    gas_severidad: int,
) -> dict:
    """
    Valida si el porcentaje seleccionado por slider es "seguro" según GAS.

    Si selecciona 100% pero GAS agotamiento severo (>8), alertar pero PERMITIR.

    Retorna:
    {
        "es_seguro": bool,
        "advertencia": str | None,
        "permitido": bool,
    }
    """

    if gas_fase == "agotamiento" and gas_severidad >= 8:
        if slider_porcentaje > 80:
            return {
                "es_seguro": False,
                "advertencia": (
                    f"⚠️ ADVERTENCIA: GAS {gas_severidad}/10 (agotamiento crítico) + slider {slider_porcentaje}%.\n"
                    f"Riesgo muy alto de lesión. **Recomendamos ≤60%.**\n"
                    f"Pero si te sientes bien, **tú decides**. 💪"
                ),
                "permitido": True,  # Permitir pero avisar
            }

    if gas_fase == "alarma" and gas_severidad >= 7:
        if slider_porcentaje > 90:
            return {
                "es_seguro": False,
                "advertencia": (
                    f"⚠️ ALERTA: GAS alarma severa ({gas_severidad}/10) + slider {slider_porcentaje}%.\n"
                    f"Buena señal que te sientas fuerte, pero el cuerpo está bajo estrés.\n"
                    f"Considera ≤80% para permitir recuperación. **Tu decisión.**"
                ),
                "permitido": True,
            }

    return {
        "es_seguro": True,
        "advertencia": None,
        "permitido": True,
    }
