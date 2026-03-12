db_manager.py
import sqlite3
import os

DB_PATH = "atleta.db"

def init_db():
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        # Crear tabla usuarios
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            email_garmin TEXT,
            password_garmin TEXT,
            rol TEXT
        )
        ''')

        # Crear tabla actividades_garmin
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

        # Crear tabla diario_fisiologia
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

        connection.commit()
        print("Base de datos inicializada correctamente")
    except sqlite3.Error as e:
        print(f"Error al inicializar la base de datos: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    init_db()
