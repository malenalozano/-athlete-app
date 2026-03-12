import libsql as sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("TURSO_DATABASE_URL")
TOKEN = os.getenv("TURSO_AUTH_TOKEN")

def get_db_connection():
    return sqlite3.connect(URL, auth_token=TOKEN)

def init_db():
    conn = get_db_connection()
    # Tabla Usuarios
    conn.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, email_garmin TEXT, password_garmin TEXT, rol TEXT)")
    # Tabla Garmin
    conn.execute("CREATE TABLE IF NOT EXISTS actividades_garmin (id_actividad TEXT PRIMARY KEY, usuario_id INTEGER, fecha TEXT, tipo_deporte TEXT, distancia_m REAL, tiempo_seg REAL, ritmo_medio REAL, fc_media INTEGER, fc_max INTEGER)")
    # Tabla Fisio
    conn.execute("CREATE TABLE IF NOT EXISTS diario_fisiologia (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, fecha TEXT, fase_ciclo TEXT, fatiga_subjetiva INTEGER, dolor_notas TEXT)")
    # Tabla Fuerza (Corregida con todas las columnas)
    conn.execute('''CREATE TABLE IF NOT EXISTS entrenamientos_fuerza (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, ejercicio TEXT, peso REAL, 
        series INTEGER, repeticiones INTEGER, grupo_muscular TEXT, rpe INTEGER, 
        musculo_principal TEXT, notas TEXT)''')
    conn.commit()
    conn.close()

init_db()
