const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
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
  fuerza_reciente: { ejercicio: string; peso: number; series: number; repeticiones: number }[];
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

export interface EjerciciosBiblioteca {
  grupos: {
    nombre: string;
    ejercicios: EjercicioBiblioteca[];
  }[];
}

export interface EjercicioBiblioteca {
  id: number;
  nombre: string;
  grupo_muscular: string;
  musculo_principal: string | null;
  alias: string | null;
  ultimo_peso: number | null;
  ultima_fecha: string | null;
  mejor_peso: number | null;
}

export interface EntradaDiario {
  usuario_id?: number;
  fecha: string;
  fase_ciclo: string | null;
  fatiga_subjetiva: number | null;
  dolor_notas: string | null;
  estado_animo: string | null;
  feedback_entreno: string | null;
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
