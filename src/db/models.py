# Definiciones SQL de tablas como constantes limpias.
# Importar desde aquí para evitar duplicados entre módulos.

CREATE_USUARIOS = """
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

CREATE_EJERCICIOS_POR_DEFECTO = """
CREATE TABLE IF NOT EXISTS ejercicios_por_defecto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    ejercicio TEXT,
    grupo_muscular TEXT,
    musculo_principal TEXT
)
"""

CREATE_ACTIVIDADES_GARMIN = """
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
"""

CREATE_DIARIO_FISIOLOGIA = """
CREATE TABLE IF NOT EXISTS diario_fisiologia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    fecha TEXT,
    fase_ciclo TEXT,
    fatiga_subjetiva INTEGER,
    dolor_notas TEXT
)
"""

CREATE_ENTRENAMIENTOS_FUERZA = """
CREATE TABLE IF NOT EXISTS entrenamientos_fuerza (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    ejercicio TEXT,
    peso REAL,
    series INTEGER,
    repeticiones INTEGER,
    grupo_muscular TEXT,
    rpe INTEGER,
    musculo_principal TEXT,
    notas TEXT
)
"""

CREATE_PLAN_ENTRENAMIENTO = """
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

CREATE_SESIONES_FUERZA = """
CREATE TABLE IF NOT EXISTS sesiones_fuerza (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    fecha TEXT,
    nota_original TEXT,
    resumen TEXT,
    created_at TEXT
)
"""

CREATE_EJERCICIOS_FUERZA = """
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

CREATE_DATOS_BIOMETRICOS_PREMIUM = """
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

CREATE_HISTORIAL_LESIONES = """
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

CREATE_ESTUDIOS_REFERENCIA = """
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

CREATE_DATOS_SUENO = """
CREATE TABLE IF NOT EXISTS datos_sueno (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    fecha TEXT,
    horas_totales REAL,
    score INTEGER,
    UNIQUE(usuario_id, fecha)
)
"""

CREATE_EJERCICIOS_BIBLIOTECA = """
CREATE TABLE IF NOT EXISTS ejercicios_biblioteca (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    nombre TEXT NOT NULL,
    grupo_muscular TEXT,
    musculo_principal TEXT,
    tipo TEXT DEFAULT 'Fuerza',
    alias TEXT,
    notas TEXT,
    activo INTEGER DEFAULT 1,
    creado_en TEXT,
    UNIQUE(usuario_id, nombre)
)
"""

CREATE_HISTORIAL_EJERCICIO = """
CREATE TABLE IF NOT EXISTS historial_ejercicio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ejercicio_id INTEGER,
    usuario_id INTEGER,
    fecha TEXT,
    peso REAL,
    series INTEGER,
    repeticiones INTEGER,
    rpe INTEGER,
    notas TEXT
)
"""

# Índices de lectura frecuente
INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS idx_act_usuario_fecha ON actividades_garmin(usuario_id, fecha)",
    "CREATE INDEX IF NOT EXISTS idx_sueno_usuario_fecha ON datos_sueno(usuario_id, fecha)",
    "CREATE INDEX IF NOT EXISTS idx_fisio_usuario_fecha ON diario_fisiologia(usuario_id, fecha)",
    "CREATE INDEX IF NOT EXISTS idx_fuerza_usuario_fecha ON sesiones_fuerza(usuario_id, fecha)",
    "CREATE INDEX IF NOT EXISTS idx_plan_usuario_semana ON plan_entrenamiento(usuario_id, semana_inicio)",
]
