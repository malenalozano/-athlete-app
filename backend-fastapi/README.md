# Athlete Performance Tracker - FastAPI Backend

Backend API built with FastAPI for the Athlete Performance Tracker application.

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Turso, Genai, and Garmin credentials
```

4. Run server:
```bash
uvicorn main:app --reload
```

Server will be available at http://localhost:8000

## API Routes

- `POST /api/auth/login` - Login with password
- `GET /api/dashboard/stats` - Get dashboard statistics
- `GET /api/plan/weekly/{week}` - Get weekly training plan
- `GET /api/diario/entries/{date}` - Get daily entries
- `POST /api/garmin/sync` - Sync Garmin data
- `GET /api/ejercicios/list` - List exercises
- `POST /api/entrenador/ask` - Ask AI coach

## Environment Variables

- `TURSO_URL` - Turso database URL
- `TURSO_AUTH_TOKEN` - Turso authentication token
- `GENAI_API_KEY` - Google Generative AI API key
- `GARMIN_EMAIL` - Garmin account email
- `GARMIN_PASSWORD` - Garmin account password

## Deployment

Deploy to Railway:
1. Connect GitHub repository
2. Add environment variables
3. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
