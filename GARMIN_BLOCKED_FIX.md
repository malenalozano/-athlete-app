# ⌚ GARMIN - Solución Rápida para Bloqueo 429

## 🚫 Error: "Garmin ha bloqueado temporalmente el login por demasiados intentos"

Este error significa que Garmin está rechazando intentos de login desde el servidor Cloud porque detectó múltiples intentos en poco tiempo.

---

## ✅ SOLUCIÓN INMEDIATA (Sigue estos pasos)

### **Paso 1: En tu Ordenador** (LOCAL)

Abre terminal en la carpeta `athlete-performance-tracker`:

```bash
# Windows (PowerShell)
.venv\Scripts\activate

# Mac/Linux (Bash)
source .venv/bin/activate
```

### **Paso 2: Ejecuta el Script de Login**

```bash
python scripts/garmin_login_once.py
```

**Salida esperada:**
```
=== Login único Garmin ===
Email Garmin: tu-email@gmail.com
Password: ••••••••
Conectando con Garmin... (puede tardar 10-30 seg)

✓ Tokens guardados en DISCO: ~/.garth_athlete/tu-email@gmail.com
✓ Sesión activa como: Tu Nombre
✓ Tokens guardados en BASE DE DATOS (Turso)

✅ SUCCESS: Tokens guardados en disco Y BD.
   La app en Cloud podrá usar estos tokens sin volver a hacer login.
```

### **Paso 3: Espera 2-3 Minutos**

Los tokens deben propagarse en Turso Cloud.

### **Paso 4: Vuelve a la App en Cloud**

- Ve a https://share.streamlit.io/malenalozano/athlete-performance-tracker
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
