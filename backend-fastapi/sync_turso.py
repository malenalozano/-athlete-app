"""
Sincroniza Turso con los datos locales sin borrar nada existente.
- Actualiza el schema (columnas nuevas)
- Añade el plan de Dani desde SQLite local
- Actualiza el perfil de Dani en usuarios
- No toca los datos de Malena

Uso: python sync_turso.py
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from database import TursoHTTPConnection, exec_batch
from config import settings

LOCAL_DB = "atleta.db"

SCHEMA_MIGRATIONS = [
    # Columnas nuevas en plan_entrenamiento que pueden no existir
    "ALTER TABLE plan_entrenamiento ADD COLUMN completado INTEGER DEFAULT 0",
    "ALTER TABLE plan_entrenamiento ADD COLUMN km_planificados REAL",
    "ALTER TABLE plan_entrenamiento ADD COLUMN km_realizados REAL",
    # Columnas nuevas en usuarios
    "ALTER TABLE usuarios ADD COLUMN fcmax INTEGER",
    "ALTER TABLE usuarios ADD COLUMN fecha_inicio_entrenamiento TEXT",
    "ALTER TABLE usuarios ADD COLUMN fecha_objetivo TEXT",
    "ALTER TABLE usuarios ADD COLUMN objetivo_tipo TEXT",
    "ALTER TABLE usuarios ADD COLUMN garmin_tokens TEXT",
    "ALTER TABLE usuarios ADD COLUMN ciclo_dias_personalizado INTEGER",
    # Nuevas tablas si no existen
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
    # Indices
    "CREATE INDEX IF NOT EXISTS idx_plan_usuario_semana ON plan_entrenamiento(usuario_id, semana_inicio)",
    "CREATE INDEX IF NOT EXISTS idx_act_usuario_fecha ON actividades_garmin(usuario_id, fecha)",
    "CREATE INDEX IF NOT EXISTS idx_biom_usuario_fecha ON datos_biometricos_premium(usuario_id, fecha)",
    "CREATE INDEX IF NOT EXISTS idx_sueno_usuario_fecha ON datos_sueno(usuario_id, fecha)",
    "CREATE INDEX IF NOT EXISTS idx_fisio_usuario_fecha ON diario_fisiologia(usuario_id, fecha)",
    "CREATE INDEX IF NOT EXISTS idx_fuerza_usuario_fecha ON sesiones_fuerza(usuario_id, fecha)",
]


def val_to_sql(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def sync():
    if not settings.turso_database_url or not settings.turso_auth_token:
        print("ERROR: Pon TURSO_DATABASE_URL y TURSO_AUTH_TOKEN en .env")
        sys.exit(1)

    turso = TursoHTTPConnection(settings.turso_database_url, settings.turso_auth_token)
    local = sqlite3.connect(LOCAL_DB)
    local.row_factory = sqlite3.Row

    # 1. Aplicar migraciones de schema (ignore_errors=True porque muchas ya existen)
    print("1. Aplicando migraciones de schema...")
    exec_batch(turso, SCHEMA_MIGRATIONS, ignore_errors=True)
    print("   OK")

    # 2. Asegurar que Dani existe en usuarios
    print("\n2. Asegurando perfil de Dani (userId=2)...")
    turso.execute("""
        INSERT OR IGNORE INTO usuarios
        (id, nombre, edad, genero, peso, objetivo, carrera, fuerza, nivel, ritmo,
         fecha_objetivo, objetivo_tipo)
        VALUES (2, 'Dani', 26, 'Hombre', 72.0, 'Ultra Madrid-Segovia', 1, 1,
                'Intermedio', '5:00', '2026-09-19', 'ultramaraton')
    """)
    print("   OK")

    # 3. Plan de Dani: borrar lo viejo de Turso e insertar todo desde SQLite local
    print("\n3. Sincronizando plan de Dani (userId=2) desde SQLite local...")
    existing = turso.execute("SELECT COUNT(*) FROM plan_entrenamiento WHERE usuario_id=2").fetchone()
    print(f"   Entradas existentes en Turso para Dani: {existing[0]}")

    turso.execute("DELETE FROM plan_entrenamiento WHERE usuario_id=2")
    print("   Borradas. Insertando desde local...")

    local_rows = local.execute(
        "SELECT usuario_id, semana_inicio, fecha, tipo, sesion, detalles, "
        "duracion_min, intensidad, km_planificados, completado, km_realizados "
        "FROM plan_entrenamiento WHERE usuario_id=2 ORDER BY fecha"
    ).fetchall()

    inserted = 0
    errors = 0
    for row in local_rows:
        vals = ", ".join(val_to_sql(v) for v in row)
        sql = (
            f"INSERT INTO plan_entrenamiento "
            f"(usuario_id, semana_inicio, fecha, tipo, sesion, detalles, "
            f"duracion_min, intensidad, km_planificados, completado, km_realizados) "
            f"VALUES ({vals})"
        )
        try:
            turso.execute(sql)
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"   ERR: {e}")

    print(f"   Insertadas {inserted} sesiones de Dani ({errors} errores)")

    # 4. Actualizar Malena con fcmax si no tiene
    print("\n4. Actualizando datos de Malena...")
    turso.execute("""
        UPDATE usuarios SET
            objetivo_tipo = 'maraton',
            fecha_objetivo = '2027-02-21',
            nivel = 'Intermedio',
            ritmo = '5:30',
            fcmax = 190
        WHERE id = 1 AND (objetivo_tipo IS NULL OR objetivo_tipo = '')
    """)
    print("   OK")

    local.close()
    print("\n✓ Sync completo!")
    print("\nVerificando resultado en Turso:")
    for tabla in ["usuarios", "plan_entrenamiento"]:
        cnt = turso.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        print(f"  {tabla}: {cnt} filas")


if __name__ == "__main__":
    sync()
