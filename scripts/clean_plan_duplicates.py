"""Limpia duplicados históricos en plan_entrenamiento.

Regla de deduplicación:
- 1 fila por (usuario_id, semana_inicio, fecha)
- Si hay varias filas para el mismo día, conserva la "mejor" según:
  1) No-Descanso por encima de Descanso
  2) Mayor duracion_min
  3) Última fila (id más alto)

Uso:
  python scripts/clean_plan_duplicates.py           # Solo informe (dry-run)
  python scripts/clean_plan_duplicates.py --apply   # Aplica borrado
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from src.db.db_manager import get_db_connection


@dataclass
class DupStats:
    grupos_con_duplicados: int
    filas_duplicadas: int


def _get_dup_stats(conn) -> DupStats:
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS grupos_con_duplicados,
            COALESCE(SUM(cnt - 1), 0) AS filas_duplicadas
        FROM (
            SELECT usuario_id, semana_inicio, fecha, COUNT(*) AS cnt
            FROM plan_entrenamiento
            GROUP BY usuario_id, semana_inicio, fecha
            HAVING COUNT(*) > 1
        ) t
        """
    ).fetchone()

    if not row:
        return DupStats(0, 0)
    return DupStats(int(row[0] or 0), int(row[1] or 0))


def _delete_duplicates(conn) -> int:
    before = _get_dup_stats(conn)
    if before.filas_duplicadas == 0:
        return 0

    conn.execute(
        """
        DELETE FROM plan_entrenamiento
        WHERE id IN (
            SELECT id FROM (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY usuario_id, semana_inicio, fecha
                        ORDER BY
                            CASE WHEN COALESCE(tipo, '') = 'Descanso' THEN 1 ELSE 0 END ASC,
                            COALESCE(duracion_min, 0) DESC,
                            id DESC
                    ) AS rn
                FROM plan_entrenamiento
            ) ranked
            WHERE rn > 1
        )
        """
    )

    try:
        conn.commit()
    except Exception:
        pass

    return before.filas_duplicadas


def _print_examples(conn, limit: int = 20) -> None:
    rows = conn.execute(
        """
        SELECT usuario_id, semana_inicio, fecha, COUNT(*) AS cnt
        FROM plan_entrenamiento
        GROUP BY usuario_id, semana_inicio, fecha
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC, semana_inicio DESC, fecha DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    if not rows:
        print("No hay grupos duplicados.")
        return

    print("Ejemplos de grupos duplicados (max 20):")
    for r in rows:
        print(f"- usuario_id={r[0]} semana_inicio={r[1]} fecha={r[2]} filas={r[3]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Limpia duplicados de plan_entrenamiento")
    parser.add_argument("--apply", action="store_true", help="Aplica borrado de duplicados")
    args = parser.parse_args()

    conn = get_db_connection()
    try:
        stats = _get_dup_stats(conn)
        print(f"Grupos con duplicados: {stats.grupos_con_duplicados}")
        print(f"Filas duplicadas a eliminar: {stats.filas_duplicadas}")

        _print_examples(conn)

        if not args.apply:
            print("\nModo simulacion. Para aplicar: --apply")
            return 0

        deleted = _delete_duplicates(conn)
        after = _get_dup_stats(conn)

        print("\nLimpieza aplicada.")
        print(f"Filas eliminadas: {deleted}")
        print(f"Duplicados restantes: {after.filas_duplicadas}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
