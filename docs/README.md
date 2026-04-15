# Athlete - Docs Rápidas

## Punto de entrada oficial

La app se ejecuta siempre desde:

```bash
streamlit run app.py
```

No usar `src/app.py` (retirado para evitar confusiones).

## Estructura principal

- `app.py`: router principal y navegación multipágina.
- `pages/`: vistas de Dashboard, Plan, Diario, Garmin, Ejercicios y Entrenador.
- `src/core/`: lógica de negocio y componentes reutilizables.
- `src/db/`: acceso a base de datos.
- `src/garmin/`: integración Garmin y sincronización.
- `tests/`: pruebas.

## Nota

`src/app_legacy.py` se conserva solo como referencia histórica de código extraído/refactorizado.