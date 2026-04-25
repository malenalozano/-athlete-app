# 📊 Predicción del Ciclo Menstrual - Documentación

## Cambios Implementados

### 1. **Eliminación de Opciones Duplicadas** ❌
Se han eliminado las opciones de sangrado que eran duplicadas o no relevantes:
- ❌ **"Manchado"** - Eliminado (era duplicado de Ligero)
- ❌ **"Flujo"** - Eliminado (no cuenta como día de regla)

Se mantienen solo:
- ✅ **"Sin sangre"** - Sin sangrado
- ✅ **"Ligero"** - Sangrado ligero (cuenta como día de regla)
- ✅ **"Medio"** - Sangrado medio (cuenta como día de regla)
- ✅ **"Fuerte"** - Sangrado fuerte (cuenta como día de regla)

### 2. **Sistema de Historial de Ciclos** 📅
Se creó una nueva tabla en la base de datos: `historial_ciclos_menstruales`

Almacena para cada ciclo:
- `fecha_inicio_regla`: Primer día de la menstruación
- `fecha_fin_regla`: Último día de la menstruación
- `duracion_menstruacion_dias`: Cantidad de días que dura la regla
- `duracion_ciclo_dias`: Días entre el inicio de una regla y la siguiente
- `fecha_siguiente_regla`: Fecha predicha del siguiente ciclo

### 3. **Funciones de Análisis** 🔬

#### `calcular_ciclos_desde_registros(usuario_id, conn)`
Calcula todos los ciclos menstruales basados en los registros de sangrado real.

**Retorna:** Lista de diccionarios con información de cada ciclo

```python
[
    {
        "fecha_inicio_regla": date(2024, 1, 1),
        "fecha_fin_regla": date(2024, 1, 5),
        "duracion_menstruacion_dias": 5,
        "duracion_ciclo_dias": 27,
        "fecha_siguiente_regla": date(2024, 1, 28),
    },
    ...
]
```

#### `obtener_estadisticas_ciclo(usuario_id, conn)`
Calcula estadísticas agregadas del ciclo menstrual.

**Retorna:** Diccionario con estadísticas:

```python
{
    "duracion_promedio_ciclo": 28,           # Promedio de días entre ciclos
    "duracion_promedio_menstruacion": 5,     # Promedio de días de sangrado
    "ciclos_registrados": 3,                 # Cantidad de ciclos completos registrados
    "proxima_regla_predicha": date(...),     # Predicción del próximo ciclo
    "duracion_proxima_predicha": 5,          # Duración predicha de la menstruación
}
```

#### `guardar_ciclo_en_historial(usuario_id, conn, ciclo_info)`
Guarda un ciclo menstrual en el historial para futuras referencias.

### 4. **Panel de Estadísticas en la UI** 📈

En la sección del ciclo menstrual del diario se agregó un panel con:

- **Ciclos registrados:** Número total de ciclos completos registrados
- **Duración promedio:** Promedio de días entre ciclos (ej: 28 días)
- **Menstruación promedio:** Promedio de días que dura la menstruación (ej: 5 días)
- **Próxima regla en:** Predicción de cuántos días faltan para la próxima menstruación
- **Predicción:** Fecha predicha del inicio y duración de la próxima regla

### 5. **Lógica de Cálculo** ⚙️

#### Identificación de Ciclos
1. Se identifican bloques de días consecutivos con sangrado real (Ligero/Medio/Fuerte)
2. Se valida que cada bloque sea de:
   - Mínimo 2 días de sangrado, O
   - 1 día de sangrado pero separado de otros por al menos 20 días

#### Cálculo de Duración de Ciclo
La duración del ciclo se calcula como:
- Diferencia de días entre el inicio de una regla y la siguiente
- Se valida que esté en rango realista (20-40 días)
- Solo ciclos con siguiente se utilizan para calcular el promedio

#### Predicción del Próximo Ciclo
Si hay ciclos registrados:
- Se usa la última fecha de inicio de regla
- Se suma el promedio de duración del ciclo
- Se predice que durará el promedio de días de menstruación

Si no hay ciclos:
- Promedio por defecto: 28 días de ciclo
- Menstruación por defecto: 5 días

### 6. **Cambios en Base de Datos** 💾

#### Nueva Tabla
```sql
CREATE TABLE historial_ciclos_menstruales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    fecha_inicio_regla TEXT NOT NULL,
    fecha_fin_regla TEXT NOT NULL,
    duracion_menstruacion_dias INTEGER,
    fecha_siguiente_regla TEXT,
    duracion_ciclo_dias INTEGER,
    registrado_en TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(usuario_id, fecha_inicio_regla)
);
```

#### Nuevo Índice
```sql
CREATE INDEX idx_ciclo_usuario_fecha ON historial_ciclos_menstruales(usuario_id, fecha_inicio_regla)
```

## Cómo Usar

### Registro de Datos
1. Ve a la sección "Diario" → "Ciclo"
2. Selecciona la fecha del registro
3. Indica el tipo de sangrado:
   - **Sin sangre** si no hay sangrado ese día
   - **Ligero** para sangrado ligero (cuenta como día de regla ✓)
   - **Medio** para sangrado medio (cuenta como día de regla ✓)
   - **Fuerte** para sangrado fuerte (cuenta como día de regla ✓)
4. (Opcional) Agrega síntomas, ánimo y feedback del entreno
5. Haz clic en "Guardar"

### Interpretación de Estadísticas

Después de registrar al menos **2 ciclos completos**, verás:

| Métrica | Significado |
|---------|------------|
| **Ciclos registrados** | Número de ciclos que has registrado completamente |
| **Duración promedio** | Media de días entre menstruaciones (típicamente 21-35 días) |
| **Menstruación promedio** | Media de días que dura tu regla (típicamente 3-7 días) |
| **Próxima regla en** | Días que faltan para tu próximo ciclo (predicción) |
| **Predicción** | Fecha exacta y duración esperada |

## Ejemplos

### Ejemplo 1: Ciclo Regular
```
Ciclo 1: 1-5 enero (5 días) → Ciclo 2: 28 enero (27 días después)
Ciclo 2: 28-31 enero (4 días) → Ciclo 3: 24 febrero (27 días después)

Promedio: 27 días de ciclo, 4.5 días de menstruación
Próxima predicción: 23 marzo (27 días después del 24 febrero)
```

### Ejemplo 2: Ciclo Irregular
```
Ciclo 1: 1-5 enero (5 días) → Ciclo 2: 28 enero (27 días después)
Ciclo 2: 28-31 enero (4 días) → Ciclo 3: 20 febrero (23 días después)
Ciclo 3: 20-23 febrero (4 días) → Ciclo 4: 18 marzo (24 días después)

Promedio: 24.5 ≈ 25 días de ciclo, 4 días de menstruación
Próxima predicción: 12 abril (25 días después del 18 marzo)
```

## Notas Importantes

⚠️ **La predicción es más precisa después de registrar:**
- Mínimo 3-6 meses de datos
- Ciclos completos y consecutivos
- Los ciclos irregulares afectarán la precisión

🔔 **Cambios Importantes:**
- Las opciones "Manchado" y "Flujo" han sido eliminadas
- Solo se cuentan Ligero/Medio/Fuerte como días de regla
- Los datos históricos con "Manchado" o "Flujo" no se modifican automáticamente

✨ **Nuevas Capacidades:**
- Visualiza el historial de tus ciclos
- Predice automáticamente tu próxima menstruación
- Optimiza tu entrenamiento según el ciclo
- Identifica patrones de regularidad

## Archivos Modificados

1. **src/db/models.py** - Nueva tabla de historial de ciclos
2. **src/db/db_manager.py** - Inicialización de la tabla nueva
3. **src/core/ciclo_helpers.py** - Funciones de cálculo y análisis
4. **pages/03_diario.py** - UI mejorada con estadísticas

## Próximas Mejoras Sugeridas

- 📱 Notificaciones de ciclo predicho
- 📊 Gráficas de tendencias del ciclo
- 🎯 Recomendaciones de entrenamiento por fase del ciclo
- ⚙️ Configuración manual de duración de ciclo personalizada
- 🔄 Sincronización con aplicaciones de salud
