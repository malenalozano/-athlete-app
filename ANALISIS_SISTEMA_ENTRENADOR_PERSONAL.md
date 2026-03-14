# Analisis tecnico del sistema de entrenador personal (Proyecto Athlete)

Fecha del analisis: 2026-03-14  
Ultima actualizacion: 2026-03-14

## 1. Vision general del sistema

El sistema actual esta implementado principalmente como una app de Streamlit en `app.py`, con persistencia en SQLite/Turso y sincronizacion manual con Garmin Connect.

Objetivo funcional:
- Gestionar entrenamiento de 2 atletas (Malena `usuario_id=1`, Dani `usuario_id=2`).
- Combinar running, fuerza, biometria Garmin, sueno, lesiones y (para Malena) ciclo menstrual.
- Generar plan semanal adaptativo con reglas de riesgo/recuperacion.
- Permitir coordinacion de entrenamientos en pareja.

Piezas principales:
- Interfaz y logica principal: `app.py`.
- Capa de base de datos y esquema: `db_manager.py`.
- Sincronizacion Garmin y extraccion de metricas: `garmin_sync.py`.
- Procesamiento IA de notas y chat: `ai_coach.py`.
- Cifrado de credenciales Garmin: `seguridad.py`.
- Worker batch de sincronizacion (CLI): `garmin_worker.py`.
- Script de borrado completo: `reset.py`.

## 2. Arquitectura y flujo end-to-end

## 2.1 Entrada de datos

### A) Datos de perfil
Se guardan en tabla `usuarios`:
- nombre, edad, genero, peso, objetivo.
- disponibilidad semanal: dias carrera y dias fuerza.
- nivel y rango de ritmo objetivo.
- credenciales Garmin (email + password cifrada).

### B) Sincronizacion Garmin (manual)
La sincronizacion no es automatica al cargar pagina; se dispara por boton `↻` en cabecera o desde Perfil.

Flujo:
1. Leer credenciales desde BD (`obtener_credenciales_garmin`).
2. Desencriptar password (`desencriptar_password`).
3. Sincronizar actividades (`sincronizar_actividades_inteligente`).
4. Sincronizar biometria/sueno (`sincronizar_biometricos_garmin`).
5. Guardar en tablas `actividades_garmin`, `datos_sueno`, `datos_biometricos_premium`.

### C) Diario de entrenamiento (texto libre)
Entrada en lenguaje natural, con soporte multi-fecha en un solo texto:
- Detecta bloques temporales (`hoy`, `ayer`, fecha explicita, dia de semana).
- Clasifica bloque: `fuerza`, `carrera`, `mixto`, `lesion`, `general`.
- Intenta vincular bloque de carrera a actividad Garmin del mismo dia.
- Si hay fuerza, parsea ejercicios con IA (Gemini) o parser local fallback.
- Guarda sesion en `sesiones_fuerza` y ejercicios en `ejercicios_fuerza`.

### D) Ciclo menstrual (solo Malena)
Registro diario en `diario_fisiologia`:
- sangre, sintomas, estado de animo, feedback de entreno.
- fase inferida simplificada: si hay sangre -> `Fase Folicular`; si no -> `No Aplica`.

### E) Lesiones
Registro de lesiones en `historial_lesiones` con estado activa/resuelta.

### F) Biblioteca cientifica
Carga de PDF/TXT/MD, extraccion de texto y resumen (manual o IA), guardado en:
- archivo fisico: carpeta `uploaded_studies/`.
- metadatos y texto/resumen en tabla `estudios_referencia`.

## 2.2 Salida / decisiones del sistema

### A) Dashboard operativo
Muestra:
- resumen ultimos 7 dias,
- checkpoints por objetivo,
- calendario semanal real,
- semaforo Garmin,
- progreso running/fuerza/sueno,
- vista de entrenamientos conjuntos (Malena + Dani).

### B) Plan semanal premium
La funcion `generar_plan_semanal(...)` arma 7 dias de plan con tipo, sesion, detalles, duracion e intensidad.

### C) Recomendacion IA
- Chat contextual (`obtener_consejo`) con master system prompt y snapshot completo de datos.
- Ajuste de plan por feedback textual (`ajustar_plan_con_feedback`).

## 3. Modelo de datos (tablas usadas)

Tablas principales activas:
- `usuarios`.
- `actividades_garmin`.
- `datos_sueno`.
- `datos_biometricos_premium`.
- `diario_fisiologia`.
- `sesiones_fuerza`.
- `ejercicios_fuerza`.
- `plan_entrenamiento`.
- `historial_lesiones`.
- `estudios_referencia`.

Indices de rendimiento:
- `idx_act_usuario_fecha`, `idx_sueno_usuario_fecha`, `idx_fisio_usuario_fecha`.
- `idx_sesiones_usuario_fecha`, `idx_plan_usuario_semana_fecha`.
- `idx_bio_usuario_fecha`, `idx_lesion_usuario_activa`.

Regla anti-duplicados relevante:
- `actividades_garmin.id_actividad` es PK, se usa `INSERT OR REPLACE`.

## 4. Que datos tiene en cuenta el sistema cada semana (detalle)

La agregacion central ocurre en `resumen_usuario_para_plan(usuario_id)` y se usa para dashboard, semaforo y plan.

## 4.1 Ventanas temporales por tipo de dato

- Running: ultimos 14 dias (`actividades_garmin`).
- Fuerza: ultimos 14 dias (`sesiones_fuerza`, tipo fuerza/mixto).
- Sueno: ultimos 7 registros (`datos_sueno`).
- Fisiologia/ciclo/fatiga: ultimos 3 registros (`diario_fisiologia`).
- Biometricos premium: ultimos 14 registros (`datos_biometricos_premium`).
- Lesiones activas: estado actual (`historial_lesiones.activa=1`).

## 4.2 Variables semanales/recientes que calcula

Carga de entrenamiento:
- `carreras_14d`, `km_14d`, `fc_media_14d`, `fuerza_14d`.

Recuperacion y sueno:
- `sueno_horas_7d`, `sueno_score_7d`, `dias_mal_sueno`.
- `sleep_profundo_7d`, `sleep_rem_7d`, `sleep_vigilia_7d`, `despertares_7d`.

Sistema nervioso / readiness:
- `hrv_actual`, `hrv_tendencia`.
- `training_readiness`, `body_battery`, `recovery_hours`.

Cardiovascular y respiratorio:
- `fc_reposo`, `fc_maxima`, `spo2`.

Biomecanica running:
- `cadencia_media`, `longitud_zancada_m`, `tiempo_contacto`, `oscilacion_vertical`, `potencia_media_w`.

Carga interna y sensaciones:
- `estres_vital`, `rpe_ultima`, `sensacion_ultima`, `fatiga_reciente`.

Riesgo de carga:
- `carga_aguda`, `carga_cronica`, `ratio_ctl_atl = carga_aguda / carga_cronica`.

Salud y contexto:
- `lesiones_activas`.
- `fase_ciclo_actual` (si aplica).

## 4.3 Limpieza de datos reciente importante

Si Garmin crea fila del dia con nulls en biometria, el sistema no toma esa fila vacia como referencia principal; busca la ultima con señales utiles y usa esa para semaforo/plan.

## 5. Motor de planificacion semanal: reglas tecnicas exactas

Entradas al plan:
- Perfil: dias carrera, dias fuerza, nivel, objetivo, genero.
- Resumen reciente: HRV/sueno/readiness/carga/lesiones/ciclo/estres/RPE/tecnica.
- Opcional: plan de pareja para alinear dias activos.

Salida:
- DataFrame de 7 dias con: `dia`, `fecha`, `tipo`, `sesion`, `detalles`, `duracion_min`, `intensidad`.
- Lista de alertas explicativas.

## 5.1 Umbrales de control

Bloqueo o reduccion de intensidad/volumen segun:
- HRV bajo (`hrv < 50`) o tendencia negativa fuerte (`hrv_tendencia < -5`).
- `dias_mal_sueno >= 3` (sleep score < 60).
- `training_readiness < 40`.
- `body_battery < 35`.
- `recovery_hours >= 24`.
- sueno profundo medio bajo (`< 1.2 h`).
- despertares medios altos (`>= 3`).
- ratio carga:
  - `>= 1.5`: descarga forzada.
  - `>= 1.3`: sin alta intensidad.
- estres vital alto (`>= 7`): reduce dias de carrera.
- fatiga subjetiva alta (`>= 8`).
- RPE ultimo muy alto (`>= 9`): prioriza recuperacion.

## 5.2 Ajustes por ciclo menstrual

Si genero mujer y hay fase:
- Fase lutea: baja volumen y evita maxima intensidad.
- Fase ovulatoria: permite ventana de alto rendimiento.
- Fase folicular: tolerancia a intensidad moderada/alta.

## 5.3 Ajustes por lesion

Reglas por zona:
- Lesion de impacto (rodilla, fascia, gemelo, tobillo, plantar, tibia): sustituye carrera por cardio sin impacto.
- Isquios: elimina sprints/series y anade trabajo excenctrico.
- Lumbar/espalda: sin carga axial, prioriza variantes seguras.

## 5.4 Ajustes por tecnica de carrera

- Cadencia < 170: drills tecnicos.
- Oscilacion vertical > 12 cm: trabajo de core/estabilidad.
- Cadencia baja + zancada alta: alerta de posible overstride.

## 5.5 Construccion del microciclo

- Distribuye dias de carrera y fuerza con `_indices_distribuidos`.
- Evita fuerza pesada de piernas el dia previo a sesion de calidad.
- Construye tipos de sesion por objetivo:
  - maraton/media: tempo, umbral, tirada larga,
  - ultra/trail: tirada larga de montana, excenctrico,
  - hyrox: bloques mixtos especificos.
- Puede mover dias para coincidir con la pareja si mejora overlap.

## 6. Funcionalidades por pantalla (Streamlit real)

Menu visible actual:
- Inicio.
- Perfil.
- Diario de Entrenamiento.
- Entrenador Personal.
- Ciclo Menstrual (solo Malena).

### Inicio
- KPIs 7d, checkpoints, semana actual, progreso running/fuerza/sueno.
- Semaforo Garmin con reglas de alerta.
- Estado del ciclo de Malena visible para Dani.
- Calendario de entrenamientos conjuntos por color.

### Perfil
- Edicion de datos del atleta.
- Guardado/actualizacion de credenciales Garmin cifradas.
- Sincronizacion manual de N actividades.

### Diario de Entrenamiento
- Parsing de texto libre multi-dia.
- Extraccion de ejercicios (IA + fallback local).
- Deteccion de estado/sensaciones/lesion.
- Vinculacion de carrera manual con actividad Garmin por fecha.
- Historial de sesiones + detalle de ejercicios + metricas Garmin vinculadas.

### Entrenador Personal
Pestanas:
- Check-in Diario: semaforo + historico de biometria/sueno.
- Generar Plan Semanal: genera, guarda y permite ajuste por feedback IA.
- Lesiones y Prevencion: alta y cierre de lesiones activas.

### Ciclo Menstrual (Malena)
- Registro diario de sangre/sintomas/animo/feedback.
- Historial reciente.
- Prediccion de fases y calendario mensual.

## 7. Funciones tecnicas presentes pero no expuestas en menu actual

En `app.py` existen ramas para:
- `Biblioteca Cientifica`.
- `Asistente Virtual`.
- `Calendario`.

Estas ramas contienen logica funcional, pero en `_opciones_menu` no aparecen actualmente (quedan fuera de navegacion visible).

## 8. Seguridad y privacidad

Credenciales Garmin:
- Password se cifra con Fernet (`seguridad.py`).
- Clave desde `ENCRYPTION_KEY`; si no existe, usa/crea `.encryption_key` local persistente.

Practicas observadas:
- Inputs de password usan `type="password"` en onboarding/perfil.
- No se muestran passwords en UI.

Base de datos:
- Soporta Turso via `libsql` si hay `TURSO_DATABASE_URL`.
- Fallback automatico a SQLite local (`atleta.db`).

## 9. IA y tolerancia a fallos

`ai_coach.py`:
- Si Gemini no esta configurado (`GEMINI_API_KEY`/`GOOGLE_API_KEY`), el sistema no se cae:
  - parsing de fuerza se hace en modo local regex.
  - `obtener_consejo` devuelve mensaje de degradacion controlada.

### 9.1 Master system prompt en `obtener_consejo` (implementado 2026-03-14)

La funcion `obtener_consejo(duda, contexto)` opera con un system prompt estructurado que incluye:

**Identidad y atletas:**
- Conoce a Malena (usuario_id=1, mujer, objetivo Maraton) y Dani (usuario_id=2, hombre, objetivo Ultramaraton 100km).
- Responde siempre en español, tono tecnico pero cercano.

**Reglas de seguridad no negociables (codificadas en el prompt):**
- HRV < 50 o tendencia HRV < -5: prioriza descanso activo, sin sesiones de calidad.
- Ratio carga aguda/cronica >= 1.5: descarga forzada, no añadir volumen.
- Ratio carga aguda/cronica >= 1.3: evitar alta intensidad.
- Lesion de impacto activa (rodilla, fascia plantar, gemelo, tobillo, tibia): sustituir carrera por cardio sin impacto.
- Isquios lesionados: eliminar sprints, anadir excentrico.
- Lumbar/espalda: sin carga axial.
- Dias mal sueno >= 3 o body_battery < 35: reducir carga.

**Reglas ciclo menstrual para Malena:**
- Fase lutea: bajar volumen, evitar maxima intensidad.
- Fase ovulatoria: ventana de alto rendimiento.
- Fase folicular: tolerancia a intensidad moderada/alta.

### 9.2 Snapshot de datos en el Asistente Virtual (implementado 2026-03-14)

Antes: el chat inyectaba solo las 3 ultimas actividades Garmin y 1 fila de fisiologia (query manual limitado).

Ahora: cada mensaje al chat incluye un snapshot completo construido desde `resumen_usuario_para_plan(user_actual)` + `obtener_perfil_cache(user_actual)` con las siguientes secciones:

- **Perfil:** nombre, objetivo, nivel, genero, disponibilidad semanal (dias carrera/fuerza).
- **Carga 14d:** carreras, km totales, FC media, sesiones fuerza, ratio ATL/CTL con alertas inline (`[RIESGO ALTO]` / `[ATENCION]`).
- **Recuperacion y sistema nervioso:** HRV actual + tendencia (con alertas inline), sueno horas/score/dias mal sueno, sueno profundo/REM, Body Battery, Training Readiness, Recovery Hours.
- **Salud:** lesiones activas, fase del ciclo (Malena), estres vital, RPE ultima sesion, sensacion.
- **Biomecanica running:** cadencia, potencia, oscilacion vertical, tiempo de contacto.
- **Estudios cientificos subidos** (si los hay).

Esto hace que la IA tenga el mismo nivel de contexto que el motor de planificacion semanal.

`garmin_sync.py`:
- Uso de wrappers tolerantes (`_safe_api_call`) para endpoints variables de Garmin.
- Extraccion robusta de metricas mediante busqueda recursiva de claves.

## 10. Diferencia entre app productiva y frontend React

Existe un frontend React en `_figma_inbox/Proyecto Athlete` con rutas para las mismas secciones.

Estado observado:
- Es principalmente una maqueta UI con datos mock/placeholder.
- No se ve integracion real con la BD o APIs del backend Python.
- La logica operativa real (sincronizacion, reglas, guardado) esta en Streamlit `app.py`.

## 11. Notas de cumplimiento con reglas del proyecto

Reglas esperadas del proyecto:
- No duplicar actividades Garmin por `activityId`: si, se cumple por PK + replace.
- Sincronizacion manual (no automatica en carga): si, se cumple por boton/form.
- Filtrar solo running al cargar Garmin: parcialmente.
  - En `sincronizar_actividades` se insertan actividades sin filtro estricto por tipo.
  - En algunas vistas/metricas si hay filtros de uso para running, pero no en la ingesta base.

## 12. Resumen ejecutivo

El sistema funciona como un entrenador personal data-driven con reglas explicitamente codificadas y foco en:
- recuperacion real (HRV, readiness, sueno, estres),
- prevencion de lesion,
- especificidad por objetivo (maraton/ultra/hyrox),
- integracion de ciclo menstrual para Malena,
- coordinacion en pareja.

La parte mas critica y diferencial tecnicamente es el pipeline:
- `resumen_usuario_para_plan` -> `generar_plan_semanal` -> `guardar_plan_semanal`.

Eso convierte datos recientes multi-fuente en decisiones semanales concretas de carga, intensidad, tipo de sesion y alertas de riesgo.
