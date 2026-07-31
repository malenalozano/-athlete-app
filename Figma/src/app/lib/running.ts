// Qué tipos de actividad Garmin cuentan como "carrera" (running/cinta) — usado para
// distinguir del resto de deportes (bici, natación, etc.) al calcular km de plan.
// Antes duplicado (y desincronizado) entre PlanSemanal.tsx y LandingPage.tsx.
// Debe reflejar backend-fastapi/constants.py::RUNNING_TIPOS.
export const RUNNING_TIPOS = new Set([
  "running", "trail_running", "treadmill_running", "track_running",
  "correr", "carrera", "trail", "run", "indoor_running",
]);

export function esActividadRunning(tipoDeporte: string | null | undefined): boolean {
  return RUNNING_TIPOS.has((tipoDeporte ?? "").toLowerCase());
}
