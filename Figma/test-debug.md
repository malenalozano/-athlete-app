# Debug Checklist para Figma Make

## Archivos Creados y Verificados:

### ✅ Estructura Principal
- `/src/app/App.tsx` - Punto de entrada principal
- `/src/app/AppRouter.tsx` - Maneja login vs app principal
- `/src/app/routes.ts` - Definición de rutas con react-router
- `/src/app/context/UserContext.tsx` - Context para manejo de usuario

### ✅ Páginas Completas
- `/src/app/pages/Login.tsx` - Pantalla de selección de perfil
- `/src/app/pages/Home.tsx` - Dashboard principal (COMPLETO)
- `/src/app/pages/Profile.tsx` - Página de perfil (COMPLETO)
- `/src/app/pages/CicloMenstrual.tsx` - Ciclo menstrual (COMPLETO)
- `/src/app/pages/BibliotecaCientifica.tsx` - Biblioteca (COMPLETO)
- `/src/app/pages/DiarioFuerza.tsx` - Diario de fuerza (COMPLETO)
- `/src/app/pages/PersonalTrainer.tsx` - Entrenador con 4 tabs (COMPLETO)
- `/src/app/pages/Calendario.tsx` - Calendario semanal

### ✅ Componentes
- `/src/app/components/Header.tsx` - Header con navegación dinámica
- `/src/app/components/KPICard.tsx` - Tarjetas de métricas
- `/src/app/components/CheckpointCard.tsx` - Tarjetas de checkpoints

### ✅ Componentes UI (Shadcn)
Todos los componentes UI de Radix están instalados y configurados

## Posibles Problemas y Soluciones:

### 1. Si la app no carga nada:
**Problema**: Puede que el sistema esté esperando en la pantalla de login
**Solución**: En el navegador, debería verse la pantalla de login primero

### 2. Si hay error de "Cannot find module":
**Problema**: Alguna importación incorrecta
**Verificar**:
- Todos los imports usan rutas relativas correctas
- No hay imports de 'react-router-dom' (debe ser 'react-router')

### 3. Si los estilos no se ven bien:
**Problema**: Tailwind no está aplicando correctamente
**Verificar**: Los colores personalizados están en los archivos

### 4. Para probar rápidamente:
1. La app debe mostrar primero el Login
2. Seleccionar "Malena" o "Dani"
3. Debería redirigir automáticamente al Dashboard
4. La navegación debe mostrar todas las páginas
5. "Ciclo Menstrual" solo aparece si eres Malena

## Flujo Esperado:
```
1. App carga → UserProvider inicializa
2. AppRouter verifica si hay userId
3. No hay userId → Muestra Login
4. Usuario selecciona perfil → setUser() guarda en localStorage
5. userId existe → Muestra RouterProvider con rutas
6. Header aparece en todas las páginas
7. Navegación funciona correctamente
```

## Verificación de Dependencias:
Todas las dependencias necesarias están en package.json:
- ✅ react-router: 7.13.0
- ✅ lucide-react: 0.487.0
- ✅ @radix-ui/* (todos los componentes UI)
- ✅ tailwindcss: 4.1.12
