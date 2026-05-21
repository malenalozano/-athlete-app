const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function req<T>(path: string, options?: RequestInit, timeoutMs = 60000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...options,
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`API ${res.status}: ${err}`);
    }
    return res.json();
  } catch (e: unknown) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error("La petición tardó demasiado. Inténtalo de nuevo.");
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export function login(nombre: string) {
  return req<{ id: number; nombre: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ nombre }),
  });
}

export function getPerfil(usuarioId: number) {
  return req<PerfilUsuario>(`/auth/perfil/${usuarioId}`);
}

export function actualizarPerfil(usuarioId: number, data: Partial<Omit<PerfilUsuario, "id">>) {
  return req<{ ok: boolean }>(`/auth/perfil/${usuarioId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// ── Dashboard ────────────────────────────────────────────────────────────────

export function getDashboard(usuarioId: number) {
  return req<DashboardData>(`/dashboard/${usuarioId}`);
}

// ── Plan ─────────────────────────────────────────────────────────────────────

export function getPlanSemana(usuarioId: number, fechaInicio: string) {
  return req<PlanSemana>(`/plan/${usuarioId}/semana/${fechaInicio}`);
}

export function actualizarSesion(sesionId: number, completado: boolean, kmRealizados?: number) {
  return req<{ ok: boolean }>(`/plan/sesion/${sesionId}`, {
    method: "PATCH",
    body: JSON.stringify({ completado, km_realizados: kmRealizados }),
  });
}

export function crearSesion(s: {
  usuario_id: number;
  fecha: string;
  tipo: string;
  sesion: string;
  detalles?: string;
  duracion_min?: number;
  intensidad?: string;
  km_planificados?: number;
}) {
  return req<{ ok: boolean }>("/plan/sesion", { method: "POST", body: JSON.stringify(s) });
}

export function borrarSesion(sesionId: number) {
  return req<{ ok: boolean }>(`/plan/sesion/${sesionId}`, { method: "DELETE" });
}

// ── Ejercicios ───────────────────────────────────────────────────────────────

export function getEjercicios(usuarioId: number) {
  return req<EjerciciosBiblioteca>(`/ejercicios/${usuarioId}`);
}

export function archivarEjercicio(ejercicioId: number, archivar: boolean) {
  return req<{ ok: boolean }>(`/ejercicios/${ejercicioId}/archivar?archivar=${archivar}`, {
    method: "PATCH",
  });
}

export function crearEjercicio(data: {
  usuario_id: number;
  nombre: string;
  grupo_muscular: string;
  musculo_principal?: string;
  alias?: string;
}) {
  return req<{ ok: boolean }>("/ejercicios/crear", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function registrarSerie(s: {
  usuario_id: number;
  ejercicio_nombre: string;
  peso: number;
  series: number;
  repeticiones: number;
  rpe?: number;
}) {
  return req<{ ok: boolean }>("/ejercicios/serie", {
    method: "POST",
    body: JSON.stringify(s),
  });
}

export function getSesionFuerzaHoy(usuarioId: number) {
  return req<SesionFuerzaHoy>(`/ejercicios/${usuarioId}/sesion-fuerza-hoy`);
}

export function registrarSesionFuerza(
  usuarioId: number,
  registros: RegistroEjercicioInput[]
) {
  return req<{ ok: boolean }>(`/ejercicios/${usuarioId}/sesion`, {
    method: "POST",
    body: JSON.stringify({ registros }),
  });
}

export function getHistorialEjercicio(usuarioId: number, ejercicioId: number) {
  return req<HistorialEntrada[]>(
    `/ejercicios/${usuarioId}/historial/${ejercicioId}`
  );
}

export function editarEjercicio(
  ejercicioId: number,
  data: Partial<{
    nombre: string;
    grupo_muscular: string;
    alias: string;
    series_objetivo: number;
    reps_objetivo: number;
    peso_objetivo: number;
    subir_peso: number;
  }>
) {
  return req<{ ok: boolean }>(`/ejercicios/${ejercicioId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// ── Diario ───────────────────────────────────────────────────────────────────

export function getDiarioFisiologia(usuarioId: number) {
  return req<EntradaDiario[]>(`/diario/fisiologia/${usuarioId}`);
}

export function crearEntradaDiario(e: Partial<EntradaDiario> & { usuario_id: number }) {
  return req<{ ok: boolean }>("/diario/fisiologia", {
    method: "POST",
    body: JSON.stringify(e),
  });
}

export function getDiarioBiometrico(usuarioId: number) {
  return req<EntradaBiometrica[]>(`/diario/biometrico/${usuarioId}`);
}

// ── Garmin ───────────────────────────────────────────────────────────────────

export function getActividades(usuarioId: number, dias = 30) {
  return req<ActividadGarmin[]>(`/garmin/${usuarioId}/actividades?dias=${dias}`);
}

export function getGarminStats(usuarioId: number) {
  return req<GarminStats>(`/garmin/${usuarioId}/stats`);
}

export function sincronizarGarmin(usuarioId: number) {
  return req<{ ok: boolean; actividades_importadas: number; dias_biometrico: number; dias_sueno: number; advertencias: string[] | null }>(`/garmin/${usuarioId}/sync`, { method: "POST" }, 90000);
}

export function guardarCredencialesGarmin(usuarioId: number, emailGarmin: string, passwordGarmin: string) {
  return req<{ ok: boolean }>(`/auth/garmin-credentials/${usuarioId}`, {
    method: "PUT",
    body: JSON.stringify({ email_garmin: emailGarmin, password_garmin: passwordGarmin }),
  });
}

export function generarPlanSemana(usuarioId: number, fechaInicio: string, kmTotal?: number) {
  return req<PlanGenerado>(`/plan/${usuarioId}/generar-semana`, {
    method: "POST",
    body: JSON.stringify({ fecha_inicio: fechaInicio, km_total: kmTotal ?? null }),
  });
}

export function regenerarPlanTotal(usuarioId: number, semanas = 4) {
  return req<{ ok: boolean; km_base_real: number; semanas_regeneradas: number; detalle: { semana_inicio: string; km_total: number; descarga: boolean }[] }>(
    `/plan/${usuarioId}/regenerar-total`,
    { method: "POST", body: JSON.stringify({ semanas }) }
  );
}

export function actualizarSesionCompleta(sesionId: number, data: Partial<{ completado: boolean; km_realizados: number; sesion: string; tipo: string; detalles: string; duracion_min: number; intensidad: string; km_planificados: number; fecha: string }>) {
  return req<{ ok: boolean }>(`/plan/sesion/${sesionId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// ── Entrenador ───────────────────────────────────────────────────────────────

export function getResumenEntrenador(usuarioId: number) {
  return req<ResumenEntrenador>(`/entrenador/${usuarioId}/resumen`);
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface PerfilUsuario {
  id: number;
  nombre: string;
  edad: number;
  genero: string;
  peso: number;
  objetivo: string;
  nivel: string;
  ritmo: string;
  fcmax: number | null;
  fecha_objetivo: string | null;
  objetivo_tipo: string;
  fecha_inicio_entrenamiento?: string | null;
  email_garmin?: string | null;
}

export interface FaseMacrociclo {
  nombre: string;
  km_max: number;
  dias_fuerza: number;
}

export interface DashboardData {
  perfil: PerfilUsuario;
  fase_macrociclo: FaseMacrociclo;
  semaforo: { color: "verde" | "ambar" | "rojo"; mensaje: string };
  semana_actual: { km_realizados: number; km_planificados: number; sesiones_fuerza: number };
  actividades_recientes: ActividadGarmin[];
  hrv_data: HrvEntry[];
  sleep_data: SleepEntry[];
  running_trend: { semana: string; km: number }[];
  ritmo_trend: { semana: string; ritmo: number }[];
  fuerza_reciente: { ejercicio: string; peso: number; series: number; repeticiones: number }[];
  cadencia_trend: { semana: string; cadencia: number }[];
  ciclo: {
    fase: string;
    dia_ciclo: number;
    duracion_ciclo: number;
    dias_para_regla: number;
    proxima_fecha: string;
    energia: string;
  } | null;
}

export interface PlanSemana {
  semana_inicio: string;
  sesiones: SesionPlan[];
  actividades_garmin: ActividadGarmin[];
  stats: { km_planificados: number; km_realizados: number; sesiones_completadas: number; total_sesiones: number };
  fase: string;
  coach_tip: string;
}

export interface SesionPlan {
  id: number;
  fecha: string;
  tipo: string;
  sesion: string;
  detalles: string | null;
  duracion_min: number | null;
  intensidad: string | null;
  completado: number;
  km_planificados: number | null;
  km_realizados: number | null;
}

export interface ActividadGarmin {
  id?: string;
  fecha: string;
  tipo_deporte: string;
  distancia_m: number;
  tiempo_seg: number;
  ritmo_medio: number | null;
  fc_media: number | null;
  fc_max: number | null;
  cadencia_media: number | null;
  km?: number;
  duracion_fmt?: string;
}

export interface HrvEntry {
  fecha: string;
  hrv_ms: number | null;
  fc_reposo: number | null;
  sleep_score: number | null;
  body_battery: number | null;
  training_status: string | null;
  training_readiness: number | null;
  estres_medio: number | null;
}

export interface SleepEntry {
  fecha: string;
  horas_totales: number | null;
  score: number | null;
  sleep_profundo_horas: number | null;
  sleep_rem_horas: number | null;
}

export type GrupoFuerza = "Push" | "Pull" | "Pierna";

export interface EjercicioBiblioteca {
  id: number;
  nombre: string;
  grupo_muscular: GrupoFuerza;
  musculo_principal: string | null;
  alias: string | null;
  archivado: boolean;
  series_objetivo: number | null;
  reps_objetivo: number | null;
  peso_objetivo: number | null;
  ultimo_peso: number | null;
  ultima_series: number | null;
  ultimas_reps: number | null;
  ultima_fecha: string | null;
  mejor_peso: number | null;
  subir_peso: boolean;
}

export interface EjercicioFuerzaHoy {
  id: number;
  nombre: string;
  series_objetivo: number | null;
  reps_objetivo: number | null;
  peso_objetivo: number | null;
  subir_peso: boolean;
  ultimo_peso: number | null;
  ultima_series: number | null;
  ultimas_reps: number | null;
}

export interface SesionFuerzaHoy {
  tiene_fuerza: boolean;
  grupo: GrupoFuerza | null;
  sesion_nombre: string | null;
  ejercicios: EjercicioFuerzaHoy[];
}

export interface RegistroEjercicioInput {
  ejercicio_id: number;
  series: number;
  repeticiones: number;
  peso: number;
  completado: boolean;
}

export interface HistorialEntrada {
  fecha: string;
  peso: number | null;
  series: number | null;
  repeticiones: number | null;
  rpe: number | null;
  notas: string | null;
}

export interface EjerciciosBiblioteca {
  grupos: Record<GrupoFuerza, { activos: EjercicioBiblioteca[]; archivados: EjercicioBiblioteca[] }>;
}

export interface EntradaDiario {
  usuario_id?: number;
  fecha: string;
  fase_ciclo: string | null;
  fatiga_subjetiva: number | null;
  dolor_notas: string | null;
  estado_animo: string | null;
  feedback_entreno: string | null;
  sangre?: string | null;
  sintomas?: string | null;
}

export interface EntradaBiometrica {
  fecha: string;
  hrv_ms: number | null;
  fc_reposo: number | null;
  sleep_score: number | null;
  carga_aguda: number | null;
  carga_cronica: number | null;
  estres_medio: number | null;
  body_battery: number | null;
  training_readiness: number | null;
  training_status: string | null;
  vo2max: number | null;
  horas_totales: number | null;
  sleep_profundo_horas: number | null;
  sleep_rem_horas: number | null;
}

export interface GarminStats {
  km_semana: number;
  km_mes: number;
  total_actividades: number;
  ultima_actividad: { fecha: string; tipo: string } | null;
}

export interface ResumenEntrenador {
  km_semana: number;
  sesiones_fuerza: number;
  actividades_count: number;
  biometrico: Record<string, number | string | null>;
  lesiones_activas: { tipo: string; grado: number }[];
  recomendaciones: string[];
}

export interface SesionGenerada {
  fecha: string;
  tipo: string;
  sesion: string;
  detalles: string | null;
  km_planificados: number | null;
  duracion_min: number | null;
  intensidad: string | null;
}

export interface PlanGenerado {
  ok: boolean;
  semana_inicio: string;
  km_total: number;
  tipo_semana: string;
  coach_tip: string;
  macrociclo: number;
  sesiones: SesionGenerada[];
}
