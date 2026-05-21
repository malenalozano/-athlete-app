from fastapi import FastAPI
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
    return {"ok": True, "mensaje": "Notificación de prueba enviada. Comprueba tu iPhone."}
