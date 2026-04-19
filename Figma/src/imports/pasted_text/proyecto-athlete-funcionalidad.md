Documento Técnico de Funcionalidades y Pantallas (Base para Rediseño en Figma)

1. Contexto de producto para diseño
La app es un ecosistema de entrenamiento personal para 2 atletas fijos:

Malena (perfil 1), objetivo principal maratón.
Dani (perfil 2), objetivo principal ultra 100 km.
La experiencia combina:

Running.
Fuerza.
Recuperación y biometría Garmin.
IA para consejo y ajuste de planes.
Contexto fisiológico femenino (solo Malena en ciclo menstrual).
Objetivo de diseño:

Mejorar estética y claridad sin perder lógica técnica.
Mantener rapidez, simplicidad y accesibilidad.
Mantener seguridad de credenciales (campos sensibles ocultos).
2. Mapa completo de experiencia (de inicio a uso diario)
Flujo principal:

Selección de perfil (login simple sin contraseña local).
Si perfil no existe en BD: onboarding completo.
Si perfil existe: app principal con navegación horizontal.
Navegación principal:

Dashboard.
Perfil.
Biblioteca Científica.
Ciclo Menstrual (solo Malena).
Asistente Virtual.
Diario de Fuerza.
Entrenador Personal.
Calendario.
Elementos persistentes en cabecera:

Marca Proyecto Athlete.
Menú horizontal.
Botón de sincronización Garmin (manual).
Selector rápido de perfil Malena/Dani.
3. Sistema visual actual (importante para replicar y mejorar)
Dirección visual actual:

Tema oscuro verde-lima.
Estilo premium deportivo.
Tarjetas con bordes suaves, sombras y alto contraste de acentos.
Uso intensivo de métricas (cards numéricas).
Componentes custom HTML/CSS para bloques destacados (checkpoints, calendario conjunto, cards semanales).
Paleta dominante aproximada:

Fondo profundo: verdes muy oscuros.
Superficies: verde petróleo.
Acento principal: lima brillante.
Texto principal: verde claro desaturado.
Estados: warnings, success, info según Streamlit + colores custom en tarjetas.
4. Pantallas y funcionalidades (inventario exhaustivo)
4.1 Pantalla de selección de perfil (pre-login)
Objetivo:

Entrar con identidad de atleta.
Elementos:

Logo/insignia central.
Título Proyecto Athlete.
Subtítulo seleccionar perfil.
Botón Malena.
Botón Dani.
Comportamiento:

Guarda último usuario en archivo local para autologin futuro.
Si existe último usuario válido, entra automáticamente al perfil sin mostrar esta pantalla.
4.2 Onboarding inicial (solo cuando no hay perfil guardado)
Objetivo:

Crear perfil deportivo y credenciales Garmin opcionales.
Estructura:

Formulario en 2 columnas.
Bloques temáticos:
Datos personales y objetivo.
Conexión Garmin.
Ritmo objetivo.
Disponibilidad y nivel.
Campos:

Nombre.
Edad.
Sexo.
Peso.
Objetivo deportivo.
Email Garmin.
Contraseña Garmin (oculta).
Ritmo rápido (slider).
Ritmo lento (slider).
Días carrera por semana.
Días fuerza por semana.
Nivel (Principiante, Intermedio, Avanzado, Élite).
Validaciones:

Nombre obligatorio y mínimo 2 caracteres.
Objetivo obligatorio.
Ritmo lento no puede ser más rápido que ritmo rápido.
Rango de edad y peso validado.
Email Garmin debe tener formato válido.
Si hay email, contraseña Garmin obligatoria.
Contraseña Garmin mínimo 6 caracteres.
Persistencia:

Guarda perfil en tabla usuarios.
Garmin password se cifra antes de guardar.
4.3 Cabecera global dentro de app
Objetivo:

Navegación y acciones rápidas en cualquier sección.
Componentes:

Bloque de marca con saludo personalizado (bienvenida/bienvenido).
Radio horizontal con pestañas.
Botón sincronizar Garmin (icono de refresco).
Select de cambio de perfil.
Reglas:

Al cambiar perfil, rerender completo y persiste último usuario local.
Sincronización Garmin se ejecuta manualmente.
Si faltan credenciales Garmin, aviso para configurarlas en Perfil.
4.4 Dashboard
Objetivo:

Vista ejecutiva del estado semanal y estado de forma.
Secciones:

Métricas rápidas:
Km 7 días.
Carreras 7 días.
Fuerza 7 días.
Sueño medio 7 días.
Bloque especial para Dani:
Estado ciclo de Malena.
Fase actual.
Días para próxima regla.
Consejos contextuales de convivencia/entrenamiento.
Checkpoints y pequeños logros:
Progreso por objetivo (maratón, media, trail, hyrox, etc.).
Barra de progreso global.
Cards por checkpoint con estado hecho/pendiente.
Mejor marca detectada.
Calendario semanal de actividades:
7 tarjetas (lunes a domingo).
Resumen diario running/fuerza o descanso/movilidad.
Progreso de running:
Gráfico de kilómetros por semana.
Estado vacío si no hay datos.
Radar antilesiones y técnica:
Cadencia, zancada, tiempo de contacto, oscilación vertical, potencia.
Alertas de técnica: overstride, rebote alto, contacto alto.
Semáforo diario Garmin:
HRV, readiness, body battery, recuperación, FC reposo, SpO2.
Alertas tipo banderas rojas.
Progreso de gimnasio por grupo muscular:
Gráfico evolutivo de volumen por grupo muscular.
Sueño última semana (si hay datos):
Gráfico horas y score.
Métricas: profundo, REM, vigilia, despertares.
Entrenamientos conjuntos Malena y Dani:
Selector de semana.
Rejilla 7 días con sesión de ambos.
Código visual:
Rosa: solo Malena activa.
Azul: solo Dani activo.
Verde: entrenan ambos.
4.5 Perfil
Objetivo:

Editar parámetros base que alimentan la IA y planificación.
Contenido:

Métricas de perfil actual:
Objetivo.
Nivel.
Carrera/sem.
Fuerza/sem.
Expander con datos biométricos recientes usados por la IA:
HRV, readiness, body battery, FC reposo, estrés, RPE, cadencia, zancada, contacto, oscilación, días de mal sueño.
Formulario de edición:
Datos personales.
Ritmo objetivo.
Disponibilidad y nivel.
Garmin opcional.
Validaciones similares a onboarding.

Guardado:

Perfil siempre.
Email Garmin opcional.
Contraseña Garmin solo si se informa una nueva.
4.6 Biblioteca Científica
Objetivo:

Cargar estudios para que IA use contexto científico personalizado.
Elementos:

Radio de alcance:
Solo este perfil.
Compartido para ambos.
Categoría del estudio.
File uploader (PDF, TXT, MD).
Resumen manual opcional.
Botón guardar estudio.
Flujos:

Guarda archivo físico en carpeta local.
Extrae texto del archivo.
Si no hay resumen manual, genera resumen automático con IA.
Inserta metadatos + texto/resumen en BD.
Lista histórica en expanders con fecha y resumen.
Estado vacío cuando no hay estudios.
4.7 Ciclo Menstrual (solo Malena)
Objetivo:

Registro fisiológico y predicción de fases.
Formulario:

Fecha.
Fase del ciclo.
Fatiga subjetiva 1-10.
Notas/molestias/dolor.
Botón guardar.
Visualización:

Métrica de ciclo estimado en días.
Calendario mensual con color por fase.
Diferenciación visual:
Registro real (borde sólido).
Predicción (borde discontinuo).
Tabla de próximos inicios de fase folicular (predicción).
Restricción:

Si entra perfil no autorizado, muestra sección no disponible.
4.8 Asistente Virtual
Objetivo:

Chat IA contextualizado con datos reales del atleta.
Entradas de contexto:

Últimas actividades.
Último estado fisiológico.
Resúmenes de biblioteca científica.
Interfaz:

Historial de mensajes persistente en sesión.
Campo de entrada tipo chat_input.
Render de mensajes usuario y asistente.
Comportamiento:

Al enviar duda, agrega mensaje usuario.
Ejecuta respuesta IA con spinner.
Guarda respuesta en historial.
Manejo de errores con mensaje visible.
4.9 Diario de Fuerza
Objetivo:

Transformar texto libre en sesiones estructuradas de fuerza.
Entrada:

Text area de entreno libre en lenguaje natural.
Capacidades:

Detectar múltiples bloques temporales en una única nota (hoy, ayer, fechas, días de semana).
Inferir fecha por bloque.
Procesar cada bloque con IA para extraer ejercicios.
Salida previa a guardado:

Mensajes de detección de sesiones y fechas.
Tabla por sesión detectada.
Errores por bloque si IA no parsea correctamente.
Guardado:

Botón dinámico Guardar N sesiones.
Inserta sesión en tabla sesiones_fuerza.
Inserta ejercicios en tabla ejercicios_fuerza.
Historial:

Últimas sesiones en expanders.
Tabla de detalle por sesión (ejercicio, series, reps, peso, rpe, grupos musculares).
4.10 Entrenador Personal Premium
Pantalla con 3 tabs internas.

Tab A: Check-in Diario
Objetivo:

Semáforo de estado diario para decidir carga.
Elementos:

Botón sincronizar biométricos Garmin.
Bloques de métricas:
HRV, readiness, body battery, recuperación.
FC reposo, estrés, SpO2, sleep score.
Cadencia, zancada, contacto, oscilación.
Tabla últimos 7 días biométricos.
Tabla reparación nocturna (sueño detallado).
Tab B: Generar Plan Semanal
Objetivo:

Crear plan adaptativo con reglas avanzadas y guardarlo.
Elementos:

Dashboard de señales de entrada (HRV, tendencia, estrés, RPE, sueño, etc.).
Indicador ratio carga aguda/crónica con semáforo.
Indicador fase del ciclo si aplica.
Lesiones activas detectadas.
Selector de semana (lunes inicio).
Checkbox coordinar con pareja.
Botón generar plan premium.
Bloque informativo de lógica IA.
Alertas generadas por motor de planificación.
Tabla plan guardado.
Lógica de adaptación del plan:

Ajusta intensidad/volumen según HRV, sueño, readiness, body battery, recuperación.
Considera fatiga subjetiva, RPE y estrés vital.
Considera lesiones activas por zona para vetar impacto o velocidad.
Considera técnica de carrera para añadir drills/core.
Considera fase menstrual en mujer.
Coordina días activos con la pareja si está activado.
Regla específica: evita fuerza pesada de piernas antes de sesión de calidad.
Feedback post-plan:

Text area para cambios en lenguaje natural.
Botón aplicar cambios con IA.
Reescritura del plan y guardado de versión actualizada.
Tab C: Lesiones y Prevención
Objetivo:

Registrar, visualizar y cerrar lesiones activas.
Formulario:

Zona lesionada.
Tipo (sobreuso, aguda, prevención).
Fecha inicio.
Notas.
Botón registrar lesión.
Historial:

Expanders por lesión con estado activa/resuelta.
Botón marcar como resuelta para lesiones activas.
Al resolver, guarda fecha_fin y desactiva impacto en planificación futura.
4.11 Calendario
Objetivo:

Visualizar plan semanal guardado en formato calendario.
Elementos:

Selector de semana.
Vista semanal en tarjetas (lunes-domingo):
Fecha.
Sesión.
Duración e intensidad.
Color por tipo (carrera, fuerza, mixto, recuperación).
Vista detallada tabular:
Fecha, tipo, sesión, duración, intensidad, detalles.
Estado vacío:

Si no hay plan generado para semana, aviso con CTA hacia Entrenador Personal.
5. Reglas de producto y seguridad que impactan diseño
Sincronización Garmin debe ser manual desde botón de refresco en interfaz.
Evitar duplicados de actividades usando identificador único de Garmin en base de datos.
El foco de actividades Garmin es running.
Nunca mostrar contraseñas en claro.
Inputs sensibles deben mantenerse como password.
UX debe distinguir claramente acciones irreversibles o de impacto (guardar plan, marcar lesión resuelta, etc.).
6. Estados UI que Figma debe contemplar sí o sí
Carga:
Spinner en sincronización Garmin.
Spinner en procesamiento IA (chat, fuerza, ajuste plan).
Éxito:
Mensajes de confirmación de guardado/sincronización.
Error:
Errores de validación de formulario.
Error de conexión o credenciales Garmin.
Error IA (parseo o generación).
Error SQL en guardados.
Vacío:
Sin datos de running.
Sin fuerza.
Sin sueño.
Sin estudios.
Sin plan semanal.
Sin lesiones.
Condicional por perfil:
Ciclo menstrual visible solo en Malena.
Bloque ciclo de Malena visible en dashboard de Dani.
7. Inventario de componentes reutilizables para sistema de diseño
Cabecera con branding + navegación + acciones.
Cards de métrica numérica.
Tarjetas semanales (día).
Tarjetas de checkpoint con estado.
Expanders para detalle histórico.
Tablas de datos.
Gráficos line/bar temáticos.
Formularios en paneles.
Badges/labels de estado (hecho, pendiente, activa, resuelta).
Leyendas de color para calendarios.
Inputs de chat.
CTA primario/secundario e icon-only.
8. Recomendaciones de adaptación a Figma (contextualización para diseñador)
Priorizar una arquitectura de información de 3 niveles:
Nivel 1: Estado rápido (métricas y semáforos).
Nivel 2: Acción (sincronizar, generar plan, guardar).
Nivel 3: Profundidad (históricos, tablas, detalles IA).
Diseñar un lenguaje común de estado:
Readiness de entrenamiento.
Riesgo de lesión.
Calidad de sueño.
Progreso de objetivo.
Crear patrones visuales consistentes por tipo de dato:
Fisiología.
Carga de entrenamiento.
Técnica de carrera.
Fuerza.
Planificación semanal.
Mantener alta legibilidad de dashboards densos:
Jerarquía tipográfica fuerte.
Espaciado por bloques.
Evitar saturación de color en una sola vista.
Diseñar para uso doméstico en desktop y portátil, pero con degradación clara en móvil:
Grids adaptables.
Cards apilables.
Menú horizontal con alternativa compacta.
Mantener tono emocional del producto:
Coaching cercano.
Enfoque técnico.
Sensación de control y personalización.
9. Funcionalidades operativas no visibles en UI (para contexto de producto)
Existe worker de sincronización Garmin para ejecución programada o manual fuera de la UI.
Existe script de reseteo completo de datos (incluye usuarios, sesiones y archivos subidos).
Persistencia de último usuario en dispositivo local para entrada rápida.