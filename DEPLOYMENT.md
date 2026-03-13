# Deployment y Sincronizacion

## 1) Publicar en Streamlit Cloud
- Repositorio: `malenalozano/athlete-performance-tracker`
- Main file: `app.py`
- Python: `3.11` o `3.12`

### Secrets/Variables de entorno en Streamlit Cloud
- `TURSO_DATABASE_URL`
- `TURSO_AUTH_TOKEN`
- `ENCRYPTION_KEY`
- `GOOGLE_API_KEY` (si usas IA de Gemini en `ai_coach.py`)

La app ya esta preparada para multiusuario (Malena/Dani) por perfil, y cada usuario puede tener sus propias credenciales Garmin guardadas cifradas en la base de datos.

## 2) Worker diario de Garmin (desacoplado de la UI)
Archivo: `.github/workflows/garmin-worker.yml`

Este workflow ejecuta `garmin_worker.py` una vez al dia y tambien manualmente (`workflow_dispatch`).

### Secrets necesarios en GitHub Actions
- `TURSO_DATABASE_URL`
- `TURSO_AUTH_TOKEN`
- `ENCRYPTION_KEY`

## 3) Ejecucion manual del worker
```bash
python garmin_worker.py --dias 7 --actividades 25
```

Opcional (solo un usuario):
```bash
python garmin_worker.py --user-id 1 --dias 7 --actividades 25
```

## 4) Flujo recomendado
- Usuario abre app: ve al instante lo que ya existe en DB.
- Worker diario actualiza Garmin en segundo plano.
- Boton `↺ Sincronizar Garmin` queda como opcion manual cuando quieras refresco inmediato.
