"""
Este software está diseñado bajo una perspectiva de fisiología femenina.
"""

import sqlite3
import csv

# Función para calcular el tiempo de maratón basado en un ritmo objetivo de 5:00 min/km
def calcular_tiempo_maraton():
    ritmo_objetivo_minutos = 5
    ritmo_objetivo_segundos = 0
    distancia_maraton_km = 42.195

    total_segundos_por_km = ritmo_objetivo_minutos * 60 + ritmo_objetivo_segundos
    tiempo_total_segundos = total_segundos_por_km * distancia_maraton_km

    horas = tiempo_total_segundos // 3600
    minutos = (tiempo_total_segundos % 3600) // 60
    segundos = tiempo_total_segundos % 60

    return f"{int(horas):02}:{int(minutos):02}:{int(segundos):02}"

# Función para importar un archivo CSV de Garmin
def importar_csv_garmin(ruta_csv, db_path="atleta.db"):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Crear tabla si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS datos_garmin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            pulsaciones_media INTEGER,
            km_recorridos REAL
        )
    ''')

    # Leer e insertar datos del CSV
    import os

    if not os.path.exists(ruta_csv):
        print(f"Error: El archivo {ruta_csv} no existe. Asegúrate de que el archivo esté en el directorio actual.")
        return

    with open(ruta_csv, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            cursor.execute('''
                INSERT INTO datos_garmin (fecha, pulsaciones_media, km_recorridos)
                VALUES (?, ?, ?)
            ''', (row['Fecha'], int(row['Pulsaciones Media']), float(row['KM recorridos'])))

    # Analizar los KM recorridos y proporcionar un consejo nutricional
    cursor.execute("SELECT km_recorridos FROM datos_garmin")
    km_recorridos = cursor.fetchall()

    for km in km_recorridos:
        if km[0] > 10:
            print("Has realizado un gran esfuerzo. Tu cuerpo necesita energía para recuperarse y proteger tu salud hormonal; prioriza carbohidratos de calidad en tu próxima comida sin contar calorías.")

    connection.commit()
    connection.close()

# Código para ejecutar la importación y mostrar el tiempo estimado de maratón
if __name__ == "__main__":
    ruta_csv = "actividad.csv"
    importar_csv_garmin(ruta_csv)
    print("Tiempo estimado para completar un maratón:", calcular_tiempo_maraton())
