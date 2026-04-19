"""
ultramarathon_planner.py
Protocolo de Periodización para Dani: Ultramaratón 100km
Macrociclo: 6 abril 2026 - 21 febrero 2027 (aprox. 46 semanas)
Objetivo: Completar 100km en condición óptima, con estrategia nutricional y mental robusta.

Diferencias vs Marathon Malena:
- Mayor volumen de carrera semanal (más énfasis en resistencia)
- Entrenamiento en terreno variado (asfalto, trail, montaña)
- Fuerza funcional orientada a estabilidad en fatiga
- Nutrición en carrera (práctica de geles, bebidas, alimentos)
- Mayor ventana de entrenamiento en Z1/Z2 (economía de movimiento)
"""

from datetime import datetime


def obtener_fase_macrociclo_ultramaratonista(fecha_actual=None):
    """
    Devuelve la fase del macrociclo para Dani (100km ultramaratón).
    MACROCICLO: 6 abril 2026 - 21 febrero 2027 (46 semanas)
    
    Fases adaptadas para ultramaratón:
    1. Acondicionamiento General: Volumen bajo, énfasis en técnica y resistencia base.
    2. Preparación General: Incremento de volumen aerobi co (Z2 largo).
    3. Preparación Específica: Tiradas largas (20-30km), ritmos competición prolongados.
    4. Pico de Forma: Entrenamientos de ultradistancia (35-40km), tapering parcial.
    5. Tapering y Competición: Cargas mínimas, recuperación general.
    """
    if fecha_actual is None:
        fecha_actual = datetime.now()
    
    # Definir fechas de inicio para cada fase
    fases_fechas = [
        {
            'nombre': 'Acondicionamiento General',
            'inicio': datetime.strptime('2026-04-06', '%Y-%m-%d'),
            'fin': datetime.strptime('2026-05-31', '%Y-%m-%d'),
            'km_semanales_max': 50,  # Dani corre más volumen que Malena
            'dias_carrera_recomendados': 5,  # Más días de entrenamiento
            'dias_fuerza_recomendados': 2,  # Menos fuerza, más carrera
            'enfoque_fuerza': 'Funcional: Core, glúteos, estabilidad. Bajo volumen.',
            'enfoque_running': 'Base aeróbica (Z1/Z2) en terreno mixto. Técnica en trail.',
            'restricciones': {'limitar_impacto': False, 'permitir_series_running': False},
            'notas': 'Adaptar a trail: trabajar técnica de descensos y subidas.'
        },
        {
            'nombre': 'Preparación General',
            'inicio': datetime.strptime('2026-06-01', '%Y-%m-%d'),
            'fin': datetime.strptime('2026-08-31', '%Y-%m-%d'),
            'km_semanales_max': 80,  # Incremento significativo
            'dias_carrera_recomendados': 5,
            'dias_fuerza_recomendados': 2,
            'enfoque_fuerza': 'Fuerza funcional: Press, dominadas, trabajo de piernas en isometría.',
            'enfoque_running': 'Incremento progresivo de volumen Z2 (20-25km tiradas). Fartlek corto.',
            'restricciones': {'limitar_impacto': False, 'permitir_series_running': True},
            'notas': 'Introducir entrenamientos duales: correr + fuerte el mismo día.'
        },
        {
            'nombre': 'Preparación Específica',
            'inicio': datetime.strptime('2026-09-01', '%Y-%m-%d'),
            'fin': datetime.strptime('2026-11-30', '%Y-%m-%d'),
            'km_semanales_max': 100,  # Pico de volumen
            'dias_carrera_recomendados': 5,
            'dias_fuerza_recomendados': 1,  # Mínima fuerza
            'enfoque_fuerza': 'Mantenimiento funcional: 1x/semana, sesión corta (30-40 min).',
            'enfoque_running': 'Tiradas largas de 25-30km en Z2. Practicar nutrición en carrera.',
            'restricciones': {'limitar_impacto': False, 'permitir_series_running': True},
            'notas': 'Pruebas de nutrición e hidratación en sesiones largas. Simulacros de 30km.'
        },
        {
            'nombre': 'Pico de Forma',
            'inicio': datetime.strptime('2026-12-01', '%Y-%m-%d'),
            'fin': datetime.strptime('2027-01-31', '%Y-%m-%d'),
            'km_semanales_max': 110,  # Máximo volumen
            'dias_carrera_recomendados': 5,
            'dias_fuerza_recomendados': 1,
            'enfoque_fuerza': 'Mantenimiento mínimo: movilidad, activación, core ligero.',
            'enfoque_running': 'Tiradas ultradistancia (35-40km en Z2). Aclimatación mental a fatiga.',
            'restricciones': {'limitar_impacto': False, 'permitir_series_running': False},
            'notas': '1-2 entrenamientos largos por semana. Énfasis en recuperación entre sesiones.'
        },
        {
            'nombre': 'Tapering y Competición',
            'inicio': datetime.strptime('2027-02-01', '%Y-%m-%d'),
            'fin': datetime.strptime('2027-02-21', '%Y-%m-%d'),
            'km_semanales_max': 40,  # Descenso drástico
            'dias_carrera_recomendados': 2,  # Mínimo para mantener ritmo
            'dias_fuerza_recomendados': 0,
            'enfoque_fuerza': 'Cero: solo movilidad y activación dinámica.',
            'enfoque_running': 'Recuperación activa. Sesiones cortas (10-15km) de reconocimiento de circuito.',
            'restricciones': {'limitar_impacto': True, 'permitir_series_running': False},
            'notas': 'Descanso completo 48h antes de la competencia. Sobrecompensación GAS.'
        }
    ]
    
    # Buscar fase actual
    for fase in fases_fechas:
        if fase['inicio'] <= fecha_actual <= fase['fin']:
            return {
                'fase_nombre': fase['nombre'],
                'km_semanales_max': fase['km_semanales_max'],
                'dias_carrera_recomendados': fase['dias_carrera_recomendados'],
                'dias_fuerza_recomendados': fase['dias_fuerza_recomendados'],
                'enfoque_fuerza': fase['enfoque_fuerza'],
                'enfoque_running': fase['enfoque_running'],
                'restricciones': fase['restricciones'],
                'notas': fase['notas']
            }
    
    # Si la fecha está antes del macrociclo
    if fecha_actual < fases_fechas[0]['inicio']:
        return {
            'fase_nombre': 'Acondicionamiento General (Próximo)',
            'km_semanales_max': 50,
            'dias_carrera_recomendados': 5,
            'dias_fuerza_recomendados': 2,
            'enfoque_fuerza': 'Prepararse para funcional de ultramaratón.',
            'enfoque_running': 'Base aeróbica 100km (economía de movimiento).',
            'restricciones': {'limitar_impacto': False, 'permitir_series_running': False},
            'notas': 'Comenzar transición a trail si es posible.'
        }
    
    # Si la fecha está después
    return {
        'fase_nombre': 'Competición Finalizada',
        'km_semanales_max': 0,
        'dias_carrera_recomendados': 0,
        'dias_fuerza_recomendados': 0,
        'enfoque_fuerza': 'Recuperación post-competición.',
        'enfoque_running': 'Recuperación activa: paseos ligeros, natación.',
        'restricciones': {'limitar_impacto': False, 'permitir_series_running': False},
        'notas': 'Evaluación de lesiones y fatiga. Descanso 1-2 semanas mínimo.'
    }


def obtener_template_semana_ultramaratonista(fase_nombre, km_objetivo):
    """
    Distribuye los 7 días de la semana para un ultramaratonista.
    Estructura diferente a maratonista: énfasis en Z2 sostenido, menos velocidad estructurada.
    """
    templates = {
        'Acondicionamiento General': {
            'dias': [
                {'dia': 'Lunes', 'tipo': 'Fuerza Tren Superior', 'km': 0, 'duracion_min': 45},
                {'dia': 'Martes', 'tipo': 'Carrera Z2 Fácil', 'km': km_objetivo * 0.12, 'duracion_min': 50},
                {'dia': 'Miércoles', 'tipo': 'Descanso / Movilidad', 'km': 0},
                {'dia': 'Jueves', 'tipo': 'Carrera Z2 + Técnica Trail', 'km': km_objetivo * 0.10, 'duracion_min': 45},
                {'dia': 'Viernes', 'tipo': 'Fuerza Funcional', 'km': 0, 'duracion_min': 40},
                {'dia': 'Sábado', 'tipo': 'Tirada Larga Z2', 'km': km_objetivo * 0.35, 'duracion_min': 150},
                {'dia': 'Domingo', 'tipo': 'Regenerativo / Trail suave', 'km': km_objetivo * 0.13, 'duracion_min': 60},
            ],
            'observaciones': 'Énfasis en recobijación. La tirada larga es el pico de la semana.'
        },
        'Preparación General': {
            'dias': [
                {'dia': 'Lunes', 'tipo': 'Carrera Z2 Moderada', 'km': km_objetivo * 0.12, 'duracion_min': 65},
                {'dia': 'Martes', 'tipo': 'Fuerza Funcional', 'km': 0, 'duracion_min': 50},
                {'dia': 'Miércoles', 'tipo': 'Carrera Z2 + Fartlek suave', 'km': km_objetivo * 0.12, 'duracion_min': 60},
                {'dia': 'Jueves', 'tipo': 'Descanso / Yoga / Movilidad', 'km': 0},
                {'dia': 'Viernes', 'tipo': 'Carrera Trail técnica', 'km': km_objetivo * 0.10, 'duracion_min': 50},
                {'dia': 'Sábado', 'tipo': 'Tirada Larga Z2 (20-25km)', 'km': km_objetivo * 0.38, 'duracion_min': 180},
                {'dia': 'Domingo', 'tipo': 'Regenerativo', 'km': km_objetivo * 0.12, 'duracion_min': 70},
            ],
            'observaciones': 'Aumentar minutos más que km. Practicar nutrición en tiradas largas.'
        },
        'Preparación Específica': {
            'dias': [
                {'dia': 'Lunes', 'tipo': 'Carrera Z2 sostenida', 'km': km_objetivo * 0.12, 'duracion_min': 75},
                {'dia': 'Martes', 'tipo': 'Descanso / Sauna / Recuperación', 'km': 0},
                {'dia': 'Miércoles', 'tipo': 'Carrera Media Montaña', 'km': km_objetivo * 0.12, 'duracion_min': 70},
                {'dia': 'Jueves', 'tipo': 'Fuerza Mantenimiento rápido', 'km': 0, 'duracion_min': 30},
                {'dia': 'Viernes', 'tipo': 'Carrera Z2 Trail larga', 'km': km_objetivo * 0.15, 'duracion_min': 90},
                {'dia': 'Sábado', 'tipo': 'Tirada Ultradistancia (25-30km)', 'km': km_objetivo * 0.35, 'duracion_min': 210},
                {'dia': 'Domingo', 'tipo': 'Regenerativo muy suave', 'km': km_objetivo * 0.12, 'duracion_min': 80},
            ],
            'observaciones': 'Simulacros de 30km. Practicar estrategia nutricional: geles, bebidas, alimentos sólidos.'
        },
        'Pico de Forma': {
            'dias': [
                {'dia': 'Lunes', 'tipo': 'Carrera Z2 soft', 'km': km_objetivo * 0.10, 'duracion_min': 60},
                {'dia': 'Martes', 'tipo': 'Descanso / Recuperación activa', 'km': 0},
                {'dia': 'Miércoles', 'tipo': 'Carrera Z2 montaña técnica', 'km': km_objetivo * 0.12, 'duracion_min': 70},
                {'dia': 'Jueves', 'tipo': 'Fuerza mínima / Movilidad', 'km': 0, 'duracion_min': 25},
                {'dia': 'Viernes', 'tipo': 'Carrera Z2 recreativa', 'km': km_objetivo * 0.10, 'duracion_min': 55},
                {'dia': 'Sábado', 'tipo': 'Tirada Ultradistancia (35-40km)', 'km': km_objetivo * 0.40, 'duracion_min': 240},
                {'dia': 'Domingo', 'tipo': 'Recuperación completa / Sauna / Stretching', 'km': 0},
            ],
            'observaciones': '1-2 entrenamientos ultradistancia. Máximo énfasis en fatiga psicológica y mental.'
        },
        'Tapering y Competición': {
            'dias': [
                {'dia': 'Lunes', 'tipo': 'Descanso / Movilidad', 'km': 0},
                {'dia': 'Martes', 'tipo': 'Carrera reconocimiento 10km', 'km': 10, 'duracion_min': 50},
                {'dia': 'Miércoles', 'tipo': 'Descanso / Masaje / Activación', 'km': 0},
                {'dia': 'Jueves', 'tipo': 'Carrera ligera 8km', 'km': 8, 'duracion_min': 40},
                {'dia': 'Viernes', 'tipo': 'Descanso total / Mentalización', 'km': 0},
                {'dia': 'Sábado', 'tipo': 'Descanso / Activación dinámica 15min', 'km': 0, 'duracion_min': 15},
                {'dia': 'Domingo', 'tipo': '🎯 COMPETENCIA 100km', 'km': 100, 'duracion_min': 700},
            ],
            'observaciones': 'Descanso mental. Revisión de estrategia de nutrición y pacing.'
        }
    }
    
    return templates.get(fase_nombre, templates['Acondicionamiento General'])


# ============= Especificidades de Ultramaratón =============

def protocolo_nutricion_ultramaratón(distancia_km=100, peso_kg=70, duracion_estimada_horas=12):
    """
    Estrategia nutricional específica para Dani en 100km.
    Basada en metabolismo de grasas y glycógeno persistencia.
    """
    return {
        'calorias_totales': distancia_km * 80,  # 80 cal/km para ultramaratón
        'carbohidratos': {
            'gramos_totales': (duracion_estimada_horas * 30),  # 30g/hora en carrera ultra
            'estrategia': '10-15g cada 20min (geles) + bebida deportiva con electrolitos',
            'notas': 'Practicar en entrenamientos largos. Cambiar sabores para evitar monotonía.'
        },
        'proteina': {
            'gramos': peso_kg * 1.8,  # Mayor para recuperación ante daño muscular
            'timing': 'Dentro de 30min post-carrera'
        },
        'grasas': {
            'estrategia': 'Barras de frutos secos, mantequilla de cacahuete. Fuente de energía en horas finales.',
            'momento': 'Última mitad de la carrera (a partir de km 60)'
        },
        'hidratacion': {
            'volumen_ml_hora': 500,  # Conservador para evitar sobrehidratación
            'electrolitos': 'Duplicar en días calurosos o si stress Garmin > 60',
            'monitoreo': 'Revisar peso corporal: no perder >2% del peso inicial'
        },
        'entrenamiento_nutricional': {
            'semanas_practica': 12,
            'protocolo': 'En tiradas largas (25-30km), probar geles, bebidas, alimentos sólidos.',
            'objetivo': 'Llegar a competencia con sistema GI probado, sin sorpresas.'
        }
    }


def reglas_especificas_ultramaratón():
    """
    Reglas específicas para ultramaratonista que difieren de maratonista.
    """
    return {
        '1_economia_energetica': {
            'regla': 'El 90% debe ser Z1/Z2. La economía de movimiento es crítica en 12+ horas.',
            'accion': 'Si ACWR > 1.2, reducir series. Priorizar volumen Z2 sobre velocidad.',
            'checkpoint': 'Revisar Pace/HR cada 2 semanas. Si mejora, ir bien; si estanca, añadir fartlek.'
        },
        '2_terreno_variado': {
            'regla': 'Entrenar en trail 50% del volumen. No puede ser solo asfalto.',
            'accion': 'Incluir subidas, bajadas, terreno técnico en entrenamientos. Practicar descensos.',
            'checkpoint': 'GCT > 280ms = riesgo de lesión en descensos. Trabajar técnica.'
        },
        '3_fatiga_acumulada': {
            'regla': 'Respetar descanso 48h después de tiradas >30km.',
            'accion': 'Día siguiente: Regenerativo Z1 o Descanso total.',
            'checkpoint': 'Si HRV cae >15%, detener volumen +5% esa semana.'
        },
        '4_trabajo_mental': {
            'regla': 'Incluir sesiones de visualización y meditación (2x/semana, 10-15 min).',
            'accion': 'Construir narrativa mental positiva para horas 8-12 de fatiga extrema.',
            'checkpoint': 'Evaluación psicológica cada 4 semanas: ¿Confianza en completar? ¿Miedos?'
        },
        '5_lesión_especifica_ultra': {
            'lesion': 'Fricciones / Rozaduras (miles de pasos)',
            'prevencion': 'Usar body glide, cambiar calcetines cada 20km en entrenamientos',
            'monitoreo': 'Revisar pies después de tiradas largas.'
        },
        '6_pacing_estrategico': {
            'regla': 'Ir LENTO y por ritmo cardíaco, no por pace.',
            'accion': 'En competencia: mantener <Z3 las primeras 6 horas, Z2 estricto.',
            'checkpoint': 'Entrenamientos de pacing: correr 20km pensando en un maratón+58km después.'
        }
    }
