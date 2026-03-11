"""
Este software está diseñado bajo una perspectiva de fisiología femenina.
"""

import sqlite3
import csv
from datetime import datetime, timedelta

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
        genero = input("Por favor, introduce tu género (hombre/mujer): ").strip().lower()
        fase_ciclo = None
        if genero == "mujer":
            fecha_ultima_regla = input("Introduce la fecha de tu última regla (YYYY-MM-DD): ").strip()
            duracion_ciclo = int(input("Introduce la duración media de tu ciclo en días (por defecto 28): ") or 28)
            fase_ciclo = calcular_fase_ciclo(fecha_ultima_regla, duracion_ciclo)

        if km[0] > 10:
            ajustar_consejo_nutricional(km[0], genero, fase_ciclo)
        elif genero == "hombre" and km[0] > 100:
            print("Has realizado un esfuerzo extremo. Prioriza alimentos ricos en proteínas y carbohidratos para una recuperación óptima.")

    connection.commit()
    connection.close()

# Crear tabla para usuarios
def crear_tabla_usuarios(db_path="atleta.db"):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            genero TEXT NOT NULL,
            objetivo TEXT
        )
    ''')

    connection.commit()
    connection.close()

# Insertar usuarios en la tabla
def insertar_usuario(nombre, genero, objetivo, db_path="atleta.db"):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Verificar si el usuario ya existe
    cursor.execute('''
        SELECT * FROM usuarios WHERE nombre = ? AND genero = ? AND objetivo = ?
    ''', (nombre, genero, objetivo))
    usuario_existente = cursor.fetchone()

    if not usuario_existente:
        cursor.execute('''
            INSERT INTO usuarios (nombre, genero, objetivo)
            VALUES (?, ?, ?)
        ''', (nombre, genero, objetivo))
        print(f"Usuario '{nombre}' insertado correctamente.")
    else:
        print(f"El usuario '{nombre}' ya existe en la base de datos.")

    connection.commit()
    connection.close()
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            genero TEXT NOT NULL,
            objetivo TEXT
        )
    ''')

    connection.commit()
    connection.close()

# Crear tabla para entrenamientos de fuerza
def crear_tabla_fuerza(db_path="atleta.db"):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entrenamientos_fuerza (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            ejercicio TEXT,
            series INTEGER,
            repeticiones INTEGER,
            peso REAL
        )
    ''')

    connection.commit()
    connection.close()

# Crear tabla para entrenamientos de fuerza
def crear_tabla_fuerza(db_path="atleta.db"):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entrenamientos_fuerza (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            ejercicio TEXT,
            series INTEGER,
            repeticiones INTEGER,
            peso REAL
        )
    ''')

    connection.commit()
    connection.close()

# Calcular fase del ciclo menstrual
def calcular_fase_ciclo(fecha_ultima_regla, duracion_ciclo=28):
    if isinstance(fecha_ultima_regla, str):
        fecha_ultima = datetime.strptime(fecha_ultima_regla, "%Y-%m-%d")
    else:
        fecha_ultima = fecha_ultima_regla
    hoy = datetime.now()
    dias_desde_ultima = (hoy - fecha_ultima).days
    dia_ciclo = dias_desde_ultima % duracion_ciclo

    if dia_ciclo <= 13:
        return "Fase Folicular"
    elif 14 <= dia_ciclo <= 16:
        return "Fase Ovulatoria"
    else:
        return "Fase Lútea"

# Ajustar consejo nutricional según género y fase del ciclo
def ajustar_consejo_nutricional(km, genero, fase_ciclo=None):
    if genero.lower() == "mujer":
        if fase_ciclo == "Fase Lútea":
            return "Has realizado un gran esfuerzo. Prioriza carbohidratos de calidad en tu próxima comida para apoyar tu salud hormonal."
        else:
            return "Has realizado un gran esfuerzo. Asegúrate de consumir una comida balanceada con carbohidratos y proteínas."
    else:
        return "Has realizado un gran esfuerzo. Considera alimentos con baja carga glucémica para optimizar tu recuperación."

# Código para ejecutar la importación y mostrar el tiempo estimado de maratón
if __name__ == "__main__":
    # Preparación para Streamlit: En el futuro, estas funciones pueden ser llamadas desde una interfaz gráfica.
    ruta_csv = "actividad.csv"
    crear_tabla_fuerza()
    crear_tabla_usuarios()

    # Insertar perfiles iniciales
    insertar_usuario("Malena", "Mujer", "Maraton < 5min/km")
    insertar_usuario("Dani", "Hombre", "Ultra 100km")
    print("Base de datos y tablas inicializadas correctamente.")
    importar_csv_garmin(ruta_csv)
    print("Tiempo estimado para completar un maratón:", calcular_tiempo_maraton())
