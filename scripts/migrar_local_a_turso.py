import os
import sqlite3
import sys

from dotenv import load_dotenv


def _normalize_create_sql(sql: str) -> str:
    sql_u = sql.strip()
    if sql_u.upper().startswith("CREATE TABLE ") and "IF NOT EXISTS" not in sql_u.upper():
        return sql_u.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1)
    return sql_u


def _iter_tables(conn_local: sqlite3.Connection):
    rows = conn_local.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    for name, sql in rows:
        if not sql:
            continue
        yield name, sql


def _copy_table(conn_local: sqlite3.Connection, conn_remote, table_name: str) -> int:
    cols = conn_local.execute(f"PRAGMA table_info({table_name})").fetchall()
    col_names = [c[1] for c in cols]
    if not col_names:
        return 0

    quoted = ", ".join([f'"{c}"' for c in col_names])
    placeholders = ", ".join(["?" for _ in col_names])
    rows = conn_local.execute(f"SELECT {quoted} FROM {table_name}").fetchall()
    if not rows:
        return 0

    insert_sql = f"INSERT OR REPLACE INTO {table_name} ({quoted}) VALUES ({placeholders})"
    for row in rows:
        conn_remote.execute(insert_sql, row)
    return len(rows)


def main() -> int:
    load_dotenv()

    try:
        import libsql  # type: ignore
    except Exception as exc:
        print(f"Falta libsql: {exc}")
        return 1

    local_db = os.getenv("LOCAL_DB_PATH", "atleta.db")
    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")

    if len(sys.argv) > 1 and sys.argv[1].strip():
        local_db = sys.argv[1].strip()

    if not os.path.exists(local_db):
        print(f"No existe la base local: {local_db}")
        return 1
    if not turso_url or not turso_token:
        print("Faltan TURSO_DATABASE_URL o TURSO_AUTH_TOKEN en el entorno/.env")
        return 1

    conn_local = sqlite3.connect(local_db)
    conn_remote = libsql.connect(turso_url, auth_token=turso_token)

    total = 0
    try:
        for table_name, create_sql in _iter_tables(conn_local):
            conn_remote.execute(_normalize_create_sql(create_sql))
            copied = _copy_table(conn_local, conn_remote, table_name)
            total += copied
            print(f"{table_name}: {copied} filas")
    finally:
        conn_local.close()
        conn_remote.close()

    print(f"Migracion completada. Filas totales: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
