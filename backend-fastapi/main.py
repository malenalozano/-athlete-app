from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from routers import auth, dashboard, diario, ejercicios, entrenador, garmin, plan

app = FastAPI(title="Athlete Performance API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
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


@app.get("/health")
def health():
    return {"status": "ok"}
