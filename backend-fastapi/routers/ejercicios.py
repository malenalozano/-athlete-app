from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_db

router = APIRouter(prefix="/ejercicios", tags=["ejercicios"])

GRUPOS_VALIDOS = {"Push", "Pull", "Pierna"}


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
    grupo_muscular: str   # Push | Pull | Pierna
    musculo_principal: Optional[str] = None
    alias: Optional[str] = None


def _ejercicio_row(conn, ej_id: int, nombre: str, grupo: str, musculo, alias, archivado, usuario_id: int) -> dict:
    hist = conn.execute(
        """SELECT peso, series, repeticiones, fecha
           FROM historial_ejercicio
           WHERE ejercicio_id = ? AND usuario_id = ?
           ORDER BY fecha DESC, id DESC LIMIT 1""",
        (ej_id, usuario_id),
    ).fetchone()

    best = conn.execute(
        "SELECT MAX(peso) FROM historial_ejercicio WHERE ejercicio_id = ? AND usuario_id = ?",
        (ej_id, usuario_id),
    ).fetchone()

    return {
        "id": ej_id,
        "nombre": nombre,
        "grupo_muscular": grupo,
        "musculo_principal": musculo,
        "alias": alias,
        "archivado": bool(archivado),
        "ultimo_peso": hist[0] if hist else None,
        "ultima_fecha": hist[3] if hist else None,
        "mejor_peso": best[0] if best and best[0] else None,
    }


@router.get("/{usuario_id}")
def get_ejercicios(usuario_id: int):
    """Devuelve ejercicios agrupados en Push / Pull / Pierna.
    Cada grupo tiene: activos[] y archivados[].
    """
    conn = get_db()
    rows = conn.execute(
        """SELECT e.id, e.nombre, e.grupo_muscular, e.musculo_principal, e.notas, e.archivado
           FROM ejercicios_catalogo e
           WHERE e.usuario_id = ?
           ORDER BY e.grupo_muscular, e.nombre""",
        (usuario_id,),
    ).fetchall()

    # Organizar en 3 grupos fijos
    grupos: dict[str, dict] = {
        "Push":   {"activos": [], "archivados": []},
        "Pull":   {"activos": [], "archivados": []},
        "Pierna": {"activos": [], "archivados": []},
    }

    for r in rows:
        ej_id, nombre, grupo, musculo, alias, archivado = r
        # Normalizar grupo al válido más cercano
        grupo_norm = next((g for g in GRUPOS_VALIDOS if g.lower() in (grupo or "").lower()), None)
        if not grupo_norm:
            continue  # Ignorar ejercicios con grupo desconocido

        ej = _ejercicio_row(conn, ej_id, nombre, grupo_norm, musculo, alias, archivado, usuario_id)
        if archivado:
            grupos[grupo_norm]["archivados"].append(ej)
        else:
            grupos[grupo_norm]["activos"].append(ej)

    conn.close()
    return {"grupos": grupos}


@router.get("/{usuario_id}/grupo/{grupo}")
def get_ejercicios_grupo(usuario_id: int, grupo: str):
    """Devuelve solo los ejercicios ACTIVOS de un grupo (Push/Pull/Pierna).
    Usado por las notificaciones del plan diario.
    """
    grupo_norm = next((g for g in GRUPOS_VALIDOS if g.lower() == grupo.lower()), None)
    if not grupo_norm:
        raise HTTPException(status_code=400, detail=f"Grupo no válido. Usa: {', '.join(GRUPOS_VALIDOS)}")

    conn = get_db()
    rows = conn.execute(
        """SELECT e.id, e.nombre, e.grupo_muscular, e.musculo_principal, e.notas, e.archivado
           FROM ejercicios_catalogo e
           WHERE e.usuario_id = ? AND LOWER(e.grupo_muscular) = LOWER(?)
             AND (e.archivado IS NULL OR e.archivado = 0)
           ORDER BY e.nombre""",
        (usuario_id, grupo_norm),
    ).fetchall()

    ejercicios = []
    for r in rows:
        ej_id, nombre, grupo_r, musculo, alias, archivado = r
        ej = _ejercicio_row(conn, ej_id, nombre, grupo_r, musculo, alias, archivado, usuario_id)
        ejercicios.append(ej)

    conn.close()
    return {"grupo": grupo_norm, "ejercicios": ejercicios}


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


@router.patch("/{ejercicio_id}/archivar")
def toggle_archivar(ejercicio_id: int, archivar: bool = True):
    """Archiva o desarchiva un ejercicio. ?archivar=true para archivar, ?archivar=false para desarchivar."""
    conn = get_db()
    conn.execute(
        "UPDATE ejercicios_catalogo SET archivado = ? WHERE id = ?",
        (1 if archivar else 0, ejercicio_id),
    )
    conn.commit()
    conn.close()
    accion = "archivado" if archivar else "desarchivado"
    return {"ok": True, "mensaje": f"Ejercicio {accion}"}


@router.post("/serie")
def registrar_serie(s: SerieCreate):
    conn = get_db()
    fecha = datetime.now().strftime("%Y-%m-%d")

    row = conn.execute(
        "SELECT id FROM ejercicios_catalogo WHERE usuario_id = ? AND nombre = ?",
        (s.usuario_id, s.ejercicio_nombre),
    ).fetchone()

    if not row:
        conn.execute(
            "INSERT OR IGNORE INTO ejercicios_catalogo (usuario_id, nombre, creado_en) VALUES (?, ?, ?)",
            (s.usuario_id, s.ejercicio_nombre, fecha),
        )
        row = conn.execute(
            "SELECT id FROM ejercicios_catalogo WHERE usuario_id = ? AND nombre = ?",
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
    grupo_norm = next((g for g in GRUPOS_VALIDOS if g.lower() == e.grupo_muscular.lower()), None)
    if not grupo_norm:
        raise HTTPException(status_code=400, detail=f"Grupo no válido. Usa: {', '.join(GRUPOS_VALIDOS)}")

    conn = get_db()
    fecha = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        """INSERT OR IGNORE INTO ejercicios_catalogo
           (usuario_id, nombre, grupo_muscular, musculo_principal, notas, creado_en)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (e.usuario_id, e.nombre, grupo_norm, e.musculo_principal, e.alias, fecha),
    )
    conn.commit()
    conn.close()
    return {"ok": True}
