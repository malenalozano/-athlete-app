from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from database import get_db

router = APIRouter(prefix="/ejercicios", tags=["ejercicios"])


class SerieCreate(BaseModel):
    usuario_id: int
    ejercicio_nombre: str
    peso: float
    series: int
    repeticiones: int
    rpe: Optional[int] = None
    notas: Optional[str] = None


class EjercicioCreate(BaseModel):
    usuario_id: int
    nombre: str
    grupo_muscular: str
    musculo_principal: Optional[str] = None
    alias: Optional[str] = None


@router.get("/{usuario_id}")
def get_ejercicios(usuario_id: int):
    """Devuelve biblioteca completa agrupada por grupo muscular con último peso usado."""
    conn = get_db()

    # Biblioteca de ejercicios del usuario
    rows = conn.execute(
        """SELECT e.id, e.nombre, e.grupo_muscular, e.musculo_principal, e.alias
           FROM ejercicios_biblioteca e
           WHERE e.usuario_id = ? AND e.activo = 1
           ORDER BY e.grupo_muscular, e.nombre""",
        (usuario_id,),
    ).fetchall()

    ejercicios = []
    for r in rows:
        ej_id, nombre, grupo, musculo, alias = r

        # Último registro de historial
        hist = conn.execute(
            """SELECT peso, series, repeticiones, fecha
               FROM historial_ejercicio
               WHERE ejercicio_id = ? AND usuario_id = ?
               ORDER BY fecha DESC, id DESC LIMIT 1""",
            (ej_id, usuario_id),
        ).fetchone()

        # Mejor peso histórico
        best = conn.execute(
            "SELECT MAX(peso) FROM historial_ejercicio WHERE ejercicio_id = ? AND usuario_id = ?",
            (ej_id, usuario_id),
        ).fetchone()

        ejercicios.append({
            "id": ej_id,
            "nombre": nombre,
            "grupo_muscular": grupo,
            "musculo_principal": musculo,
            "alias": alias,
            "ultimo_peso": hist[0] if hist else None,
            "ultima_fecha": hist[3] if hist else None,
            "mejor_peso": best[0] if best and best[0] else None,
        })

    conn.close()

    # Agrupar por grupo muscular
    grupos: dict[str, list] = {}
    for ej in ejercicios:
        g = ej["grupo_muscular"] or "Otros"
        grupos.setdefault(g, []).append(ej)

    return {
        "grupos": [
            {"nombre": g, "ejercicios": lista}
            for g, lista in sorted(grupos.items())
        ]
    }


@router.get("/{usuario_id}/historial/{ejercicio_id}")
def get_historial(usuario_id: int, ejercicio_id: int):
    conn = get_db()
    rows = conn.execute(
        """SELECT fecha, peso, series, repeticiones, rpe, notas
           FROM historial_ejercicio
           WHERE ejercicio_id = ? AND usuario_id = ?
           ORDER BY fecha DESC LIMIT 20""",
        (ejercicio_id, usuario_id),
    ).fetchall()
    conn.close()
    cols = ["fecha", "peso", "series", "repeticiones", "rpe", "notas"]
    return [dict(zip(cols, r)) for r in rows]


@router.post("/serie")
def registrar_serie(s: SerieCreate):
    conn = get_db()
    fecha = datetime.now().strftime("%Y-%m-%d")

    # Buscar ejercicio por nombre
    row = conn.execute(
        "SELECT id FROM ejercicios_biblioteca WHERE usuario_id = ? AND nombre = ?",
        (s.usuario_id, s.ejercicio_nombre),
    ).fetchone()

    if not row:
        # Crear ejercicio si no existe
        conn.execute(
            "INSERT OR IGNORE INTO ejercicios_biblioteca (usuario_id, nombre, activo, creado_en) VALUES (?, ?, 1, ?)",
            (s.usuario_id, s.ejercicio_nombre, fecha),
        )
        row = conn.execute(
            "SELECT id FROM ejercicios_biblioteca WHERE usuario_id = ? AND nombre = ?",
            (s.usuario_id, s.ejercicio_nombre),
        ).fetchone()

    ejercicio_id = row[0]
    conn.execute(
        """INSERT INTO historial_ejercicio
           (ejercicio_id, usuario_id, fecha, peso, series, repeticiones, rpe, notas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (ejercicio_id, s.usuario_id, fecha, s.peso, s.series, s.repeticiones, s.rpe, s.notas),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "ejercicio_id": ejercicio_id}


@router.post("/crear")
def crear_ejercicio(e: EjercicioCreate):
    conn = get_db()
    fecha = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        """INSERT OR IGNORE INTO ejercicios_biblioteca
           (usuario_id, nombre, grupo_muscular, musculo_principal, alias, activo, creado_en)
           VALUES (?, ?, ?, ?, ?, 1, ?)""",
        (e.usuario_id, e.nombre, e.grupo_muscular, e.musculo_principal, e.alias, fecha),
    )
    conn.commit()
    conn.close()
    return {"ok": True}
