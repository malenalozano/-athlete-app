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
