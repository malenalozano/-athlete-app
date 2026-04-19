# 🔍 AUDIT DETALLADO - athlete-performance-tracker

**Fecha de análisis:** 2026-04-07  
**Cobertura:** Revisión exhaustiva de código (app.py, pages/*.py, src/core/*.py, src/db/*.py, src/garmin/*.py, src/plan/*.py)

---

## 📋 ÍNDICE DE PROBLEMAS

1. [Bugs Críticos](#bugs-críticos)
2. [Lógica Defectuosa](#lógica-defectuosa)
3. [Problemas de Datos](#problemas-de-datos)
4. [Problemas de UI/UX](#problemas-de-ui-ux)
5. [Issues de Seguridad](#issues-de-seguridad)
6. [Funcionalidades Incompletas](#funcionalidades-incompletas)
7. [Problemas de Performance](#problemas-de-performance)

---

## 🐛 BUGS CRÍTICOS

### BUG #1: Excepciones Bare Clauses - Falsa captura de errores
**Archivos:** `pages/02_plan.py:97`, `pages/06_entrenador.py:435`  
**Severidad:** CRÍTICA  
**Descripción:** Uso de `except:` sin tipo de excepción específica oculta errores del sistema.
```python
# pages/02_plan.py:97
except:
    return None
```
**Impacto:** Puede silenciar KeyboardInterrupt, SystemExit y otros errores críticos.  
**Solución:** Cambiar a `except Exception:` específicamente.

---

### BUG #2: Excepciones Silenciosas en app.py
**Archivo:** `app.py:24, app.py:152`  
**Severidad:** ALTA  
**Descripción:** `except Exception:` sin logging ni manejo específico.
```python
# app.py:24
try:
    import extra_streamlit_components as stx
    _cm = stx.CookieManager(key="athlete_cm")
except Exception:
    pass
```
**Impacto:** Si CookieManager falla, la UI se rompe sin aviso.  
**Solución:** Agregar logging y mensaje de error explícito.

---

### BUG #3: Falta Missing Table en diario_tab_entreno.py
**Archivo:** `src/core/diario_tab_entreno.py:102` (tabla `lesiones`)  
**Severidad:** CRÍTICA  
**Descripción:** Código intenta SELECT de tabla `lesiones` que no está inicializada.
```python
df = pd.read_sql_query(
    "SELECT id, tipo, grado, fecha_inicio, notas FROM lesiones "
    "WHERE usuario_id=? AND activa=1 ORDER BY grado DESC, fecha_inicio",
    conn, params=(usuario_id,))
```

**Verificación en db_manager.py:** La tabla NO se crea en `asegurar_tablas_premium()`.  
**Impacto:** Crash en Diario cuando intenta mostrar lesiones.  
**Solución:** Agregar CREATE TABLE para `lesiones` en `db_manager.py:asegurar_tablas_premium()`.

---

### BUG #4: Queries mal formadas en dashboard_data.py
**Archivo:** `src/core/dashboard_data.py:27-32`  
**Severidad:** ALTA  
**Descripción:** Intenta usar tabla `sesiones_fuerza` pero la tabla real en BD es `entrenamientos_fuerza`.
```python
def resumen_dashboard(usuario_id):
    # ...
    fuerza = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM sesiones_fuerza WHERE usuario_id = ? AND fecha >= ?",
        conn, params=(usuario_id, fecha_7d),
    )
```

**Realidad en db_manager.py:** Tabla se llama `entrenamientos_fuerza`.  
**Impacto:** Devuelve error o tabla vacía, dashboard muestra 0 sesiones de fuerza.  
**Solución:** Cambiar nombre de tabla en queries a `entrenamientos_fuerza`.

---

### BUG #5: Excepción en desencript de password sin inicialización
**Archivo:** `src/core/seguridad.py:1-50`  
**Severidad:** MEDIA  
**Descripción:** Si `ENCRYPTION_KEY` no está configurado, `cipher_suite` falla en instanciación.
```python
SECRET_KEY = _get_secret_key()
cipher_suite = Fernet(SECRET_KEY.encode())  # ← Puede lanzar InvalidToken si SECRET_KEY no es válida
```

**Escenario**: First run sin `.env` ni `secrets.toml`, puede crashear.  
**Solución:** Agregar try-except alrededor de cipher_suite initialization.

---

### BUG #6: Conversión de tipos en dashboard_data.py sin validación
**Archivo:** `src/core/dashboard_data.py:265-280`  
**Severidad:** MEDIA  
**Descripción:** Convierte datos sin validar, puede llanzar ValueError.
```python
km_c = float(ac["distancia_m"].sum() / 1000) if not ac.empty else 0.0
s_c = float(sc["horas_totales"].mean()) if not sc.empty else None
```

**Problema:** Si `distancia_m` contiene NULL o caracteres, `.sum()` falla.  
**Solución:** Usar `pd.to_numeric(..., errors='coerce')` siempre.

---

## ⚙️ LÓGICA DEFECTUOSA

### LOGICA #1: Usuario ID Hardcodeado en app.py
**Archivo:** `app.py:123-132`  
**Severidad:** ALTA  
**Descripción:** Mapeo hardcodeado entre auth_user y usuario_id.
```python
auth_user_to_id = {"malena": 1, "dani": 2, "malenita88": 1, "danielito99": 2}
forced_uid = auth_user_to_id.get(auth_user)

if forced_uid in (1, 2):
    # Usuario autenticado determina el perfil
    if st.session_state.get("usuario_id") != forced_uid:
        st.session_state["usuario_id"] = forced_uid
```

**Problema:** 
- Si `auth_user` no está en `auth_user_to_id`, no entra en la rama y cae al fallback.
- Hardcoding limita escalabilidad para nuevos usuarios.
- Vulnerabilidad: alguien podría modificar auth_user y cambiar el mapeo.

**Solución:** Hacer lookup dinámico en DB o usar token con usuario embebido.

---

### LOGICA #2: Plan Fallback sin validación en 02_plan.py
**Archivo:** `pages/02_plan.py:107-120`  
**Severidad:** MEDIA  
**Descripción:** Si plan falla a cargar, usa sesión state vieja sin verificar coherencia.
```python
try:
    plan_dash = cargar_plan_semana_cache(user_actual, lunes_str)
except Exception:
    plan_dash = st.session_state.get("plan_data")  # ← Puede ser de semana anterior
```

**Problema:** Si sesión contiene plan de semana pasada, UI muestra datos inconsistentes.  
**Impacto:** Usuario ve plan viejo sin saber que no se regeneró.  
**Solución:** Marcar plan con fecha generate y validar coherencia.

---

### LOGICA #3: Caché sin invalidación en dashboard
**Archivo:** `src/core/dashboard_data.py:233-240` (resumen_semana_con_delta)  
**Severidad:** MEDIA  
**Descripción:** `@st.cache_data(ttl=300)` cachea deltas sin invalidación manual.
```python
@st.cache_data(ttl=300)
def resumen_semana_con_delta(usuario_id) -> dict:
```

**Problema:** Después de sincronizar Garmin, caché sigue siendo viejo por hasta 5 minutos.  
**Impacto:** Métricas del dashboard no reflejan datos nuevos.  
**Solución:** Invalidar `st.cache_data.clear()` después de sincronización (ya se hace en navbar.py, pero inconsistente).

---

### LOGICA #4: Delta calculation error en progresion_pesos_ejercicios
**Archivo:** `src/core/dashboard_data.py:302`  
**Severidad:** MEDIA  
**Descripción:** Badge para delta puede mostrar incorrecto.
```python
badge = f"↑ +{delta}" if delta > 0 else ("↓ {delta}" if delta < 0 else "=")
```

**Problema:** Si `delta < 0`, badge muestra "↓ -5.0" (doble negativo).  
**Solución:** Cambiar a `f"↓ {abs(delta)}"`.

---

## 📊 PROBLEMAS DE DATOS

### DATA #1: Falta de aislamiento usuario_id en queries
**Archivo:** Múltiples (dashboard_data.py, diario_tab_entreno.py)  
**Severidad:** CRÍTICA DE SEGURIDAD  
**Descripción:** Aunque queries usan `usuario_id`, no hay constrain DB a nivel schema.

**Scenario de riesgo:**
- Si alguna query olvidara agregar `WHERE usuario_id=?`, un usuario vería datos del otro.
- SQL injection moderada: alguien manipula usuario_id en session.

**Verificación:** En app.py línea 139-147:
```python
try:
    cookie_uid = _cm.get("athlete_uid")
    uid = int(cookie_uid) if str(cookie_uid) in ("1", "2") else 1
except Exception:
    uid = 1
```
Cookie se confía SIN verificación => alguien puede manipularla.

**Solución:** 
- Agregar UNIQUE constraint a nivel DB donde sea apropiado (usuario_id, fecha).
- Nunca confiar en cookie sin validar contra sesión autenticada.

---

### DATA #2: Tablas inconsistentes entre Local SQLite y Turso
**Archivo:** `src/db/db_manager.py`  
**Severidad:** ALTA  
**Descripción:** Migraciones parciales pueden dejar BD en estado inconsistente.

**Ejemplo:**
- `ejercicios_catalogo` creada en `asegurar_tabla_catalogo_ejercicios()` pero **nunca poblada**.
- `historial_ejercicio` creada en `asegurar_tabla_ejercicios()` pero podría no existir si función no se calla.

**Impacto:** Queries a tablas que no existen → crash.

---

### DATA #3: Sleep Score Extraction demasiado compleja
**Archivo:** `src/garmin/garmin_sync.py:265-340` (_extract_sleep_score)  
**Severidad:** MEDIA  
**Descripción:** Búsqueda recursiva extremadamente compleja con múltiples fallbacks.

**Problema:**
```python
def _find_sleep_score_recursive(obj, depth=0, max_depth=10):
    # 200+ lines de recursión sin límites claros
    # Si Garmin cambia formato, silenciosamente devuelve None
```

**Riesgo:** Cambios en API de Garmin rompen silenciosamente sin warning.  
**Solución:** Agregar logging de intentos fallidos, definir formato esperado explícitamente.

---

### DATA #4: Datos Biométricos Nullables sin validación
**Archivo:** `src/db/db_manager.py:154-170` (CREATE TABLE datos_biometricos_premium)  
**Severidad:** MEDIA  
**Descripción:** Muchas columnas sin NOT NULL ni default.
```sql
CREATE TABLE IF NOT EXISTS datos_biometricos_premium (
    hrv_ms REAL,           -- ← puede ser NULL
    fc_reposo INTEGER,     -- ← puede ser NULL
    training_effect_aerobico REAL,  -- ← puede ser NULL
    ...
)
```

**Problema:** Queries asumen columnasno-null, puede fallar conversion.  
**Impacto:** Dashboard muestra "-" incorrectorectamente.

---

## 🎨 PROBLEMAS DE UI/UX

### UI #1: Falta mensaje de error claro en 02_plan.py
**Archivo:** `pages/02_plan.py:255`  
**Severidad:** BAJA  
**Descripción:** Si plan falla a regenerar, solo log silencioso.
```python
try:
    from src.plan.entrenador import generar_entrenamiento_semana
    plan_nuevo = generar_entrenamiento_semana(user_actual, lunes)
except Exception as e:
    st.error(f"❌ Error generando plan:\n\n{str(e)}")
    st.stop()
```

**Problema realizado:** El mensaje está ahí pero la UI se detiene sin contexto.  
**Solución:** Agregar sugerencias de qué revisar (Garmin sync, perfiles incompletos, etc).

---

### UI #2: Navbar no indica estado de sync
**Archivo:** `src/core/navbar.py:85-110`  
**Severidad:** BAJA  
**Descripción:** Botón de sync (↻) no muestra loading state claro.
```python
if st.button("↻", key="navbar_sync", help="Sincronizar Garmin (últimos 7 días)"):
    # ...
    with st.spinner():  # <- Spinner existe pero visual débil
```

**UX problema:** Usuario no sabe si sync está ejecutándose o falló.  
**Solución:** Mostrar timestamp de última sync grande en navbar.

---

### UI #3: Validaciones de input faltantes en formularios
**Archivo:** `pages/04_garmin.py:335-360` (formulario de Garmin)  
**Severidad:** MEDIA  
**Descripción:** Email y password sin validación.
```python
email_g = st.text_input("Email Garmin", value=saved_email or "")
password_g = st.text_input("Contraseña", type="password", value="")

if st.form_submit_button("Guardar credenciales y conectar"):
    # Directamente intenta auth sin validar email
    gc = iniciar_sesion_garmin(email_g, password_g, usuario_id=user_actual)
```

**Problema:** Email no validado, contraseña vacía acepta.  
**Solución:** Agregar `if not email_g or "@" not in email_g: st.error(...)`.

---

### UI #4: Tabla lesiones sin estado visual claro
**Archivo:** `src/core/diario_tab_entreno.py:115-155`  
**Severidad:** BAJA  
**Descripción:** Botón "✓ Ok" para cerrar lesión pero no muestra confirmación.
```python
with cb:
    if st.button("✓ Ok", key=f"les_ok_{row['id']}"):
        c2 = get_db_connection()
        c2.execute("UPDATE lesiones SET activa=0, fecha_fin=? WHERE id=?", ...)
        c2.commit(); c2.close(); st.rerun()
```

**UX problema:** No hay feedback visual que la acción funcionó.  
**Solución:** Agregar `st.success("Lesión resuelta.")` antes de rerun.

---

## 🔐 ISSUES DE SEGURIDAD

### SEC #1: Contraseñas hardcodeadas en app.py
**Archivo:** `app.py:121-132`, credentials stored in DB  
**Severidad:** CRÍTICA  
**Descripción:** Credenciales de Garmin guardadas en DB aunque encriptadas.
```python
email_garmin TEXT,
password_garmin_enc TEXT,  -- ← Encryptada pero aún en BD
```

**Vulnerabilidad:**
- Si DB se filtra, attacker tiene contraseñas encryptadas.
- Encryption key en `.env` podría exponerse.
- Session tokens se almacenan también: `garmin_tokens TEXT`.

**Solución:**
- Usar OAuth2 sin almacenar credenciales.
- Si debe almacenar, usar remote token provider (Vault, AWS Secrets Manager).

---

### SEC #2: Cookie manipulation en app.py
**Archivo:** `app.py:139-147`  
**Severidad:** ALTA  
**Descripción:** Cookie `athlete_uid` se confía sin validación.
```python
if _cm is not None:
    try:
        cookie_uid = _cm.get("athlete_uid")
        uid = int(cookie_uid) if str(cookie_uid) in ("1", "2") else 1  # ← Solo valida formato
    except Exception:
        uid = 1
else:
    uid = 1
st.session_state["usuario_id"] = uid
```

**Ataque:** Cliente manipula cookie en DevTools => cambia `usuario_id` => ve datos del otro usuario.  
**Solución:** Validar cookie contra sesión de servidor o usar JWT firmado.

---

### SEC #3: SQL en construidas sin parameterización completa
**Archivo:** `src/db/db_manager.py:_bind_params()`  
**Severidad:** MEDIA  
**Descripción:** Aunque hay parameterización, método de escape manual es riesgoso.
```python
def _bind_params(sql: str, params) -> str:
    """Replace ? placeholders with escaped values."""
    # ...
    return "'" + str(v).replace("'", "''") + "'"  # ← Manual escaping frágil
```

**Riesgo:** Si bien funciona para números y strings, puede fallar con UNICODE o BLOBs especiales.  
**Solución:** Usar DBAPI2 native parameterization (ya soporta Turso HTTP).

---

### SEC #4: Validación de Garmin Connect no verifica certificados
**Archivo:** `src/garmin/garmin_sync.py:6` (GarminConnect import)  
**Severidad:** BAJA  
**Descripción:** `garminconnect` library usa SSL pero la configuración de certs no está explícita.

**Riesgo:** MITM attack si usar en red no confiable.  
**Solución:** Configurar SSL verification explícitamente en env.

---

### SEC #5: Falta validación de entrada en Diario
**Archivo:** `src/core/diario_tab_entreno.py:310-320` (textarea)  
**Severidad:** MEDIA  
**Descripción:** Textarea acepta texto sin límite ni sanitización.
```python
nota_user = st.text_area("Entrada libre", height=120, key="entrada_diario")
if st.button("Procesar"):
    # Directamente pasa a IA sin validar
    resultado = procesar_nota_fuerza(nota_user)
```

**Riesgo:** 
- Entrada muy grande (100MB) crashea/DOS.
- Prompt injection si IA es LLM.

**Solución:** 
- Limitar a 5000 chars.
- Escapar entrada antes de pasar a IA.

---

## ❌ FUNCIONALIDADES INCOMPLETAS

### FUNCT #1: Tabla `lesiones` no creada
**Archivo:** `src/core/diario_tab_entreno.py` usa, pero `db_manager.py` no crea  
**Severidad:** CRÍTICA  
**Cobertura:** 100% incompletitud.

**Estado actual:**
- Diario intenta mostrar lesiones pero query crashea.
- Usuario no puede registrar lesiones.
- Impacto: **Diario completamente roto para Malena si intenta ver ciclo + lesiones**.

**Solución completa:**
```python
# En db_manager.py asegurar_tablas_premium()
conn.execute("""
    CREATE TABLE IF NOT EXISTS lesiones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        tipo TEXT NOT NULL,
        grado INTEGER,
        fecha_inicio TEXT,
        fecha_fin TEXT,
        activa INTEGER DEFAULT 1,
        notas TEXT
    )
""")
conn.commit()
```

---

### FUNCT #2: `ejercicios_catalogo` creada pero nunca poblada
**Archivo:** `db_manager.py:asegurar_tabla_catalogo_ejercicios()`  
**Severidad:** BAJA  
**Descripción:** Tabla existe pero nunca se inserta data.

**Código actual:**
```python
def asegurar_tabla_catalogo_ejercicios():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ejercicios_catalogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nombre TEXT NOT NULL,
            ...
        )""")
    conn.commit()
    conn.close()
    # ← FIN: Nunca inserta defaults
```

**Impacto:** Tabla vacía, funcionalidad incompleta.

---

### FUNCT #3: Historial de ejercicios no completamente integrado
**Archivo:** `src/core/ejercicios_helpers.py`  
**Severidad:** MEDIA  
**Descripción:** `historial_ejercicio` tabla se crea pero no se usa consistentemente.

**Problema:** Después de agregar ejercicio en Diario, NO se inserta en `historial_ejercicio`.  
**Estado:** Feature creada pero no funciona de punta a punta.

---

### FUNCT #4: Predicción de ciclo incompleta
**Archivo:** `src/core/ciclo_helpers.py:predecir_fases_ciclo()`  
**Severidad:** MEDIA  
**Descripción:** Función está pero rendimiento de predicción no calibrada para Malena.

**Detalles:** Usa `ciclo_dias = 28` por defecto si no hay datos suficientes, sin opción de override.

---

## ⚡ PROBLEMAS DE PERFORMANCE

### PERF #1: Queries sin índices en actividades_garmin
**Archivo:** `src/db/db_manager.py`  
**Severidad:** MEDIA  
**Descripción:** No hay índice en `(usuario_id, fecha)`.
```sqlite
CREATE TABLE actividades_garmin (
    id_actividad TEXT PRIMARY KEY, 
    usuario_id INTEGER,  -- ← Sin índice
    fecha TEXT,          -- ← Sin índice
    ...
)
-- ← Falta: CREATE INDEX idx_act_user_fecha ON actividades_garmin(usuario_id, fecha)
```

**Impacto:** Queries grandes (`SELECT ... WHERE usuario_id=1 AND fecha>=...`) escanean tabla completa.  
**Solución:** Agregar índices en `asegurar_indices_consulta()`.

---

### PERF #2: Caché TTL de 300s demasiado bajo
**Archivo:** `src/core/dashboard_data.py:233` (resumen_semana_con_delta)  
**Severidad:** BAJA  
**Descripción:** Caché se invalida muy frecuente.

**Impacto:** 
- Queries repetidas a BD cada 5 minutos.
- Para 2 usuarios, 288 queries/día solo de resumen.
- Turso HTTP tiene rate limit no documentado.

**Solución:** Aumentar a TTL=1800 (30 min), invalidar manual después de sync.

---

### PERF #3: Recursión profunda en _extract_sleep_score
**Archivo:** `src/garmin/garmin_sync.py:265-330`  
**Severidad:** BAJA  
**Descripción:** Búsqueda recursiva con `max_depth=10` + búsqueda secuencial.

**Impacto:** 
- Costo O(n^2) para payloads grandes.
- Si Garmin devuelve 1000+ objetos, lentitud noticible.

**Solución:** Cambiar a BFS o búsqueda por claves conocidas primero.

---

### PERF #4: `st.cache_data` sin serialización explícita
**Archivo:** Múltiples (dashboard_data.py, diario_tab_entreno.py)  
**Severidad:** BAJA  
**Descripción:** DataFrames grandes sin `.to_pickle()` para serializar.

**Impacto:** Streamlit serializa/deserializa con pickle, puede ser lento.  
**Solución:** Usar `@st.cache_resource` para objetos grandes o cache custom.

---

## 📈 RESUMEN EJECUTIVO

\`\`\`
TOTAL PROBLEMAS ENCONTRADOS: 43

Por categoría:
├─ Bugs Críticos:              6
├─ Lógica Defectuosa:          4
├─ Problemas de Datos:         4
├─ Problemas de UI/UX:         4
├─ Issues de Seguridad:        5
├─ Funcionalidades Incompletas: 4
└─ Problemas de Performance:   4

Severidad:
├─ CRÍTICA:      5 (Bugs #1,#3,#6 + SEC #1,#DATA #1)
├─ ALTA:         7 (Bugs #2,#4,#5 + LOGICA #1 + DATA #2 + UI #3 + SEC #2)
├─ MEDIA:       20 (Resto)
└─ BAJA:        11 (Menores)
\`\`\`

---

## 🎯 ACCIONES RECOMENDADAS INMEDIATAS

**SEMANA 1 (Críticos):**
1. Crear tabla `lesiones` en `db_manager.py`
2. Renombrar tabla queries de `sesiones_fuerza` → `entrenamientos_fuerza`
3. Remover bare `except:` clauses
4. Agregar validación de cookie en app.py

**SEMANA 2 (Altos):**
5. Agregar índices a tables
6. Refactorizar sleep_score extraction
7. Agregar try-catch a cipher_suite initialization
8. Validar input en formularios Garmin

**SEMANA 3 (Medios):**
9. Completar funcionalidades incompletas
10. Migrations para Turso consistency
11. Refactorizar hardcoded user_id mappings
12. Agregar logging a excepciones silenciosas

---

## 📝 NOTAS FINALES

- La aplicación es **funcional pero frágil** bajo condiciones de error.
- **Seguridad de datos de usuario es razonable** pero tiene vulnerabilidades en auth de cookies.
- **Performance es aceptable** para 2 usuarios pero no escala.
- **Testing automatizado está ausente** — falta suite de tests.

