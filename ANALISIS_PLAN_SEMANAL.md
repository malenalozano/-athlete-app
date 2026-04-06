# 📊 Análisis del Sistema de Plan Semanal Adaptativo

## 1. FLUJO ACTUAL DE GENERACIÓN (Cómo funciona hoy)

```
Usuario solicita plan
         ↓
generar_entrenamiento_semana() [entrenador.py]
         ↓
generar_plan_semana() [motor.py]  ← DECISIONES PYTHON (100% determinista)
         ↓
┌────────┴────────────────────────────┐
│ PIPELINE DE CÁLCULO                  │
├──────────────────────────────────────┤
│ 1. cargar_datos_plan()               │
│    - HRV (actual + media 7d)         │
│    - Sleep score + breakdown         │
│    - Lesiones activas + grados       │
│    - Km semana anterior              │
│    - Cadencia, ACWR                  │
│    - Métricas running (7d promedio)  │
│    - Ciclo menstrual                 │
│    - Stress, Body Battery, VO2max    │
│    - Training Status Garmin          │
│    - Actividades Z2 (últimas 28d)    │
│                                      │
│ 2. obtener_fase_macrociclo(fecha)   │
│    → Determina mes → Fase + reglas   │
│    (Acondicionamiento/General/       │
│     Específica/Pico/Tapering)        │
│                                      │
│ 3. calcular_semaforo()               │
│    - HRV actual vs media (caída %)   │
│    - Sleep score (< 60 rojo)         │
│    - Sleep profundo (< 45min rojo)   │
│    - Estrés (> 75 rojo)              │
│    - Body Battery min (< 10 rojo)    │
│    - Training Status Garmin          │
│    → Color: VERDE/ÁMBAR/ROJO         │
│    → Multiplicador volumen           │
│                                      │
│ 4. ajustar_por_ciclo()               │
│    - Fase menstrual                  │
│    - Multiplica volumen (0.8-1.05)   │
│    - Bloquea calidad si lútea        │
│                                      │
│ 5. aplicar_restricciones_lesion()    │
│    - Cada lesión grado 1-3           │
│    - Bloqueos/sustituciones          │
│    - Alertas                         │
│                                      │
│ 6. evaluar_cadencia()                │
│    - < 170 spm → necesita drills     │
│    - > 175 spm → puede subir 10%     │
│                                      │
│ 7. calcular_volumen_semana()         │
│    - km_anterior × 1.10 (base)       │
│    - Si ACWR > 1.5 → × 0.5 (descarga)│
│    - Si ACWR > 1.3 → mantener        │
│    - Si lesión activa → × 0.5        │
│    - Respeta fase km_max             │
│                                      │
│ 8. evaluar_eficiencia_aerobica()     │
│    - Compara Z2 pace/HR últimos 30d  │
│    - Si no mejora → fuerza fartlek   │
│                                      │
│ 9. Multiplicadores finales            │
│    km_objetivo × semaforo × ciclo    │
│                                      │
│ 10. distribuir_semana()              │
│     - Template fijo por fase         │
│     - Aplica semáforo (rojo→regen)   │
│     - Aplica lesión (bloqueos)       │
│     - Distribución km en 7 días      │
│     - Inserta drills si cadencia <170│
└──────────────────────────────────────┘
         ↓
_construir_contexto_atleta() [entrenador.py]
         ↓
Para CADA DÍA (no-descanso):
  _pedir_descripcion_ia() → Gemini
         ↓
_generar_recomendaciones_nutricion()
_generar_reporte_semanal()
         ↓
RETORNA plan completo + contexto IA
```

## 2. QUÉ TIENE EN CUENTA ACTUALMENTE

### ✅ IMPLEMENTADO (después de cambios)
- **HRV multi-señal**: Caída %, media 7d
- **Sleep integral**: Score + breakdown (profundo/REM/vigilia/despertares)
- **Stress Garmin**: 0-100 (rojo >75, ámbar >55)
- **Body Battery**: Min/max del día (rojo <10)
- **VO2max**: Estimado Garmin (solo display)
- **Training Status**: Productive/Peaking/Overreaching/Maintenance
- **Ciclo menstrual**: Fase + fatiga + estado ánimo
- **Métricas running**: GCT, oscilación, potencia, training effect aeróbico/anaeróbico
- **Lesiones**: Catálogo 6 lesiones × 3 grados
- **Cadencia**: Técnica drills si <170 spm
- **ACWR**: Carga aguda/crónica (descarga si >1.5)
- **Eficiencia aeróbica**: Z2 pace/HR trend
- **Regla 10%**: Volumen no supera anterior ×1.1
- **Nutrición básica**: Proteína 2g/kg, carbos, electrolitos, ciclo

### ⚠️ LIMITACIONES ACTUALES

1. **Template fijo por fase** (distribuir_semana)
   - L/M/X/J/V/S/D siempre igual
   - NO adapta a lesiones específicas del día anterior
   - NO reordena sesiones si hay conflicto

2. **VO2max NO se usa en reglas**
   - Solo en display del contexto IA
   - Podría bloquear/adaptar intensidad si <40 ml/kg/min

3. **Training Effect sin interpretación**
   - Se carga pero no influye en plan
   - Debería sugerir descanso si últimas 3 actividades > 4.5/5

4. **Estrategia de intensidad simplista**
   - Semáforo rojo → regen en TODO
   - No considera: "¿puedo hacer isquio excéntrico si tengo tendinitis pero no running?"
   - No diferencia "rojo por sueño" vs "rojo por lesión"

5. **Ciclo menstrual superficial**
   - Multiplica volumen pero no adapta TIPO de sesión
   - Fase lútea: debería reordenar (carrera suave primero, luego fuerza ligera)
   - No considera cramps → dolor grado 4-5

6. **Sueño profundo sin acción**
   - Se mide pero no ajusta (salvo estar incluido en semáforo rojo)
   - Si < 45 min: debería reducir series, no solo avisar

7. **Cadencia drills insertados pero no personalizados**
   - Siempre "+5min drills"
   - No sabe qué drills según issues (zancada larga, oscilación, GCT)

8. **Últimas 3 sesiones ignoradas en contexto plan**
   - ¿Hice 3 series hace 2 días? → IA no lo sabe para no repetir
   - Plan NO revisa si hay conflicto fuerza-serie en 48h

9. **IA sin restricción de cambios**
   - Gemini redacta descripción pero NO bloquea
   - Podría proponer "prueba fartlek" aunque semáforo = rojo

10. **Reporte semanal + nutrición desconectados del plan**
    - Se generan pero NO afectan a decisiones posteriores
    - Nutrición debería influir en intensidad (si proteína < 100g → reducir fuerza)

## 3. FLUJO DE DATOS ACTUAL (Qué entra, qué sale)

### ENTRADA (cargar_datos_plan)
```python
{
  "hrv_actual": 45.0,
  "hrv_media_7d": 50.0,
  "sleep_score": 75,
  "sleep_breakdown": {"profundo_h": 0.8, "rem_h": 1.2, ...},
  "lesiones_activas": [{"zona": "Periostitis", "grado": 1}],
  "km_semana_anterior": 30.5,
  "cadencia_media": 168,
  "acwr": 1.15,
  "metricas_running": {
    "potencia_media_w": 185,
    "tiempo_contacto_ms": 265,
    "oscilacion_vertical_cm": 8.2,
    "training_effect_aerobico": 3.8
  },
  "fase_ciclo": {"fase": "folicular", "fatiga_subjetiva": 3, "estado_animo": "bien"},
  "estres_medio": 45,
  "body_battery_max": 85,
  "body_battery_min": 22,
  "vo2max": 52.3,
  "training_status": "productive",
  "actividades_z2": [...]
}
```

### SALIDA (generar_plan_semana)
```python
{
  "dias": [
    {
      "dia": "Lunes",
      "fecha": "2025-04-07",
      "tipo": "Fuerza",
      "intensidad": "Media",
      "km": 0,
      "duracion_min": 60,
      "alerta": ""
    },
    ...
  ],
  "alertas": ["Cadencia baja...", "..."],
  "semaforo": {"color": "verde", "mensaje": "..."},
  "fase": {"fase_nombre": "Preparación Específica", ...},
  "km_totales": 52.3,
  "acwr": 1.15,
  "ciclo_ajuste": {"multiplicador_volumen": 0.85, ...},
  "metricas_running": {...},
  "training_status": "productive",
  "vo2max": 52.3
}
```

---

## 4. GAPS E IDEAS DE MEJORA

### 🎯 NIVEL 1: Mejoras implementables INMEDIATAMENTE

1. **Usar VO2max en decisiones**
   - Si VO2max < 45: máximo 1 sesión alta intensidad/semana
   - Si VO2max > 55: permite 2 sesiones alta intensidad

2. **Training Effect como predictor de descanso**
   - Si promedio últimas 3 sesiones > 4.5/5: avisar de descanso inminente
   - Si Training Effect anaeróbico > 4.0: reducir series esta semana

3. **Sueño profundo como acción, no solo métrica**
   - Si profundo < 45 min: reducir series en -50%, mantener Z2
   - Si profundo < 30 min: regenerativo total

4. **Cadencia + Oscilación = drills específicos**
   - Si GCT > 270: "enfoque en cadencia (180+ spm) + media zancada"
   - Si oscilación > 9: "enfoque en cadera/glúteo antes de regar"

5. **Historial de últimas 48-72h en regla**
   - Si [X-2] fue series VO2max: No permitir [X] con fuerza piernas
   - Si [X-1] fue tirada larga: [X] regenerativo FORZADO

6. **Semáforo diferenciado por causa**
   - Semáforo rojo por "sueño": permite fuerza ligera (no piernas)
   - Semáforo rojo por "HRV": solo regenerativo
   - Semáforo rojo por "lesión": bloqueos específicos

### 🎯 NIVEL 2: Mejoras estructurales (requieren BD/lógica nueva)

1. **Templates DINÁMICOS en lugar de fijos**
   - Generar template en tiempo real basado en:
     - Fase macrociclo + semáforo + ciclo + lesión
     - Ejemplo: si Preparación Específica + fase lútea + lesión rodilla
       → L=Fuerza tren superior, M=Z2, X=descanso, J=Carrera fácil, V=Fuerza tren superior, S=TL corta, D=regen

2. **Detector de conflictos + reordenador**
   - Si hay conflict fuerza-series en mismo día:
     - Opción A: mover series 48h atrás/adelante
     - Opción B: convertir series en fartlek (menos peso neuro-muscular)

3. **Predictor de lesión** (usando histórico)
   - GCT + oscilación + km semana pasada + sin descanso
     → Avisar "riesgo periostitis en 2-3 semanas"

4. **Nutrición bidireccional**
   - Si proteína diaria < 100g: bloquear fuerza, sugerir Z2 + descanso
   - Si carbos pérentrenamiento insuficientes: reducir duraciones

5. **Fase del ciclo + composición corporal**
   - Registrar peso diario
   - Fase lútea: si ganancia > 1.5 kg → edema → cargas acuáticas
   - Fase folicular: ventana mejor para hipertrofia → ajustar plan

### 🎯 NIVEL 3: Machine Learning / IA adaptativa

1. **Predicción de frecuencia cardíaca**
   - Histórico de ritmo_medio vs FC_media en Z2
   - Si relación empeora (ritmo sube pero FC baja): overtraining oculto

2. **Optimizer del plan semanal**
   - Red neuronal pequeña: entradas [fase, semáforo, ciclo, lesión, fitness]
     → outputs [tipo_sesión, km_ideal, intensidad_real]
   - Entrenada con tus datos históricos

3. **Predicción de sueño futuro**
   - Basada en: stress, intensidad del día, cafeína, menstruación
   - Avisar: "mañana dormirás poco → plan regenerativo"

---

## 5. PROPUESTA DE "SUPER ENTRENADOR" — MVP (Próximas 2-3 semanas)

Implementar NIVEL 1 + mejoras templates dinámicos básicos. Objetivo: pasar de "plan adaptativo" a "plan inteligente que previene".

**Fases:**
1. ✅ **Hecho**: Captura de datos 360° (Garmin + ciclo + lesiones)
2. ✅ **Hecho**: Semáforo multi-señal + ciclo menstrual
3. **TODO**: Validar VO2max + Training Effect en decisiones
4. **TODO**: Templates dinámicos + reordenador de conflictos
5. **TODO**: Drills específicos por biomecánica
6. **TODO**: Dashboard de predicciones (riesgo lesión, overtraining, descanso recomendado)

---

