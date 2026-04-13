Voy a hacer un inventario completo de la app directamente desde el código para darte una especificación útil para Figma: navegación, páginas, componentes, formularios, estados y datos que muestra cada sección.

He visto que el inventario automático salió con referencias desactualizadas, así que ahora lo saco manualmente del app.py actual para que sea fiel al estado real de tu app.

Perfecto. Te dejo una especificación funcional/UI completa de la app actual para que tu diseñador la pueda traducir a Figma con contexto real.

1. Flujo General De La App

La app es Streamlit con layout wide y sin sidebar (app.py:1483, app.py:1492).
Flujo de entrada:
Si no hay sesión de usuario, aparece pantalla de login con 2 botones: Malena y Dani (app.py:1501).
Si hay usuario pero no perfil guardado, aparece onboarding inicial (app.py:1574).
Si hay usuario + perfil, entra al shell principal con header y páginas.
Persistencia:
Se guarda el último usuario en ~/.athlete_last_user (app.py:17).
Se usa caché en varias lecturas para rendimiento (@st.cache_data en múltiples funciones).
2. Shell Principal (Header Superior)

Está compuesto en una sola fila de 4 bloques (app.py:2130):
Bloque marca/logo izquierda.
Bloque navegación central.
Botón sincronización Garmin.
Selector de perfil (Malena/Dani).
Layout actual de columnas:
[0.18, 0.67, 0.05, 0.10] (app.py:2131).
El contenedor superior tiene paleta verde/lima, borde destacado y estilo premium (app.py:1708).
Navegación central:
Todas las pestañas van en una línea con botones tipo “pill” calculando ancho por longitud del texto (app.py:2174).
Estado activo con borde lima brillante (app.py:1789).
Botón sync:
Icono circular ↻ con help="Sincronizar Garmin" (app.py:2160).
Selector usuario:
selectbox compacta con nombres de perfil (app.py:2167).
3. Pantalla De Login

Elementos (app.py:1508):
Badge superior con icono.
Título Proyecto Athlete.
Subtítulo Selecciona tu perfil de atleta.
Botón Malena (lima).
Botón Dani (verde oscuro).
Acción:
Selección de usuario y rerun inmediato.
4. Onboarding Inicial (Si Perfil No Existe)

Título + subtítulo (app.py:1575).

Formulario onboarding_form con 2 columnas (app.py:1578).

Columna izquierda:

Nombre, Edad, Sexo, Peso actual, Objetivo.
Bloque de conexión Garmin: Email Garmin, Contraseña Garmin (password).
Columna derecha:

Ritmo objetivo con 2 select_slider:
Límite superior (rápido).
Límite inferior (lento).
Disponibilidad:
Días de carrera/semana.
Días de fuerza/semana.
Validaciones al enviar (app.py:1611):

Nombre obligatorio y mínimo 2 caracteres.
Rango edad/peso.
Coherencia de ritmo.
Validación básica de email.
Si hay email Garmin, exige contraseña.
Longitud mínima contraseña Garmin.
CTA: 🚀 Generar mi Ecosistema.

5. Menú Principal (Páginas)

Opciones base (app.py:2114):
Inicio
Perfil
Biblioteca Científica
Diario de Fuerza
Entrenador Personal
Calendario
Condicional:
Ciclo Menstrual solo aparece para Malena (user_actual == 1) (app.py:2122).
Estado de navegación en st.session_state.main_nav (app.py:2124).
6. Página Inicio
Referencia: app.py:2216

Contiene:

Título visual Inicio.
Bloque resumen 7 días:
Km, número de carreras, sesiones fuerza, horas sueño media.
Si usuario es Dani:
Módulo “Estado del ciclo de Malena” con fase, próxima regla y consejos (app.py:2236).
Checkpoints y pequeños logros (módulo de progreso objetivo).
Entrenamientos esta semana:
7 tarjetas (lunes-domingo) con actividad del día.
Progreso de running:
Gráfico línea km/semana.
Radar Antilesiones y Técnica:
Métricas biomecánicas + avisos.
Semáforo Diario Garmin:
HRV, readiness, body battery, recuperación, RHR, SpO2 + warnings.
Progreso de gimnasio por grupo muscular:
Gráfico multi-línea por grupo muscular.
Calidad del Sueño:
Bar chart horas/score + métricas de sueño.
Entrenamientos conjuntos — Malena & Dani:
Calendario semanal comparado (colores rosa/celeste/verde cuando coinciden).
Leyenda de colores al final.
7. Página Perfil
Referencia: app.py:2464

Contiene:

KPIs rápidos:
Objetivo, Ritmo, Carrera/sem, Fuerza/sem.
Expander Datos completos que se pasan a la IA:
Tabla completa de campos de perfil + biométricos/contexto.
Formulario perfil_edit_form:
Columna izquierda:
Nombre, edad, sexo, peso, objetivo.
Columna derecha:
Ritmo objetivo (2 sliders).
Disponibilidad (días carrera/fuerza).
Bloque Garmin opcional (email + nueva contraseña).
Validaciones equivalentes al onboarding.
CTA:
💾 Guardar cambios de perfil.
8. Página Biblioteca Científica
Referencia: app.py:2647

Contiene:

Texto explicativo de cómo se guarda.
Alcance del estudio: solo perfil o compartido.
Categoría del estudio.
File uploader (pdf, txt, md).
Campo de resumen manual opcional.
Botón guardar estudio.
Listado de estudios previos (expanders con resumen y fecha).
9. Página Ciclo Menstrual (solo Malena)
Referencia: app.py:2713

Contiene:

Restricción de acceso (Dani ve mensaje de no disponible).
Formulario fisio_form:
Fecha.
Fase del ciclo.
Fatiga 1-10.
Notas/molestias.
Guardado en diario fisiología.
Visualización:
Métrica de ciclo estimado.
Calendario de fase (real vs predicción).
Tabla de próximas fases predichas.
10. Página Diario De Fuerza
Referencia: app.py:2770

Contiene:

Text area de entrada libre (“entreno libre”).
Detección automática de múltiples fechas en un solo texto.
Botón Procesar entrenamiento con IA.
Resultado:
Tabla de ejercicios detectados por sesión.
Botón guardar una o varias sesiones.
Historial:
Expanders por sesión con detalle de ejercicios.
11. Página Entrenador Personal Premium
Referencia: app.py:2920

Tiene 4 tabs internas (app.py:2923):

📊 Check-in Diario
🧠 Generar Plan Semanal
🩹 Lesiones y Prevención
🤖 Asistente Virtual
Tab Check-in Diario

Sincronización biométricos Garmin.
Dashboard de métricas (HRV, readiness, body battery, etc).
Tabla últimos 7 días biométricos.
Tabla de sueño detallado.
Tab Generar Plan Semanal

Señales de estado (HRV, estrés, sueño, RPE, etc).
Fecha de semana a planificar.
Opción coordinar con pareja.
Botón generar plan premium.
Tabla de plan guardado.
Bloque de feedback para reajuste con IA.
Tab Lesiones y Prevención

Formulario alta lesión (zona, tipo, fecha, notas).
Listado de lesiones activas/resueltas.
Acción para marcar lesión como resuelta.
Tab Asistente Virtual

Chat conversacional con historial en sesión.
Construye contexto desde:
Últimas actividades.
Estado fisiológico.
Estudios científicos cargados.
12. Página Calendario
Referencia: app.py:3271

Contiene:

Selector de semana.
Si no hay plan: mensaje informativo.
Si hay plan:
Vista semanal en tarjetas (Lunes a Domingo).
Vista detallada en tabla con fecha/tipo/sesión/duración/intensidad/detalles.
13. Sistema Visual Actual (Para Que Tu Diseñador Lo Reemplace Con Criterio)

Tema principal:
Verde oscuro de fondo + acentos lima.
Componentes customizados:
Tarjetas métricas.
Botones primarios lima.
DateInput y calendario en paleta verde/lima.
Sliders en lima.
Dataframes con cabecera verde y celdas oscuras.
Header:
Contenedor principal con borde lima.
Pills de navegación compactas.
Botón sync circular.
14. Reglas Funcionales Importantes Para UX

Multiusuario fijo:
Malena (id 1), Dani (id 2).
Ciclo Menstrual solo para Malena.
Sincronización Garmin manual desde botón (no auto al cargar).
Datos sensibles:
Contraseñas tipo password.
Fechas visibles:
Formato DD-MM-YYYY en inputs/tablas principales.
El plan y varias lecturas están cacheadas (puede afectar expectativas de “actualización instantánea”).
Si quieres, en el siguiente mensaje te lo convierto en un brief Figma listo para entregar con:

Mapa de pantallas.
Wireframe de cada pantalla (secciones y jerarquía).
Design tokens (colores, spacing, radios, estados).
Lista de componentes reutilizables y variantes.