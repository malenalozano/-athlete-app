import libsql_experimental as sqlite3
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Variables de conexión a Turso
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

def get_db_connection():
    """Establece una conexión con la base de datos de Turso."""
    return sqlite3.connect(TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)

def init_db():
    """Inicializa la base de datos y crea las tablas base del proyecto."""
    conexion = get_db_connection()
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

    # 4. Tabla de Entrenamientos de Fuerza
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entrenamientos_fuerza (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            ejercicio TEXT,
            peso REAL,
            series INTEGER,
            repeticiones INTEGER,
            grupo_muscular TEXT,
            notas TEXT
        )
    ''')

    conexion.commit()
    conexion.close()

# Ejecutar la creación de la base de datos al importar el módulo
init_db()

if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada correctamente")
