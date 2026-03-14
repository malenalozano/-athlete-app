import sqlite3
import os
from dotenv import load_dotenv

try:
    import libsql as libsql_sqlite3
except Exception:
    libsql_sqlite3 = None

load_dotenv()
URL = os.getenv("TURSO_DATABASE_URL")
TOKEN = os.getenv("TURSO_AUTH_TOKEN")
LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", "atleta.db")


def get_db_connection():
    # Prefer Turso when URL is available; otherwise use local SQLite file.
    if URL and libsql_sqlite3 is not None:
        return libsql_sqlite3.connect(URL, auth_token=TOKEN)
    return sqlite3.connect(LOCAL_DB_PATH)


def _column_exists(conn, table_name, column_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def _ensure_column(conn, table_name, column_name, column_type):
    if not _column_exists(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def init_db():
    conn = get_db_connection()
    # Tabla Usuarios
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            edad INTEGER,
            genero TEXT,
            peso REAL,
            objetivo TEXT,
            carrera INTEGER,
            fuerza INTEGER,
            nivel TEXT,
            ritmo TEXT,
            email_garmin TEXT,
            password_garmin TEXT,
            password_garmin_enc TEXT,
            rol TEXT
        )
        """
    )

    # Migraciones ligeras para bases creadas con esquemas previos.
    _ensure_column(conn, "usuarios", "edad", "INTEGER")
    _ensure_column(conn, "usuarios", "genero", "TEXT")
    _ensure_column(conn, "usuarios", "peso", "REAL")
    _ensure_column(conn, "usuarios", "objetivo", "TEXT")
    _ensure_column(conn, "usuarios", "carrera", "INTEGER")
    _ensure_column(conn, "usuarios", "fuerza", "INTEGER")
    _ensure_column(conn, "usuarios", "nivel", "TEXT")
    _ensure_column(conn, "usuarios", "ritmo", "TEXT")
    _ensure_column(conn, "usuarios", "password_garmin_enc", "TEXT")

    # Tabla Garmin
    conn.execute("CREATE TABLE IF NOT EXISTS actividades_garmin (id_actividad TEXT PRIMARY KEY, usuario_id INTEGER, fecha TEXT, tipo_deporte TEXT, distancia_m REAL, tiempo_seg REAL, ritmo_medio REAL, fc_media INTEGER, fc_max INTEGER)")
    # Tabla Fisio
    conn.execute("CREATE TABLE IF NOT EXISTS diario_fisiologia (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, fecha TEXT, fase_ciclo TEXT, fatiga_subjetiva INTEGER, dolor_notas TEXT)")
    _ensure_column(conn, "diario_fisiologia", "sangre", "TEXT")
    _ensure_column(conn, "diario_fisiologia", "sintomas", "TEXT")
    _ensure_column(conn, "diario_fisiologia", "estado_animo", "TEXT")
    _ensure_column(conn, "diario_fisiologia", "feedback_entreno", "TEXT")
    # Tabla Fuerza (Corregida con todas las columnas)
    conn.execute('''CREATE TABLE IF NOT EXISTS entrenamientos_fuerza (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, ejercicio TEXT, peso REAL, 
        series INTEGER, repeticiones INTEGER, grupo_muscular TEXT, rpe INTEGER, 
        musculo_principal TEXT, notas TEXT)''')
    conn.commit()
    conn.close()


def obtener_perfil(usuario_id):
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT id, nombre, edad, genero, peso, objetivo, carrera, fuerza, nivel, ritmo,
               email_garmin, password_garmin_enc
        FROM usuarios
        WHERE id = ?
        """,
        (usuario_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "nombre": row[1],
        "edad": row[2],
        "genero": row[3],
        "peso": row[4],
        "objetivo": row[5],
        "carrera": row[6],
        "fuerza": row[7],
        "nivel": row[8],
        "ritmo": row[9],
        "email_garmin": row[10],
        "password_garmin_enc": row[11],
    }


def guardar_perfil(usuario_id, datos):
    conn = get_db_connection()

    existente = conn.execute("SELECT id FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    params = (
        datos.get("nombre"),
        datos.get("edad"),
        datos.get("genero"),
        datos.get("peso"),
        datos.get("objetivo"),
        datos.get("carrera"),
        datos.get("fuerza"),
        datos.get("nivel"),
        datos.get("ritmo"),
        usuario_id,
    )

    if existente:
        conn.execute(
            """
            UPDATE usuarios
            SET nombre = ?, edad = ?, genero = ?, peso = ?, objetivo = ?,
                carrera = ?, fuerza = ?, nivel = ?, ritmo = ?
            WHERE id = ?
            """,
            params,
        )
    else:
        conn.execute(
            """
            INSERT INTO usuarios
            (nombre, edad, genero, peso, objetivo, carrera, fuerza, nivel, ritmo, id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            params,
        )

    conn.commit()
    conn.close()


def obtener_credenciales_garmin(usuario_id):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT email_garmin, password_garmin_enc FROM usuarios WHERE id = ?",
        (usuario_id,),
    ).fetchone()
    conn.close()
    return row


init_db()
