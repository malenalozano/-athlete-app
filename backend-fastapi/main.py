from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from routers import auth, dashboard, diario, ejercicios, entrenador, garmin, plan
from scheduler import start_scheduler, stop_scheduler

app = FastAPI(title="Athlete Performance API", version="1.0.0")

_cors_origins = list({
    "https://athlete-app-kohl.vercel.app",
    *settings.cors_origins,
})

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # Permitir dominios Vercel dinamicos (ej: *.vercel.app)
    allow_origin_regex=r"https?://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(plan.router)
app.include_router(ejercicios.router)
app.include_router(diario.router)
app.include_router(garmin.router)
app.include_router(entrenador.router)


@app.on_event("startup")
def startup():
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def shutdown():
    stop_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/notificaciones/test-hoy")
def test_notificacion_hoy():
    """Dispara el recordatorio de hoy inmediatamente (para probar ntfy sin esperar las 9am)."""
    from scheduler import daily_training_reminder
    daily_training_reminder()
    return {"ok": True, "mensaje": "Notificacion de prueba enviada. Comprueba tu iPhone."}


@app.post("/tasks/daily")
def tasks_daily(x_cron_secret: str = Header(default=None)):
    """
    Endpoint para cron-job.org (llamado cada dia automaticamente).
    Requiere header X-Cron-Secret con el valor de CRON_SECRET.

    Hace dos cosas en orden:
      1. Sync Garmin para todos los usuarios con tokens (7:00 AM recomendado)
      2. Envia el recordatorio de entrenamiento por ntfy (9:00 AM recomendado)

    Como Render duerme el dyno gratis, usamos DOS jobs en cron-job.org:
      - 07:00 → POST /tasks/garmin-sync  (despierta el servidor + sincroniza)
      - 09:00 → POST /tasks/daily        (ya despierto, manda la notificacion)
    """
    from fastapi import HTTPException

    secret = settings.cron_secret
    if secret and x_cron_secret != secret:
        raise HTTPException(status_code=401, detail="Cron secret invalido")

    from scheduler import daily_training_reminder
    daily_training_reminder()
    return {"ok": True, "paso": "reminder_enviado"}


@app.post("/tasks/garmin-sync")
def tasks_garmin_sync(x_cron_secret: str = Header(default=None)):
    """
    Sincroniza Garmin para todos los usuarios con tokens guardados.
    Llamado por cron-job.org a las 7:00 AM para:
      1. Despertar el dyno de Render antes de la notificacion de las 9:00
      2. Tener datos frescos de Garmin para el plan del dia

    Requiere header: X-Cron-Secret: <valor de CRON_SECRET en Render>
    """
    from fastapi import HTTPException, Header
    from database import get_db
    from routers.garmin import _do_sync
    from notifications import send_notification

    # Verificar secreto
    secret = settings.cron_secret
    if secret and x_cron_secret != secret:
        raise HTTPException(status_code=401, detail="Cron secret invalido")

    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, nombre FROM usuarios WHERE garmin_tokens IS NOT NULL AND garmin_tokens != ''",
        ).fetchall()
    finally:
        conn.close()

    resultados = []
    for usuario_id, nombre in rows:
        try:
            res = _do_sync(usuario_id)
            acts = res.get("actividades_importadas", 0)
            resultados.append({"usuario": nombre, "ok": True, "actividades": acts})
        except Exception as e:
            resultados.append({"usuario": nombre, "ok": False, "error": str(e)[:100]})

    # Notificacion solo si algo fue mal
    errores = [r for r in resultados if not r["ok"]]
    if errores:
        send_notification(
            f"Sync automatico con errores: {', '.join(r['usuario'] for r in errores)}",
            title="Garmin auto-sync",
            tags=["warning"],
            priority="low",
        )

    return {"ok": True, "resultados": resultados}
