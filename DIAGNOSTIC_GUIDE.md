# 🔧 GUÍA DE DIAGNÓSTICO: Importación de Datos Biométricos Garmin

## 📋 Estado Actual

He realizado una auditoría completa del código y he identificado y **ARREGLADO** varios problemas críticos:

### ✅ PROBLEMAS SOLUCIONADOS
1. **Logging silencioso** - `_safe_api_call()` ahora registra todos los errores
2. **Sin visibilidad en métricas** - `_extract_daily_metrics()` ahora muestra cada dato procesado
3. **Parsing incorrecto** - Verificado y validado (test_parsing.py: 100% éxito)
4. **Schema BD** - Verificado (todas las tablas existen y bien formadas)

### ⚠️ POSIBLES PROBLEMAS RESTANTES
1. **Credenciales Garmin inválidas o expiradas**
2. **Cambio de contraseña sin actualizar en BD**
3. **MFA (Multi-Factor Authentication) activo en Garmin**
4. **Datos realmente no disponibles en API de Garmin**
5. **Rate limiting de Garmin API**

---

## 🧪 CÓMO HACER LA PRUEBA

### **Opción 1: Prueba Simple (Recomendado)**
```bash
cd c:\Users\malen\OneDrive\ -\ Universidad\ Carlos\ III\ de\ Madrid\Personal\Proyecto\ Athlete\athlete-performance-tracker
python test_garmin_simple.py
```

**Qué esperar:**
- Se pedirá email y contraseña Garmin
- Verás logs detallados de cada paso
- Los resultados se guardarán en `garmin_sync_test.log`

**Output esperado:**
```
INICIANDO SINCRONIZACIÓN BIOMÉTRICA
- Iniciando sesión en Garmin... ✓
- Buscando actividades...
- Procesando fecha 2026-03-15:
  ✓ HRV: 45.5 ms
  ✓ Training Readiness: 78
  ✓ Body Battery: 85
  ... etc
SINCRONIZACIÓN COMPLETADA: 7 días procesados
```

### **Opción 2: Diagnóstico sin Credenciales**
```bash
python diagnose_garmin.py
```
(Verifica que el código está bien estructurado)

### **Opción 3: Test de Parsing**
```bash
python test_parsing.py
```
(Verifica que el parsing de datos funciona correctamente)

---

## 📊 QUÉ REVISAR EN LOS LOGS

Si la sincronización falla, busca estos mensajes en `garmin_sync_test.log`:

### ❌ ERROR: Autenticación
```
❌ ERROR DE AUTENTICACIÓN: Credenciales de Garmin incorrectas.
```
**Solución:** Verifica que el email y la contraseña son correctos. Prueba loguearte en https://connect.garmin.com directamente.

### ❌ ERROR: Conexión
```
❌ ERROR DE CONEXIÓN: Connection refused / Network error
```
**Solución:** Verifica tu conexión a internet

### ❌ ERROR: MFA
```
❌ ERROR DE AUTENTICACIÓN: MFA required / 2FA code needed
```
**Solución:** Desactiva temporalmente MFA en Garmin o usa un token guardado.

### ⚠️ WARNING: Datos Vacíos
```
⚠️ HRV: No encontrado
⚠️ Body Battery: No encontrado
```
**Significado:** La API de Garmin NO devolvió datos para esa fecha (probablemente porque el dispositivo no registró datos ese día)

---

## 🔍 CHECKLIST DE DIAGNÓSTICO

Responde SÍ o NO a estas preguntas:

- [ ] ¿Puedes loguearte en https://connect.garmin.com sin problemas?
- [ ] ¿Tu dispositivo Garmin está sincronizado (aparecen datos en el panel)?
- [ ] ¿Tienes datos de HRV/training readiness en los últimos 7 días?
- [ ] ¿No tienes MFA (2FA) activado en Garmin?
- [ ] ¿La contraseña de Garmin no ha cambiado recientemente?

**Si respondiste NO a alguna:**
- Soluciona ese problema en Garmin primero
- Luego intenta la sincronización nuevamente

---

## 💾 PRÓXIMOS PASOS POR FAVOR:

1. **Ejecuta** `python test_garmin_simple.py`
2. **Comparte** los errores/logs que veas
3. Responde el **checklist de diagnóstico** arriba
4. **Describe** qué datos VES en https://connect.garmin.com (¿HRV? ¿Readiness? ¿Sleep?)

Con esa información podré identificar exactamente qué falta.

---

## 📝 NOTAS TÉCNICAS

- Todos los cambios están en `garmin_sync.py`
- El logging ahora es DETALLADO (puedes ver cada llamada API)
- Si algo falla, aparecerá un mensaje claro (no silencioso)
- Los datos se guardan en `datos_biometricos_premium` de la BD local

