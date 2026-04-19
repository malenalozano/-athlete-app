# Proyecto Athlete - Handoff tecnico para rediseno en Figma

## 0) Objetivo de este documento
Este documento describe de forma exhaustiva:
1. Arquitectura de informacion completa (pantallas, secciones, bloques, prioridad de contenido).
2. User flows reales con estados (vacio, carga, error, exito, condicional por perfil).
3. Inventario de componentes con variantes para desktop y movil.

Contexto del producto:
- App beta para 2 atletas (Malena y Dani).
- Entrenamiento combinado running + fuerza + recuperacion + IA + Garmin.
- La app tiene logica de personalizacion por perfil y por estado fisiologico.

---

## 1) Arquitectura de Informacion (IA)

## 1.1 Mapa global de navegacion
Nivel 0 (acceso):
1. Selector de perfil (Malena / Dani).
2. Onboarding (solo si el perfil aun no existe en BD).

Nivel 1 (navegacion principal dentro de app):
1. Dashboard.
2. Perfil.
3. Biblioteca Cientifica.
4. Ciclo Menstrual (solo para Malena).
5. Asistente Virtual.
6. Diario de Fuerza.
7. Entrenador Personal.
8. Calendario.

Elementos globales persistentes en cabecera:
1. Branding + saludo personalizado.
2. Navegacion horizontal por radio.
3. Boton de sincronizacion Garmin (manual).
4. Selector de perfil (switch Malena/Dani).

Principio de prioridad de informacion:
1. Estado del atleta (metricas y semaforos).
2. Acciones principales (sincronizar, generar plan, guardar).
3. Profundidad analitica (tablas historicas, detalle por dia, detalle por ejercicio).

---

## 1.2 Pantalla de acceso: Seleccion de perfil
Objetivo UX:
- Entrar rapido al ecosistema personal del atleta.

Contenido:
1. Badge/icono principal de marca.
2. Titulo Proyecto Athlete.
3. Subtitulo para seleccionar perfil.
4. Boton primario Malena.
5. Boton secundario Dani.

Comportamiento:
1. Si existe ultimo usuario local, autologin sin mostrar esta vista.
2. Si no existe, mostrar seleccion manual.

Estados:
1. Normal: ambos botones habilitados.
2. Cambio de perfil: rerun inmediato a app principal.

---

## 1.3 Onboarding inicial (si perfil no existe)
Objetivo UX:
- Capturar setup minimo para planificacion inteligente + conexion Garmin opcional.

Estructura:
- Formulario de 2 columnas, dividido en paneles.

Paneles de contenido:
1. Datos personales y objetivo.
2. Conexion Garmin.
3. Ritmo objetivo.
4. Disponibilidad y nivel.

Campos:
1. Nombre.
2. Edad.
3. Sexo.
4. Peso actual.
5. Objetivo (5K/10K, Media, Maraton, Trail, HYROX).
6. Email Garmin.
7. Contrasena Garmin (password).
8. Ritmo rapido (slider).
9. Ritmo lento (slider).
10. Dias carrera/semana.
11. Dias fuerza/semana.
12. Nivel actual.

CTA principal:
1. Generar mi Ecosistema.

Validaciones funcionales:
1. Nombre obligatorio y >= 2 caracteres.
2. Objetivo obligatorio.
3. Ritmo lento no puede ser mas rapido que ritmo rapido.
4. Edad en rango permitido.
5. Peso en rango permitido.
6. Email Garmin con formato basico valido.
7. Si hay email Garmin, contrasena obligatoria.
8. Contrasena Garmin minimo 6 caracteres.

Mensajeria:
1. Error por campo invalido.
2. Exito implicito con redireccion por rerun.

---

## 1.4 Cabecera y navegacion principal (post login)
Objetivo UX:
- Control total del contexto actual sin abandonar pantalla.

Bloques:
1. Brand pill:
- Icono.
- Nombre de producto.
- Saludo por nombre y genero gramatical.

2. Menu principal horizontal.
3. Boton icon-only de sincronizacion Garmin.
4. Selector de perfil.

Reglas:
1. El menu muestra Ciclo Menstrual solo para Malena.
2. El boton de sync ejecuta sincronizacion manual (no automatica al cargar).
3. Si faltan credenciales Garmin, se muestra warning.

---

## 1.5 Dashboard
Objetivo UX:
- Vista ejecutiva semanal + alertas tecnicas + progreso + coordinacion de pareja.

Secciones en orden:
1. Metricas rapidas (fila de 4):
- Km (7d).
- Carreras (7d).
- Fuerza (7d).
- Sueno medio (7d).

2. Bloque especial para Dani: estado del ciclo de Malena.
- Fase actual.
- Proxima regla (dias).
- Consejos contextuales de convivencia y entreno compartido.

3. Checkpoints y pequenos logros.
- Progreso global.
- Lista de checkpoints por objetivo.
- Estado hecho/pendiente.
- Mejor marca por checkpoint.

4. Calendario semanal de actividades (7 cards).
- Dia, fecha corta, resumen actividad.

5. Progreso running.
- Grafico de km semanales.

6. Radar antilesiones y tecnica.
- Cadencia, zancada, contacto, oscilacion, potencia.
- Reglas de alerta tecnica.

7. Semaforo diario Garmin.
- HRV, readiness, body battery, recuperacion, FC reposo, SpO2.
- Mensajes de alerta sin/rojo.

8. Progreso de gimnasio por grupo muscular.
- Grafico temporal por grupo.

9. Calidad del sueno ultima semana (si hay datos).
- Bar chart horas/sleep score.
- Metricas profundo, REM, vigilia, despertares.

10. Entrenamientos conjuntos Malena y Dani.
- Selector de semana.
- Rejilla semanal con codigo color por coincidencia.
- Leyenda de color.

Estados vacios tipicos:
1. Sin datos de running.
2. Sin datos de fuerza.
3. Sin datos de sueno.
4. Sin alertas tecnicas.

---

## 1.6 Perfil
Objetivo UX:
- Gestion centralizada de datos base y credenciales Garmin.

Contenido:
1. Metricas resumen de perfil.
2. Expander con variables que consume la IA.
3. Formulario completo de edicion.

Bloques del formulario:
1. Datos personales y objetivo.
2. Ritmo objetivo.
3. Disponibilidad y nivel.
4. Conexion Garmin opcional.

CTA:
1. Guardar cambios de perfil.

Reglas:
1. Mismas validaciones de onboarding.
2. Si no se introduce nueva contrasena Garmin, se conserva la actual.
3. Mensaje de exito y rerun.

---

## 1.7 Biblioteca Cientifica
Objetivo UX:
- Inyectar conocimiento cientifico utilizable por IA de entrenamiento.

Formulario superior:
1. Alcance del estudio:
- Solo este perfil.
- Compartido para ambos.

2. Categoria.
3. Subida de archivo (PDF/TXT/MD).
4. Resumen manual opcional.
5. CTA Guardar estudio.

Comportamiento:
1. Guarda archivo en almacenamiento local.
2. Extrae texto automatico.
3. Si no hay resumen manual, intenta resumen automatico con IA.
4. Persiste metadato y resumen en BD.

Listado historico:
1. Expanders por estudio.
2. Muestra titulo, categoria, alcance, fecha y resumen.

Estados:
1. Sin estudios.
2. Error al guardar.
3. Exito guardado + recarga.

---

## 1.8 Ciclo Menstrual (solo Malena)
Objetivo UX:
- Registro diario + prediccion de fases + soporte a planificacion.

Formulario:
1. Fecha.
2. Fase del ciclo.
3. Fatiga subjetiva (1-10).
4. Notas/molestias/dolor.
5. CTA guardar registro.

Visualizacion:
1. Metrica ciclo estimado en dias.
2. Calendar month picker.
3. Calendario coloreado por fase.
4. Diferenciacion visual:
- Borde solido: dato real.
- Borde discontinuo: prediccion.

5. Tabla de proximos ciclos (inicios fase folicular).

Regla de acceso:
1. Si no es Malena, no disponible.

---

## 1.9 Asistente Virtual
Objetivo UX:
- Resolver dudas del atleta con contexto dinamico real.

Contexto que alimenta el prompt:
1. Ultimas actividades Garmin.
2. Ultimo estado fisiologico.
3. Estudios cientificos disponibles.

Interfaz:
1. Historial de chat persistido en session_state.
2. Mensajes estilo user/assistant.
3. Campo chat_input.

Flujo:
1. Usuario envia duda.
2. Se muestra mensaje del usuario.
3. Spinner de analisis.
4. Respuesta IA.
5. Persistencia en historial.

Estados:
1. Error de modulo IA.
2. Error de generacion.
3. Respuesta normal.

---

## 1.10 Diario de Fuerza
Objetivo UX:
- Convertir lenguaje natural a estructura de entrenamiento y guardar sesiones.

Entrada:
1. Text area de nota libre de entreno.

Funciones clave:
1. Deteccion de fechas naturales (hoy/ayer/fecha/dia semana).
2. Deteccion multi-bloque temporal dentro del mismo texto.
3. Parseo IA a tabla de ejercicios.

Previsualizacion:
1. Numero de bloques detectados.
2. Fecha inferida por bloque.
3. Tabla de ejercicios por sesion.

CTA y guardado:
1. Procesar entrenamiento con IA.
2. Guardar N sesiones.
3. Insercion en sesiones_fuerza y ejercicios_fuerza.

Historial:
1. Expanders por sesion reciente.
2. Tabla detalle por sesion.

Estados:
1. Parseo fallido por bloque.
2. Exito parcial (algunos bloques bien, otros mal).
3. Exito total.
4. Error SQL.

---

## 1.11 Entrenador Personal (3 tabs)

### Tab A: Check-in Diario
Objetivo UX:
- Ver estado fisiologico de hoy y ultimos dias.

Contenido:
1. CTA sincronizar biometricos Garmin.
2. Bloques de metricas en 3 filas.
3. Tabla historica ultimos 7 dias (premium).
4. Tabla reparacion nocturna (sueno detallado).

Estados:
1. Sin credenciales Garmin.
2. Sync en curso.
3. Sync OK.
4. Sync error.

### Tab B: Generar Plan Semanal
Objetivo UX:
- Generar y ajustar plan inteligente segun estado real.

Inputs:
1. Semana a planificar (lunes).
2. Checkbox coordinar con pareja.

Context panel (antes de generar):
1. HRV actual y tendencia.
2. FC reposo.
3. Dias mal sueno.
4. Estres vital.
5. RPE ultimo.
6. Readiness/body battery/recuperacion.
7. Potencia.
8. Ratio carga aguda/cronica (semaforo).
9. Fase ciclo (si aplica).
10. Lesiones activas (si aplica).

CTA principal:
1. Generar plan premium.

Salida:
1. Alertas generadas por reglas.
2. Tabla plan semanal guardado.

Ajuste post-generacion:
1. Text area de feedback libre.
2. CTA aplicar cambios con IA.
3. Reescritura del plan manteniendo estructura.

Estados:
1. Sin plan para esa semana.
2. Plan generado.
3. Error IA ajuste feedback.
4. Error guardado.

### Tab C: Lesiones y Prevencion
Objetivo UX:
- Registrar lesiones activas y cerrarlas cuando se resuelven.

Formulario:
1. Zona lesionada.
2. Tipo.
3. Fecha inicio.
4. Notas.
5. CTA registrar lesion.

Listado:
1. Expanders por lesion.
2. Estado activa/resuelta.
3. CTA marcar como resuelta (solo activas).

Regla funcional:
1. Lesiones activas alimentan la logica del plan semanal automaticamente.

---

## 1.12 Calendario
Objetivo UX:
- Consultar plan semanal en formato visual y detallado.

Contenido:
1. Selector de semana.
2. Vista semanal en 7 tarjetas (lunes-domingo).
3. Vista detallada en tabla.

Tarjeta por dia:
1. Fecha.
2. Sesion.
3. Duracion + intensidad.
4. Color lateral por tipo de sesion.

Estados:
1. Sin plan para semana seleccionada.
2. Plan disponible.

---

## 2) User Flows completos (con estados)

## 2.1 Flujo A - Acceso y contexto de usuario
1. Abrir app.
2. Decision: existe usuario en session/local?
3. Si si: cargar perfil y menu principal.
4. Si no: mostrar selector Malena/Dani.
5. Tras seleccionar perfil:
- Si perfil no existe en BD: onboarding.
- Si perfil existe: dashboard.

Estados de error:
1. Fallo en lectura local (degrada a seleccion manual).
2. Perfil inexistente (redireccion onboarding).

---

## 2.2 Flujo B - Sincronizacion Garmin manual (global)
1. Usuario pulsa boton sincronizar en cabecera.
2. Decision: hay credenciales?
3. Si no: warning configurar credenciales.
4. Si si: spinner conectando.
5. Sincroniza:
- Actividades running.
- Biometricos premium.
- Sueno reciente.
6. Muestra toast de exito y recarga.

Estados de error:
1. Credenciales invalidas.
2. Error conexion Garmin.
3. Error inesperado en parser/DB.

---

## 2.3 Flujo C - Onboarding
1. Usuario completa form.
2. Pulsa Generar mi Ecosistema.
3. Validaciones cliente.
4. Si falla validacion: errores en pantalla.
5. Si ok:
- Guarda perfil.
- Cifra y guarda credenciales Garmin (si existen).
- Limpia cache y rerun.

---

## 2.4 Flujo D - Dashboard operativo
1. Carga resumen de datos cacheado.
2. Render secciones progresivas (metricas -> progreso -> tecnico -> conjunto).
3. Si faltan datos en algun bloque, mostrar estado vacio por bloque.
4. Si usuario Dani, inyectar bloque especial estado ciclo de Malena.

---

## 2.5 Flujo E - Biblioteca cientifica
1. Usuario define alcance y categoria.
2. Sube archivo.
3. Opcional resumen manual.
4. Pulsa Guardar estudio.
5. Sistema:
- Guarda binario en carpeta local.
- Extrae texto.
- Resume con IA si hace falta.
- Guarda en BD.
6. Refresca y aparece en listado.

Errores:
1. Archivo invalido/no parseable.
2. Error en resumen IA.
3. Error persistencia.

---

## 2.6 Flujo F - Ciclo menstrual
1. Registrar entrada diaria.
2. Guardar en BD.
3. Recalcular prediccion por ciclo.
4. Mostrar calendario con mezcla de datos reales y prediccion.
5. Mostrar proximos inicios de ciclo.

---

## 2.7 Flujo G - Asistente Virtual
1. Usuario escribe pregunta.
2. Construccion de contexto dinamico.
3. Llamada IA.
4. Render respuesta.
5. Persistencia en historial local de sesion.

Errores:
1. Modulo IA no disponible.
2. Excepcion en inferencia.

---

## 2.8 Flujo H - Diario de Fuerza con IA
1. Usuario escribe nota libre.
2. Sistema detecta segmentos temporales.
3. Usuario pulsa procesar.
4. IA devuelve tabla por bloque.
5. Usuario revisa resultados.
6. Usuario pulsa guardar N sesiones.
7. Insercion en tablas y confirmacion.
8. Historial actualizado.

Errores:
1. Parseo IA fallido por bloque.
2. Error SQL.

---

## 2.9 Flujo I - Entrenador Personal (plan)
1. Usuario entra en tab Generar Plan.
2. Revisa biometria y alertas base.
3. Selecciona semana.
4. Activa/desactiva coordinar con pareja.
5. Pulsa generar plan.
6. Motor reglas construye 7 dias.
7. Guarda plan y muestra alertas.
8. Usuario revisa tabla final.

Subflujo ajuste IA:
1. Usuario escribe feedback de cambios.
2. Pulsa aplicar cambios.
3. IA ajusta CSV del plan.
4. Guarda nueva version.
5. Refresca vista.

---

## 2.10 Flujo J - Lesiones
1. Usuario registra lesion.
2. Guardar como activa.
3. Lesion aparece en listado.
4. Usuario marca resuelta cuando procede.
5. Sistema cierra lesion con fecha_fin.

Impacto cruzado:
1. Lesiones activas alteran automaticamente planes futuros.

---

## 2.11 Flujo K - Calendario semanal
1. Usuario elige semana.
2. Sistema carga plan guardado.
3. Si existe plan:
- Render tarjetas por dia.
- Render tabla detallada.
4. Si no existe:
- Estado vacio + indicacion de generar en Entrenador Personal.

---

## 3) Checklist de componentes y variantes (Design System Figma)

## 3.1 Componentes de estructura
1. App Header Compact.
- Slots: Brand, Nav, Sync CTA, Profile Select.
- Variantes: desktop / tablet / movil.

2. Page Section Container.
- Titulo, subtitulo, contenido, divider opcional.

3. Form Panel Card.
- Titulo panel + cuerpo.
- Variantes: normal / error.

4. Tabs Container.
- 2+ tabs, selected/unselected.

---

## 3.2 Inputs y controles
1. Text Input.
2. Number Input.
3. Select / Dropdown.
4. Slider.
5. Select Slider.
6. Date Input.
7. Text Area.
8. File Uploader.
9. Chat Input.
10. Radio horizontal.
11. Checkbox.
12. Button:
- Primary.
- Secondary.
- Icon-only (sync).
- Disabled.
- Loading.

Estados minimos por input:
1. Default.
2. Focus.
3. Filled.
4. Error.
5. Disabled.

---

## 3.3 Data display
1. Metric Card.
- Label + value + delta opcional.
- Variantes: neutral / warning / critical.

2. Stat Grid.
- 4 cols, 5 cols, 6 cols adaptables.

3. Data Table.
- Header + rows + empty state.

4. Expander/Accordion.
- Closed/open.

5. Badge/Chip.
- Scope (compartido/perfil), estado (activa/resuelta), checkpoint.

6. Alert banners:
- Info.
- Success.
- Warning.
- Error.

7. Toast pattern.
- Sync completada.

---

## 3.4 Cards especificas de negocio
1. Weekly Day Card (Dashboard).
2. Weekly Plan Card (Calendario).
3. Checkpoint Card (hecho/pendiente).
4. Joint Training Card (Malena/Dani/coinciden/descanso).
5. Cycle Calendar Day Cell (registrado/predicho/sin dato).

Variantes criticas:
1. Con contenido.
2. Sin contenido.
3. Estado positivo.
4. Estado de riesgo.

---

## 3.5 Graficos
1. Line chart (progreso running, fuerza grupos).
2. Bar chart (sueno horas + score).

Necesidades de diseno para charts:
1. Tema oscuro consistente.
2. Colores de series semanticos.
3. Leyenda legible.
4. Tooltips claros.

---

## 3.6 Patrones de estado global
Definir variantes de pagina completa:
1. Loading page.
2. Empty page.
3. Error page.
4. Partial data page.
5. Complete data page.

Definir variantes de bloque:
1. Skeleton breve (opcional).
2. Mensaje vacio.
3. Mensaje de error recuperable.

---

## 3.7 Responsive y breakpoints
Breakpoints recomendados para Figma:
1. Desktop: >= 1280.
2. Laptop: 1024-1279.
3. Tablet: 768-1023.
4. Mobile: <= 767.

Reglas de adaptacion:
1. Header:
- Desktop: 4 zonas en fila.
- Mobile: marca + acciones arriba, menu en bloque aparte.

2. Metric grids:
- Desktop: 4-6 columnas.
- Mobile: 2 columnas maximo.

3. Calendarios semanales:
- Desktop: 7 columnas.
- Mobile: lista vertical por dia.

4. Tablas:
- Desktop: tabla completa.
- Mobile: cards o tabla con scroll horizontal controlado.

---

## 4) Matriz de estados por pagina (para prototipado)

1. Acceso perfil:
- Primera visita.
- Ultimo usuario autologin.

2. Onboarding:
- Form vacio.
- Form con error.
- Exito.

3. Dashboard:
- Sin datos iniciales.
- Datos parciales.
- Datos completos.
- Con alertas.
- Sin alertas.

4. Perfil:
- Modo lectura.
- Modo edicion.
- Error validacion.
- Guardado correcto.

5. Biblioteca:
- Sin estudios.
- Subida en curso.
- Guardado ok.
- Error subida.

6. Ciclo menstrual:
- Sin registros.
- Con registros.
- Con prediccion.

7. Asistente:
- Chat vacio.
- Chat con historial.
- Pensando (spinner).
- Error IA.

8. Diario fuerza:
- Nota vacia.
- Bloques detectados.
- Parseo fallido.
- Parseo correcto.
- Guardado ok.

9. Entrenador personal:
- Sin credenciales Garmin.
- Sync en curso.
- Sin plan semana.
- Plan generado.
- Ajuste IA plan ok/error.

10. Calendario:
- Sin sesiones.
- Sesiones semanales disponibles.

---

## 5) Reglas de negocio criticas que el diseno debe respetar
1. Sync Garmin es manual por boton, nunca automatica al abrir pagina.
2. Credenciales sensibles no visibles (password input).
3. Secciones condicionadas por perfil (Ciclo Menstrual solo Malena).
4. Lesiones activas afectan recomendaciones y plan.
5. El plan puede coordinar dias con pareja.
6. IA siempre debe tener espacio para feedback y correccion humana.

---

## 6) Recomendaciones de handoff al especialista de diseno
1. Crear pagina Figma por modulo principal:
- Acceso + onboarding.
- Shell global (header/nav).
- Dashboard.
- Perfil.
- Biblioteca.
- Ciclo.
- Asistente.
- Diario fuerza.
- Entrenador personal (3 tabs).
- Calendario.

2. Por cada pagina incluir:
- Variante desktop.
- Variante movil.
- Variante empty.
- Variante error.
- Variante loading.

3. Definir tokens:
- Color (bg/surface/brand/warn/success/error/info).
- Tipografia (h1/h2/body/caption).
- Espaciado (4/8/12/16/24/32).
- Radio (8/10/12/16).
- Sombra (sm/md/lg).

4. Priorizar legibilidad sobre decoracion en vistas densas de datos.

---

## 7) Checklist rapido de validacion previa a desarrollo UI
1. Estan todas las pantallas del menu principal modeladas?
2. Existen variantes condicionales por Malena/Dani?
3. Estan cubiertos todos los estados vacios por bloque?
4. Se modelaron mensajes de error y exito reales?
5. Estan definidos los componentes reutilizables en libreria?
6. Se incluyeron flows de IA (chat, parseo fuerza, ajuste plan)?
7. Se incluyo flujo de sync Garmin manual?
8. Estan contempladas acciones de alto impacto (guardar, resolver lesion)?

---

Fin del documento.
