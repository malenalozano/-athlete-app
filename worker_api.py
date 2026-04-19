"""
worker_api.py
API para ejecutar sincronizacion Garmin desde una infraestructura con IP estable.

Ejecucion local:
    uvicorn worker_api:app --host 0.0.0.0 --port 8000

Auth:
- Header Authorization: Bearer <WORKER_API_TOKEN>
  o header X-Worker-Token: <WORKER_API_TOKEN>
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from src.db.db_manager import get_db_connection
from src.garmin.garmin_sync import (
    cargar_sesion_tokens,
    sincronizar_todo_con_sesion,
    check_garmin_blockade,
)

app = FastAPI(title="Athlete Garmin Worker API", version="1.0.0")


class SyncRequest(BaseModel):
    usuario_id: int = Field(..., ge=1)
    dias: int = Field(default=7, ge=1, le=30)


def _expected_token() -> str:
    token = os.getenv("WORKER_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("WORKER_API_TOKEN no configurado")
    return token


def _extract_token(authorization: Optional[str], x_worker_token: Optional[str]) -> str:
    if x_worker_token:
        return x_worker_token.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def _require_auth(authorization: Optional[str], x_worker_token: Optional[str]) -> None:
    expected = _expected_token()
    incoming = _extract_token(authorization, x_worker_token)
    if not incoming or incoming != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _ensure_jobs_table() -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_sync_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                dias INTEGER NOT NULL,
                error TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _has_running_job(usuario_id: int) -> bool:
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT id FROM garmin_sync_jobs WHERE usuario_id=? AND status='running' ORDER BY id DESC LIMIT 1",
            (usuario_id,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def _start_job(usuario_id: int, dias: int) -> int:
    conn = get_db_connection()
    try:
        cur = conn.execute(
            "INSERT INTO garmin_sync_jobs (usuario_id, status, started_at, dias) VALUES (?, 'running', ?, ?)",
            (usuario_id, datetime.now().isoformat(), dias),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def _finish_job(job_id: int, status: str, error: Optional[str] = None) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE garmin_sync_jobs SET status=?, finished_at=?, error=? WHERE id=?",
            (status, datetime.now().isoformat(), error, job_id),
        )
        conn.commit()
    finally:
        conn.close()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "garmin-worker-api", "time": datetime.now().isoformat()}


@app.post("/sync/manual")
def sync_manual(
    payload: SyncRequest,
    authorization: Optional[str] = Header(default=None),
    x_worker_token: Optional[str] = Header(default=None),
) -> dict:
    _require_auth(authorization, x_worker_token)
    _ensure_jobs_table()

    blockade = check_garmin_blockade()
    if blockade and blockade.get("is_blocked"):
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Garmin bloqueado temporalmente (429)",
                "blocked_until": blockade.get("blocked_until"),
                "remaining_hours": blockade.get("remaining_hours"),
            },
        )

    if _has_running_job(payload.usuario_id):
        raise HTTPException(status_code=409, detail="Ya hay una sincronizacion en curso para este usuario")

    job_id = _start_job(payload.usuario_id, payload.dias)
    try:
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT email_garmin FROM usuarios WHERE id=?",
                (payload.usuario_id,),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            raise RuntimeError("Usuario no encontrado")

        email = row[0]
        gc = cargar_sesion_tokens(email, usuario_id=payload.usuario_id)
        if gc is None:
            raise RuntimeError("No hay tokens validos en BD para este usuario")

        result = sincronizar_todo_con_sesion(gc, payload.usuario_id, dias=payload.dias)
        _finish_job(job_id, "success")
        return {
            "ok": True,
            "job_id": job_id,
            "usuario_id": payload.usuario_id,
            "result": result,
        }
    except Exception as exc:
        _finish_job(job_id, "error", error=str(exc)[:800])
        raise HTTPException(status_code=500, detail=f"Error en sync Garmin: {exc}") from exc
