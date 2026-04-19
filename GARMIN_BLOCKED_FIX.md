# ⌚ GARMIN 429 - Guía Completa de Solución

## 🚫 El Problema

### Error: "Garmin ha bloqueado temporalmente el login por demasiados intentos (429)"

**Esto significa que Garmin está rechazando TODOS los intentos de login** desde nuestra aplicación (o todas las aplicaciones) porque detectó múltiples fallos de autenticación en poco tiempo.

---

## 🔍 Por qué ocurre esto?

1. **La app está en Cloud de Streamlit** → Todas las peticiones vienen de la misma IP
2. **Se intenta login múltiples veces sin éxito** → Garmin interpreta esto como ataque
3. **El token expira y la app intenta refrescarlo** → Fallos en cadena = bloqueo de 24-48 horas

---

## 🛡️ Nuevo Sistema de Detección y Bloqueo (Implementado Abril 2026)

Ahora la app detecta el error 429 automáticamente y:

1. **Registra el bloqueo** en `~/.garth_athlete/.blockade.json`
2. **Previene reintentos** durante las próximas 48 horas
3. **Muestra contador** de tiempo restante en la UI
4. **Evita alargar** el bloqueo con intentos automáticos

---

## ✅ SOLUCIÓN: 4 Pasos Simples

### **Paso 1: ESPERAR 48 horas** ⏱️

**NO hagas nada por ahora.** Garmin mantiene bloqueada tu IP/cuenta durante 48 horas.

**⚠️ IMPORTANTE:**
- **NO intentes sincronizar** — la app te mostrará un banner diciendo que está bloqueada
- **NO intentes reconectar** — cada intento reinicia el contador
- **NO ejecutes `garmin_login_once.py`** — el script te lo impedirá automáticamente

**Lo que SÍ puedes hacer:**
- ✅ Usar la app normalmente con los datos ya guardados
- ✅ Entrenar y registrar datos locales
- ✅ Ver tu historial y estar preparado

### **Paso 2: Verificar el Tiempo de Bloqueo** (después de esperar)

Abre la página Garmin de la app:
- Si ves un **banner rojo** con ⏳ → Bloqueo aún activo
- Si **NO ves el banner** → ¡Bloqueo ha pasado! Ya puedes proceder

### **Paso 3: Preparar Tokens Locales**

En tu **ordenador personal:**

1. Abre PowerShell/Terminal ⚡
2. Navega a la carpeta:
   ```bash
   cd "C:\Users\[TuNombre]\OneDrive - Universidad Carlos III de Madrid\Personal\Proyecto Athlete\athlete-performance-tracker"
   ```

3. Activa el virtual environment:
   ```bash
   .venv\Scripts\activate
   ```

4. **Ejecuta (UNA SOLA VEZ):**
   ```bash
   python scripts/garmin_login_once.py
   ```

5. Introduce tus credenciales cuando aparezca el prompt:
   ```
   Email Garmin: tu-email@gmail.com
   Password: [escribe aquí]
   ```

   **Espera 10-30 segundos...**

6. **Verifica el éxito:**
   ```
   ✅ SUCCESS: Tokens guardados en disco Y BD.
   ```

   Si ves este mensaje, ¡todo está bien!

### **Paso 4: Vuelve a la App en Cloud**

En https://share.streamlit.io/malenalozano/athlete-performance-tracker:

1. **Ve a la pestaña Garmin** 🔄
2. **Panel izquierdo** → Verás el estado de conexión
3. **Pulsa "↻ Sincronizar todo"** → ✅ Debe funcionar

---

## ⏰ Tiempos de Bloqueo Registrados

| Situación | Tiempo Espera | Cómo se Registra |
|-----------|---|---|
| Después de error 429 | 48 horas | Script crea `.blockade.json` |
| Bloqueo detectado en app | 48 horas | Automático al detectar 429 |
| Token expirado durante sync | 24 horas | Extendido si Garmin sigue bloqueado |
| Bloqueo limpiado | Auto | Al hacer login exitoso |

---

## ❌ QUÉ NO DEBES HACER

- ❌ NO intentes reconectar mientras ves el banner rojo
- ❌ NO ejecutes `garmin_login_once.py` mientras haya bloqueo (el script lo impedirá)
- ❌ NO intentes sincronizar si aparece mensaje de bloqueo
- ❌ NO cambies contraseña en Garmin sin avisar (pueden saltarse los tokens)
- ❌ NO intentes hacer login desde múltiples aplicaciones al mismo tiempo

---

## 🔐 Cómo Funciona Internamente

### **Script `garmin_login_once.py`**
```
1. Verifica si hay .blockade.json
2. Si hay bloqueo activo:
   - Calcula tiempo restante
   - Muestra contador
   - Se niega a intentar login
3. Si no hay bloqueo:
   - Intenta login normalmente
   - Si detecta 429:
     - Crea .blockade.json con fecha +48h
     - Muestra mensaje claro de qué hacer
4. Si login exitoso:
   - Limpia .blockade.json
   - Guarda tokens en disco y BD
```

### **UI `pages/04_garmin.py`**
```
1. Al cargar la página:
   - Verifica check_garmin_blockade()
   - Si hay bloqueo:
     - Muestra banner rojo con contador
     - Desactiva botones de reconexión/sincronización
   - Si no hay bloqueo:
     - Muestra botones normales
2. Al intentar conectar:
   - Si detecta 429 en error:
     - Muestra mensaje detallado
     - Registra bloqueo automáticamente
```

---

## ❓ FAQs

**P: ¿Cuándo puedo volver a intentar?**
A: Cuando el contador en la app llegue a 0h0m. O cuando ejecutes el script y no veas el contador.

**P: ¿La app completamente inutilizable durante el bloqueo?**
A: No. Puedes ver tu historial, entrenar localmente, y ver tus datos guardados.

**P: ¿Qué pasa si la IP cambia (cambio de WiFi/móvil)?**
A: Posiblemente funcione. Prueba. Si aparece otro 429, se registra otro bloqueo.

**P: ¿Y si siempre falla el login?**
A: 
1. Verifica credenciales en panel "Sin conectar"
2. Asegúrate de que Garmin no está bloqueando por MFA
3. Busca "429" en mensaje de error - si aparece, espera 48h

**P: ¿Se afecta mi cuenta Garmin?**
A: No. Es solo un bloqueo temporal de acceso. Tu cuenta sigue siendo válida.

---

## 📞 Diagrama de Flujo

```
Usuario intenta conectar Garmin
         ↓
¿Hay bloqueo .blockade.json?
  ├─ NO → Intenta login normal
  │        ├─ ✅ Éxito → Limpia .blockade.json
  │        └─ ❌ Error 429 → Crea .blockade.json (48h)
  │
  └─ SÍ → ¿Ha pasado 48h?
           ├─ NO → Muestra contador, bloquea UI
           └─ SÍ → Limpia .blockade.json, intenta login
```

---

## 🔐 Seguridad

- ✅ Tus credenciales nunca se transmiten a la app si hay tokens guardados
- ✅ El archivo `.blockade.json` solo contiene fecha/hora, no datos sensibles
- ✅ Los tokens OAuth se guardan encriptados en Turso
- ✅ El bloqueo es LOCAL en tu ordenador/nube

---

## 📈 Próximas Mejoras Planeadas

- [ ] Resend automático después de 48h (sin intervención manual)
- [ ] Integración con servicio de MCP (Model Context Protocol) de Garmin
- [ ] Uso de datacenter dedicado de Garmin (para evitar bloqueos por IP compartida)
- [ ] Sincronización OAuth mediante navegador (más seguro)
- Abre la página **Garmin**
- Debería mostrar **"✓ Conectado"** sin pedir contraseña
- Pulsa **🔄 Sincronizar** (debería funcionar)

---

## ⏱️ Tiempos de Espera

| Situación | Tiempo de Espera |
|-----------|------------------|
| Primer login fallido | 15-30 min |
| Segunda vez fallida | 1-2 horas |
| Tercera vez fallida | 24-48 horas |

**NUNCA** vuelvas a intentar login desde Cloud si fallaste. Solo desde LOCAL con este script.

---

## 🔧 Si Aún No Funciona

### **Opción A: Resetear Credenciales Guardadas**

Si los tokens están corruptos, limpia primero:

```bash
# Windows
rmdir %USERPROFILE%\.garth_athlete /s /q

# Mac/Linux
rm -rf ~/.garth_athlete
```

Luego ejecuta de nuevo:
```bash
python scripts/garmin_login_once.py
```

### **Opción B: Verificar que Garmin ya Desbloqueó**

Puedes comprobar sin ejecutar el script. En Python:

```python
import time
from garminconnect import Garmin

# Si esta línea no tira error, Garmin ya desbloqueó
gc = Garmin(email="tu-email@gmail.com", password="tu-password")
gc.login()
print("✅ Login exitoso - ya puedes ejecutar el script")
```

### **Opción C: Esperar Más Tiempo**

Si todo falla, Garmin podría estar bloqueando tu IP por 24-48 horas. 

Intenta mañana desde otra red (WiFi móvil, otro ordenador, VPN, etc.)

---

## 📋 Checklist Final

- [ ] Ejecuté `python scripts/garmin_login_once.py` desde LOCAL
- [ ] Vi el mensaje **"SUCCESS: Tokens guardados"**
- [ ] Esperé 2-3 minutos
- [ ] La página Garmin en Cloud muestra **"✓ Conectado"**
- [ ] El botón 🔄 Sincronizar funciona sin error

---

## 💡 Cómo Funcionan los Tokens

1. **Primera vez (Local)**: El script hace login y guarda tokens (OAuth)
2. **Después (Cloud)**: La app SOLO usa los tokens, nunca pide contraseña
3. **Si expiran**: La app intenta renovarlos automáticamente (sin pedir contraseña)

**Importante**: Una vez guardados los tokens, **NUNCA** intentes hacer login directamente desde Cloud. Los tokens se renovarán automáticamente.

---

## 🆘 Último Recurso

Si nada funciona después de 48 horas:

1. Resetea todo:
   ```bash
   rm -rf ~/.garth_athlete  # o en Windows: rmdir
   ```

2. Cambia tu contraseña de Garmin en https://connect.garmin.com

3. Intenta nuevamente

4. Si Garmin sigue bloqueando, contacta con su soporte: support@garmin.com

---

## ✨ Referencia Rápida

```bash
# Ejecutar el login único
python scripts/garmin_login_once.py

# Reset de tokens si falla
rm -rf ~/.garth_athlete

# Verificar que Garmin desbloqueó (test)
python -c "from garminconnect import Garmin; gc = Garmin(email='tú', password='tú'); gc.login()"
```

**¡Debería funcionar después de estos pasos!** ✅
