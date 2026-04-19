# 🔐 Configuración de Autenticación

## Sistema Nuevo (Activado)

La app ahora usa **autenticación simple con una única contraseña maestra** para acceder.

### Cómo Configurar

#### 1. Configuración Local (Para desarrollo/testing)

Edita o crea el archivo `.streamlit/secrets.toml`:

```toml
APP_PASSWORD = "tu_contraseña_aqui"
```

Guarda el archivo. La próxima vez que recargues la app, te pedirá la contraseña.

#### 2. Configuración en Streamlit Cloud

En **Streamlit Cloud Dashboard**:
1. Ve al deploy de tu app
2. **Settings** → **Secrets**
3. Añade:
   ```
   APP_PASSWORD = "tu_contraseña_aqui"
   ```
4. La app se redeploy automáticamente

### Flujo de Acceso

1. **Login**: Ingresa la contraseña maestra → Acceso a la app
2. **Menú**: Haz clic en el avatar (arriba derecha) → Selector de perfil (Malena / Dani)
3. **Cambiar Perfil**: Elige entre **Malena** o **Dani** en cualquier momento
4. **Logout**: Botón "🚪 Cerrar sesión" en el menú

### Características Seguridad

✅ **Contraseña única** — Solo 1 contraseña para toda la app  
✅ **Cookies persistentes** — Se mantiene autenticado 30 días (sin reintentos)  
✅ **Sin usuario/contraseña duplicado** — Simpler y más seguro  
✅ **Perfil switcheable** — Cambiar entre Malena y Dani sin logout  
✅ **Logout completo** — Limpia todo (caché, cookies, sesiones)  

### Resetear Autenticación

Si quieres acceso libre nuevamente (desarrollo):

1. En `app.py`, comenta la línea:
   ```python
   # require_auth(_cm)
   ```

2. O elimina/deja vacía la variable `APP_PASSWORD` en secrets

---

**Nota**: Sin `APP_PASSWORD` configurada, la app carga sin autenticación (acceso libre).
