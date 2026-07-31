import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import {
  Calendar, TrendingUp, Award, ChevronLeft, ChevronRight,
  ArrowLeftRight, X, Clock, Flame, Plus, Check, Save, Trash2,
  RefreshCw, ArrowRight, Zap,
} from "lucide-react";
import {
  addDays, addMonths, addWeeks, differenceInCalendarDays, format,
  getDay, isSameDay, parseISO, startOfMonth, startOfWeek,
} from "date-fns";
import { es } from "date-fns/locale";
import { useUser } from "../context/UserContext";
import {
  actualizarSesionCompleta, aplicarSemanaGenerada, borrarSesion, crearSesion, generarPlanSemana,
  getDashboard, getPlanSemana, sincronizarGarmin,
  type ActividadGarmin, type CicloOverride, type DashboardData, type SesionGenerada, type SesionPlan,
} from "../api";

// ─────────────────────────────────────────────────────────────────────────────
// DESIGN TOKENS (exact spec hex codes)
// ─────────────────────────────────────────────────────────────────────────────
const T = {
  bgApp:    "#020617",
  bgSurf:   "#0f172a",
  border:   "#1e293b",
  text1:    "#f8fafc",
  text2:    "#94a3b8",
  text3:    "#64748b",
  success:  "#10b981",
  successBg:"#064e3b",
  reorder:  "#f97316",
  reorderTx:"#020617",
} as const;

type Subtype = "RB" | "CAL" | "TL" | "PUSH" | "PULL" | "PIERNA" | "EXTRA";

const SUB: Record<Subtype, { bg: string; color: string; glow: string; label: string }> = {
  RB:     { bg: "#083344", color: "#22d3ee", glow: "0 0 8px rgba(34,211,238,0.3)",   label: "RB" },
  CAL:    { bg: "#0c4a6e", color: "#38bdf8", glow: "0 0 8px rgba(56,189,248,0.3)",   label: "CAL" },
  TL:     { bg: "#172554", color: "#60a5fa", glow: "0 0 8px rgba(96,165,250,0.35)",  label: "TL" },
  PUSH:   { bg: "#431407", color: "#f97316", glow: "0 0 8px rgba(249,115,22,0.25)",  label: "PUSH" },
  PULL:   { bg: "#451a03", color: "#f59e0b", glow: "0 0 6px rgba(245,158,11,0.2)",   label: "PULL" },
  PIERNA: { bg: "#450a0a", color: "#ef4444", glow: "0 0 6px rgba(239,68,68,0.2)",    label: "PIERNA" },
  EXTRA:  { bg: "#2e1065", color: "#a855f7", glow: "0 0 8px rgba(168,85,247,0.35)",  label: "EXTRA" },
};

// Actividades Garmin realizadas pero no planificadas — se muestran igualmente en
// el calendario, marcadas como hechas, en color violeta ("EXTRA").
const RUNNING_KEYWORDS = ["running", "trail_running", "treadmill_running", "track_running", "correr", "carrera"];

function esActividadRunning(tipoDeporte: string): boolean {
  const t = (tipoDeporte || "").toLowerCase();
  return RUNNING_KEYWORDS.some(k => t.includes(k));
}

function humanizarTipoActividad(tipoDeporte: string): string {
  const map: Record<string, string> = {
    running: "Carrera", trail_running: "Trail running", treadmill_running: "Cinta de correr",
    strength_training: "Fuerza", indoor_climbing: "Escalada", hiit: "HIIT",
    cross_training: "Cross training", cycling: "Ciclismo", indoor_cycling: "Ciclismo indoor",
    yoga: "Yoga", pilates: "Pilates", walking: "Caminata", hiking: "Senderismo",
    stand_up_paddleboarding_v2: "Paddle surf", swimming: "Natación",
  };
  const key = (tipoDeporte || "").toLowerCase();
  if (map[key]) return map[key];
  return capitalize(key.replace(/_/g, " ")) || "Actividad";
}

const DAYS = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"];

// ─────────────────────────────────────────────────────────────────────────────
// SESSION MODEL (backed by /plan real data — ver Figma/src/app/api.ts)
// ─────────────────────────────────────────────────────────────────────────────
interface Session {
  id: string; // String(SesionPlan.id) — usado para llamar a la API
  dayIndex: number; // 0=Lun … 6=Dom, relativo al lunes de la semana mostrada
  type: "carrera" | "fuerza";
  subtype: Subtype;
  title: string; duration: string; metric: string;
  notes: string; completed: boolean;
  origin: "plan" | "garmin"; // "garmin" = actividad real sin sesión planificada (no editable)
  kmRealizados?: number; // km reales (Garmin) para mostrar "hechos/planeados"
  kmPlanificados?: number;
  garminBacked?: boolean; // completada porque hay actividad Garmin ese día — no se puede desmarcar
  extraKm?: number; // km de déficit de sesiones pasadas redistribuidos aquí (se muestra en rojo)
}

// ── Date / mapping helpers ──────────────────────────────────────────────────

function mondayFor(weekOffset: number): Date {
  return startOfWeek(addWeeks(new Date(), weekOffset), { weekStartsOn: 1 });
}

function toISODate(d: Date): string {
  return format(d, "yyyy-MM-dd");
}

function capitalize(s: string): string {
  return s.length ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

function formatWeekLabel(monday: Date): string {
  const sunday = addDays(monday, 6);
  return `${format(monday, "d MMM", { locale: es })} – ${format(sunday, "d MMM yyyy", { locale: es })}`;
}

function formatDuracion(min: number | null | undefined): string {
  if (!min) return "";
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${h}h ${String(m).padStart(2, "0")}m`;
}

function parseDuracion(text: string): number | undefined {
  const trimmed = text.trim();
  const hm = trimmed.match(/^(\d+)\s*h\s*(?:(\d+)\s*m)?$/i);
  if (hm) return parseInt(hm[1], 10) * 60 + (hm[2] ? parseInt(hm[2], 10) : 0);
  const minOnly = trimmed.match(/^(\d+)/);
  return minOnly ? parseInt(minOnly[1], 10) : undefined;
}

function formatPace(ritmo: number): string {
  const min = Math.floor(ritmo);
  const sec = Math.round((ritmo - min) * 60);
  return `${min}:${String(sec).padStart(2, "0")}`;
}

function classifySubtype(tipo: string, sesion: string): Subtype {
  const isFuerza = (tipo || "").toLowerCase() === "fuerza";
  const s = (sesion || "").toLowerCase();
  if (isFuerza) {
    if (s.includes("pierna")) return "PIERNA";
    if (s.includes("push")) return "PUSH";
    return "PULL";
  }
  if (s.includes("tirada")) return "TL";
  if (s.includes("rodaje") || s.includes("regenerativo") || s.includes("descanso")) return "RB";
  return "CAL";
}

function defaultTitleFor(type: "carrera" | "fuerza", subtype: Subtype): string {
  if (type === "carrera") {
    return subtype === "RB" ? "Rodaje Base Zona 2" : subtype === "TL" ? "Tirada Larga" : "Series de Calidad";
  }
  return subtype === "PIERNA" ? "Pierna" : subtype === "PUSH" ? "Push" : "Pull";
}

function toSession(s: SesionPlan, monday: Date): Session {
  const dayIndex = Math.min(6, Math.max(0, differenceInCalendarDays(parseISO(s.fecha), monday)));
  const type: "carrera" | "fuerza" = (s.tipo || "").toLowerCase() === "fuerza" ? "fuerza" : "carrera";
  const kmRealizados = s.km_realizados ?? undefined;
  return {
    id: String(s.id),
    dayIndex,
    type,
    subtype: classifySubtype(s.tipo, s.sesion),
    title: s.sesion,
    duration: formatDuracion(s.duracion_min),
    metric: s.completado && kmRealizados !== undefined && s.km_planificados
      ? `${kmRealizados}/${s.km_planificados} km`
      : s.km_planificados ? `${s.km_planificados} km` : "",
    notes: s.detalles ?? "",
    completed: !!s.completado,
    origin: "plan",
    kmRealizados,
    kmPlanificados: s.km_planificados ?? undefined,
  };
}

/** Combina las sesiones planificadas con las actividades Garmin de la semana:
 * - Sesión planificada completada con actividad Garmin del mismo tipo ese día →
 *   se marca `garminBacked` (tarjeta verde bloqueada, no se puede desmarcar).
 * - Actividad Garmin sobrante sin sesión planificada que la consuma → tarjeta
 *   "EXTRA" de solo lectura, para que nada de lo entrenado se pierda del calendario.
 * Se recalcula en cada fetch, así que mover una sesión al día de una actividad
 * suelta la "consume" automáticamente (la extra desaparece, la movida se marca). */
function applyGarminMatching(planSessions: Session[], actividades: ActividadGarmin[], monday: Date): Session[] {
  const todayIso = toISODate(new Date());
  const byDay = new Map<number, ActividadGarmin[]>();
  for (const a of actividades) {
    const dayIndex = differenceInCalendarDays(parseISO(a.fecha), monday);
    if (dayIndex < 0 || dayIndex > 6) continue;
    const list = byDay.get(dayIndex) ?? [];
    list.push(a);
    byDay.set(dayIndex, list);
  }

  const updatedPlanSessions: Session[] = [];
  const extras: Session[] = [];

  for (let dayIndex = 0; dayIndex <= 6; dayIndex++) {
    const acts = byDay.get(dayIndex) ?? [];
    const daySessions = planSessions.filter(s => s.dayIndex === dayIndex);
    const running = acts.filter(a => esActividadRunning(a.tipo_deporte));
    const noRunning = acts.filter(a => !esActividadRunning(a.tipo_deporte));
    // Match por día+tipo, sin exigir que `completado` ya esté a true en BD — así una
    // sesión recién regenerada (id nuevo, completado=0) se sigue reconociendo si ese
    // día ya hay actividad Garmin correspondiente, en vez de quedar como "extra".
    const isPastOrToday = toISODate(addDays(monday, dayIndex)) <= todayIso;

    let runningUsed = 0;
    let noRunningUsed = 0;
    daySessions.forEach(s => {
      if (s.type === "carrera" && isPastOrToday && runningUsed < running.length) {
        const a = running[runningUsed++];
        const km = (a.distancia_m || 0) / 1000;
        updatedPlanSessions.push({
          ...s,
          completed: true,
          garminBacked: true,
          kmRealizados: km > 0.1 ? Math.round(km * 10) / 10 : s.kmRealizados,
          metric: s.kmPlanificados ? `${km > 0.1 ? Math.round(km * 10) / 10 : (s.kmRealizados ?? "?")}/${s.kmPlanificados} km` : s.metric,
        });
      } else if (s.type === "fuerza" && isPastOrToday && noRunningUsed < noRunning.length) {
        noRunningUsed++;
        updatedPlanSessions.push({ ...s, completed: true, garminBacked: true });
      } else {
        updatedPlanSessions.push(s);
      }
    });

    const leftover = [...running.slice(runningUsed), ...noRunning.slice(noRunningUsed)];
    leftover.forEach((a, i) => {
      const km = (a.distancia_m || 0) / 1000;
      extras.push({
        id: `garmin-${dayIndex}-${i}-${a.fecha}-${a.tipo_deporte}`,
        dayIndex,
        type: esActividadRunning(a.tipo_deporte) ? "carrera" : "fuerza",
        subtype: "EXTRA",
        title: humanizarTipoActividad(a.tipo_deporte),
        duration: formatDuracion(a.tiempo_seg ? Math.round(a.tiempo_seg / 60) : null),
        metric: km > 0.1 ? `${km.toFixed(1)} km` : "",
        notes: "Actividad de Garmin no planificada.",
        completed: true,
        garminBacked: true,
        origin: "garmin",
        kmRealizados: km > 0.1 ? Math.round(km * 10) / 10 : undefined,
      });
    });
  }

  return [...updatedPlanSessions, ...extras];
}

/** Si una sesión de carrera pasada se quedó corta de km (o no se hizo), el déficit se
 * reparte a partes iguales entre las sesiones de carrera de esta semana que aún quedan
 * por hacer (hoy o en el futuro, no completadas) — se muestra como "+X km" en rojo. */
function applyDeficitRedistribution(sessions: Session[], monday: Date): Session[] {
  const todayIso = toISODate(new Date());
  const carreraSessions = sessions.filter(s => s.type === "carrera" && s.origin === "plan");

  let deficit = 0;
  carreraSessions.forEach(s => {
    const fecha = toISODate(addDays(monday, s.dayIndex));
    if (fecha >= todayIso) return; // solo sesiones ya pasadas
    const planificado = s.kmPlanificados ?? 0;
    if (planificado <= 0) return;
    const realizado = s.garminBacked ? (s.kmRealizados ?? 0) : s.completed ? planificado : 0;
    const shortfall = planificado - realizado;
    if (shortfall > 0.05) deficit += shortfall;
  });

  // Km corridos de más (actividades Garmin sin sesión planificada, "extra") cuentan
  // para el total semanal y reducen el déficit — no son km perdidos.
  const extraRunningKm = sessions
    .filter(s => s.type === "carrera" && s.origin === "garmin")
    .reduce((sum, s) => sum + (s.kmRealizados ?? 0), 0);
  deficit = Math.max(0, deficit - extraRunningKm);

  if (deficit <= 0.05) return sessions;

  const targets = carreraSessions
    .filter(s => !s.completed && toISODate(addDays(monday, s.dayIndex)) >= todayIso)
    .sort((a, b) => a.dayIndex - b.dayIndex);
  if (targets.length === 0) return sessions;

  // Reparto ponderado: la Tirada Larga absorbe más déficit que el resto, el
  // Regenerativo (recuperación) el menos posible.
  const pesoDe = (s: Session): number => {
    if (s.subtype === "TL") return 3;
    if (s.title.toLowerCase().includes("regenerativo")) return 0.5;
    return 1;
  };
  const pesoTotal = targets.reduce((sum, t) => sum + pesoDe(t), 0);
  if (pesoTotal <= 0) return sessions;

  const extraPorId = new Map<string, number>();
  targets.forEach(t => {
    const extra = Math.round(deficit * (pesoDe(t) / pesoTotal) * 10) / 10;
    if (extra > 0) extraPorId.set(t.id, extra);
  });
  if (extraPorId.size === 0) return sessions;

  return sessions.map(s => extraPorId.has(s.id) ? { ...s, extraKm: extraPorId.get(s.id) } : s);
}

// ─────────────────────────────────────────────────────────────────────────────
// BADGE
// ─────────────────────────────────────────────────────────────────────────────
function Badge({ sub, size = "sm" }: { sub: Subtype; size?: "sm" | "xs" }) {
  const c = SUB[sub];
  const px = size === "xs" ? "4px 6px" : "4px 8px";
  const fs = size === "xs" ? 8 : 9;
  return (
    <span
      className="rounded font-black uppercase tracking-wider inline-block"
      style={{ background: c.bg, color: c.color, border: `1px solid ${c.color}55`, boxShadow: c.glow, padding: px, fontSize: fs, lineHeight: "14px" }}
    >
      {c.label}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// COMPLETE BUTTON
// ─────────────────────────────────────────────────────────────────────────────
function CompleteBtn({ completed, locked, onToggle }: { completed: boolean; locked?: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); if (!locked) onToggle(); }}
      className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-all ${locked ? "cursor-default" : ""}`}
      title={locked ? "Sincronizado con Garmin — no se puede desmarcar" : undefined}
      style={{
        background: completed ? "rgba(16,185,129,0.2)" : T.bgSurf,
        border: `1px solid ${completed ? "#10b98166" : "#334155"}`,
      }}
    >
      {completed
        ? <Check className="w-3.5 h-3.5" style={{ color: "#34d399" }} />
        : <div className="w-1.5 h-1.5 rounded-full" style={{ background: "#334155" }} />
      }
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// CARD CARRERA
// ─────────────────────────────────────────────────────────────────────────────
function CardCarrera({ session, isReorderMode, onToggle, onOpen, onReorderTap }: {
  session: Session; isReorderMode: boolean;
  onToggle: () => void; onOpen: () => void; onReorderTap: () => void;
}) {
  const locked = !!session.garminBacked;
  return (
    <div
      onClick={() => isReorderMode ? onReorderTap() : onOpen()}
      className="p-3 rounded-xl cursor-pointer transition-all relative"
      style={{
        background: locked ? "rgba(16,185,129,0.14)" : session.completed ? "rgba(15,23,42,0.5)" : T.bgSurf,
        border: `1px solid ${isReorderMode ? T.reorder + "80" : locked ? "#10b98180" : T.border}`,
        opacity: session.completed && !locked ? 0.7 : 1,
        boxShadow: isReorderMode ? `0 0 0 1px ${T.reorder}60` : locked ? "0 0 0 1px rgba(16,185,129,0.25)" : "none",
      }}
    >
      {isReorderMode && (
        <div className="absolute top-2 right-2 w-5 h-5 rounded-full flex items-center justify-center animate-pulse" style={{ background: T.reorder }}>
          <ArrowLeftRight className="w-2.5 h-2.5" style={{ color: T.reorderTx }} />
        </div>
      )}
      {/* Top row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge sub={session.subtype} />
          <span className="text-xs font-bold line-clamp-1" style={{ color: T.text1 }}>{session.title}</span>
        </div>
        {!isReorderMode && <CompleteBtn completed={session.completed} locked={locked} onToggle={onToggle} />}
      </div>
      {/* Bottom row */}
      <div className="mt-2 flex items-center justify-between text-[11px]" style={{ color: T.text2 }}>
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3" style={{ color: T.text3 }} />
          <span>{session.duration}</span>
        </div>
        {session.metric && (
          <span className="font-semibold" style={{ color: locked ? "#34d399" : "#f1f5f9" }}>
            {session.metric}
            {session.extraKm ? <span style={{ color: "#f87171" }}> +{session.extraKm.toFixed(1).replace(".0", "")}km</span> : null}
          </span>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// CARD FUERZA
// ─────────────────────────────────────────────────────────────────────────────
function CardFuerza({ session, isReorderMode, onToggle, onReorderTap }: {
  session: Session; isReorderMode: boolean;
  onToggle: () => void; onReorderTap: () => void;
}) {
  const locked = !!session.garminBacked;
  return (
    <div
      onClick={() => isReorderMode ? onReorderTap() : undefined}
      className="p-3 rounded-xl transition-all relative"
      style={{
        background: locked ? "rgba(16,185,129,0.14)" : session.completed ? "rgba(15,23,42,0.5)" : T.bgSurf,
        border: `1px solid ${isReorderMode ? T.reorder + "80" : locked ? "#10b98180" : T.border}`,
        opacity: session.completed && !locked ? 0.7 : 1,
        boxShadow: isReorderMode ? `0 0 0 1px ${T.reorder}60` : locked ? "0 0 0 1px rgba(16,185,129,0.25)" : "none",
        cursor: isReorderMode ? "pointer" : "default",
      }}
    >
      {isReorderMode && (
        <div className="absolute top-2 right-2 w-5 h-5 rounded-full flex items-center justify-center animate-pulse" style={{ background: T.reorder }}>
          <ArrowLeftRight className="w-2.5 h-2.5" style={{ color: T.reorderTx }} />
        </div>
      )}
      {/* Top row */}
      <div className="flex items-center justify-between">
        <Badge sub={session.subtype} />
        {!isReorderMode && <CompleteBtn completed={session.completed} locked={locked} onToggle={onToggle} />}
      </div>
      <div className="mt-2 flex items-center gap-1 text-[11px]" style={{ color: T.text2 }}>
        <Clock className="w-3 h-3" style={{ color: T.text3 }} />
        <span>{session.duration}</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// CARD EXTRA (actividad Garmin hecha pero no planificada — solo lectura)
// ─────────────────────────────────────────────────────────────────────────────
function CardExtra({ session }: { session: Session }) {
  const c = SUB.EXTRA;
  return (
    <div className="p-3 rounded-xl relative" style={{ background: `${c.bg}55`, border: `1px solid ${c.color}40` }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge sub="EXTRA" />
          <span className="text-xs font-bold line-clamp-1" style={{ color: T.text1 }}>{session.title}</span>
        </div>
        <Check className="w-3.5 h-3.5 shrink-0" style={{ color: c.color }} />
      </div>
      <div className="mt-2 flex items-center justify-between text-[11px]" style={{ color: T.text2 }}>
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3" style={{ color: T.text3 }} />
          <span>{session.duration}</span>
        </div>
        {session.metric && (
          <span className="font-semibold" style={{ color: "#f1f5f9" }}>{session.metric}</span>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DAY BLOCK
// ─────────────────────────────────────────────────────────────────────────────
function DayBlock({ dayLabel, sessions, isReorderMode, onToggle, onOpen, onReorderTap }: {
  dayLabel: string; sessions: Session[]; isReorderMode: boolean;
  onToggle: (id: string) => void; onOpen: (s: Session) => void; onReorderTap: (s: Session) => void;
}) {
  return (
    <div className="rounded-2xl p-3" style={{ background: "rgba(30,41,59,0.55)", border: `1px solid ${T.border}` }}>
      {/* Day header */}
      <div className="flex items-center justify-center mb-2">
        <span className="text-[10px] font-black" style={{ color: "#818cf8" }}>{dayLabel}</span>
      </div>

      {/* Session cards */}
      <div className="space-y-2">
        {sessions.map(s => s.origin === "garmin"
          ? <CardExtra key={s.id} session={s} />
          : s.type === "carrera"
            ? <CardCarrera key={s.id} session={s} isReorderMode={isReorderMode}
                onToggle={() => onToggle(s.id)} onOpen={() => onOpen(s)}
                onReorderTap={() => onReorderTap(s)} />
            : <CardFuerza key={s.id} session={s} isReorderMode={isReorderMode}
                onToggle={() => onToggle(s.id)} onReorderTap={() => onReorderTap(s)} />
        )}
        {sessions.length === 0 && (
          <p className="py-2 text-center text-[10px] italic" style={{ color: "#475569" }}>
            Carga de asimilación / descanso activo
          </p>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// RUNNING EDIT MODAL (Bottom Sheet)
// ─────────────────────────────────────────────────────────────────────────────
function RunningEditModal({ session, onClose, onSave, onToggle, onDelete, onMove, days }: {
  session: Session; onClose: () => void;
  onSave: (id: string, fields: Partial<Session>) => void;
  onToggle: (id: string) => void; onDelete: (id: string) => void;
  onMove: (id: string, dayIndex: number) => void; days: string[];
}) {
  const [title, setTitle] = useState(session.title);
  const [duration, setDuration] = useState(session.duration);
  const [metric, setMetric] = useState(session.metric);
  const [notes, setNotes] = useState(session.notes);

  return (
    <div className="absolute inset-0 z-50 flex items-end" style={{ background: "rgba(2,6,23,0.85)", backdropFilter: "blur(4px)" }}>
      <div className="w-full rounded-t-[32px] overflow-y-auto" style={{ background: T.bgSurf, border: `1px solid ${T.border}`, borderBottom: "none", maxHeight: "85%", paddingBottom: "env(safe-area-inset-bottom)" }}>
        <div className="p-6 space-y-5">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge sub={session.subtype} />
              <span className="text-xs font-bold" style={{ color: T.text2 }}>Editar Plan: {days[session.dayIndex]}</span>
            </div>
            <button onClick={onClose} className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: T.border }}>
              <X className="w-5 h-5" style={{ color: T.text2 }} />
            </button>
          </div>

          {/* Title */}
          <div className="space-y-1.5">
            <label className="text-[9px] font-black uppercase tracking-wider block" style={{ color: T.text3 }}>Título de la Sesión</label>
            <input value={title} onChange={e => setTitle(e.target.value)} className="w-full rounded-xl py-2.5 px-3 text-xs font-bold outline-none focus:border-cyan-500" style={{ background: T.bgApp, border: `1px solid ${T.border}`, color: T.text1 }} />
          </div>

          {/* Duration + Metric */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-[9px] font-black uppercase tracking-wider block" style={{ color: T.text3 }}>Duración</label>
              <div className="relative flex items-center">
                <Clock className="absolute left-3 w-4 h-4" style={{ color: T.text3 }} />
                <input value={duration} onChange={e => setDuration(e.target.value)} className="w-full rounded-xl py-2.5 pl-9 pr-3 text-xs font-bold outline-none" style={{ background: T.bgApp, border: `1px solid ${T.border}`, color: T.text1 }} />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-black uppercase tracking-wider block" style={{ color: T.text3 }}>Volumen (km)</label>
              <div className="relative flex items-center">
                <Flame className="absolute left-3 w-4 h-4 text-cyan-400" />
                <input value={metric} onChange={e => setMetric(e.target.value)} className="w-full rounded-xl py-2.5 pl-9 pr-3 text-xs font-bold outline-none" style={{ background: T.bgApp, border: `1px solid ${T.border}`, color: T.text1 }} />
              </div>
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <label className="text-[9px] font-black uppercase tracking-wider block" style={{ color: T.text3 }}>Notas de Ejecución y Ritmo Z2 medio</label>
            <textarea rows={3} value={notes} onChange={e => setNotes(e.target.value)} className="w-full rounded-xl py-2.5 px-3 text-xs resize-none outline-none font-mono leading-relaxed" style={{ background: T.bgApp, border: `1px solid ${T.border}`, color: T.text2 }} />
          </div>

          {/* Move to day */}
          <div className="space-y-2">
            <h4 className="text-[10px] font-black uppercase tracking-wider" style={{ color: T.reorder }}>Mover entrenamiento</h4>
            <div className="flex justify-between gap-1">
              {days.map((d, i) => (
                <button key={d} onClick={() => onMove(session.id, i)}
                  className="flex-1 py-2 rounded-lg text-[10px] font-black border transition-all"
                  style={{
                    background: session.dayIndex === i ? T.reorder : T.bgApp,
                    color: session.dayIndex === i ? T.reorderTx : T.text2,
                    borderColor: session.dayIndex === i ? T.reorder : T.border,
                  }}>
                  {d.substring(0, 3)}
                </button>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button onClick={() => { onSave(session.id, { title, duration, metric, notes }); onClose(); }}
              className="flex-1 py-3 px-4 text-white font-black text-xs rounded-xl flex items-center justify-center gap-2"
              style={{ background: "linear-gradient(135deg,#06b6d4,#4f46e5)", boxShadow: "0 4px 16px rgba(6,182,212,0.25)" }}>
              <Save className="w-4 h-4" /> Guardar
            </button>
            <button onClick={() => { if (!session.garminBacked) onToggle(session.id); }}
              disabled={session.garminBacked}
              title={session.garminBacked ? "Sincronizado con Garmin — no se puede desmarcar" : undefined}
              className="py-3 px-4 rounded-xl font-bold text-xs flex items-center gap-2 border transition-all disabled:cursor-default"
              style={{ background: session.completed ? "rgba(16,185,129,0.15)" : "rgba(255,255,255,0.06)", color: session.completed ? "#34d399" : T.text2, borderColor: session.completed ? "#10b98166" : T.border }}>
              <Check className="w-4 h-4" />{session.completed ? "Hecho" : "Completar"}
            </button>
            <button onClick={() => { onDelete(session.id); onClose(); }}
              className="w-12 rounded-xl flex items-center justify-center border transition-all"
              style={{ background: "rgba(239,68,68,0.08)", borderColor: "rgba(239,68,68,0.25)", color: "#f87171" }}>
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// REORDER MODAL
// ─────────────────────────────────────────────────────────────────────────────
function ReorderModal({ session, days, onMove, onClose }: {
  session: Session; days: string[]; onMove: (id: string, dayIndex: number) => void; onClose: () => void;
}) {
  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center p-6" style={{ background: "rgba(2,6,23,0.8)", backdropFilter: "blur(4px)" }}>
      <div className="w-full rounded-3xl p-5 space-y-4" style={{ background: T.bgSurf, border: `1px solid ${T.border}` }}>
        <div className="text-center">
          <h3 className="text-sm font-bold" style={{ color: T.reorder }}>¿A qué día quieres mover la sesión?</h3>
          <p className="text-xs mt-1 font-semibold" style={{ color: T.text2 }}>{session.title}</p>
        </div>
        <div className="grid grid-cols-4 gap-2">
          {days.map((d, i) => (
            <button key={d} onClick={() => onMove(session.id, i)}
              className="py-3 rounded-xl text-xs font-black border transition-all active:scale-95"
              style={{ background: T.bgApp, color: T.text2, border: `1px solid ${T.border}` }}>
              {d}
            </button>
          ))}
        </div>
        <button onClick={onClose} className="w-full py-2.5 rounded-xl text-xs font-bold" style={{ background: T.border, color: T.text2 }}>
          Cancelar
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ADD SESSION MODAL
// ─────────────────────────────────────────────────────────────────────────────
interface NewSessionFields {
  type: "carrera" | "fuerza"; subtype: Subtype; dayIndex: number; metric: string; notes: string;
}

function AddSessionModal({ days, onAdd, onClose }: {
  days: string[]; onAdd: (fields: NewSessionFields) => Promise<void>; onClose: () => void;
}) {
  const [type, setType] = useState<"carrera" | "fuerza">("carrera");
  const [subtype, setSubtype] = useState<Subtype>("RB");
  const [day, setDay] = useState(0);
  const [metric, setMetric] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const runSubs: Subtype[] = ["RB", "TL", "CAL"];
  const strSubs: Subtype[] = ["PUSH", "PULL", "PIERNA"];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onAdd({ type, subtype, dayIndex: day, metric, notes });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="absolute inset-0 z-50 flex items-end" style={{ background: "rgba(2,6,23,0.8)", backdropFilter: "blur(4px)" }}>
      <form onSubmit={handleSubmit} className="w-full rounded-t-[32px] p-6 space-y-5" style={{ background: T.bgSurf, border: `1px solid ${T.border}`, borderBottom: "none" }}>
        <div className="flex items-center justify-between">
          <h3 className="text-base font-black" style={{ color: T.text1 }}>Nueva Sesión</h3>
          <button type="button" onClick={onClose} className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: T.border }}>
            <X className="w-4 h-4" style={{ color: T.text2 }} />
          </button>
        </div>

        {/* Type */}
        <div>
          <label className="text-[10px] font-black uppercase tracking-wider mb-2 block" style={{ color: T.text3 }}>Tipo</label>
          <div className="grid grid-cols-2 gap-2 p-1 rounded-xl" style={{ background: T.bgApp, border: `1px solid ${T.border}` }}>
            {(["carrera","fuerza"] as const).map(t => (
              <button key={t} type="button" onClick={() => { setType(t); setSubtype(t === "carrera" ? "RB" : "PUSH"); }}
                className="py-2 text-xs font-black rounded-lg transition-all"
                style={{ background: type === t ? T.border : "transparent", color: type === t ? T.text1 : T.text3 }}>
                {t === "carrera" ? "Carrera" : "Fuerza"}
              </button>
            ))}
          </div>
        </div>

        {/* Subtype */}
        <div>
          <label className="text-[10px] font-black uppercase tracking-wider mb-2 block" style={{ color: T.text3 }}>Categoría</label>
          <div className="grid grid-cols-3 gap-2">
            {(type === "carrera" ? runSubs : strSubs).map(st => {
              const c = SUB[st];
              const active = subtype === st;
              return (
                <button key={st} type="button" onClick={() => setSubtype(st)}
                  className="py-2 rounded-xl text-xs font-black border transition-all"
                  style={{ background: active ? c.bg : T.bgApp, borderColor: active ? c.color : T.border, color: active ? c.color : T.text3, boxShadow: active ? c.glow : "none" }}>
                  {st === "RB" ? "RB (Rodaje)" : st === "TL" ? "TL (Larga)" : st === "CAL" ? "Calidad" : st === "PUSH" ? "Push" : st === "PULL" ? "Pull" : "Pierna"}
                </button>
              );
            })}
          </div>
        </div>

        {/* Day */}
        <div>
          <label className="text-[10px] font-black uppercase tracking-wider mb-2 block" style={{ color: T.text3 }}>Día Planificado</label>
          <div className="flex gap-1 p-1 rounded-xl" style={{ background: T.bgApp, border: `1px solid ${T.border}` }}>
            {days.map((d, i) => (
              <button key={d} type="button" onClick={() => setDay(i)}
                className="flex-1 py-1.5 rounded text-[10px] font-black transition-all"
                style={{ background: day === i ? T.border : "transparent", color: day === i ? T.text1 : T.text3 }}>
                {d.substring(0, 3)}
              </button>
            ))}
          </div>
        </div>

        {type === "carrera" && (
          <div>
            <label className="text-[10px] font-black uppercase tracking-wider mb-1.5 block" style={{ color: T.text3 }}>Objetivo (km)</label>
            <input value={metric} onChange={e => setMetric(e.target.value)} placeholder="Ej: 12"
              className="w-full rounded-xl py-2 px-3 text-xs font-semibold outline-none"
              style={{ background: T.bgApp, border: `1px solid ${T.border}`, color: T.text2 }} />
          </div>
        )}

        <div>
          <label className="text-[10px] font-black uppercase tracking-wider mb-1.5 block" style={{ color: T.text3 }}>Notas de apoyo</label>
          <input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Ej: Calentar bien..."
            className="w-full rounded-xl py-2 px-3 text-xs font-semibold outline-none"
            style={{ background: T.bgApp, border: `1px solid ${T.border}`, color: T.text2 }} />
        </div>

        <button type="submit" disabled={saving} className="w-full py-3 rounded-xl text-xs font-black text-white active:scale-[0.98] disabled:opacity-60"
          style={{ background: "linear-gradient(135deg,#06b6d4,#4f46e5)" }}>
          {saving ? "Añadiendo…" : "Añadir al Calendario"}
        </button>
      </form>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// REHACER PLAN — recalcula las sesiones de Carrera de la semana. El usuario fija
// los km objetivo y si quiere sesión de calidad; "Generar" solo previsualiza
// (dry_run, no toca la BD) y deja editar cada sesión antes de "Añadir estas
// sesiones", que sustituye las sesiones de Carrera planificadas por las nuevas
// (Fuerza no se toca). Sin sesión de calidad, esos km se rellenan con Rodaje Base.
// ─────────────────────────────────────────────────────────────────────────────
function RegenerarPlanCard({ userId, monday, onApplied, showToast }: {
  userId: number; monday: Date; onApplied: () => void;
  showToast: (text: string, kind?: "error" | "success") => void;
}) {
  const [open, setOpen] = useState(false);
  const [kmObjetivo, setKmObjetivo] = useState("");
  const [incluirCalidad, setIncluirCalidad] = useState(true);
  const [cicloOverride, setCicloOverride] = useState<"" | CicloOverride>("");
  const [generating, setGenerating] = useState(false);
  const [applying, setApplying] = useState(false);
  const [preview, setPreview] = useState<SesionGenerada[] | null>(null);

  const handleGenerar = async () => {
    setGenerating(true);
    setPreview(null);
    try {
      const km = kmObjetivo.trim() ? parseFloat(kmObjetivo) : undefined;
      const res = await generarPlanSemana(userId, toISODate(monday), km, {
        incluirCalidad, dryRun: true, cicloOverride: cicloOverride || undefined,
      });
      setPreview(res.sesiones.filter(s => s.tipo === "Carrera"));
    } catch {
      showToast("No se pudo generar la previsualización.");
    } finally {
      setGenerating(false);
    }
  };

  const updatePreviewRow = (idx: number, field: "sesion" | "km_planificados", value: string) => {
    setPreview(prev => {
      if (!prev) return prev;
      const next = [...prev];
      const row = { ...next[idx] };
      if (field === "sesion") row.sesion = value;
      else row.km_planificados = value === "" ? null : parseFloat(value);
      next[idx] = row;
      return next;
    });
  };

  const handleAplicar = async () => {
    if (!preview) return;
    setApplying(true);
    try {
      await aplicarSemanaGenerada(userId, toISODate(monday), preview);
      showToast("Plan de carrera actualizado.", "success");
      setPreview(null);
      setOpen(false);
      onApplied();
    } catch {
      showToast("No se pudo aplicar el nuevo plan.");
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="rounded-2xl p-4 mt-2" style={{ background: "rgba(15,23,42,0.6)", border: `1px solid ${T.border}` }}>
      <button onClick={() => setOpen(p => !p)} className="w-full flex items-center justify-between">
        <span className="flex items-center gap-2 text-xs font-black" style={{ color: T.text1 }}>
          <RefreshCw className="w-4 h-4" style={{ color: "#22d3ee" }} /> Rehacer plan de la semana
        </span>
        <ChevronRight className="w-4 h-4 transition-transform" style={{ color: T.text3, transform: open ? "rotate(90deg)" : "none" }} />
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-[9px] font-black uppercase tracking-wider block" style={{ color: T.text3 }}>Km esta semana</label>
              <input type="number" min="0" step="0.5" value={kmObjetivo} onChange={e => setKmObjetivo(e.target.value)}
                placeholder="Auto"
                className="w-full rounded-xl py-2.5 px-3 text-xs font-bold outline-none" style={{ background: T.bgApp, border: `1px solid ${T.border}`, color: T.text1 }} />
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-black uppercase tracking-wider block" style={{ color: T.text3 }}>Tipo de semana</label>
              <select value={cicloOverride} onChange={e => setCicloOverride(e.target.value as "" | CicloOverride)}
                className="w-full rounded-xl py-2.5 px-3 text-xs font-bold outline-none" style={{ background: T.bgApp, border: `1px solid ${T.border}`, color: T.text1 }}>
                <option value="">Automático</option>
                <option value="carga1">Carga 1</option>
                <option value="carga2">Carga 2</option>
                <option value="carga3">Carga 3</option>
                <option value="descarga">Descarga</option>
              </select>
            </div>
            <label className="flex items-center gap-2 self-end pb-2.5 cursor-pointer">
              <input type="checkbox" checked={incluirCalidad} onChange={e => setIncluirCalidad(e.target.checked)}
                className="w-4 h-4 rounded" />
              <span className="text-[10px] font-bold" style={{ color: T.text2 }}>Sesión de calidad</span>
            </label>
          </div>

          <button onClick={handleGenerar} disabled={generating}
            className="w-full py-2.5 rounded-xl text-xs font-black text-white flex items-center justify-center gap-2 disabled:opacity-60"
            style={{ background: "linear-gradient(135deg,#06b6d4,#4f46e5)" }}>
            <Zap className="w-4 h-4" /> {generating ? "Generando…" : "Generar"}
          </button>

          {preview && (
            <div className="space-y-2 pt-1">
              <p className="text-[9px] font-black uppercase tracking-wider" style={{ color: T.text3 }}>
                Nuevas sesiones de carrera — revisa y edita antes de añadir
              </p>
              {preview.map((s, idx) => (
                <div key={idx} className="rounded-xl p-2.5 flex items-center gap-2" style={{ background: T.bgApp, border: `1px solid ${T.border}` }}>
                  <span className="text-[9px] font-black w-7 shrink-0" style={{ color: "#818cf8" }}>
                    {DAYS[differenceInCalendarDays(parseISO(s.fecha), monday)] ?? "?"}
                  </span>
                  <input value={s.sesion} onChange={e => updatePreviewRow(idx, "sesion", e.target.value)}
                    className="flex-1 min-w-0 text-xs font-bold bg-transparent outline-none" style={{ color: T.text1 }} />
                  <input type="number" step="0.5" value={s.km_planificados ?? ""} onChange={e => updatePreviewRow(idx, "km_planificados", e.target.value)}
                    className="w-14 text-xs font-bold bg-transparent outline-none text-right" style={{ color: "#22d3ee" }} />
                  <span className="text-[10px]" style={{ color: T.text3 }}>km</span>
                </div>
              ))}
              <div className="flex gap-2 pt-1">
                <button onClick={handleAplicar} disabled={applying}
                  className="flex-1 py-2.5 rounded-xl text-xs font-black text-white flex items-center justify-center gap-2 disabled:opacity-60"
                  style={{ background: "#10b981" }}>
                  <Save className="w-4 h-4" /> {applying ? "Añadiendo…" : "Añadir estas sesiones"}
                </button>
                <button onClick={() => setPreview(null)}
                  className="px-4 py-2.5 rounded-xl text-xs font-bold" style={{ background: T.border, color: T.text2 }}>
                  Cancelar
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// WEEKLY VIEW
// ─────────────────────────────────────────────────────────────────────────────
function WeeklyView({
  sessions, loading, error, weekLabel, onPrevWeek, onNextWeek,
  onToggle, onSave, onDelete, onMove, onAdd,
  userId, monday, onApplied, showToast, cicloLabel,
}: {
  sessions: Session[]; loading: boolean; error: string | null; weekLabel: string;
  onPrevWeek: () => void; onNextWeek: () => void;
  onToggle: (id: string) => void;
  onSave: (id: string, fields: Partial<Session>) => void;
  onDelete: (id: string) => void;
  onMove: (id: string, dayIndex: number) => void;
  onAdd: (fields: NewSessionFields) => Promise<void>;
  userId: number;
  monday: Date;
  onApplied: () => void;
  showToast: (text: string, kind?: "error" | "success") => void;
  cicloLabel: string;
}) {
  const [isReorderMode, setIsReorderMode] = useState(false);
  const [editingSession, setEditingSession] = useState<Session | null>(null);
  const [reorderingSession, setReorderingSession] = useState<Session | null>(null);
  const [isAdding, setIsAdding] = useState(false);

  return (
    <div className="flex flex-col h-full">
      {/* TopBar */}
      <header className="px-5 py-3 shrink-0 flex items-center justify-end gap-2" style={{ background: T.bgSurf, borderBottom: `1px solid ${T.border}80` }}>
        {/* Pastilla carga/descarga */}
        <span className="text-[10px] px-3 py-2 rounded-full font-black"
          style={cicloLabel === "Descarga"
            ? { background: "rgba(16,185,129,0.15)", color: "#34d399", border: "1px solid #10b98150" }
            : { background: "rgba(59,130,246,0.15)", color: "#60a5fa", border: "1px solid #3b82f650" }}>
          {cicloLabel}
        </span>
        {/* Reorder button */}
        <button onClick={() => setIsReorderMode(p => !p)}
          className="flex items-center gap-1.5 text-xs px-3.5 py-2 rounded-full font-black transition-all"
          style={{
            background: isReorderMode ? T.reorder : T.border,
            color: isReorderMode ? T.reorderTx : T.text2,
            boxShadow: isReorderMode ? `0 4px 12px ${T.reorder}40` : "none",
          }}>
          <ArrowLeftRight className="w-3.5 h-3.5" />
          {isReorderMode ? "Listo" : "Reorganizar"}
        </button>
      </header>

      {/* Week navigator */}
      <div className="px-4 py-2.5 flex items-center justify-between shrink-0" style={{ background: T.bgSurf, border: "1px solid #22d3ee40", margin: "0 16px 12px", borderRadius: 16, boxShadow: "0 4px 16px rgba(0,0,0,0.25)" }}>
        <button onClick={onPrevWeek} className="w-10 h-10 flex items-center justify-center rounded-xl" style={{ background: "rgba(34,211,238,0.12)", border: "1px solid #22d3ee50", color: "#22d3ee" }}>
          <ChevronLeft className="w-5 h-5" />
        </button>
        <div className="text-center">
          <p className="text-[9px] font-black uppercase tracking-widest" style={{ color: "#22d3ee" }}>PROGRAMA SEMANAL</p>
          <p className="text-xs font-bold" style={{ color: T.text1 }}>{weekLabel}</p>
        </div>
        <button onClick={onNextWeek} className="w-10 h-10 flex items-center justify-center rounded-xl" style={{ background: "rgba(34,211,238,0.12)", border: "1px solid #22d3ee50", color: "#22d3ee" }}>
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Days scroll */}
      <div className="flex-1 overflow-y-auto px-4 pb-6 space-y-3">
        {loading && (
          <p className="py-8 text-center text-xs font-semibold" style={{ color: T.text3 }}>Cargando plan semanal…</p>
        )}
        {!loading && error && (
          <p className="py-8 text-center text-xs font-semibold" style={{ color: "#f87171" }}>{error}</p>
        )}
        {!loading && !error && DAYS.map((d, i) => (
          <DayBlock key={d} dayLabel={d}
            sessions={sessions.filter(s => s.dayIndex === i)}
            isReorderMode={isReorderMode}
            onToggle={onToggle}
            onOpen={s => setEditingSession(s)}
            onReorderTap={s => setReorderingSession(s)}
          />
        ))}
        {!loading && !error && (
          <RegenerarPlanCard userId={userId} monday={monday} onApplied={onApplied} showToast={showToast} />
        )}
      </div>

      {/* FAB */}
      <button onClick={() => setIsAdding(true)}
        className="absolute bottom-24 right-4 w-14 h-14 rounded-full flex items-center justify-center shadow-lg z-30 transition-all hover:scale-105"
        style={{ background: "linear-gradient(135deg,#06b6d4,#4f46e5)", boxShadow: "0 8px 24px rgba(6,182,212,0.35)" }}>
        <Plus className="w-6 h-6 text-white" />
      </button>

      {/* Modals */}
      {editingSession && (
        <RunningEditModal session={editingSession} days={DAYS}
          onClose={() => setEditingSession(null)} onSave={onSave}
          onToggle={onToggle} onDelete={onDelete} onMove={onMove}
        />
      )}
      {reorderingSession && (
        <ReorderModal session={reorderingSession} days={DAYS}
          onMove={(id, dayIndex) => { onMove(id, dayIndex); setReorderingSession(null); }}
          onClose={() => setReorderingSession(null)} />
      )}
      {isAdding && (
        <AddSessionModal days={DAYS} onAdd={onAdd} onClose={() => setIsAdding(false)} />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MONTHLY VIEW (fetch propio de 5 semanas reales para cubrir la cuadrícula)
// ─────────────────────────────────────────────────────────────────────────────
interface WeekRow { monday: Date; sessions: Session[]; kmPlanificados: number; kmRealizados: number }

function MonthlyView({ userId, refreshKey }: { userId: number; refreshKey: number }) {
  const [monthOffset, setMonthOffset] = useState(0);
  const [weeks, setWeeks] = useState<WeekRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [clickedDayIso, setClickedDayIso] = useState<string | null>(null);

  const monthDate = useMemo(() => startOfMonth(addMonths(new Date(), monthOffset)), [monthOffset]);
  const gridStart = useMemo(() => {
    const offsetDays = (getDay(monthDate) + 6) % 7; // Lun=0…Dom=6
    return addDays(monthDate, -offsetDays);
  }, [monthDate]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setClickedDayIso(null);
    const mondays = Array.from({ length: 5 }, (_, i) => addDays(gridStart, i * 7));
    Promise.all(mondays.map(m => getPlanSemana(userId, toISODate(m))))
      .then(plans => {
        if (cancelled) return;
        setWeeks(plans.map((p, i) => {
          const planSessions = p.sesiones.map(s => toSession(s, mondays[i]));
          return {
            monday: mondays[i],
            sessions: applyGarminMatching(planSessions, p.actividades_garmin, mondays[i]),
            kmPlanificados: p.stats.km_planificados,
            kmRealizados: p.stats.km_realizados,
          };
        }));
      })
      .catch(() => { if (!cancelled) setWeeks([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [userId, gridStart, refreshKey]);

  const DAYS_HEADER = ["L","M","M","J","V","S","D"];
  const today = new Date();

  const clickedSessions = useMemo(() => {
    if (!clickedDayIso) return [];
    const rowIdx = weeks.findIndex(w => {
      const diff = differenceInCalendarDays(parseISO(clickedDayIso), w.monday);
      return diff >= 0 && diff <= 6;
    });
    if (rowIdx === -1) return [];
    const dIdx = differenceInCalendarDays(parseISO(clickedDayIso), weeks[rowIdx].monday);
    return weeks[rowIdx].sessions.filter(s => s.dayIndex === dIdx);
  }, [clickedDayIso, weeks]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 pb-6 pt-4">
        {/* Month nav */}
        <div className="flex items-center justify-between p-2 rounded-xl my-3" style={{ background: T.bgSurf, border: `1px solid ${T.border}` }}>
          <button onClick={() => setMonthOffset(o => o - 1)}
            className="w-9 h-9 flex items-center justify-center rounded-lg transition-all"
            style={{ background: T.bgApp, border: `1px solid ${T.border}`, color: "#22d3ee" }}>
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs font-black uppercase tracking-wider" style={{ color: "#818cf8" }}>
            {capitalize(format(monthDate, "MMMM yyyy", { locale: es }))}
          </span>
          <button onClick={() => setMonthOffset(o => o + 1)}
            className="w-9 h-9 flex items-center justify-center rounded-lg transition-all"
            style={{ background: T.bgApp, border: `1px solid ${T.border}`, color: "#22d3ee" }}>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {loading && (
          <p className="py-8 text-center text-xs font-semibold" style={{ color: T.text3 }}>Cargando mes…</p>
        )}

        {!loading && (
          <>
            {/* Grid header */}
            <div className="grid grid-cols-8 text-center mb-2">
              {DAYS_HEADER.map((d, i) => (
                <span key={i} className="text-[9px] font-black uppercase" style={{ color: T.text3 }}>{d}</span>
              ))}
              <span className="text-[9px] font-black uppercase" style={{ color: "#22d3ee", borderLeft: `1px solid ${T.border}60`, paddingLeft: 2 }}>Kms</span>
            </div>

            {/* Grid rows */}
            <div className="space-y-1">
              {weeks.map((row, weekIdx) => (
                <div key={weekIdx} className="grid grid-cols-8 gap-1 items-center">
                  {Array.from({ length: 7 }).map((_, dIdx) => {
                    const dayDate = addDays(row.monday, dIdx);
                    const inMonth = dayDate.getMonth() === monthDate.getMonth();
                    if (!inMonth) {
                      return <div key={dIdx} className="aspect-square rounded-lg" style={{ background: "rgba(2,6,23,0.2)" }} />;
                    }
                    const daySessions = row.sessions.filter(s => s.dayIndex === dIdx);
                    const isToday = isSameDay(dayDate, today);
                    const iso = toISODate(dayDate);
                    const isSel = clickedDayIso === iso;
                    return (
                      <div key={dIdx} onClick={() => setClickedDayIso(isSel ? null : iso)}
                        className="aspect-square rounded-lg flex flex-col justify-between p-1 cursor-pointer transition-all relative"
                        style={{ background: T.bgSurf, border: `1px solid ${isSel || isToday ? "#22d3ee80" : T.border}`, borderWidth: isToday ? 2 : 1 }}>
                        <span className="text-[9px] font-bold" style={{ color: isToday ? "#22d3ee" : T.text3 }}>{format(dayDate, "d")}</span>
                        <div className="flex gap-0.5 justify-center pb-0.5">
                          {daySessions.slice(0, 3).map((s, i) => (
                            <span key={i} className="w-1.5 h-1.5 rounded-full" style={{ background: SUB[s.subtype].color, boxShadow: SUB[s.subtype].glow }} />
                          ))}
                        </div>
                      </div>
                    );
                  })}
                  {/* Km column: hechos/planeados */}
                  <div className="aspect-square rounded-lg flex flex-col justify-center items-center p-1 text-center"
                    style={{ background: "rgba(15,23,42,0.5)", borderLeft: "2px solid #06b6d4" }}>
                    <span className="text-[10px] font-black leading-tight" style={{ color: "#22d3ee" }}>{row.kmRealizados.toFixed(0)}/{row.kmPlanificados.toFixed(0)}</span>
                    <span className="text-[7px] font-bold uppercase" style={{ color: T.text3 }}>km</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Day detail */}
            {clickedDayIso && (
              <div className="mt-4 rounded-2xl overflow-hidden" style={{ background: T.bgSurf, border: `1px solid ${T.border}` }}>
                <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: `1px solid ${T.border}`, background: "rgba(255,255,255,0.02)" }}>
                  <p className="text-sm font-black" style={{ color: T.text1 }}>{capitalize(format(parseISO(clickedDayIso), "d 'de' MMMM", { locale: es }))}</p>
                  <button onClick={() => setClickedDayIso(null)} className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: T.border }}>
                    <X className="w-3.5 h-3.5" style={{ color: T.text2 }} />
                  </button>
                </div>
                <div className="p-3 space-y-2">
                  {clickedSessions.length > 0
                    ? clickedSessions.map(s => (
                      <div key={s.id} className="flex items-center gap-2 rounded-xl px-3 py-2.5"
                        style={{ background: T.bgApp, border: `1px solid ${T.border}` }}>
                        <Badge sub={s.subtype} size="xs" />
                        <span className="text-xs font-bold flex-1" style={{ color: T.text1 }}>{s.title}</span>
                        <span className="text-[10px]" style={{ color: T.text2 }}>{s.duration}</span>
                        {s.metric && <span className="text-[10px] font-bold" style={{ color: SUB[s.subtype].color }}>{s.metric}</span>}
                      </div>
                    ))
                    : <p className="text-xs italic text-center py-3" style={{ color: T.text3 }}>Sin entrenamientos planificados</p>
                  }
                </div>
              </div>
            )}

            {/* Legend */}
            <div className="mt-4 pt-3.5 grid grid-cols-2 gap-2 text-[9px]" style={{ borderTop: `1px solid ${T.border}60`, color: T.text2 }}>
              <div className="space-y-1.5">
                <p className="font-black uppercase tracking-wide" style={{ color: "#22d3ee" }}>Carrera</p>
                {(["RB","CAL","TL"] as Subtype[]).map(k => (
                  <div key={k} className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-sm" style={{ background: SUB[k].color, boxShadow: SUB[k].glow }} />
                    <span>{k === "RB" ? "RB (Rodaje Base)" : k === "CAL" ? "CAL (Calidad / Series)" : "TL (Tirada Larga)"}</span>
                  </div>
                ))}
              </div>
              <div className="space-y-1.5 pl-2.5" style={{ borderLeft: `1px solid ${T.border}` }}>
                <p className="font-black uppercase tracking-wide" style={{ color: T.reorder }}>Fuerza</p>
                {(["PUSH","PULL","PIERNA"] as Subtype[]).map(k => (
                  <div key={k} className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-sm" style={{ background: SUB[k].color, boxShadow: SUB[k].glow }} />
                    <span>{k === "PUSH" ? "Push (Empuje)" : k === "PULL" ? "Pull (Tirón)" : "Pierna"}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// PROGRESS VIEW (datos reales de /dashboard: running_trend, ritmo_trend, semana_actual)
// ─────────────────────────────────────────────────────────────────────────────
function ProgressView({ weekStats, dashboard, loadingDashboard }: {
  weekStats: { km_planificados: number; km_realizados: number } | null;
  dashboard: DashboardData | null;
  loadingDashboard: boolean;
}) {
  const bars = dashboard?.running_trend ?? [];
  const paceTrend = dashboard?.ritmo_trend ?? [];
  const maxBar = Math.max(1, ...bars.map(b => b.km));
  const totalKm = bars.reduce((a, b) => a + b.km, 0);
  const pctChange = bars.length >= 2 && bars[bars.length - 2].km > 0
    ? Math.round(((bars[bars.length - 1].km - bars[bars.length - 2].km) / bars[bars.length - 2].km) * 100)
    : null;

  const paceMin = paceTrend.length ? Math.min(...paceTrend.map(p => p.ritmo)) : 0;
  const paceMax = paceTrend.length ? Math.max(...paceTrend.map(p => p.ritmo)) : 0;
  const paceRange = paceMax - paceMin || 1;
  const pacePoints = paceTrend.map((p, i) => {
    const x = paceTrend.length > 1 ? 10 + (i / (paceTrend.length - 1)) * 280 : 150;
    const norm = (p.ritmo - paceMin) / paceRange;
    const y = 15 + norm * 90;
    return { x, y, ritmo: p.ritmo, semana: p.semana };
  });
  const pacePath = pacePoints.length
    ? "M " + pacePoints.map(p => `${p.x} ${p.y}`).join(" L ")
    : "";
  const paceAreaPath = pacePoints.length
    ? `${pacePath} L ${pacePoints[pacePoints.length - 1].x} 120 L ${pacePoints[0].x} 120 Z`
    : "";

  const weeklyKms = weekStats?.km_realizados ?? 0;
  const weeklyPlan = weekStats?.km_planificados ?? 0;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        <h2 className="text-base font-bold flex items-center gap-2" style={{ color: T.text1 }}>
          <Award className="w-4 h-4" style={{ color: "#22d3ee" }} /> Rendimiento y Volumen
        </h2>

        {/* Bar chart */}
        <div className="rounded-2xl p-4" style={{ background: "rgba(2,6,23,0.5)", border: `1px solid ${T.border}80` }}>
          <h3 className="text-xs font-black uppercase tracking-wide mb-4" style={{ color: T.text2 }}>Volumen semanal (últimas {bars.length || 8} semanas)</h3>
          {loadingDashboard && <p className="text-[10px] italic text-center py-8" style={{ color: T.text3 }}>Cargando…</p>}
          {!loadingDashboard && bars.length === 0 && (
            <p className="text-[10px] italic text-center py-8" style={{ color: T.text3 }}>Sin datos de Garmin suficientes todavía</p>
          )}
          {!loadingDashboard && bars.length > 0 && (
            <div className="h-40 w-full flex items-end justify-between px-2 relative">
              <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
                <div className="border-b text-[8px] pt-1" style={{ borderColor: T.border + "80", color: T.text3 }}>{maxBar.toFixed(0)} km</div>
                <div className="text-[8px]" style={{ color: T.text3 }}>0 km</div>
              </div>
              {bars.map((b, i) => {
                const h = Math.round((b.km / maxBar) * 140);
                const active = i === bars.length - 1;
                return (
                  <div key={i} className="flex flex-col items-center z-10 group">
                    <span className="text-[9px] font-black mb-1 opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: "#22d3ee" }}>{b.km}k</span>
                    <div className="w-6 rounded-t-lg" style={{
                      height: Math.max(h, 2),
                      background: active ? "linear-gradient(to top,#06b6d4,#4f46e5)" : T.border,
                      boxShadow: active ? "0 0 12px rgba(6,182,212,0.3)" : "none",
                    }} />
                    <span className="text-[10px] font-medium mt-2" style={{ color: T.text2 }}>{b.semana}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Line chart (SVG) */}
        <div className="rounded-2xl p-4" style={{ background: "rgba(2,6,23,0.5)", border: `1px solid ${T.border}80` }}>
          <h3 className="text-xs font-black uppercase tracking-wide mb-4" style={{ color: T.text2 }}>Evolución del ritmo medio (min/km)</h3>
          {!loadingDashboard && paceTrend.length < 2 && (
            <p className="text-[10px] italic text-center py-8" style={{ color: T.text3 }}>Sin datos suficientes todavía</p>
          )}
          {paceTrend.length >= 2 && (
            <div className="h-40 w-full relative">
              <svg className="w-full h-full absolute inset-0 z-10" viewBox="0 0 300 130">
                <defs>
                  <linearGradient id="line-grad-lp" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path d={paceAreaPath} fill="url(#line-grad-lp)" />
                <path d={pacePath} fill="none" stroke="#22d3ee" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
                {pacePoints.map((p, i) => (
                  <circle key={i} cx={p.x} cy={p.y} r={i === pacePoints.length - 1 ? 5 : 4}
                    fill={i === pacePoints.length - 1 ? "#10b981" : "#0891b2"} stroke="#fff" strokeWidth="1.5" />
                ))}
                {pacePoints.map((p, i) => (
                  <text key={i} x={Math.min(Math.max(p.x - 12, 4), 260)} y={p.y > 60 ? p.y + 14 : p.y - 8}
                    fill={i === pacePoints.length - 1 ? "#34d399" : T.text3} fontSize="8" fontWeight="bold">
                    {formatPace(p.ritmo)}
                  </text>
                ))}
              </svg>
            </div>
          )}
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-4 rounded-xl" style={{ background: "rgba(2,6,23,0.4)", border: `1px solid ${T.border}` }}>
            <p className="text-[10px] font-black uppercase" style={{ color: T.text3 }}>KMS ({bars.length || 8} SEMANAS)</p>
            <p className="text-xl font-black mt-1" style={{ color: "#22d3ee" }}>{totalKm.toFixed(1)} km</p>
            {pctChange !== null && (
              <span className="text-[9px] font-bold" style={{ color: pctChange >= 0 ? T.success : "#f87171" }}>
                {pctChange >= 0 ? "▲" : "▼"} {Math.abs(pctChange)}% vs. semana anterior
              </span>
            )}
          </div>
          <div className="p-4 rounded-xl" style={{ background: "rgba(2,6,23,0.4)", border: `1px solid ${T.border}` }}>
            <p className="text-[10px] font-black uppercase" style={{ color: T.text3 }}>KMS SEMANA ACTUAL</p>
            <p className="text-xl font-black mt-1" style={{ color: "#818cf8" }}>{weeklyKms.toFixed(1)} km</p>
            <div className="w-full h-1.5 rounded-full mt-2 overflow-hidden" style={{ background: T.border }}>
              <div className="h-full rounded-full" style={{ width: `${weeklyPlan ? Math.min((weeklyKms / weeklyPlan) * 100, 100) : 0}%`, background: "linear-gradient(90deg,#22d3ee,#4f46e5)" }} />
            </div>
            <span className="text-[8px] font-bold mt-1 block" style={{ color: T.text3 }}>Planificado: {weeklyPlan.toFixed(1)} km</span>
          </div>
        </div>

        {/* Dashboard link */}
        <div className="flex justify-center pt-2">
          <Link to="/dashboard" className="flex items-center gap-2 text-xs font-bold px-4 py-2 rounded-full transition-all"
            style={{ background: "rgba(99,102,241,0.12)", border: "1px solid rgba(99,102,241,0.3)", color: "#818cf8" }}>
            <Zap className="w-3.5 h-3.5" /> Dashboard completo <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// COMPARATOR VIEW (semana actual vs. semana anterior, datos reales)
// ─────────────────────────────────────────────────────────────────────────────
const COMPARE_SUBS: { sub: Subtype; title: string; tag: string }[] = [
  { sub: "RB",  title: "Rodajes Base",           tag: "Ritmo en Zona 2" },
  { sub: "CAL", title: "Series de Calidad",      tag: "Zonas 4 y 5" },
  { sub: "TL",  title: "Tirada Larga (Fondo)",   tag: "Resistencia" },
];

function ComparatorView({ currentSessions, prevSessions }: {
  currentSessions: Session[]; prevSessions: Session[];
}) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {COMPARE_SUBS.map(({ sub, title, tag }) => {
          const c = SUB[sub];
          const curr = currentSessions.find(s => s.subtype === sub);
          const prev = prevSessions.find(s => s.subtype === sub);
          return (
            <div key={sub} className="rounded-2xl overflow-hidden" style={{ border: `1px solid ${T.border}80`, background: "rgba(15,23,42,0.6)" }}>
              <div className="px-4 py-2.5 flex items-center justify-between" style={{ background: `${c.bg}60`, borderBottom: `1px solid ${T.border}80` }}>
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${c.color}20`, border: `1px solid ${c.color}50` }}>
                    <span className="text-[9px] font-black" style={{ color: c.color }}>{sub}</span>
                  </div>
                  <span className="text-xs font-black" style={{ color: T.text1 }}>{title}</span>
                </div>
                <span className="text-[9px] font-bold px-2 py-0.5 rounded-full" style={{ background: `${c.color}15`, color: c.color }}>{tag}</span>
              </div>
              <div className="p-3.5 grid grid-cols-2 gap-4">
                <div className="space-y-1" style={{ borderRight: `1px solid ${T.border}` }}>
                  <p className="text-[9px] font-black uppercase tracking-widest" style={{ color: T.text3 }}>SEMANA ANTERIOR</p>
                  {prev ? (
                    <>
                      <p className="font-black text-base" style={{ color: T.text2 }}>{prev.metric || prev.duration || "—"}</p>
                      {prev.notes && <p className="text-[10px] italic" style={{ color: T.text3 }}>{prev.notes}</p>}
                      <span className="inline-flex text-[9px] font-bold px-1.5 py-0.5 rounded mt-1" style={{ color: prev.completed ? T.success : T.text3, background: prev.completed ? `${T.success}15` : "transparent" }}>
                        {prev.completed ? "Completado" : "No completado"}
                      </span>
                    </>
                  ) : <p className="text-[11px] italic" style={{ color: T.text3 }}>Sin sesión</p>}
                </div>
                <div className="space-y-1 pl-3">
                  <p className="text-[9px] font-black uppercase tracking-widest" style={{ color: c.color }}>SEMANA ACTUAL</p>
                  {curr ? (
                    <>
                      <p className="font-black text-base" style={{ color: T.text1 }}>{curr.metric || curr.duration || "—"}</p>
                      {curr.notes && <p className="text-[10px] italic" style={{ color: c.color }}>{curr.notes}</p>}
                      <span className="inline-flex text-[9px] font-bold px-1.5 py-0.5 rounded mt-1" style={{ color: curr.completed ? T.success : c.color, background: curr.completed ? `${T.success}15` : `${c.color}15` }}>
                        {curr.completed ? "Completado" : "Programado"}
                      </span>
                    </>
                  ) : <p className="text-[11px] italic" style={{ color: T.text3 }}>Sin sesión</p>}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN
// ─────────────────────────────────────────────────────────────────────────────
export function LandingPage() {
  const { userId } = useUser();

  const [activeTab, setActiveTab] = useState<"calendario" | "progreso" | "comparador">("calendario");
  const [calView, setCalView] = useState<"semanal" | "mensual">("semanal");

  const [weekOffset, setWeekOffset] = useState(0);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [prevSessions, setPrevSessions] = useState<Session[]>([]);
  const [weekStats, setWeekStats] = useState<{ km_planificados: number; km_realizados: number } | null>(null);
  const [weekCicloLabel, setWeekCicloLabel] = useState("Carga 1");
  const [loadingWeek, setLoadingWeek] = useState(true);
  const [weekError, setWeekError] = useState<string | null>(null);

  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loadingDashboard, setLoadingDashboard] = useState(true);

  const [toast, setToast] = useState("");
  const [toastKind, setToastKind] = useState<"error" | "success">("error");

  const monday = useMemo(() => mondayFor(weekOffset), [weekOffset]);

  const fetchWeek = useCallback(async () => {
    if (!userId) return;
    setLoadingWeek(true);
    setWeekError(null);
    const currMonday = mondayFor(weekOffset);
    const prevMonday = addWeeks(currMonday, -1);
    try {
      const [curr, prev] = await Promise.all([
        getPlanSemana(userId, toISODate(currMonday)),
        getPlanSemana(userId, toISODate(prevMonday)),
      ]);
      const currPlanSessions = curr.sesiones.map(s => toSession(s, currMonday));
      setSessions(applyDeficitRedistribution(applyGarminMatching(currPlanSessions, curr.actividades_garmin, currMonday), currMonday));
      setWeekStats(curr.stats);
      setWeekCicloLabel(curr.ciclo_label);
      const prevPlanSessions = prev.sesiones.map(s => toSession(s, prevMonday));
      setPrevSessions(applyGarminMatching(prevPlanSessions, prev.actividades_garmin, prevMonday));
    } catch {
      setWeekError("No se pudo cargar el plan de esta semana.");
    } finally {
      setLoadingWeek(false);
    }
  }, [userId, weekOffset]);

  useEffect(() => { fetchWeek(); }, [fetchWeek]);

  const [syncing, setSyncing] = useState(false);
  const [syncState, setSyncState] = useState<"idle" | "success" | "error">("idle");
  const [syncedAt, setSyncedAt] = useState(0);

  const handleSync = useCallback(async () => {
    if (!userId || syncing) return;
    setSyncing(true);
    setSyncState("idle");
    try {
      const res = await sincronizarGarmin(userId);
      await Promise.all([fetchWeek(), getDashboard(userId).then(setDashboard).catch(() => {})]);
      setSyncedAt(Date.now());
      setSyncState("success");
      const auto = res.sesiones_completadas_auto ?? 0;
      setToastKind("success");
      setToast(auto > 0 ? `Garmin sincronizado — ${auto} sesión(es) marcada(s) como hechas.` : "Garmin sincronizado.");
    } catch {
      setSyncState("error");
      setToastKind("error");
      setToast("No se pudo sincronizar con Garmin. Se reintentará en la próxima sync automática.");
    } finally {
      setSyncing(false);
      setTimeout(() => setSyncState("idle"), 2500);
    }
  }, [userId, syncing, fetchWeek]);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    setLoadingDashboard(true);
    getDashboard(userId)
      .then(d => { if (!cancelled) setDashboard(d); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoadingDashboard(false); });
    return () => { cancelled = true; };
  }, [userId]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  const showToast = useCallback((text: string, kind: "error" | "success" = "error") => {
    setToastKind(kind);
    setToast(text);
  }, []);

  const handleToggle = useCallback((id: string) => {
    const target = sessions.find(s => s.id === id);
    if (target?.garminBacked) return; // sincronizada de Garmin — no se puede desmarcar
    setSessions(prev => prev.map(s => s.id === id ? { ...s, completed: !s.completed } : s));
    const nextCompleted = target ? !target.completed : true;
    actualizarSesionCompleta(Number(id), { completado: nextCompleted }).catch(() => {
      setSessions(prev => prev.map(s => s.id === id ? { ...s, completed: !s.completed } : s));
      showToast("No se pudo guardar el cambio.");
    });
  }, [sessions, showToast]);

  const handleSave = useCallback((id: string, fields: Partial<Session>) => {
    actualizarSesionCompleta(Number(id), {
      sesion: fields.title,
      duracion_min: fields.duration ? parseDuracion(fields.duration) : undefined,
      km_planificados: fields.metric ? (parseFloat(fields.metric) || undefined) : undefined,
      detalles: fields.notes,
    })
      .then(fetchWeek)
      .catch(() => showToast("No se pudo guardar la sesión."));
  }, [fetchWeek, showToast]);

  const handleDelete = useCallback((id: string) => {
    borrarSesion(Number(id))
      .then(fetchWeek)
      .catch(() => showToast("No se pudo eliminar la sesión."));
  }, [fetchWeek, showToast]);

  const handleMove = useCallback((id: string, dayIndex: number) => {
    const newFecha = toISODate(addDays(monday, dayIndex));
    actualizarSesionCompleta(Number(id), { fecha: newFecha })
      .then(fetchWeek)
      .catch(() => showToast("No se pudo mover la sesión."));
  }, [monday, fetchWeek, showToast]);

  const handleAdd = useCallback(async (fields: NewSessionFields) => {
    if (!userId) return;
    const fecha = toISODate(addDays(monday, fields.dayIndex));
    try {
      await crearSesion({
        usuario_id: userId,
        fecha,
        tipo: fields.type === "carrera" ? "Carrera" : "Fuerza",
        sesion: defaultTitleFor(fields.type, fields.subtype),
        detalles: fields.notes || "Sesión planificada.",
        duracion_min: fields.type === "carrera" ? 45 : 50,
        km_planificados: fields.type === "carrera" ? (parseFloat(fields.metric) || 10) : undefined,
      });
      await fetchWeek();
    } catch {
      showToast("No se pudo añadir la sesión.");
    }
  }, [userId, monday, fetchWeek]);

  const NAV = [
    { key: "calendario", icon: Calendar, label: "Calendario" },
    { key: "progreso",   icon: TrendingUp, label: "Progreso" },
    { key: "comparador", icon: Award, label: "Comparar" },
  ] as const;

  return (
    <div className="min-h-screen flex items-center justify-center p-0 md:p-6 select-none" style={{ background: T.bgApp }}>
      {/* Phone shell */}
      <div className="w-full max-w-[440px] md:h-[844px] h-screen md:rounded-[40px] overflow-hidden flex flex-col relative md:shadow-2xl md:border-[6px]"
        style={{ background: T.bgSurf, borderColor: T.border }}>

        {/* Global header — siempre visible, en todas las pestañas */}
        <header className="px-5 py-4 shrink-0" style={{ background: T.bgSurf, borderBottom: `1px solid ${T.border}80` }}>
          <div className="flex items-center justify-between">
            <h1 className="text-[18px] font-black bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(90deg,#22d3ee,#818cf8)" }}>
              Proyecto Athlete
            </h1>
            <button onClick={handleSync} disabled={syncing} title="Sincronizar Garmin"
              className="w-9 h-9 rounded-full flex items-center justify-center border transition-all disabled:opacity-70 shrink-0"
              style={{
                background: syncState === "success" ? "rgba(34,197,94,0.2)" : syncState === "error" ? "rgba(239,68,68,0.15)" : T.border,
                borderColor: syncState === "success" ? "rgba(34,197,94,0.5)" : syncState === "error" ? "rgba(239,68,68,0.4)" : "#334155",
              }}>
              <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`}
                style={{ color: syncState === "success" ? "#22c55e" : syncState === "error" ? "#f87171" : T.text2 }} />
            </button>
          </div>
        </header>

        {/* Segmented control (only in calendario tab) */}
        {activeTab === "calendario" && (
          <div className="px-4 pt-3 pb-0 shrink-0" style={{ background: T.bgSurf }}>
            <div className="flex p-1 rounded-xl" style={{ background: T.bgApp, border: `1px solid ${T.border}` }}>
              {(["semanal","mensual"] as const).map(v => (
                <button key={v} onClick={() => setCalView(v)}
                  className="flex-1 py-2 text-xs font-bold rounded-lg transition-all"
                  style={{
                    background: calView === v ? T.border : "transparent",
                    color: calView === v ? T.text1 : T.text3,
                    boxShadow: calView === v ? "0 1px 4px rgba(0,0,0,0.3)" : "none",
                  }}>
                  {v === "semanal" ? "Vista Semanal" : "Vista Mensual"}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Main content */}
        <main className="flex-1 overflow-hidden relative" style={{ background: "rgba(15,23,42,0.4)" }}>
          {activeTab === "calendario" && calView === "semanal" && userId && (
            <WeeklyView
              sessions={sessions} loading={loadingWeek} error={weekError}
              weekLabel={formatWeekLabel(monday)}
              onPrevWeek={() => setWeekOffset(o => o - 1)}
              onNextWeek={() => setWeekOffset(o => o + 1)}
              onToggle={handleToggle} onSave={handleSave} onDelete={handleDelete}
              onMove={handleMove} onAdd={handleAdd}
              userId={userId} monday={monday} onApplied={fetchWeek} showToast={showToast}
              cicloLabel={weekCicloLabel}
            />
          )}
          {activeTab === "calendario" && calView === "mensual" && userId && (
            <MonthlyView userId={userId} refreshKey={syncedAt} />
          )}
          {activeTab === "progreso" && (
            <ProgressView weekStats={weekStats} dashboard={dashboard} loadingDashboard={loadingDashboard} />
          )}
          {activeTab === "comparador" && (
            <ComparatorView currentSessions={sessions} prevSessions={prevSessions} />
          )}

          {toast && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-full text-xs font-bold z-40 text-center max-w-[90%]"
              style={{ background: toastKind === "success" ? "rgba(34,197,94,0.92)" : "rgba(239,68,68,0.9)", color: "#fff" }}>
              {toast}
            </div>
          )}
        </main>

        {/* Bottom NavBar */}
        <nav className="h-20 px-6 flex justify-between items-center shrink-0" style={{ background: "rgba(2,6,23,0.95)", borderTop: `1px solid ${T.border}80`, backdropFilter: "blur(16px)" }}>
          {NAV.map(({ key, icon: Icon, label }) => {
            const active = activeTab === key;
            return (
              <button key={key} onClick={() => setActiveTab(key as typeof activeTab)}
                className="flex flex-col items-center gap-1 transition-all"
                style={{ color: active ? "#22d3ee" : T.text3 }}>
                <Icon className="w-5 h-5" />
                <span className="text-[10px] font-black tracking-wide">{label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
