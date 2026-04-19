## Despliegue en Streamlit Cloud

La app está preparada para publicarse en Streamlit Cloud usando [app.py](app.py) como punto de entrada.

### Lo mínimo que hay que configurar

1. Conecta el repositorio de GitHub a Streamlit Cloud.
2. Indica `app.py` como archivo principal.
3. Añade estos secretos en el panel de Streamlit Cloud:

```toml
TURSO_DATABASE_URL = "..."
TURSO_AUTH_TOKEN = "..."
GEMINI_API_KEY = "..."
```

4. Si lo prefieres en local, puedes copiar [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example) a `.streamlit/secrets.toml` y rellenarlo.

### Notas importantes

- La base de datos local `atleta.db` solo sirve para desarrollo en tu ordenador.
- En producción, la app usa Turso/libSQL de forma automática si existen los secretos.
- No subas `.streamlit/secrets.toml` al repositorio.

## Acceso solo para Malena y Dani

Por defecto, una app en Streamlit Cloud es accesible por URL. Para restringir el acceso, esta app incluye login interno si defines usuarios en secretos.

1. Genera hash para cada contraseña:

```bash
python scripts/generar_hash_password.py "password_segura_malena"
python scripts/generar_hash_password.py "password_segura_dani"
```

2. Copia los hashes en los secretos de Streamlit Cloud:

```toml
[APP_USERS]
malena = "pbkdf2_sha256$..."
dani = "pbkdf2_sha256$..."
```

Con esto, la app pedirá usuario y contraseña antes de mostrar cualquier pantalla.

## Garmin robusto en cloud (anti-429)

Para evitar bloqueos de Garmin en Streamlit Cloud por IP compartida, la app soporta un worker externo con IP estable.

### Arquitectura recomendada

1. Streamlit: interfaz y visualización.
2. Worker API: ejecuta la sincronización Garmin con tokens guardados.
3. Turso: almacena tokens y datos sincronizados.

### Ejecutar Worker API

En la máquina/servicio donde desplegues el worker:

```bash
pip install -r requirements.txt
export WORKER_API_TOKEN="token_largo_y_privado"
uvicorn worker_api:app --host 0.0.0.0 --port 8000
```

En Windows PowerShell:

```powershell
$env:WORKER_API_TOKEN="token_largo_y_privado"
uvicorn worker_api:app --host 0.0.0.0 --port 8000
```

Endpoint de salud:

```text
GET /health
```

Endpoint de sync manual (protegido por token):

```text
POST /sync/manual
Authorization: Bearer <WORKER_API_TOKEN>
{"usuario_id": 1, "dias": 7}
```

### Configurar Streamlit para usar el Worker

Añade estos secretos en Streamlit Cloud:

```toml
WORKER_API_URL = "https://tu-worker-dominio"
WORKER_API_TOKEN = "token_largo_y_privado"
```

Con esos secretos, el botón de sincronización de Garmin usará automáticamente el worker externo.

### Qué evita esta arquitectura

- Reintentos de login desde IP compartida en cloud.
- Bloqueos 429 por picos de intentos en Streamlit.
- Sincronizaciones concurrentes del mismo usuario (el worker aplica lock por usuario).
