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


@router.get("/perfil/{usuario_id}")
def perfil(usuario_id: int):
    conn = get_db()
    row = conn.execute(
        """SELECT id, nombre, edad, genero, peso, objetivo, nivel, ritmo,
                  fcmax, fecha_objetivo, objetivo_tipo, fecha_inicio_entrenamiento
           FROM usuarios WHERE id = ?""",
        (usuario_id,),
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    cols = ["id", "nombre", "edad", "genero", "peso", "objetivo", "nivel", "ritmo",
            "fcmax", "fecha_objetivo", "objetivo_tipo", "fecha_inicio_entrenamiento"]
    return dict(zip(cols, row))
