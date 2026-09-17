# athlete. — API

FastAPI service behind [`athlete.`](../README.md). Serves the SPA, owns persistence, and calls the training
engine in [`src/plan`](../src/plan).

## Run it

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                              # leave TURSO_* empty to use local SQLite
uvicorn main:app --reload --port 8000
```

Interactive docs: `http://localhost:8000/docs`. Health check: `GET /health`.

## Routers

| Prefix | File | Main endpoints |
|---|---|---|
| `/auth` | `routers/auth.py` | `POST /login`, `GET|PUT /perfil/{user}`, `PUT /garmin-credentials/{user}` |
| `/dashboard` | `routers/dashboard.py` | `GET /{user}` — KPIs, weekly volume, marathon checkpoints |
| `/plan` | `routers/plan.py` | `GET /{user}/semana/{date}`, `POST /{user}/generar-semana`, `POST /{user}/aplicar-semana`, session CRUD, macrocycle and cycle overrides, CSV import |
| `/garmin` | `routers/garmin.py` | `POST /{user}/sync`, `GET /{user}/actividades`, `/stats`, `/token-status`, `/diagnostico` |
| `/diario` | `routers/diario.py` | `GET|POST /fisiologia`, `/biometrico`, sweat-rate and intra-session test logs |
| `/ejercicios` | `routers/ejercicios.py` | Exercise library, per-exercise history, set logging, reorder/archive |
| `/entrenador` | `routers/entrenador.py` | `GET /{user}/resumen` — coach summary |

Scheduler-only endpoints, protected by the `X-Cron-Secret` header:
`POST /tasks/daily` (sync + push notification) and `POST /tasks/garmin-sync`.

## Configuration

Settings are loaded by `pydantic-settings` from `.env` / environment — see `config.py` and `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` | empty | Production libSQL. Empty ⇒ local SQLite. |
| `LOCAL_DB_PATH` | `atleta.db` | SQLite file used in development. |
| `CORS_ORIGINS` | localhost:5173, :3000 | JSON array or comma-separated list. |
| `NTFY_TOPIC` | empty | `ntfy.sh` topic for push notifications; empty disables them. |
| `CRON_SECRET` | empty | Shared secret for `/tasks/*`. |

## Database

`database.py` returns either a `sqlite3` connection or a DB-API-compatible client that speaks Turso's hrana
HTTP pipeline protocol, so callers are storage-agnostic. `init_db()` is idempotent and safe on every boot.
Details in [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

## Tests

```bash
pytest
```

`tests/test_api.py` covers the HTTP surface; `tests/test_plan_v2.py` asserts the training rules hold for
generated weeks.

## Deployment

Containerised (`Dockerfile`) and deployed on Render via the repository-root `render.yaml` as service
`athlete-api`. `railway.toml` is kept as an alternative target.
