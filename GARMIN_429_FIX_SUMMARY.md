# GARMIN 429 FIX - Resumen Técnico (Abril 2026)

## ¿QUÉ SE ARREGLÓ?

El problema raíz era que la aplicación intentaba hacer login repetidamente con credenciales, sin usar tokens OAuth guardados. Esto causaba múltiples fallos que activaban el bloqueo 429 de Garmin.

**Ahora:** La app prioriza tokens guardados, detecta bloqueos automáticamente, y previene reintentos durante 48 horas.

---

## CAMBIOS IMPLEMENTADOS

### 1. **src/garmin/garmin_sync.py**

#### Nuevas funciones:
```python
check_garmin_blockade()        # Verifica si hay bloqueo 429 activo
_record_429_blockade(hours=48) # Registra un bloqueo por N horas
_check_token_freshness(gc)     # Valida que token tenga >5 min de validez
```

#### Funciones mejoradas:
```python
iniciar_sesion_garmin()           # Ahora verifica blockade ANTES de intentar login
sincronizar_actividades_con_sesion()    # Valida token ANTES de iniciar
sincronizar_todo_con_sesion()     # Valida token ANTES de iniciar
```

#### Mecanismo de bloqueo:
- Archivo: `~/.garth_athlete/.blockade.json`
- Contenido: `{blocked_until: ISO_datetime, reason: str, created_at: ISO_datetime}`
- Duración: 48 horas por defecto
- Auto-limpieza: Al hacer login exitoso

### 2. **scripts/garmin_login_once.py**

#### Mejoras:
- ✅ Verifica bloqueo ANTES de intentar login
- ✅ Si hay bloqueo, muestra contador de tiempo restante
- ✅ Se niega a intentar login si hay bloqueo activo
- ✅ Limpia bloqueo automáticamente si login es exitoso
- ✅ Registra nuevo bloqueo si detecta 429

#### Flujo:
```
1. Verificar .blockade.json
2. Si activo y <48h: mostrar contador, salir
3. Si activo pero >48h: limpiar y continuar
4. Si no hay bloqueo: intenta login normal
5. Si 429: crear .blockade.json, mostrar instrucciones
6. Si éxito: limpiar .blockade.json importante
```

### 3. **pages/04_garmin.py**

#### Nueva sección:
- Verifica bloqueo al cargar página
- Si hay bloqueo: muestra banner rojo con contador
- Desactiva botones de reconexión/sincronización

#### Manejo de errores mejorado:
- Distingue 429 (espera 48h) vs auth_error (reconecta) vs network (reintenta)
- Mensajes claros y accionables

---

## ARCHIVOS AFECTADOS

| Archivo | Cambios | Líneas |
|---------|---------|--------|
| `src/garmin/garmin_sync.py` | +3 nuevas funciones, mejorado iniciar_sesion_garmin() | +150 |
| `scripts/garmin_login_once.py` | Añadido blockade detection/registration | +80 |
| `pages/04_garmin.py` | Importar check_garmin_blockade, banner, mejor error handling | +40 |
| `GARMIN_BLOCKED_FIX.md` | Documentación completa del nuevo sistema | +200 |

**Total cambios:** ~470 líneas

---

## CÓMO FUNCIONA AHORA

### Escenario 1: Usuario intenta conectar (sin bloqueo)
```
1. Verifica blockade → No hay
2. Intenta login con credenciales guardadas
3. Si 429 → Registra bloqueo por 48h, muestra error claro
4. Si éxito → Limpia bloqueo anterior si lo hay
```

### Escenario 2: Usuario intenta conectar (con bloqueo activo)
```
1. Verifica blockade → SÍ hay
2. Si tiempo < 48h → Calcula tiempo restante, muestra contador, SE NIEGA A INTENTAR
3. Si tiempo >= 48h → Limpia bloqueo, intenta login normalmente
```

### Escenario 3: Sincronización durante bloqueo
```
1. UI verifica blockade al cargar
2. Si hay bloqueo → Muestra banner rojo con contador
3. Botones "Conectar" y "Sincronizar" desactivados
4. Usuario NO puede hacer nada hasta que pase el bloqueo
```

---

## ARCHIVOS CLAVE

### Token/Bloqueo Storage:
- **Tokens locales:** `~/.garth_athlete/[email_slug]/` (archivos garth)
- **Tokens BD:** `usuarios.garmin_tokens` (Turso)
- **Bloqueo:** `~/.garth_athlete/.blockade.json`

### Logs:
- Ver `logger.debug()` en garmin_sync.py para detalles
- Mensaje de bloqueo también va a stderr

---

## TESTING

Se incluyó test automatizado (`test_blockade.py`):
```bash
python test_blockade.py
```

Verifica:
- ✅ Creación de .blockade.json
- ✅ Detección de bloqueo por check_garmin_blockade()
- ✅ Cálculo de tiempo restante
- ✅ Limpieza automática

---

## PRÓXIMAS MEJORAS

- [ ] Resend automático después de 48h (webhook)
- [ ] Detección de MFA bloqueando (fingerprint de error)
- [ ] Retry automático con exponential backoff
- [ ] Integración con MCP server si es posible
- [ ] Uso de datacenter dedicado de Garmin

---

## COMPATIBILIDAD

- ✅ Python 3.8+
- ✅ Windows / Mac / Linux
- ✅ Streamlit Cloud
- ✅ Local + BD remota (Turso)
- ✅ Tokens guardados en disco O BD

---

## SEGURIDAD

- ✅ Bloqueo es LOCAL, no se transmite
- ✅ Tokens se guardan encriptados en Turso
- ✅ Credenciales nunca se loguean
- ✅ .blockade.json solo contiene fecha/hora publicas

