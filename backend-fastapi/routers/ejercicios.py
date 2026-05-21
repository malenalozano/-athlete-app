from datetime import datetime, date as date_type
from typing import Optional, List

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
    series_objetivo: Optional[int] = None
    reps_objetivo: Optional[int] = None
    peso_objetivo: Optional[float] = None


class EjercicioEdit(BaseModel):
    nombre: Optional[str] = None
    grupo_muscular: Optional[str] = None
    alias: Optional[str] = None
    series_objetivo: Optional[int] = None
    reps_objetivo: Optional[int] = None
    peso_objetivo: Optional[float] = None
    subir_peso: Optional[int] = None


class RegistroEjercicio(BaseModel):
    ejercicio_id: int
    series: int
    repeticiones: int
    peso: float
    completado: bool


class SesionFuerza(BaseModel):
    registros: List[RegistroEjercicio]


@router.get("/{usuario_id}")
def get_ejercicios(usuario_id: int):
    """Devuelve ejercicios agrupados en Push / Pull / Pierna.
    Cada grupo tiene: activos[] y archivados[].
    Una sola query con JOINs para máxima velocidad.
    """
    conn = get_db()
    rows = conn.execute(
        """SELECT e.id, e.nombre, e.grupo_muscular, e.musculo_principal, e.notas, e.archivado,
                  e.series_objetivo, e.reps_objetivo, e.peso_objetivo,
                  h_last.peso, h_last.series, h_last.repeticiones, h_last.fecha,
                  h_best.mejor_peso, COALESCE(e.subir_peso, 0)
           FROM ejercicios_catalogo e
           LEFT JOIN (
               SELECT h1.ejercicio_id, h1.peso, h1.series, h1.repeticiones, h1.fecha
               FROM historial_ejercicio h1
               WHERE h1.usuario_id = ?
                 AND h1.id = (
                     SELECT id FROM historial_ejercicio
                     WHERE ejercicio_id = h1.ejercicio_id AND usuario_id = h1.usuario_id
                     ORDER BY fecha DESC, id DESC LIMIT 1
                 )
           ) h_last ON h_last.ejercicio_id = e.id
           LEFT JOIN (
               SELECT ejercicio_id, MAX(peso) AS mejor_peso
               FROM historial_ejercicio
               WHERE usuario_id = ?
               GROUP BY ejercicio_id
           ) h_best ON h_best.ejercicio_id = e.id
           WHERE e.usuario_id = ?
           ORDER BY e.grupo_muscular, e.nombre""",
        (usuario_id, usuario_id, usuario_id),
    ).fetchall()
    conn.close()

    grupos: dict[str, dict] = {
        "Push":   {"activos": [], "archivados": []},
        "Pull":   {"activos": [], "archivados": []},
        "Pierna": {"activos": [], "archivados": []},
    }

    for r in rows:
        ej_id, nombre, grupo, musculo, alias, archivado, series_obj, reps_obj, peso_obj, u_peso, u_series, u_reps, u_fecha, mejor_peso, subir_peso = r
        grupo_norm = next((g for g in GRUPOS_VALIDOS if g.lower() in (grupo or "").lower()), None)
        if not grupo_norm:
            continue

        ej = {
            "id": ej_id,
            "nombre": nombre,
            "grupo_muscular": grupo_norm,
            "musculo_principal": musculo,
            "alias": alias,
            "archivado": bool(archivado),
            "series_objetivo": series_obj,
            "reps_objetivo": reps_obj,
            "peso_objetivo": peso_obj,
            "ultimo_peso": u_peso,
            "ultima_series": u_series,
            "ultimas_reps": u_reps,
            "ultima_fecha": u_fecha,
            "mejor_peso": mejor_peso,
            "subir_peso": bool(subir_peso),
        }
        if archivado:
            grupos[grupo_norm]["archivados"].append(ej)
        else:
            grupos[grupo_norm]["activos"].append(ej)

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
        """SELECT e.id, e.nombre, e.musculo_principal, e.notas,
                  h_last.peso, h_last.series, h_last.repeticiones,
                  h_best.mejor_peso
           FROM ejercicios_catalogo e
           LEFT JOIN (
               SELECT h1.ejercicio_id, h1.peso, h1.series, h1.repeticiones
               FROM historial_ejercicio h1
               WHERE h1.usuario_id = ?
                 AND h1.id = (
                     SELECT id FROM historial_ejercicio
                     WHERE ejercicio_id = h1.ejercicio_id AND usuario_id = h1.usuario_id
                     ORDER BY fecha DESC, id DESC LIMIT 1
                 )
           ) h_last ON h_last.ejercicio_id = e.id
           LEFT JOIN (
               SELECT ejercicio_id, MAX(peso) AS mejor_peso
               FROM historial_ejercicio WHERE usuario_id = ? GROUP BY ejercicio_id
           ) h_best ON h_best.ejercicio_id = e.id
           WHERE e.usuario_id = ? AND LOWER(e.grupo_muscular) = LOWER(?)
             AND (e.archivado IS NULL OR e.archivado = 0)
           ORDER BY e.nombre""",
        (usuario_id, usuario_id, usuario_id, grupo_norm),
    ).fetchall()
    conn.close()

    ejercicios = []
    for r in rows:
        ej_id_or_nombre, nombre, musculo, alias, u_peso, u_series, u_reps, mejor_peso = r
        ejercicios.append({
            "nombre": nombre,
            "ultimo_peso": u_peso,
            "ultima_series": u_series,
            "ultimas_reps": u_reps,
            "mejor_peso": mejor_peso,
        })
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


@router.patch("/{ejercicio_id}")
def editar_ejercicio(ejercicio_id: int, e: EjercicioEdit):
    """Edita nombre, alias, series/reps/peso objetivo de un ejercicio."""
    conn = get_db()
    fields: dict = {}
    if e.nombre is not None:
        fields["nombre"] = e.nombre
    if e.grupo_muscular is not None:
        grupo_norm = next((g for g in GRUPOS_VALIDOS if g.lower() == e.grupo_muscular.lower()), None)
        if grupo_norm:
            fields["grupo_muscular"] = grupo_norm
    if e.alias is not None:
        fields["notas"] = e.alias
    if e.series_objetivo is not None:
        fields["series_objetivo"] = e.series_objetivo
    if e.reps_objetivo is not None:
        fields["reps_objetivo"] = e.reps_objetivo
    if e.peso_objetivo is not None:
        fields["peso_objetivo"] = e.peso_objetivo
    if e.subir_peso is not None:
        fields["subir_peso"] = e.subir_peso

    if fields:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE ejercicios_catalogo SET {set_clause} WHERE id = ?",
            (*fields.values(), ejercicio_id),
        )
        conn.commit()
    conn.close()
    return {"ok": True}


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


@router.get("/{usuario_id}/sesion-fuerza-hoy")
def get_sesion_fuerza_hoy(usuario_id: int):
    """Devuelve el grupo de fuerza de hoy (Push/Pull/Pierna) y ejercicios activos con historial."""
    hoy = date_type.today().strftime("%Y-%m-%d")

    conn = get_db()
    row = conn.execute(
        """SELECT tipo, sesion FROM plan_entrenamiento
           WHERE fecha = ? AND usuario_id = ? AND LOWER(tipo) = 'fuerza'
           ORDER BY id LIMIT 1""",
        (hoy, usuario_id),
    ).fetchone()

    if not row:
        conn.close()
        return {"tiene_fuerza": False, "grupo": None, "sesion_nombre": None, "ejercicios": []}

    tipo, sesion_nombre = row

    # Detectar grupo
    grupo = None
    if sesion_nombre:
        s = sesion_nombre.lower()
        if "push" in s:
            grupo = "Push"
        elif "pull" in s:
            grupo = "Pull"
        elif "pierna" in s:
            grupo = "Pierna"

    if not grupo:
        conn.close()
        return {"tiene_fuerza": True, "grupo": None, "sesion_nombre": sesion_nombre, "ejercicios": []}

    # Obtener ejercicios activos del grupo con último historial
    rows = conn.execute(
        """SELECT e.id, e.nombre, e.series_objetivo, e.reps_objetivo, e.peso_objetivo,
                  COALESCE(e.subir_peso, 0),
                  h_last.peso, h_last.series, h_last.repeticiones
           FROM ejercicios_catalogo e
           LEFT JOIN (
               SELECT h1.ejercicio_id, h1.peso, h1.series, h1.repeticiones
               FROM historial_ejercicio h1
               WHERE h1.usuario_id = ?
                 AND h1.id = (
                     SELECT id FROM historial_ejercicio
                     WHERE ejercicio_id = h1.ejercicio_id AND usuario_id = h1.usuario_id
                     ORDER BY fecha DESC, id DESC LIMIT 1
                 )
           ) h_last ON h_last.ejercicio_id = e.id
           WHERE e.usuario_id = ? AND LOWER(e.grupo_muscular) = LOWER(?)
             AND (e.archivado IS NULL OR e.archivado = 0)
           ORDER BY e.nombre""",
        (usuario_id, usuario_id, grupo),
    ).fetchall()
    conn.close()

    ejercicios = []
    for r in rows:
        ej_id, nombre, series_obj, reps_obj, peso_obj, subir_peso, u_peso, u_series, u_reps = r
        ejercicios.append({
            "id": ej_id,
            "nombre": nombre,
            "series_objetivo": series_obj,
            "reps_objetivo": reps_obj,
            "peso_objetivo": peso_obj,
            "subir_peso": bool(subir_peso),
            "ultimo_peso": u_peso,
            "ultima_series": u_series,
            "ultimas_reps": u_reps,
        })

    return {"tiene_fuerza": True, "grupo": grupo, "sesion_nombre": sesion_nombre, "ejercicios": ejercicios}


@router.post("/{usuario_id}/sesion")
def registrar_sesion_fuerza(usuario_id: int, sesion: SesionFuerza):
    """Registra una sesión de fuerza completa. Actualiza subir_peso según completado."""
    hoy = date_type.today().strftime("%Y-%m-%d")

    conn = get_db()
    for reg in sesion.registros:
        # Obtener último peso registrado ANTES de insertar
        last = conn.execute(
            """SELECT peso FROM historial_ejercicio
               WHERE ejercicio_id = ? AND usuario_id = ?
               ORDER BY fecha DESC, id DESC LIMIT 1""",
            (reg.ejercicio_id, usuario_id),
        ).fetchone()
        peso_anterior = float(last[0]) if last and last[0] is not None else None

        # Insertar en historial_ejercicio
        conn.execute(
            """INSERT INTO historial_ejercicio
               (ejercicio_id, usuario_id, fecha, peso, series, repeticiones)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (reg.ejercicio_id, usuario_id, hoy, reg.peso, reg.series, reg.repeticiones),
        )

        # Calcular subir_peso:
        # - completado=False → 0 (no subir)
        # - completado=True y subió peso → 0 (ya lo logró, resetear)
        # - completado=True y mismo/sin historial → 1 (subir próxima vez)
        if reg.completado:
            if peso_anterior is not None and reg.peso > peso_anterior:
                subir_peso = 0  # Ya subió el peso, resetear
            else:
                subir_peso = 1  # Completó, subir en la próxima sesión
        else:
            subir_peso = 0

        conn.execute(
            "UPDATE ejercicios_catalogo SET subir_peso = ? WHERE id = ? AND usuario_id = ?",
            (subir_peso, reg.ejercicio_id, usuario_id),
        )

    conn.commit()
    conn.close()
    return {"ok": True}
