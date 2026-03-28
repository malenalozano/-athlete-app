streamlit run src/app.py



src/core/: Lógica de negocio (ai_coach.py, atleta_core.py, historial_manager.py, seguridad.py)
src/db/: Base de datos y gestor (db_manager.py, athlete.db, atleta.db)
src/garmin/: Integración Garmin (garmin_sync.py, garmin_worker.py, diagnose_garmin.py, garmin_sync_test.log)
src/utils/: Utilidades (reset.py)
src/app.py: Punto de entrada principal
data/: Archivos de datos (actividad.csv, historial_entrenamientos.csv, Archivo `actividad.csv)
tests/: Pruebas automáticas
config/: Configuración y dependencias (requirements.txt, runtime.txt)
docs/: Documentación principal (README.md)

Aquí tienes una lista de todo lo que se importa desde Garmin en tu proyecto:

### 1. Actividades deportivas
- Actividades 
- Datos principales de cada actividad:
  - id_actividad (identificador único)
  - usuario_id
  - fecha
  - tipo_deporte
  - distancia (metros)
  - tiempo (segundos)
  - ritmo medio
  - frecuencia cardíaca media y máxima
  - potencia media
  - cadencia media
  - longitud de zancada
  - tiempo de contacto con el suelo
  - oscilación vertical

### 2. Métricas biométricas premium
- HRV (variabilidad de la frecuencia cardíaca)
- FC reposo y máxima
- Cadencia media
- Longitud de zancada
- Tiempo de contacto
- Oscilación vertical
- Sleep score
- SPO2 (oxígeno en sangre)
- Potencia media
- Carga aguda y crónica
- Estrés vital
- RPE sesión
- Sensación/notas
- Disponibilidad

### 3. Datos de sueño
- Horas totales de sueño
- Sleep score
- Horas de sueño profundo, REM y vigilia
- Número de despertares

---

¿Quieres que te lo prepare en formato tabla o para documentación técnica?