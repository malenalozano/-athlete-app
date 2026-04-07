# 🚫 Garmin 429 Rate Limit - GUÍA COMPLETA

## El Problema

Garmin bloqueó tu cuenta por **múltiples intentos de login fallidos desde Streamlit Cloud**.

Cuando intentas autenticarte desde la app en Cloud:
1. Tu IP es la del servidor Streamlit (no la tuya personal)
2. Garmin detecta múltiples intentos desde esta IP
3. Garmin **activa su sistema de seguridad antibot**
4. Bloquea TODOS los intentos de login desde esa IP

**Duración del bloqueo:** 24-48 horas (Garmin no publica el tiempo exacto)

---

## Por Qué Esto Sucede

```
Cloud App en browser → Intento de login (FALLA) 
                     → Reintento automático (FALLA)
                     → Otro reintento (FALLA)
                        ↓
                    🚫 GARMIN BLOQUEADO - 429 Rate Limit
```

Cada reintento **reinicia el contador de bloqueo** de Garmin.

---

## ✅ SOLUCIÓN: Login Local Una Sola Vez

En lugar de intentar login desde Cloud, hazlo **UNA SOLA VEZ desde tu ordenador personal**.

### Paso 1: Abre Terminal
```bash
cd athlete-performance-tracker
```

### Paso 2: Activa el Entorno Virtual
**Windows:**
```bash
.venv\Scripts\activate
```

**Mac/Linux:**
```bash
source .venv/bin/activate
```

### Paso 3: Ejecuta el Script de Login
```bash
python scripts/garmin_login_once.py
```

### Paso 4: Introduce Credenciales
El script te pedirá:
- Email de Garmin
- Contraseña de Garmin

**Ejemplo esperado:**
```
Introduce tu email de Garmin: malena@email.com
Introduce tu contraseña: ••••••••
⏳ Conectando a Garmin...
✅ SUCCESS: Tokens guardados en disco Y BD
```

### Paso 5: Espera 24-48 HORAS
No intentes acceder a Garmin hasta que el bloqueo expire automáticamente.

---

## ⏰ Cronograma

| Momento | Acción |
|---------|--------|
| **Ahora** | ❌ NO intentes nada. Espera 24-48 horas |
| **24-48 horas después** | ✅ Ejecuta el script local (`garmin_login_once.py`) |
| **10 min después del script** | ✅ Vuelve a Cloud, debería funcionar |

---

## 🔑 Qué Hace el Script

El script `garmin_login_once.py`:

1. **Connecta a Garmin** con tus credenciales
2. **Obtiene los tokens OAuth2** de Garmin
3. **Guarda los tokens en 2 lugares:**
   - Archivo local: `~/.config/garmin/tokens.json` (o en Windows: `%APPDATA%`)
   - BD Turso: tabla `garmin_tokens`
4. **Nunca más necesitará tu contraseña** — Cloud usará los tokens

---

## 🚫 Lo Que NO Debes Hacer

❌ No reinicies la app de Cloud  
❌ No intentes login múltiples veces  
❌ No llames al email de Garmin (no lo van a "desbloquear")  
❌ No uses una VPN (Garmin podría detectarla como intento de fraude)  
❌ No esperes que la app "se arregle sola" sin hacer el paso 4

---

## ✅ Lo Que Debes Hacer

✅ **Espera 24-48 horas** sin tocar nada de Garmin  
✅ **Ejecuta el script local** después del espacio de tiempo  
✅ **Vuelve al Cloud** y prueba la sincronización  

---

## ¿Y Si Sigue Fallando?

Si después de 48 horas y de ejecutar el script sigue fallando:

1. **Verifica que el script terminó bien:**
   ```bash
   # Busca "SUCCESS" en la salida
   python scripts/garmin_login_once.py
   ```

2. **Si ves "SUCCESS", prueba en Cloud:**
   - Recarga la página de Garmin (Ctrl+Shift+R)
   - Haz clic en "🔄 Sincronizar"
   - Espera 20 segundos máximo

3. **Si aún falla, contacta con Garmin Support:**
   - Email: support@garmin.com
   - Explica: "He intentado múltiples logins desde una app web y Garmin me bloqueó"
   - Solicita: "Desbloqueo manual de cuenta"

---

## 📊 Status de la Implementación

| Componente | Estado |
|-----------|--------|
| Script (`garmin_login_once.py`) | ✅ Listo |
| Almacenamiento de tokens | ✅ Dual (disco + BD) |
| Cloud app (usa tokens) | ✅ Listo |
| Documentación | ✅ Completa |
| Bloqueo Garmin | ⏳ Esperando 24-48h |

---

## 🎯 Resumen Rápido

**TL;DR:**

1. Espera **24-48 horas** (sin intentos)
2. Ejecuta: `python scripts/garmin_login_once.py` (desde tu PC)
3. Vuelve al Cloud y haz clic en "🔄 Sincronizar"
4. ✅ Debería funcionar

**Más info:** Ver GARMIN_BLOCKED_FIX.md para troubleshooting detallado.
