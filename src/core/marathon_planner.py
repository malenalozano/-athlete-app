def resumen_fases_plan(plan):
    """
    Devuelve lista de fases con porcentaje completado y resumen breve.
    """
    fases_resumen = [
        {
            'nombre': 'Acondicionamiento General',
            'resumen': 'Base aeróbica, fuerza glúteo, volumen bajo.'
        },
        {
            'nombre': 'Preparación General',
            'resumen': 'Resistencia y fuerza máxima, volumen medio.'
        },
        {
            'nombre': 'Preparación Específica',
            'resumen': 'Ritmos competición, volumen alto.'
        },
        {
            'nombre': 'Pico de Forma',
            'resumen': 'Tiradas largas, core, volumen máximo.'
        },
        {
            'nombre': 'Tapering y Competición',
            'resumen': 'Descanso, activación, supercompensación.'
        }
    ]
    fases = [f['nombre'] for f in fases_resumen]
    total_semanas = len(plan)
    fases_semanas = {f: 0 for f in fases}
    for semana in plan:
        fases_semanas[semana['fase']] += 1
    # Calcular semanas completadas por fase
    hoy = pd.Timestamp.today()
    semanas_completadas = {f: 0 for f in fases}
    for semana in plan:
        # Suponemos que cada semana tiene un campo 'semana' y empieza desde la actual
        # Si la semana ya pasó, se cuenta como completada
        # (esto se puede ajustar si hay fecha real por semana)
        if semana['semana'] <= (hoy - pd.Timestamp.today().replace(hour=0, minute=0, second=0, microsecond=0)).days // 7 + 1:
            semanas_completadas[semana['fase']] += 1
    # Generar lista de dicts para el widget
    tarjetas = []
    for f in fases_resumen:
        total = fases_semanas[f['nombre']]
        completado = semanas_completadas[f['nombre']]
        porcentaje = int(round(100 * completado / max(total,1)))
        tarjetas.append({
            'fase': f['nombre'],
            'porcentaje': porcentaje,
            'resumen': f['resumen']
        })
    return tarjetas
"""
marathon_planner.py
Lógica de planificación de maratón basada en datos de Garmin.
"""
import pandas as pd
import os
from datetime import datetime

def cargar_historial_garmin(csv_path):
    """
    Carga el historial de actividades desde historial_entrenamientos.csv.
    Si se especifica tipo, filtra por ese tipo; si no, carga todas las actividades.
    """
    def cargar(csv_path, tipo=None):
        df = pd.read_csv(csv_path)
        if 'tipo' not in df.columns:
            raise KeyError("El archivo debe tener la columna 'tipo' para filtrar actividades.")
        if tipo:
            return df[df['tipo'].str.lower() == tipo.lower()]
        return df
    return cargar(csv_path)

def analizar_estado_atleta(df_running):
    """
    Analiza el estado actual del atleta basado en el historial de running.
    Devuelve volumen semanal, tirada larga, frecuencia, etc.
    """
    # Usar columna 'fecha' y 'distancia'
    df_running['fecha'] = pd.to_datetime(df_running['fecha'])
    df_running = df_running.sort_values('fecha')
    df_running['week'] = df_running['fecha'].dt.isocalendar().week
    volumen_semanal = df_running.groupby('week')['distancia'].sum().mean()
    tirada_larga = df_running['distancia'].max()
    frecuencia_semanal = df_running.groupby('week').size().mean()
    return {
        'volumen_semanal': volumen_semanal,
        'tirada_larga': tirada_larga,
        'frecuencia_semanal': frecuencia_semanal
    }

def generar_plan_maraton(estado, semanas=16):
    """
    Genera un plan de entrenamiento para maratón con periodización personalizada.
    """
    # Definición de fases del macrociclo
    fases = [
        {
            'nombre': 'Acondicionamiento General',
            'meses': ['marzo', 'abril', 'mayo'],
            'volumen': (20, 30),
            'fuerza': 'Hipertrofia glúteo. Máximo Volumen: 4 días/semana.',
            'enfoque': 'Curar tibia + Hipertrofia base + Base aeróbica (Z2). Mucha bici/elíptica.'
        },
        {
            'nombre': 'Preparación General',
            'meses': ['junio', 'julio', 'agosto'],
            'volumen': (35, 45),
            'fuerza': 'Fuerza Máxima: Cargas altas, pocas repes.',
            'enfoque': 'Construcción de resistencia y fuerza máxima.'
        },
        {
            'nombre': 'Preparación Específica',
            'meses': ['septiembre', 'octubre', 'noviembre'],
            'volumen': (50, 60),
            'fuerza': 'Mantenimiento: 2-3 días. Menos series, más peso.',
            'enfoque': 'Ritmos de competición (Media Maratón Nov).' 
        },
        {
            'nombre': 'Pico de Forma',
            'meses': ['diciembre', 'enero'],
            'volumen': (60, 75),
            'fuerza': 'Funcional: Foco en core y estabilidad.',
            'enfoque': 'Tiradas largas y ritmos Maratón.'
        },
        {
            'nombre': 'Tapering y Competición',
            'meses': ['febrero'],
            'volumen': (8, 30),  # Descenso drástico (-60%)
            'fuerza': 'Mínimo: Movilidad y activación.',
            'enfoque': 'Supercompensación (GAS).'
        }
    ]
    # Calcular semanas hasta la competición
    fecha_competicion = datetime.strptime('2027-02-21', '%Y-%m-%d')
    hoy = datetime.now()
    semanas_totales = (fecha_competicion - hoy).days // 7
    # Asignar semanas a cada fase según meses
    meses_fase = sum([len(f['meses']) for f in fases])
    semanas_por_mes = semanas_totales / meses_fase
    plan = []
    semana_actual = 1
    for fase in fases:
        semanas_fase = int(round(len(fase['meses']) * semanas_por_mes))
        for s in range(semanas_fase):
            # Progresión dentro de la fase
            min_km, max_km = fase['volumen']
            km_total = round(min_km + (max_km - min_km) * s / max(semanas_fase-1,1))
            semana_plan = {
                'semana': semana_actual,
                'fase': fase['nombre'],
                'enfoque': fase['enfoque'],
                'km_total': km_total,
                'fuerza': fase['fuerza']
            }
            plan.append(semana_plan)
            semana_actual += 1
    return plan

def mostrar_plan(plan):
    """
    Muestra el plan de entrenamiento por pantalla, indicando fase, semana, volumen y fuerza.
    """
    for semana in plan:
        print(f"Semana {semana['semana']} | Fase: {semana['fase']} | {semana['km_total']} km | Fuerza: {semana['fuerza']} | Enfoque: {semana['enfoque']}")

# --- Generadores de entrenamientos base ---
def crear_tirada_larga(distancia_km, fcmax, duracion_min=None):
    return {
        'tipo': 'tirada_larga',
        'zona': 2,
        'fcmax_pct': min(fcmax, 80),
        'distancia_km': distancia_km,
        'duracion_min': duracion_min,
        'descripcion': 'Carrera continua fácil, zona 2, <80% FCmax.'
    }

def crear_tempo(distancia_km, fcmax, duracion_min=None):
    return {
        'tipo': 'tempo',
        'zona': 4,
        'fcmax_pct': min(fcmax, 90),
        'distancia_km': distancia_km,
        'duracion_min': duracion_min,
        'descripcion': 'Carrera a ritmo umbral, zona 4, ~90% FCmax.'
    }

def crear_progresiva(distancia_km, bloques=4, zonas=[1,2,3,4], fcmax=[70,75,85,90]):
    return {
        'tipo': 'progresiva',
        'bloques': bloques,
        'zonas': zonas,
        'fcmax_pct': fcmax,
        'distancia_km': distancia_km,
        'descripcion': 'Carrera progresiva en bloques, de zona 1/2 a zona 4.'
    }

def crear_cambios_ritmo(distancia_km, repeticiones, ritmo_rapido_pct=90, ritmo_lento_pct=70):
    return {
        'tipo': 'cambios_ritmo',
        'repeticiones': repeticiones,
        'ritmo_rapido_pct': ritmo_rapido_pct,
        'ritmo_lento_pct': ritmo_lento_pct,
        'distancia_km': distancia_km,
        'descripcion': 'Carrera alternando ritmos, zona 4 y zona 1/2.'
    }

def crear_intervalos_vo2max(repeticiones, distancia_intervalo_km, fcmax_pct=95, descanso_min=2):
    return {
        'tipo': 'intervalos_vo2max',
        'repeticiones': repeticiones,
        'distancia_intervalo_km': distancia_intervalo_km,
        'fcmax_pct': fcmax_pct,
        'descanso_min': descanso_min,
        'descripcion': 'Intervalos VO2max, >umbral lactato, descanso pasivo.'
    }

def crear_regenerativo(distancia_km, fcmax_pct=70, duracion_min=None):
    return {
        'tipo': 'regenerativo',
        'zona': 1,
        'fcmax_pct': fcmax_pct,
        'distancia_km': distancia_km,
        'duracion_min': duracion_min,
        'descripcion': 'Carrera regenerativa, baja intensidad, <80% FCmax.'
    }

def obtener_fase_macrociclo(fecha_actual=None):
    """
    Devuelve la fase del macrociclo y sus reglas según el mes actual.
    """
    if fecha_actual is None:
        fecha_actual = datetime.now()
    mes_actual = fecha_actual.month
    # 1. ACONDICIONAMIENTO GENERAL (Marzo - Mayo)
    if mes_actual in [3, 4, 5]:
        return {
            "fase_nombre": "Acondicionamiento General",
            "km_semanales_max": 30,
            "dias_fuerza_recomendados": 4,
            "enfoque_fuerza": "Hipertrofia base y curar tibia. Foco en glúteo.",
            "enfoque_running": "Base aeróbica (Z2). Mucha bici/elíptica.",
            "restricciones": {"limitar_impacto": True, "permitir_series_running": False}
        }
    # 2. PREPARACIÓN GENERAL (Junio - Agosto)
    elif mes_actual in [6, 7, 8]:
        return {
            "fase_nombre": "Preparación General",
            "km_semanales_max": 45,
            "dias_fuerza_recomendados": 3,
            "enfoque_fuerza": "Fuerza Máxima: Cargas altas, pocas repeticiones.",
            "enfoque_running": "Construcción de resistencia.",
            "restricciones": {"limitar_impacto": False, "permitir_series_running": True}
        }
    # 3. PREPARACIÓN ESPECÍFICA (Septiembre - Noviembre)
    elif mes_actual in [9, 10, 11]:
        return {
            "fase_nombre": "Preparación Específica",
            "km_semanales_max": 60,
            "dias_fuerza_recomendados": 2,
            "enfoque_fuerza": "Mantenimiento: Bajar nº de ejercicios/series, mantener peso.",
            "enfoque_running": "Ritmos competición (Media Maratón Nov).",
            "restricciones": {"limitar_impacto": False, "permitir_series_running": True}
        }
    # 4. PICO DE FORMA (Diciembre - Enero)
    elif mes_actual in [12, 1]:
        return {
            "fase_nombre": "Pico de Forma",
            "km_semanales_max": 75,
            "dias_fuerza_recomendados": 2,
            "enfoque_fuerza": "Funcional: Foco en core y estabilidad.",
            "enfoque_running": "Tiradas largas y ritmos Maratón.",
            "restricciones": {"limitar_impacto": False, "permitir_series_running": True}
        }
    # 5. TAPERING Y COMPETICIÓN (Febrero)
    elif mes_actual == 2:
        return {
            "fase_nombre": "Tapering y Competición",
            "km_semanales_max": 30, # Descenso drástico
            "dias_fuerza_recomendados": 1,
            "enfoque_fuerza": "Mínimo: Movilidad y activación.",
            "enfoque_running": "Supercompensación (GAS). Mínima fatiga.",
            "restricciones": {"limitar_impacto": True, "permitir_series_running": False}
        }
    else:
        return {
            "fase_nombre": "Desconocida",
            "km_semanales_max": 0,
            "dias_fuerza_recomendados": 0,
            "enfoque_fuerza": "",
            "enfoque_running": "",
            "restricciones": {}
        }

# Cada función puede ser adaptada según los factores individuales del atleta.

# Ejemplo de uso:
if __name__ == "__main__":
    csv_path = os.path.join('data', 'actividad.csv')
    df_running = cargar_historial_garmin(csv_path)
    estado = analizar_estado_atleta(df_running)
    plan = generar_plan_maraton(estado)
    mostrar_plan(plan)

def evaluar_cadencia_y_recomendar(df_actividades):
    """
    Recorre las actividades y aplica reglas:
    - Si cadencia < 170 spm: añade recomendación de técnica de carrera.
    - Si cadencia > 175 spm: añade mensaje de excelencia para reporte semanal.
    Devuelve lista de recomendaciones y mensajes.
    """
    recomendaciones = []
    mensajes = []
    for idx, row in df_actividades.iterrows():
        cadencia = row.get('cadencia_media')
        if cadencia is None:
            continue
        if cadencia < 170:
            recomendaciones.append({
                'fecha': row.get('fecha'),
                'tipo': row.get('tipo'),
                'recomendacion': "Añadir 5' de técnica de carrera antes del rodaje"
            })
        elif cadencia > 175:
            mensajes.append({
                'fecha': row.get('fecha'),
                'mensaje': '¡Excelente cadencia!'
            })
    return recomendaciones, mensajes

def generar_reporte_semanal(df_actividades, semana, estado, fase):
    """
    Genera un resumen semanal con recomendaciones y mensajes.
    Incluye análisis de cadencia y otros indicadores clave.
    """
    # Filtrar actividades de la semana
    df_semana = df_actividades[df_actividades['week'] == semana]
    volumen = df_semana['distancia'].sum()
    tirada_larga = df_semana['distancia'].max()
    sesiones_fuerza = df_semana[df_semana['tipo'].str.lower() == 'fuerza'].shape[0]
    recomendaciones, mensajes = evaluar_cadencia_y_recomendar(df_semana)
    return {
        'volumen_total': volumen,
        'tirada_larga': tirada_larga,
        'sesiones_fuerza': sesiones_fuerza,
        'recomendaciones': recomendaciones,
        'mensajes': mensajes,
        'fase': fase,
        'estado': estado
    }

def adaptar_entrenamiento_por_recuperacion(entrenamiento, hrv_estado, puntuacion_sueno):
    """
    Modifica el entrenamiento según el estado de recuperación (HRV y sueño).
    Devuelve el entrenamiento adaptado y un mensaje para el reporte semanal.
    Estados:
    - VERDE: HRV ok y sueño >85 -> sin cambios
    - ÁMBAR: sueño 60-80 -> no subir pesos, reducir series -20%
    - ROJO: HRV cae >10% o sueño <60 -> todo regenerativo o descanso/movilidad
    """
    mensaje = ""
    entrenamiento_adaptado = entrenamiento.copy()
    if hrv_estado == 'verde' and puntuacion_sueno > 85:
        mensaje = "Recuperación óptima: se mantiene el plan sin cambios."
    elif hrv_estado == 'ambar' or (60 <= puntuacion_sueno <= 80):
        if entrenamiento_adaptado.get('tipo') == 'fuerza':
            entrenamiento_adaptado['subir_pesos'] = False
            mensaje = "Sueño subóptimo: no subir pesos en fuerza, mantener cargas."
        if entrenamiento_adaptado.get('tipo') in ['tempo', 'progresiva', 'cambios_ritmo', 'intervalos_vo2max']:
            entrenamiento_adaptado['series'] = max(1, int(entrenamiento_adaptado.get('series', 1) * 0.8))
            mensaje = "Sueño subóptimo: reducir series en carrera un 20%."
    elif hrv_estado == 'rojo' or puntuacion_sueno < 60:
        entrenamiento_adaptado['tipo'] = 'regenerativo'
        entrenamiento_adaptado['zona'] = 1
        mensaje = "Recuperación insuficiente: cambiar calidad por regenerativo (Z1), descanso o movilidad."
    else:
        mensaje = "Recuperación no evaluada: mantener plan base."
    return entrenamiento_adaptado, mensaje

def controlar_distribucion_intensidad(entrenamientos):
    """
    Ajusta la distribución de intensidad semanal:
    - 80% baja intensidad (Z1/Z2)
    - 20% alta intensidad (Z3+)
    Devuelve lista de entrenamientos ajustados y mensaje para el reporte.
    """
    total = len(entrenamientos)
    baja = [e for e in entrenamientos if e.get('zona') in [1,2]]
    alta = [e for e in entrenamientos if e.get('zona') in [3,4]]
    baja_pct = 100 * len(baja) / max(total,1)
    alta_pct = 100 * len(alta) / max(total,1)
    mensaje = f"Distribución semanal: {baja_pct:.0f}% baja intensidad, {alta_pct:.0f}% alta intensidad."
    # Si la proporción no cumple, sugerir ajuste
    if baja_pct < 80:
        mensaje += " | Recomendación: aumentar sesiones de baja intensidad."
    if alta_pct > 20:
        mensaje += " | Recomendación: reducir sesiones de alta intensidad."
    return entrenamientos, mensaje

def aplicar_regla_10pct(volumen_actual, volumen_prev, lesion_activa=False, acwr=None):
    """
    Aplica la regla del 10% para el volumen semanal:
    - El volumen actual no puede superar el 110% del volumen previo.
    - Si hay lesión activa o ACWR > 1.3, el incremento se bloquea al 0%.
    Devuelve el volumen ajustado y mensaje para el reporte.
    """
    mensaje = ""
    if lesion_activa or (acwr is not None and acwr > 1.3):
        volumen_ajustado = volumen_prev
        mensaje = "Incremento de volumen bloqueado por lesión activa o ACWR > 1.3."
    else:
        max_volumen = volumen_prev * 1.10
        if volumen_actual > max_volumen:
            volumen_ajustado = max_volumen
            mensaje = f"Volumen ajustado por regla del 10%: {volumen_ajustado:.1f} km (máx 110% semana anterior)."
        else:
            volumen_ajustado = volumen_actual
            mensaje = "Volumen dentro de rango seguro (regla del 10%)."
    return volumen_ajustado, mensaje

def evaluar_eficiencia_aerobica(df_actividades, fecha_actual=None):
    """
    Evalúa la eficiencia aeróbica (ritmo/pulsaciones) en entrenamientos de zona 2.
    - Cada 15 días compara la métrica Pace/HR.
    - Si no mejora en 30 días, recomienda añadir más Fartleks.
    Devuelve mensaje para el reporte y recomendación.
    """
    import pandas as pd
    if fecha_actual is None:
        fecha_actual = pd.Timestamp.today()
    df_z2 = df_actividades[df_actividades['zona'] == 2]
    df_z2['fecha'] = pd.to_datetime(df_z2['fecha'])
    df_z2 = df_z2.sort_values('fecha')
    # Filtrar últimos 30 días
    fecha_inicio = fecha_actual - pd.Timedelta(days=30)
    df_mes = df_z2[df_z2['fecha'] >= fecha_inicio]
    # Calcular eficiencia Pace/HR para cada sesión
    df_mes['eficiencia'] = df_mes['ritmo_min_km'] / df_mes['fc_media']
    # Cada 15 días
    fecha_15 = fecha_actual - pd.Timedelta(days=15)
    df_15 = df_mes[df_mes['fecha'] >= fecha_15]
    eficiencia_30 = df_mes['eficiencia'].mean() if not df_mes.empty else None
    eficiencia_15 = df_15['eficiencia'].mean() if not df_15.empty else None
    mensaje = ""
    recomendacion = None
    if eficiencia_30 is not None and eficiencia_15 is not None:
        if eficiencia_15 >= eficiencia_30:
            mensaje = f"Eficiencia aeróbica estancada ({eficiencia_15:.3f}). Se recomienda añadir más Fartleks para romper la meseta."
            recomendacion = 'añadir_fartlek'
        else:
            mensaje = f"Eficiencia aeróbica mejorando ({eficiencia_15:.3f} vs {eficiencia_30:.3f})."
    else:
        mensaje = "No hay suficientes datos de zona 2 para evaluar eficiencia aeróbica."
    return mensaje, recomendacion

def verificar_orden_entrenamiento_concurrente(df_actividades):
    """
    Revisa la hora de inicio de actividades de Fuerza y Carrera el mismo día.
    - Si ambas se programan el mismo día, Fuerza debe ir primero o estar separadas por mínimo 6h.
    Devuelve mensaje para el reporte y recomendaciones.
    """
    import pandas as pd
    df_actividades['fecha'] = pd.to_datetime(df_actividades['fecha'])
    df_actividades['hora'] = pd.to_datetime(df_actividades['hora'], errors='coerce').dt.time
    mensajes = []
    dias = df_actividades['fecha'].dt.date.unique()
    for dia in dias:
        df_dia = df_actividades[df_actividades['fecha'].dt.date == dia]
        fuerza = df_dia[df_dia['tipo'].str.lower() == 'fuerza']
        carrera = df_dia[df_dia['tipo'].str.lower().isin(['running','carrera'])]
        if not fuerza.empty and not carrera.empty:
            hora_fuerza = fuerza['hora'].min()
            hora_carrera = carrera['hora'].min()
            if hora_fuerza and hora_carrera:
                h_f = pd.to_datetime(str(hora_fuerza)).hour
                h_c = pd.to_datetime(str(hora_carrera)).hour
                diff = abs(h_c - h_f)
                if h_f > h_c or diff < 6:
                    mensajes.append(f"Día {dia}: Fuerza y carrera el mismo día. Recomendación: Fuerza primero o separar mínimo 6h y nutrición.")
    if not mensajes:
        mensajes.append("Entrenamiento concurrente correctamente ordenado toda la semana.")
    return mensajes
