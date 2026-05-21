import json
import sqlite3
import urllib.error
import urllib.request

from config import settings


def _escape_val(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def _bind_params(sql: str, params) -> str:
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
        self.description = [(c["name"], None, None, None, None, None, None) for c in cols] if cols else None
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

    def __iter__(self):
        return iter(self._rows)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TursoHTTPConnection:
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
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
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
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def get_db():
    url = settings.turso_database_url
    token = settings.turso_auth_token
    if url and token:
        return TursoHTTPConnection(url, token)
    conn = sqlite3.connect(settings.local_db_path, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def exec_batch(conn, sqls: list[str], ignore_errors: bool = True):
    if not sqls:
        return
    if isinstance(conn, TursoHTTPConnection):
        results = conn._send(sqls)
        if not ignore_errors:
            for r in results:
                if r.get("type") == "error":
                    raise sqlite3.OperationalError(r.get("error", {}).get("message", "Turso error"))
    else:
        for sql in sqls:
            try:
                conn.execute(sql)
            except Exception:
                if not ignore_errors:
                    raise


_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, edad INTEGER, genero TEXT, peso REAL, objetivo TEXT,
        carrera INTEGER, fuerza INTEGER, nivel TEXT, ritmo TEXT,
        email_garmin TEXT, password_garmin_enc TEXT, rol TEXT,
        fcmax INTEGER, fecha_inicio_entrenamiento TEXT,
        fecha_objetivo TEXT, objetivo_tipo TEXT, garmin_tokens TEXT,
        ciclo_dias_personalizado INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS actividades_garmin (
        id_actividad TEXT PRIMARY KEY, usuario_id INTEGER, fecha TEXT,
        tipo_deporte TEXT, distancia_m REAL, tiempo_seg REAL,
        ritmo_medio REAL, fc_media INTEGER, fc_max INTEGER,
        potencia_media_w REAL, cadencia_media REAL,
        longitud_zancada_m REAL, tiempo_contacto_ms REAL,
        oscilacion_vertical_cm REAL
    )""",
    """CREATE TABLE IF NOT EXISTS diario_fisiologia (
        id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, fecha TEXT,
        fase_ciclo TEXT, fatiga_subjetiva INTEGER, dolor_notas TEXT,
        sangre TEXT, sintomas TEXT, estado_animo TEXT, feedback_entreno TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS plan_entrenamiento (
        id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER,
        semana_inicio TEXT, fecha TEXT, tipo TEXT, sesion TEXT,
        detalles TEXT, duracion_min INTEGER, intensidad TEXT, creado_en TEXT,
        completado INTEGER DEFAULT 0, km_planificados REAL, km_realizados REAL
    )""",
    """CREATE TABLE IF NOT EXISTS sesiones_fuerza (
        id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, fecha TEXT,
        nota_original TEXT, resumen TEXT, created_at TEXT,
        tipo_registro TEXT, actividad_garmin_id TEXT,
        nota_estado TEXT, lesion_flag INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS ejercicios_fuerza (
        id INTEGER PRIMARY KEY AUTOINCREMENT, sesion_id INTEGER, ejercicio TEXT,
        peso REAL, series INTEGER, repeticiones INTEGER, grupo_muscular TEXT,
        musculo_principal TEXT, rpe INTEGER, sensaciones TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS datos_biometricos_premium (
        id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, fecha TEXT,
        hrv_ms REAL, fc_reposo INTEGER, fc_maxima INTEGER, sleep_score INTEGER,
        carga_aguda REAL, carga_cronica REAL, estres_vital INTEGER,
        rpe_sesion INTEGER, sensacion_notas TEXT, disponibilidad_min INTEGER,
        training_readiness INTEGER, body_battery INTEGER,
        body_battery_min INTEGER, body_battery_max INTEGER,
        estres_medio REAL, recovery_hours REAL, spo2 REAL,
        potencia_media_w REAL, training_status TEXT, vo2max REAL,
        UNIQUE(usuario_id, fecha)
    )""",
    """CREATE TABLE IF NOT EXISTS datos_sueno (
        id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, fecha TEXT,
        horas_totales REAL, score INTEGER,
        sleep_profundo_horas REAL, sleep_rem_horas REAL,
        sleep_vigilia_horas REAL, despertares INTEGER,
        UNIQUE(usuario_id, fecha)
    )""",
    """CREATE TABLE IF NOT EXISTS ejercicios_biblioteca (
        id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER,
        nombre TEXT NOT NULL, grupo_muscular TEXT, musculo_principal TEXT,
        tipo TEXT DEFAULT 'Fuerza', alias TEXT, notas TEXT,
        activo INTEGER DEFAULT 1, creado_en TEXT, UNIQUE(usuario_id, nombre)
    )""",
    """CREATE TABLE IF NOT EXISTS historial_ejercicio (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ejercicio_id INTEGER,
        usuario_id INTEGER, fecha TEXT, peso REAL, series INTEGER,
        repeticiones INTEGER, rpe INTEGER, notas TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS historial_ciclos_menstruales (
        id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER,
        fecha_inicio_regla TEXT NOT NULL, fecha_fin_regla TEXT NOT NULL,
        duracion_menstruacion_dias INTEGER, fecha_siguiente_regla TEXT,
        duracion_ciclo_dias INTEGER,
        registrado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(usuario_id, fecha_inicio_regla)
    )""",
    """CREATE TABLE IF NOT EXISTS lesiones (
        id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER,
        tipo TEXT, grado INTEGER, fecha_inicio TEXT, fecha_fin TEXT,
        activa INTEGER DEFAULT 1, notas TEXT
    )""",
    # ejercicios_catalogo (tabla nueva de biblioteca de ejercicios)
    """CREATE TABLE IF NOT EXISTS ejercicios_catalogo (
        id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER,
        nombre TEXT NOT NULL, grupo_muscular TEXT, musculo_principal TEXT,
        notas TEXT, archivado INTEGER DEFAULT 0,
        series_objetivo INTEGER, reps_objetivo INTEGER, peso_objetivo REAL,
        subir_peso INTEGER DEFAULT 0, creado_en TEXT,
        UNIQUE(usuario_id, nombre)
    )""",
    # Migrations
    "ALTER TABLE plan_entrenamiento ADD COLUMN completado INTEGER DEFAULT 0",
    "ALTER TABLE plan_entrenamiento ADD COLUMN km_planificados REAL",
    "ALTER TABLE plan_entrenamiento ADD COLUMN km_realizados REAL",
    "ALTER TABLE ejercicios_catalogo ADD COLUMN series_objetivo INTEGER",
    "ALTER TABLE ejercicios_catalogo ADD COLUMN reps_objetivo INTEGER",
    "ALTER TABLE ejercicios_catalogo ADD COLUMN peso_objetivo REAL",
    "ALTER TABLE ejercicios_catalogo ADD COLUMN archivado INTEGER DEFAULT 0",
    "ALTER TABLE ejercicios_catalogo ADD COLUMN subir_peso INTEGER DEFAULT 0",
    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_act_usuario_fecha ON actividades_garmin(usuario_id, fecha)",
    "CREATE INDEX IF NOT EXISTS idx_sueno_usuario_fecha ON datos_sueno(usuario_id, fecha)",
    "CREATE INDEX IF NOT EXISTS idx_fisio_usuario_fecha ON diario_fisiologia(usuario_id, fecha)",
    "CREATE INDEX IF NOT EXISTS idx_fuerza_usuario_fecha ON sesiones_fuerza(usuario_id, fecha)",
    "CREATE INDEX IF NOT EXISTS idx_plan_usuario_semana ON plan_entrenamiento(usuario_id, semana_inicio)",
    "CREATE INDEX IF NOT EXISTS idx_biom_usuario_fecha ON datos_biometricos_premium(usuario_id, fecha)",
    # Default users
    """INSERT OR IGNORE INTO usuarios
       (id, nombre, edad, genero, peso, objetivo, carrera, fuerza, nivel, ritmo,
        fecha_objetivo, objetivo_tipo)
       VALUES (1, 'Malena', 22, 'Mujer', 58.0, 'Maratón de Sevilla', 1, 1,
               'Intermedio', '5:30', '2027-02-21', 'maraton')""",
    """INSERT OR IGNORE INTO usuarios
       (id, nombre, edad, genero, peso, objetivo, carrera, fuerza, nivel, ritmo,
        fecha_objetivo, objetivo_tipo)
       VALUES (2, 'Dani', 26, 'Hombre', 72.0, 'Ultra Madrid-Segovia', 1, 1,
               'Intermedio', '5:00', '2026-09-19', 'ultramaraton')""",
]


def init_db():
    conn = get_db()
    exec_batch(conn, _SCHEMA, ignore_errors=True)
    conn.commit()
    conn.close()
