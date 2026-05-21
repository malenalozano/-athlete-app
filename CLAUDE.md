# CLAUDE.md — Proyecto Athlete · Guía de Contexto Completa

> Este archivo es la fuente de verdad del proyecto. Léelo siempre antes de editar cualquier archivo.
> User instructions always override this file.

## ⚠️ GIT REMOTES — LEE ANTES DE HACER PUSH

Este repo tiene TRES remotes. Usa SIEMPRE `athlete-app`:

```
git push athlete-app main   ✅ CORRECTO — github.com/malenalozano/-athlete-app
git push origin main        ❌ MAL — va a athlete-performance-tracker (repo equivocado)
git push backend-origin     ❌ Solo para el backend API por separado
```

**NUNCA hacer push a `origin`** — es un repo antiguo que ya no se usa.

---

## 1. Estructura del Proyecto (ÚNICA fuente de verdad)

```
C:\Code\proyecto-athlete\
├── Figma/                  ← FRONTEND REAL (Vite + React + TypeScript)
│   ├── src/app/
│   │   ├── pages/          ← Páginas de la app (edita aquí las vistas)
│   │   ├── components/     ← Componentes reutilizables (Header, KPICard, etc.)
│   │   ├── context/        ← UserContext (userId, userName, setUser)
│   │   ├── api.ts          ← TODAS las llamadas al backend van aquí
│   │   └── routes.ts       ← Definición de rutas de React Router
│   ├── package.json
│   └── vite.config.ts
│
├── backend-fastapi/        ← BACKEND REAL (FastAPI + Python + SQLite/Turso)
│   ├── main.py             ← Punto de entrada, registra todos los routers
│   ├── database.py         ← Conexión a la base de datos
│   ├── routers/            ← Endpoints agrupados por dominio
│   │   ├── auth.py         ← POST /auth/login, GET/PUT /auth/perfil/{id}
│   │   ├── dashboard.py    ← GET /dashboard/{id}
│   │   ├── plan.py         ← GET/POST/PATCH/DELETE /plan/...
│   │   ├── garmin.py       ← GET /garmin/{id}/actividades, /stats, POST /sync
│   │   ├── diario.py       ← GET/POST /diario/fisiologia, /biometrico
│   │   ├── ejercicios.py   ← GET /ejercicios/{id}, POST /ejercicios/serie
│   │   └── entrenador.py   ← GET /entrenador/{id}/resumen
│   ├── requirements.txt
│   └── venv/               ← Entorno virtual Python del backend
│
├── src/                    ← Lógica de negocio Python compartida (plan, reglas, DB)
│   ├── plan/reglas.py      ← Reglas fisiológicas, semáforo HRV, zonas FC, etc.
│   └── db/
│       ├── db_manager.py   ← Funciones de acceso a datos
│       └── models.py       ← Modelos de datos
│
├── docs/                   ← Documentación (no editar)
│   └── MARATÓN.pdf
│
├── scripts/                ← Scripts de utilidad (migración, etc.) — no tocar
├── NORMAS ENTRENAMIENTO.pdf ← PDF con las reglas de entrenamiento (LEER antes de tocar plan.py)
├── setup-y-arrancar.bat    ← Script para arrancar backend + frontend
└── CLAUDE.md               ← Este archivo
```

**Carpetas que NO existen (fueron eliminadas):**
- `web/` — App Next.js antigua. ELIMINADA. No recrèarla.
- `streamlit-legacy/` — App Streamlit antigua. ELIMINADA.
- `_tmp_copy/`, `docs-archivo/` — Basura. ELIMINADAS.
- `Figma/dist/` — Build de producción. No commitear, se genera con `npm run build`.

---

## 2. Cómo arrancar el proyecto

```bat
# Doble click en:
setup-y-arrancar.bat

# O manualmente:
# Terminal 1 — Backend:
cd backend-fastapi
venv\Scripts\activate
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend:
cd Figma
npm run dev
```

**URLs:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Docs API: http://localhost:8000/docs

---

## 3. Páginas activas del frontend

| Ruta | Archivo | Descripción |
|------|---------|-------------|
| `/` | `pages/Home.tsx` | Dashboard principal (KPIs, checkpoints maratón) |
| `/diario` | `pages/Diario.tsx` | Diario: entreno libre, ciclo menstrual, ejercicios, lesiones |
| `/calendario` | `pages/Calendario.tsx` | Vista semanal del plan de entrenamiento |
| `/plan-semanal` | `pages/PlanSemanal.tsx` | Vista del plan semanal extendida |
| `/perfil` | `pages/Profile.tsx` | Perfil + Garmin (sincronización e historial) |
| `/entrenador` | `pages/PersonalTrainer.tsx` | Generador de plan IA, lesiones, asistente |
| `/ejercicios` | `pages/Ejercicios.tsx` | Biblioteca de ejercicios |
| `/ciclo-menstrual` | `pages/CicloMenstrual.tsx` | Solo Malena — ciclo menstrual |
| `/habitos` | `pages/Habitos.tsx` | Hábitos (sin navbar aún) |

**Páginas eliminadas (no recrear):** Nutricion, BibliotecaCientifica, DiarioFuerza, Garmin (fusionada en Perfil).

---

## 4. Navegación (Header.tsx)

El Header (`components/Header.tsx`) define los ítems visibles en la barra de navegación:

```
Inicio → /
Plan Semanal → /plan-semanal  (subtabs: Generar Plan, Datos)
Diario → /diario              (subtabs: Entreno Libre, Ciclo Menstrual*, Ejercicios, Lesiones)
Calendario → /calendario
Perfil → /perfil              (subtabs: Sincronización, Historial)
[Botón sync Garmin] [Selector Malena/Dani]
```

*Ciclo Menstrual solo visible para userId === 1 (Malena).*

**Para añadir una página al nav:** editar `NAV_ITEMS` en `Header.tsx` Y añadir la ruta en `routes.ts`.

---

## 5. Cómo añadir una nueva API call

1. Añadir el endpoint en el router correspondiente de `backend-fastapi/routers/`
2. Registrar la función en `Figma/src/app/api.ts`
3. Importar y usar en el componente

Ejemplo mínimo en `api.ts`:
```typescript
export function miFuncion(usuarioId: number) {
  return req<MiTipo>(`/mi-ruta/${usuarioId}`);
}
```

---

## 6. Usuarios del sistema

| userId | Nombre | Acceso especial |
|--------|--------|----------------|
| 1 | Malena | Ciclo Menstrual visible |
| 2 | Dani | Sin ciclo menstrual |

El usuario activo se gestiona con `useUser()` desde `context/UserContext.tsx`.
Persiste en localStorage. Se cambia desde el selector del header.

---

## 7. Reglas de entrenamiento (NORMAS ENTRENAMIENTO.pdf)

**LEER EL PDF antes de modificar `backend-fastapi/routers/plan.py` o `src/plan/reglas.py`.**

Resumen de reglas críticas implementadas:

- **Distribución semanal fija:** Lun=Pull · Mar=Calidad · Mié=Push · Jue=RB · Vie=Pierna · Sáb=RG · Dom=TL
- **Constraint de Fuerza:** Si día X = Pierna → día X+1 NO puede ser Fartlek/Tempo/Intervalos
- **Volumen:** +10%/semana, descarga ×0.70 cada 4ª semana ISO
- **TL:** 30-35% del total semanal, máximo absoluto 32 km
- **RG:** 1/3 de la TL, día siguiente a la TL
- **80% del entreno en Z1/Z2**
- **Macrociclos:** Mac1=May-Ago (Base), Mac2=Sep-Nov (Umbral), Mac3=Dic-Ene (Específico), Mac4=Feb (Tapering)
- **Fuerza en Mac2:** reducir pierna a 1 día pesado; 2º día = Core + Tren Superior
- **Fuerza en Mac3:** 1 día de pierna ligero (pliometría/saltos)

---

## 8. Base de datos

- **Desarrollo local:** SQLite (`data/athlete.db` o en `backend-fastapi/`)
- **Producción:** Turso (scripts de migración en `scripts/`)
- **Conexión:** `backend-fastapi/database.py` — función `get_db()`

Tablas principales:
- `usuarios` — perfiles de usuario
- `plan_entrenamiento` — sesiones del plan semanal
- `actividades_garmin` — actividades sincronizadas de Garmin
- `diario_fisiologia` — entradas del diario (ciclo, fatiga, ánimo)
- `diario_biometrico` — HRV, sueño, FC reposo (de Garmin)
- `ejercicios` — biblioteca de ejercicios
- `series_ejercicios` — registros de series realizadas

---

## 9. Reglas de desarrollo (prevención de errores)

1. **Nunca editar `web/`** — no existe, fue eliminada. El frontend es SOLO `Figma/`.
2. **Nunca editar la app Streamlit** — fue eliminada. El frontend es SOLO `Figma/`.
3. **Siempre leer el archivo antes de editarlo.**
4. **Para cambios en la lógica de plan:** leer `NORMAS ENTRENAMIENTO.pdf` primero.
5. **Para añadir rutas:** editar TANTO `routes.ts` COMO `Header.tsx` (si va al nav).
6. **Para nuevas llamadas API:** SIEMPRE pasar por `api.ts`, nunca fetch directo en componentes.
7. **No commitear `Figma/dist/`** — está en `.gitignore`.
8. **El backend corre en :8000, el frontend en :5173.** La variable `VITE_API_URL` en `Figma/.env.local` debe apuntar a :8000.
9. **Preferir `Edit` sobre reescribir archivos completos** — menos riesgo de perder código.
10. **Verificar build** después de cambios grandes: `cd Figma && npm run build`.

---

## 10. Variables de entorno

**Frontend** (`Figma/.env.local`):
```
VITE_API_URL=http://localhost:8000
```

**Backend** (`backend-fastapi/.env` si existe):
```
DATABASE_URL=...  (Turso en producción, vacío = SQLite local)
```

---

## 11. Iconos y design system

- **Framework UI:** shadcn/ui (componentes en `Figma/src/app/components/ui/`)
- **Iconos:** lucide-react
- **Color principal:** `#C9FF00` (verde lima)
- **Fondo:** `#0E1117`
- **Card background:** `#161B22`
- **Texto secundario:** `#8B949E`
- **Theme:** Dark, siempre. No añadir modo claro.

---

## 12. Historial de decisiones importantes

| Fecha | Decisión |
|-------|----------|
| 2026-05 | Frontend migrado de Next.js (`web/`) a Vite+React (`Figma/`) |
| 2026-05 | Eliminadas páginas: Nutricion, BibliotecaCientifica, DiarioFuerza |
| 2026-05 | Garmin fusionado en Perfil (subtabs Sincronización/Historial) |
| 2026-05 | Botón sync Garmin añadido al Header (disponible en toda la app) |
| 2026-05 | Generador de plan semanal implementado siguiendo NORMAS ENTRENAMIENTO.pdf |
| 2026-05 | Distribución de fuerza: 3 sesiones/sem (Pull/Push/Pierna) con constraint anti-colisión |
