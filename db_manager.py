import sqlite3
import os
from dotenv import load_dotenv

# Cargar variables de entorno (preparando para Turso en el futuro)
load_dotenv()

# Ruta de la base de datos
DB_PATH = os.getenv("DB_PATH", "atleta.db")

def init_db():
    """Inicializa la base de datos y crea las tablas base del proyecto."""
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()

    # 1. Tabla de Usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            email_garmin TEXT,
            password_garmin TEXT,
            rol TEXT
        )
    ''')

    # 2. Tabla de Actividades Garmin
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS actividades_garmin (
            id_actividad TEXT PRIMARY KEY,
            usuario_id INTEGER,
            fecha TEXT,
            tipo_deporte TEXT,
            distancia_m REAL,
            tiempo_seg REAL,
            ritmo_medio REAL,
            fc_media INTEGER,
            fc_max INTEGER
        )
    ''')

    # 3. Tabla Diario Fisiología (Foco Femenino y Salud)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diario_fisiologia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            fecha TEXT,
            fase_ciclo TEXT,
            fatiga_subjetiva INTEGER,
            dolor_notas TEXT
        )
    ''')

    conexion.commit()
    conexion.close()

if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada correctamente")
