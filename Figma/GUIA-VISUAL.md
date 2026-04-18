# 📸 GUÍA VISUAL - Cómo Debería Verse Proyecto Athlete

## 🎨 Paleta de Colores Aplicada

```
FONDOS:
- Fondo profundo: #0E1117 (negro verdoso)
- Tarjetas/Cards: #161B22 (gris oscuro verdoso)
- Elementos secundarios: #30363D (gris medio)

ACENTOS:
- Verde neón principal: #C9FF00 (Garmin Volt)
- Texto secundario: #8B949E (gris claro)
- Pendiente/Warning: #D29922 (dorado)

ESPECIALES:
- Rosa (Malena): #EC4899 / tonos pink
- Azul (Dani): #3B82F6 / tonos blue
- Verde compartido: #C9FF00
```

## 🖥️ PANTALLA 1: LOGIN

```
┌─────────────────────────────────────┐
│                                     │
│         [👤 Badge]                  │
│     Proyecto Athlete                │
│  Selecciona tu perfil de atleta     │
│                                     │
│  ┌───────────────────────────┐     │
│  │      [MALENA]             │     │  ← Botón verde neón brillante
│  └───────────────────────────┘     │
│                                     │
│  ┌───────────────────────────┐     │
│  │       [DANI]              │     │  ← Botón gris con borde verde
│  └───────────────────────────┘     │
│                                     │
└─────────────────────────────────────┘
```

**Lo que deberías ver:**
- Fondo oscuro degradado verde
- Badge superior con icono de usuario
- Título "Proyecto Athlete" grande y blanco
- Subtítulo gris
- Botón Malena: verde neón (#C9FF00) super brillante con sombra
- Botón Dani: gris oscuro con borde verde neón

## 🖥️ PANTALLA 2: DASHBOARD (INICIO)

```
┌──────────────────────────────────────────────────────────────┐
│ HEADER                                                        │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ [👤] Proyecto  │ Inicio│Perfil│Ciclo...│Biblioteca... │   │
│ │ Athlete        │       │      │        │              │   │
│ │ Bienvenida,    │       │      │        │    [⟳] [👤] │   │
│ │ Malena         │       │      │        │              │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                               │
│ RESUMEN ÚLTIMOS 7 DÍAS                                       │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│ │  KM      │ │ CARRERAS │ │ FUERZA   │ │  SUEÑO   │        │
│ │  0.0     │ │    0     │ │    0     │ │    -     │        │
│ │ 7 días   │ │ 7 días   │ │ Sesiones │ │ h/noche  │        │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│  ↑ Borde izquierdo verde neón                               │
│                                                               │
│ OBJETIVO: MARATÓN                                            │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ 0 de 3 checkpoints completados        0%              │   │
│ │ [▓▓▓▓▓░░░░░░░░░░░░░░░░░] ← Barra verde con degradado │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                               │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐                     │
│ │   5K     │ │   10K    │ │  MEDIA   │                     │
│ │Sub 22:30 │ │Sub 44:30 │ │ Sub 1h42 │                     │
│ │ PENDIENTE│ │ PENDIENTE│ │ PENDIENTE│ ← Badge dorado      │
│ └──────────┘ └──────────┘ └──────────┘                     │
│                                                               │
│ [+ más secciones abajo con mismo estilo...]                  │
└──────────────────────────────────────────────────────────────┘
```

**Lo que deberías ver:**

### HEADER:
- Fondo: degradado oscuro con efecto cristal
- Borde: verde neón (#C9FF00) con glow
- Logo: cuadrado verde brillante con icono
- Navegación: botones tipo pill (píldora)
- Botón activo: fondo verde/20 con borde verde brillante
- Selector de usuario: dropdown con nombres

### TARJETAS KPI:
- Fondo: #161B22
- **Borde IZQUIERDO de 4px verde neón** ← IMPORTANTE
- Texto label: gris (#8B949E)
- Valor: blanco grande y bold
- Hover: sombra verde suave

### CHECKPOINTS:
- Fondo: #161B22
- Badge "PENDIENTE": dorado (#D29922)
- Badge "COMPLETADO": verde (#C9FF00)
- Descripción: gris claro

## 🖥️ PANTALLA 3: CICLO MENSTRUAL (solo Malena)

```
┌──────────────────────────────────────────────────┐
│ HEADER (igual que arriba)                        │
│                                                   │
│ ❤️ CICLO MENSTRUAL                               │
│                                                   │
│ ┌────────────────┐  ┌────────────────┐          │
│ │ FORMULARIO     │  │ MÉTRICAS       │          │
│ │                │  │                │          │
│ │ Fecha: ____    │  │ Ciclo: 28 días │          │
│ │ Fase: ____     │  │ Día: -         │          │
│ │ Fatiga: ___    │  │ Fase: -        │          │
│ │ Notas: ____    │  │ Próxima: -     │          │
│ │                │  │                │          │
│ │ [💾 GUARDAR]   │  │                │          │
│ └────────────────┘  └────────────────┘          │
│                                                   │
│ CALENDARIO DEL CICLO                             │
│ ┌──────────────────────────────────────────┐     │
│ │ Dom Lun Mar Mié Jue Vie Sáb            │     │
│ │  1   2   3   4   5   6   7             │     │
│ │  8   9  10  11  12  13  14             │     │
│ │ ... con colores por fase               │     │
│ └──────────────────────────────────────────┘     │
│                                                   │
│ LEYENDA:                                         │
│ [🔴 Menstrual] [🔵 Folicular] [🟢 Ovulación]    │
│ [🟡 Lútea] [⚪ Predicción] [⬜ Real]             │
└──────────────────────────────────────────────────┘
```

**Lo que deberías ver:**
- Borde rosa/purple en vez de verde
- Fondo degradado rosa suave
- Calendario con celdas coloreadas
- Diferencia visual entre dato real (borde sólido) y predicción (borde discontinuo)

## 🔴 SEÑALES DE QUE ALGO NO FUNCIONA:

1. **Si ves todo en blanco**: El CSS no está cargando
2. **Si no ves el verde neón**: Los colores personalizados no están aplicándose
3. **Si ves errores en consola**: Abre DevTools (F12) y verifica
4. **Si el header no aparece**: Problema con las rutas
5. **Si "Ciclo Menstrual" aparece para Dani**: El userId no está funcionando

## ✅ SEÑALES DE QUE TODO FUNCIONA:

1. Ves el fondo oscuro (#0E1117)
2. El verde neón (#C9FF00) brilla intensamente
3. Las tarjetas tienen borde izquierdo verde de 4px
4. Los hover effects funcionan
5. Puedes cambiar entre páginas
6. "Ciclo Menstrual" solo aparece para Malena

## 🎯 PARA TU COPILOT:

Si tu copilot de Figma no está aplicando el código, pídele que:

1. **Verifique que App.tsx sea el punto de entrada**
2. **Confirme que todos los archivos existen en /src/app/pages/**
3. **Revise que las rutas en routes.ts estén correctas**
4. **Asegúrese de que UserContext.tsx esté funcionando**
5. **Verifique la consola del navegador** para ver errores específicos
