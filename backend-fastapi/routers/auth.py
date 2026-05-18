from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

USERS = {
    "malena": {"id": 1, "nombre": "Malena"},
    "dani": {"id": 2, "nombre": "Dani"},
}


class LoginRequest(BaseModel):
    nombre: str


@router.post("/login")
def login(req: LoginRequest):
    key = req.nombre.lower().strip()
    if key not in USERS:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return USERS[key]


class PerfilUpdate(BaseModel):
    nombre: Optional[str] = None
    edad: Optional[int] = None
    genero: Optional[str] = None
    peso: Optional[float] = None
    objetivo: Optional[str] = None
    nivel: Optional[str] = None
    ritmo: Optional[str] = None
    fcmax: Optional[int] = None
    fecha_objetivo: Optional[str] = None
    objetivo_tipo: Optional[str] = None


@router.put("/perfil/{usuario_id}")
def actualizar_perfil(usuario_id: int, body: PerfilUpdate):
    conn = get_db()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE usuarios SET {set_clause} WHERE id = ?",
            list(updates.values()) + [usuario_id],
        )
        conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/perfil/{usuario_id}")
def perfil(usuario_id: int):
    conn = get_db()
    row = conn.execute(
        """SELECT id, nombre, edad, genero, peso, objetivo, nivel, ritmo,
                  fcmax, fecha_objetivo, objetivo_tipo, fecha_inicio_entrenamiento,
                  email_garmin
           FROM usuarios WHERE id = ?""",
        (usuario_id,),
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    cols = ["id", "nombre", "edad", "genero", "peso", "objetivo", "nivel", "ritmo",
            "fcmax", "fecha_objetivo", "objetivo_tipo", "fecha_inicio_entrenamiento",
            "email_garmin"]
    return dict(zip(cols, row))


class GarminCredentials(BaseModel):
    email_garmin: str
    password_garmin: Optional[str] = None


@router.put("/garmin-credentials/{usuario_id}")
def guardar_credenciales_garmin(usuario_id: int, body: GarminCredentials):
    conn = get_db()
    if body.password_garmin:
        conn.execute(
            "UPDATE usuarios SET email_garmin = ?, password_garmin_enc = ? WHERE id = ?",
            (body.email_garmin, body.password_garmin, usuario_id),
        )
    else:
        conn.execute(
            "UPDATE usuarios SET email_garmin = ? WHERE id = ?",
            (body.email_garmin, usuario_id),
        )
    conn.commit()
    conn.close()
    return {"ok": True}
