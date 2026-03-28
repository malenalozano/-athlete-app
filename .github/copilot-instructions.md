# Instrucciones de Proyecto: Athlete (Malena y Dani)

## Contexto del Proyecto
Este es un ecosistema de entrenamiento personal el objetivo es crear una aplicación que gestione todos los entrenamientos como un entrenador personal, que tenga en cuenta todos los datos del usuario. En un futuro me gustaria una implementación para varios usuarios pero por ahora la fase Beta va a ser solo para dos atletas (pareja).
- **Usuario ID 1:** Malena 
- **Usuario ID 2:** Dani
- **Objetivo:** Sincronizar datos de Garmin Connect, monitorizar el ciclo menstrual de Malena que es mujer y fuerza para optimizar el rendimiento y evitar lesiones. Todo para alcanzar los objetivos de cada uno, maratón para Malena y ultraparaton de 100km para Dani, compaginando siempre en ambos el entreno de fuerza con el de resistencia.
Buscamos que cada uno pueda acceder a la app desde su ordenador personal en su casa

## Reglas de Diseño y UI
Mantener siempre la coherencia visual y de experiencia de usuario entre las diferentes secciones de la aplicación. Usar un diseño limpio y minimalista, Priorizar la usabilidad y la accesibilidad. Asegurando la rapidez de carga y fluidez.

## Reglas de Código
- **Privacidad:** Nunca imprimir contraseñas ni emails en la consola o en la interfaz (usar `type="password"` en inputs). Siempre tener mucho cuidado con estas cosas, maxima seguridad.

## Lógica de Negocio Específica
1. **No Duplicados:** Al insertar actividades de Garmin, usar siempre el `activityId` de Garmin como referencia para evitar repeticiones.
2. **Filtro de Deporte:** (Regla eliminada, ahora se cargan todas las actividades desde Garmin).
3. **Sincronización:** La sincronización debe ser manual mediante el botón 🔄 del Dashboard, nunca automática al cargar la página.