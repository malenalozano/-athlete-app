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
    from datetime import datetime, timedelta
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

# Ejemplo de uso:
if __name__ == "__main__":
    csv_path = os.path.join('data', 'actividad.csv')
    df_running = cargar_historial_garmin(csv_path)
    estado = analizar_estado_atleta(df_running)
    plan = generar_plan_maraton(estado)
    mostrar_plan(plan)
