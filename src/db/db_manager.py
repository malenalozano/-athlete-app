import sqlite3
import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

try:
    import streamlit as st
except Exception:
    st = None

load_dotenv()


def _get_setting(name, default=None):
    value = os.getenv(name)
    if value:
        return value
    if st is not None:
        try:
            return st.secrets.get(name, default)
        except Exception:
            pass
    return default


URL = _get_setting("TURSO_DATABASE_URL")
TOKEN = _get_setting("TURSO_AUTH_TOKEN")
LOCAL_DB_PATH = _get_setting("LOCAL_DB_PATH", "atleta.db")

# ---------------------------------------------------------------------------
# Turso HTTP connection wrapper (DBAPI2-compatible subset)
# ---------------------------------------------------------------------------

def _escape_val(v):
    """Inline-escape a Python value for SQLite."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def _bind_params(sql: str, params) -> str:
    """Replace ? placeholders with escaped values."""
    if not params:
        return sql
    parts = sql.split("?")
    if len(parts) != len(params) + 1:
        raise ValueError(f"SQL has {len(parts)-1} placeholders but {len(params)} params")
    result = parts[0]
    for val, tail in zip(params, parts[1:]):
        result += _escape_val(val) + tail
    return result


class _TursoCursor:
    def __init__(self, conn: "TursoHTTPConnection"):
        self._conn = conn
        self.description = None
        self._rows = []
        self._pos = 0
        self.rowcount = -1

    def execute(self, sql, params=()):
        sql_bound = _bind_params(sql, params)
        result = self._conn._send([sql_bound])
        r = result[0]
        if r.get("type") == "error":
            raise sqlite3.OperationalError(r.get("error", {}).get("message", "Turso error"))
        resp = r.get("response", {}).get("result", {})
        cols = resp.get("cols", [])
        if cols:
            self.description = [(c["name"], None, None, None, None, None, None) for c in cols]
        else:
            self.description = None
        raw_rows = resp.get("rows", [])
        self._rows = []
        for cell_row in raw_rows:
            row = []
            for cell in cell_row:
                t = cell.get("type", "null")
                if t == "null":
                    row.append(None)
                elif t == "integer":
                    row.append(int(cell["value"]))
                elif t == "float":
                    row.append(float(cell["value"]))
                else:
                    row.append(cell.get("value"))
            self._rows.append(tuple(row))
        self._pos = 0
        self.rowcount = resp.get("affected_row_count", len(self._rows))
        return self

    def fetchone(self):
        if self._pos >= len(self._rows):
            return None
        row = self._rows[self._pos]
        self._pos += 1
        return row

    def fetchall(self):
        rows = self._rows[self._pos:]
        self._pos = len(self._rows)
        return rows

    def fetchmany(self, size=1):
        rows = self._rows[self._pos:self._pos + size]
        self._pos += len(rows)
        return rows

    def __iter__(self):
        return iter(self._rows)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TursoHTTPConnection:
    """Minimal DBAPI2-compatible wrapper over Turso v2 HTTP pipeline API."""

    def __init__(self, url: str, token: str):
        self._url = url.replace("libsql://", "https://")
        self._token = token
        self._pipeline_url = f"{self._url}/v2/pipeline"

    def _send(self, sql_statements: list[str]) -> list[dict]:
        requests = [{"type": "execute", "stmt": {"sql": s}} for s in sql_statements]
        requests.append({"type": "close"})
        payload = json.dumps({"requests": requests}).encode("utf-8")
        req = urllib.request.Request(
            self._pipeline_url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data.get("results", [])
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise sqlite3.OperationalError(f"Turso HTTP {e.code}: {body[:300]}")

    def cursor(self):
        return _TursoCursor(self)

    def execute(self, sql, params=()):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        pass  # Turso auto-commits each statement

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def get_db_connection():
    """Return a Turso connection when URL is set, else local SQLite."""
    if URL and TOKEN:
        return TursoHTTPConnection(URL, TOKEN)
    conn = sqlite3.connect(LOCAL_DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


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
    _ensure_column(conn, "usuarios", "fecha_objetivo", "TEXT")   # fecha de la carrera objetivo (YYYY-MM-DD)
    _ensure_column(conn, "usuarios", "objetivo_tipo", "TEXT")    # 'maraton', 'ultramaraton', 'trail', etc.

    # Sembrar perfiles por defecto (INSERT OR IGNORE preserva datos existentes)
    conn.execute(
        """
        INSERT OR IGNORE INTO usuarios
            (id, nombre, edad, genero, peso, objetivo, carrera, fuerza, nivel, ritmo,
             fecha_objetivo, objetivo_tipo)
        VALUES (1, 'Malena', 22, 'Mujer', 58.0,
                'Maratón Sub 3:30 — 21 Feb 2027', 1, 1, 'Intermedio', '5:30',
                '2027-02-21', 'maraton')
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO usuarios
            (id, nombre, edad, genero, peso, objetivo, carrera, fuerza, nivel, ritmo,
             fecha_objetivo, objetivo_tipo)
        VALUES (2, 'Dani', 26, 'Hombre', 72.0,
                'Ultramaratón 100km — Sep 2026', 1, 1, 'Intermedio', '5:00',
                '2026-09-19', 'ultramaraton')
        """
    )

    # Tabla de ejercicios por defecto (personalizados por usuario)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ejercicios_por_defecto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            ejercicio TEXT,
            grupo_muscular TEXT,
            musculo_principal TEXT
        )''')

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
        id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, fecha TEXT, ejercicio TEXT,
        peso REAL, series INTEGER, repeticiones INTEGER, grupo_muscular TEXT, rpe INTEGER,
        musculo_principal TEXT, notas TEXT)''')
    _ensure_column(conn, "entrenamientos_fuerza", "usuario_id", "INTEGER")
    conn.commit()
    conn.close()


def obtener_perfil(usuario_id):
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT id, nombre, edad, genero, peso, objetivo, carrera, fuerza, nivel, ritmo,
               email_garmin, password_garmin_enc, fecha_objetivo, objetivo_tipo
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
        "fecha_objetivo": row[12],   # YYYY-MM-DD de la carrera objetivo
        "objetivo_tipo": row[13],    # 'maraton', 'ultramaraton', etc.
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
        datos.get("fecha_objetivo"),
        datos.get("objetivo_tipo"),
        usuario_id,
    )

    if existente:
        conn.execute(
            """
            UPDATE usuarios
            SET nombre = ?, edad = ?, genero = ?, peso = ?, objetivo = ?,
                carrera = ?, fuerza = ?, nivel = ?, ritmo = ?,
                fecha_objetivo = ?, objetivo_tipo = ?
            WHERE id = ?
            """,
            params,
        )
    else:
        conn.execute(
            """
            INSERT INTO usuarios
            (nombre, edad, genero, peso, objetivo, carrera, fuerza, nivel, ritmo,
             fecha_objetivo, objetivo_tipo, id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def asegurar_tabla_plan_entrenamiento():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS plan_entrenamiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            semana_inicio TEXT,
            fecha TEXT,
            tipo TEXT,
            sesion TEXT,
            detalles TEXT,
            duracion_min INTEGER,
            intensidad TEXT,
            creado_en TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def asegurar_tablas_fuerza():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sesiones_fuerza (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            fecha TEXT,
            nota_original TEXT,
            resumen TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ejercicios_fuerza (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id INTEGER,
            ejercicio TEXT,
            peso REAL,
            series INTEGER,
            repeticiones INTEGER,
            grupo_muscular TEXT,
            musculo_principal TEXT,
            rpe INTEGER
        )
        """
    )
    _ensure_column(conn, "ejercicios_fuerza", "sensaciones", "TEXT")
    _ensure_column(conn, "sesiones_fuerza", "tipo_registro", "TEXT")
    _ensure_column(conn, "sesiones_fuerza", "actividad_garmin_id", "TEXT")
    _ensure_column(conn, "sesiones_fuerza", "nota_estado", "TEXT")
    _ensure_column(conn, "sesiones_fuerza", "lesion_flag", "INTEGER")
    conn.commit()
    conn.close()


def asegurar_tablas_premium():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS datos_biometricos_premium (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            fecha TEXT,
            hrv_ms REAL,
            fc_reposo INTEGER,
            fc_maxima INTEGER,
            cadencia_media REAL,
            longitud_zancada_m REAL,
            tiempo_contacto_ms REAL,
            oscilacion_vertical_cm REAL,
            sleep_score INTEGER,
            carga_aguda REAL,
            carga_cronica REAL,
            estres_vital INTEGER,
            rpe_sesion INTEGER,
            sensacion_notas TEXT,
            disponibilidad_min INTEGER,
            UNIQUE(usuario_id, fecha)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS historial_lesiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            fecha_inicio TEXT,
            zona TEXT,
            tipo TEXT,
            activa INTEGER DEFAULT 1,
            notas TEXT,
            fecha_fin TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS estudios_referencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            titulo TEXT,
            categoria TEXT,
            archivo_path TEXT,
            resumen TEXT,
            texto_extraido TEXT,
            creado_en TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS datos_sueno (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            fecha TEXT,
            horas_totales REAL,
            score INTEGER,
            UNIQUE(usuario_id, fecha)
        )
        """
    )
    for col_name, col_type in [
        ("training_readiness", "INTEGER"),
        ("body_battery", "INTEGER"),
        ("body_battery_min", "INTEGER"),
        ("body_battery_max", "INTEGER"),
        ("estres_medio", "REAL"),
        ("recovery_hours", "REAL"),
        ("spo2", "REAL"),
        ("potencia_media_w", "REAL"),
    ]:
        _ensure_column(conn, "datos_biometricos_premium", col_name, col_type)

    for col_name, col_type in [
        ("sleep_profundo_horas", "REAL"),
        ("sleep_rem_horas", "REAL"),
        ("sleep_vigilia_horas", "REAL"),
        ("despertares", "INTEGER"),
    ]:
        _ensure_column(conn, "datos_sueno", col_name, col_type)

    for col_name, col_type in [
        ("potencia_media_w", "REAL"),
        ("cadencia_media", "REAL"),
        ("longitud_zancada_m", "REAL"),
        ("tiempo_contacto_ms", "REAL"),
        ("oscilacion_vertical_cm", "REAL"),
    ]:
        _ensure_column(conn, "actividades_garmin", col_name, col_type)

    conn.commit()
    conn.close()


def asegurar_tabla_ejercicios(usuario_id: int = 1):
    """Crea ejercicios_biblioteca + historial_ejercicio y siembra ejercicios por defecto."""
    from src.db.models import CREATE_EJERCICIOS_BIBLIOTECA, CREATE_HISTORIAL_EJERCICIO
    import json
    from datetime import datetime

    conn = get_db_connection()
    conn.execute(CREATE_EJERCICIOS_BIBLIOTECA)
    conn.execute(CREATE_HISTORIAL_EJERCICIO)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hist_ej_usuario ON historial_ejercicio(ejercicio_id, usuario_id, fecha)")

    # Sembrar ejercicios por defecto si la tabla está vacía para este usuario
    existing = conn.execute("SELECT COUNT(*) FROM ejercicios_biblioteca WHERE usuario_id=?", (usuario_id,)).fetchone()[0]
    if existing == 0:
        ahora = datetime.now().strftime("%Y-%m-%d")
        defaults = [
            ("Hip Thrust",         "Glúteo",        "Glúteo mayor",          "Fuerza",    '["HT","hip thrust"]'),
            ("Sentadilla búlgara", "Glúteo",        "Cuádriceps, glúteo",    "Fuerza",    '["búlgara","bulgara","split squat"]'),
            ("Abducción cadera",   "Glúteo",        "Glúteo medio",          "Fuerza",    '["abducción","abduccion"]'),
            ("Dominadas",          "Tren superior", "Espalda, bíceps",       "Fuerza",    '["pull up","pullup","dominada"]'),
            ("Remo con mancuerna", "Espalda",       "Dorsal",                "Fuerza",    '["remo","remo mancuerna","remo barra"]'),
            ("Press banca",        "Tren superior", "Pecho",                 "Fuerza",    '["press","banca","press pecho"]'),
            ("Curl bíceps",        "Tren superior", "Bíceps",                "Fuerza",    '["curl","biceps","curl biceps","bíceps martillo"]'),
            ("Curl femoral",       "Tren inferior", "Isquiotibial",          "Fuerza",    '["femoral","curl femoral","isquio"]'),
            ("Sentadilla",         "Tren inferior", "Cuádriceps",            "Fuerza",    '["squat","sentadilla libre","sentadillas"]'),
            ("Peso muerto",        "Tren inferior", "Isquiotibial, glúteo",  "Fuerza",    '["deadlift","PM","peso muerto rumano"]'),
            ("Abdominales en cable","Core",         "Abdomen",               "Fuerza",    '["abs en polea","abs cable","abdominales polea","abdominales cable"]'),
            ("Abdominales colgada", "Core",         "Abdomen",               "Fuerza",    '["abs colgado","colgadas","abdominales colgados"]'),
            ("Press militar",      "Tren superior", "Hombro",                "Fuerza",    '["press hombro","militar","press overhead"]'),
            ("Plancha",            "Core",          "Core",                  "Fuerza",    '["plank","plancha abdominal","isométrico"]'),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO ejercicios_biblioteca "
            "(usuario_id,nombre,grupo_muscular,musculo_principal,tipo,alias,activo,creado_en) "
            "VALUES (?,?,?,?,?,?,1,?)",
            [(usuario_id, n, g, m, t, a, ahora) for n, g, m, t, a in defaults])
    conn.commit()
    conn.close()


def asegurar_tabla_catalogo_ejercicios():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ejercicios_catalogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nombre TEXT NOT NULL,
            grupo_muscular TEXT,
            musculo_principal TEXT,
            peso_actual REAL DEFAULT 0,
            unidad TEXT DEFAULT 'kg',
            notas TEXT,
            UNIQUE(usuario_id, nombre)
        )""")
    conn.commit()
    conn.close()


def asegurar_tabla_lesiones():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lesiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            tipo TEXT,
            grado INTEGER,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            activa INTEGER DEFAULT 1,
            notas TEXT
        )""")
    conn.commit()
    conn.close()


def asegurar_indices_consulta():
    """Crea índices de lectura frecuente sin romper si alguna tabla aún no existe."""
    conn = get_db_connection()
    try:
        index_statements = [
            "CREATE INDEX IF NOT EXISTS idx_act_usuario_fecha ON actividades_garmin(usuario_id, fecha)",
            "CREATE INDEX IF NOT EXISTS idx_sueno_usuario_fecha ON datos_sueno(usuario_id, fecha)",
            "CREATE INDEX IF NOT EXISTS idx_fisio_usuario_fecha ON diario_fisiologia(usuario_id, fecha)",
            "CREATE INDEX IF NOT EXISTS idx_fuerza_usuario_fecha ON sesiones_fuerza(usuario_id, fecha)",
            "CREATE INDEX IF NOT EXISTS idx_plan_usuario_semana ON plan_entrenamiento(usuario_id, semana_inicio)",
        ]
        for stmt in index_statements:
            try:
                conn.execute(stmt)
            except Exception:
                pass
        conn.commit()
    finally:
        conn.close()
