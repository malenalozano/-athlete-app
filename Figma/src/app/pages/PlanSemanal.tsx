import { useState, useRef, useCallback, useEffect } from "react";
import { useLocation } from "react-router";
import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { useUser } from "../context/UserContext";
import { DndProvider, useDrag, useDrop } from "react-dnd";
import {
  getPlanSemana, actualizarSesion, actualizarSesionCompleta, crearSesion, borrarSesion,
  generarPlanSemana, regenerarPlanTotal,
  getActividades, getDiarioBiometrico, getEjercicios, getDashboard,
  type PlanSemana, type SesionPlan, type ActividadGarmin, type EntradaBiometrica, type DashboardData,
  type GrupoFuerza,
} from "../api";
import { ModalRegistroFuerza } from "../components/ModalRegistroFuerza";
import { HTML5Backend } from "react-dnd-html5-backend";
import {
  Sparkles,
  Calendar,
  Activity,
  Dumbbell,
  Moon,
  Zap,
  BarChart3,
  TrendingUp,
  Target,
  Clock,
  X,
  GripVertical,
  ChevronDown,
  CheckCircle2,
  Circle,
  Plus,
  Trash2,
  ArrowUp,
  ArrowDown,
  Minus,
  StickyNote,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  RotateCcw,
  Pencil,
  Save,
  AlertTriangle,
} from "lucide-react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

// ── Types ──────────────────────────────────────────────────────────────────────

interface Session {
  id: string;
  activity: string;
  type: "running" | "strength";
  duration: string;
  zone?: string;
  notes?: string;
  completed: boolean;
  autoCompleted?: boolean; // detectado automáticamente por Garmin
  notDone?: boolean;       // día pasado sin actividad coincidente
  kmDone?: number;
  kmPlanned?: number;
  garminKm?: number;       // km reales de Garmin si hay match
}

interface DayPlan {
  dayKey: string;
  date: string;
  isToday?: boolean;
  sessions: Session[];
}

interface ExerciseLog {
  id: string;
  name: string;
  sets: number;
  reps: string;
  weight: number | null;
  prevWeight: number | null;
}

// ── UI helpers ─────────────────────────────────────────────────────────────────

// Strength exercises per session type
const STRENGTH_PLANS: Record<string, ExerciseLog[]> = {
  "Core Activación": [
    { id: "e1", name: "Plancha Frontal", sets: 3, reps: "30s", weight: null, prevWeight: null },
    { id: "e2", name: "Dead Bug", sets: 3, reps: "12", weight: null, prevWeight: null },
    { id: "e3", name: "Pallof Press", sets: 3, reps: "12", weight: 10, prevWeight: 9 },
  ],
  "Fuerza Tren Superior": [
    { id: "e1", name: "Press Banca", sets: 3, reps: "8", weight: 15, prevWeight: 14 },
    { id: "e2", name: "Dominadas", sets: 3, reps: "8", weight: null, prevWeight: null },
    { id: "e3", name: "Remo Mancuerna", sets: 3, reps: "10", weight: 14, prevWeight: 12 },
    { id: "e4", name: "Face Pull", sets: 3, reps: "15", weight: 12, prevWeight: 11 },
  ],
  "Fuerza Piernas": [
    { id: "e1", name: "Sentadilla", sets: 3, reps: "10", weight: 50, prevWeight: 47.5 },
    { id: "e2", name: "Peso Muerto Rumano", sets: 3, reps: "10", weight: 40, prevWeight: 40 },
    { id: "e3", name: "Zancada Búlgara", sets: 3, reps: "12", weight: 14, prevWeight: 12 },
    { id: "e4", name: "Hip Thrust", sets: 3, reps: "12", weight: 60, prevWeight: 55 },
  ],
  "Activación Previa": [
    { id: "e1", name: "Puente Glúteo", sets: 3, reps: "15", weight: null, prevWeight: null },
    { id: "e2", name: "Clamshell", sets: 3, reps: "15", weight: null, prevWeight: null },
  ],
};

// ── API helpers ───────────────────────────────────────────────────────────────

const DAY_KEYS = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"];
const MONTH_NAMES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

function getWeekStart(offset = 0): string {
  const d = new Date();
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day; // Sunday → go back 6, otherwise go to Monday
  d.setDate(d.getDate() + diff + offset * 7);
  return d.toISOString().slice(0, 10);
}

function apiPlanToDayPlans(plan: PlanSemana): DayPlan[] {
  const days: DayPlan[] = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(plan.semana_inicio);
    d.setDate(d.getDate() + i);
    const todayStr = new Date().toISOString().slice(0, 10);
    const dateStr = d.toISOString().slice(0, 10);
    return {
      dayKey: DAY_KEYS[i],
      date: `${d.getDate()} ${MONTH_NAMES[d.getMonth()]}`,
      isToday: dateStr === todayStr,
      sessions: [],
    };
  });

  const TIPO_MAP: Record<string, "running" | "strength"> = {
    Carrera: "running", carrera: "running", running: "running",
    Fuerza: "strength", fuerza: "strength", strength: "strength",
  };

  const RUNNING_TIPOS = new Set([
    "running", "trail_running", "correr", "carrera", "trail", "run",
    "treadmill_running", "indoor_running",
  ]);
  const STRENGTH_TIPOS = new Set([
    "strength_training", "fitness_equipment", "gym", "fuerza", "strength",
    "indoor_cycling", "yoga", "pilates",
  ]);

  // Agrupar actividades Garmin por fecha
  const actByDate = new Map<string, typeof plan.actividades_garmin>();
  (plan.actividades_garmin ?? []).forEach((a) => {
    const arr = actByDate.get(a.fecha) ?? [];
    arr.push(a);
    actByDate.set(a.fecha, arr);
  });

  const todayStr = new Date().toISOString().slice(0, 10);

  plan.sesiones.forEach((s) => {
    const mappedType = TIPO_MAP[s.tipo];
    if (!mappedType) return; // Ignorar Descanso y tipos desconocidos — día vacío = descanso
    const dayIdx = Math.min(
      6,
      Math.max(0, Math.round((new Date(s.fecha).getTime() - new Date(plan.semana_inicio).getTime()) / 86400000))
    );

    const isPast = s.fecha < todayStr;
    const actsDia = actByDate.get(s.fecha) ?? [];
    let autoCompleted = false;
    let notDone = false;
    let garminKm: number | undefined;

    if (isPast && !Boolean(s.completado)) {
      if (mappedType === "running") {
        const runActs = actsDia.filter((a) =>
          RUNNING_TIPOS.has((a.tipo_deporte ?? "").toLowerCase())
        );
        if (runActs.length > 0) {
          autoCompleted = true;
          // Buscar la actividad con km más cercanos al plan
          const bestMatch = runActs.reduce((best, a) => {
            if (!best) return a;
            const kmA = (a.distancia_m ?? 0) / 1000;
            const kmB = (best.distancia_m ?? 0) / 1000;
            const planned = s.km_planificados ?? 0;
            return Math.abs(kmA - planned) < Math.abs(kmB - planned) ? a : best;
          }, runActs[0]);
          garminKm = bestMatch ? Math.round((bestMatch.distancia_m ?? 0) / 100) / 10 : undefined;
        } else if (actsDia.length === 0) {
          notDone = true; // día sin ninguna actividad
        } else {
          notDone = true; // actividades pero ninguna de carrera
        }
      } else if (mappedType === "strength") {
        const strActs = actsDia.filter((a) =>
          STRENGTH_TIPOS.has((a.tipo_deporte ?? "").toLowerCase())
        );
        if (strActs.length > 0) {
          autoCompleted = true;
        } else {
          notDone = true;
        }
      }
    }

    days[dayIdx].sessions.push({
      id: String(s.id),
      activity: s.sesion,
      type: mappedType,
      duration: s.duracion_min ? `${s.duracion_min} min` : "",
      zone: s.intensidad ?? undefined,
      notes: s.detalles ?? undefined,
      completed: Boolean(s.completado),
      autoCompleted,
      notDone,
      kmDone: s.km_realizados ?? undefined,
      kmPlanned: s.km_planificados ?? undefined,
      garminKm,
    });
  });

  return days;
}

// ── Colors ─────────────────────────────────────────────────────────────────────

const TYPE_COLORS: Record<string, { borderColor: string; textColor: string; badgeClass: string; bgColor: string }> = {
  running: { borderColor: "#22D3EE", textColor: "text-cyan-400", badgeClass: "bg-cyan-400/15 text-cyan-300 border-cyan-500/30", bgColor: "rgba(0,212,255,0.06)" },
  strength: { borderColor: "#C084FC", textColor: "text-purple-400", badgeClass: "bg-purple-400/15 text-purple-300 border-purple-500/30", bgColor: "rgba(168,85,247,0.06)" },
};

// ── Drag Types ─────────────────────────────────────────────────────────────────

const DRAG_DAY = "DRAG_DAY";
const DRAG_SESSION = "DRAG_SESSION";

// ── Session Card (within a day column) ────────────────────────────────────────

interface SessionCardProps {
  session: Session;
  dayIdx: number;
  sessionIdx: number;
  isSelected: boolean;
  onSelect: (dayIdx: number, sessionIdx: number) => void;
  onToggleComplete: (dayIdx: number, sessionIdx: number) => void;
  onMoveSession: (fromDayIdx: number, fromSessionIdx: number, toDayIdx: number, toSessionIdx: number) => void;
}

function SessionCard({ session, dayIdx, sessionIdx, isSelected, onSelect, onToggleComplete, onMoveSession }: SessionCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const gripRef = useRef<HTMLDivElement>(null);
  const colors = TYPE_COLORS[session.type] ?? TYPE_COLORS.running;

  const isDone = session.completed || session.autoCompleted;

  const [{ isDragging }, drag, dragPreview] = useDrag({
    type: DRAG_SESSION,
    item: { dayIdx, sessionIdx },
    collect: (m) => ({ isDragging: m.isDragging() }),
  });

  const [{ isOver }, drop] = useDrop({
    accept: DRAG_SESSION,
    hover: (item: { dayIdx: number; sessionIdx: number }) => {
      if (item.dayIdx === dayIdx && item.sessionIdx === sessionIdx) return;
      onMoveSession(item.dayIdx, item.sessionIdx, dayIdx, sessionIdx);
      item.dayIdx = dayIdx;
      item.sessionIdx = sessionIdx;
    },
    collect: (m) => ({ isOver: m.isOver() }),
  });

  dragPreview(drop(cardRef));
  drag(gripRef);

  // Estilos según estado
  const cardBg = session.notDone
    ? "rgba(14,17,23,0.5)"
    : isDone
    ? "rgba(14,17,23,0.6)"
    : isSelected
    ? colors.bgColor
    : "rgba(22,27,34,0.95)";

  const borderColor = session.notDone
    ? "rgba(48,54,61,0.3)"
    : isDone
    ? "rgba(48,54,61,0.4)"
    : isSelected
    ? colors.borderColor
    : "rgba(255,255,255,0.08)";

  const leftBorderColor = session.notDone
    ? "rgba(48,54,61,0.3)"
    : isDone
    ? "rgba(34,197,94,0.5)"
    : colors.borderColor;

  const titleClass = session.notDone
    ? "text-[#4B5563] line-through"
    : isDone
    ? "text-[#8B949E] line-through"
    : colors.textColor;

  return (
    <div
      ref={cardRef}
      className="rounded-lg select-none group relative cursor-pointer transition-all"
      style={{
        background: cardBg,
        border: `1px solid ${borderColor}`,
        borderLeftWidth: "3px",
        borderLeftColor: leftBorderColor,
        opacity: isDragging ? 0.3 : session.notDone ? 0.55 : isDone ? 0.75 : 1,
        boxShadow: isOver
          ? `0 0 0 2px ${colors.borderColor}80`
          : isSelected && !session.notDone && !isDone
          ? `0 4px 12px ${colors.borderColor}30, 0 0 0 1px ${colors.borderColor}40`
          : "0 2px 4px rgba(0,0,0,0.1)",
      }}
      onClick={() => onSelect(dayIdx, sessionIdx)}
    >
      {/* Grip */}
      <div
        ref={gripRef}
        onClick={(e) => e.stopPropagation()}
        className="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-60 transition-opacity cursor-grab z-10"
      >
        <GripVertical className="h-3 w-3 text-[#8B949E]" />
      </div>

      <div className="p-3">
        <div className="flex items-start gap-2 mb-1.5">
          {/* Estado visual */}
          <button
            onClick={(e) => { e.stopPropagation(); onToggleComplete(dayIdx, sessionIdx); }}
            className="shrink-0 mt-0.5 transition-colors"
            title={session.notDone ? "No realizado" : isDone ? "Realizado" : "Marcar completado"}
          >
            {session.notDone ? (
              <div className="h-4 w-4 rounded-full border-2 border-[#4B5563] flex items-center justify-center">
                <div className="h-1.5 w-1.5 rounded-full bg-[#4B5563]" />
              </div>
            ) : isDone ? (
              <CheckCircle2 className="h-4 w-4 text-green-400" />
            ) : (
              <Circle className="h-4 w-4 text-[#8B949E] hover:text-white" />
            )}
          </button>
          <div className="flex-1 min-w-0">
            <p className={`text-xs font-bold truncate ${titleClass}`}>
              {session.activity}
            </p>
            <p className="text-[10px] text-[#8B949E] mt-0.5">{session.duration}</p>
          </div>
        </div>

        {/* Running km */}
        {session.type === "running" && (session.kmPlanned !== undefined || session.garminKm !== undefined) && (
          <div
            className="mt-1.5 rounded-lg px-2 py-1 flex items-center justify-between"
            style={{
              background: session.notDone ? "rgba(48,54,61,0.2)" : "rgba(0,212,255,0.08)",
              border: `1px solid ${session.notDone ? "rgba(48,54,61,0.3)" : "rgba(0,212,255,0.2)"}`,
            }}
          >
            <span className="text-[10px] text-[#8B949E]">km</span>
            <span className={`text-[10px] font-bold ${session.notDone ? "text-[#4B5563]" : "text-cyan-400"}`}>
              {session.notDone
                ? `— / ${session.kmPlanned ?? "?"}`
                : isDone && session.garminKm !== undefined
                ? `${session.garminKm} / ${session.kmPlanned ?? "?"}`
                : isDone && session.kmDone !== undefined
                ? `${session.kmDone} / ${session.kmPlanned ?? "?"}`
                : `${session.kmPlanned} km`}
            </span>
          </div>
        )}

        {/* Zona/intensidad badge — solo si no hay km y no está hecho */}
        {session.zone && !isDone && !session.notDone && session.kmPlanned === undefined && (
          <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${colors.badgeClass}`}>
            {session.zone}
          </span>
        )}

        {/* Etiqueta "No realizado" para días pasados sin actividad */}
        {session.notDone && (
          <span className="text-[9px] text-[#4B5563] font-medium">No realizado</span>
        )}
        {/* Etiqueta "Garmin ✓" para auto-detectados */}
        {session.autoCompleted && !session.completed && (
          <span className="text-[9px] text-green-500/70 font-medium">Garmin ✓</span>
        )}
      </div>
    </div>
  );
}

// ── Day Column (draggable column with multiple sessions) ───────────────────────

interface DayColumnProps {
  day: DayPlan;
  dayIdx: number;
  selectedKey: string | null;
  onSelectSession: (dayIdx: number, sessionIdx: number) => void;
  onToggleComplete: (dayIdx: number, sessionIdx: number) => void;
  onMoveSession: (fromDayIdx: number, fromSessionIdx: number, toDayIdx: number, toSessionIdx: number) => void;
  onMoveDay: (from: number, to: number) => void;
}

function DayColumn({ day, dayIdx, selectedKey, onSelectSession, onToggleComplete, onMoveSession, onMoveDay }: DayColumnProps) {
  const colRef = useRef<HTMLDivElement>(null);
  const gripRef = useRef<HTMLDivElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  const [{ isDraggingCol }, dragDay, dragDayPreview] = useDrag({
    type: DRAG_DAY,
    item: { dayIdx },
    collect: (m) => ({ isDraggingCol: m.isDragging() }),
  });

  const [{ isOverCol }, dropDay] = useDrop({
    accept: DRAG_DAY,
    hover: (item: { dayIdx: number }) => {
      if (item.dayIdx === dayIdx) return;
      onMoveDay(item.dayIdx, dayIdx);
      item.dayIdx = dayIdx;
    },
    collect: (m) => ({ isOverCol: m.isOver() }),
  });

  // Drop zone for sessions at the end of the day
  const [{ isOverDropZone }, dropSessionZone] = useDrop({
    accept: DRAG_SESSION,
    drop: (item: { dayIdx: number; sessionIdx: number }) => {
      if (item.dayIdx === dayIdx && item.sessionIdx === day.sessions.length - 1) return;
      onMoveSession(item.dayIdx, item.sessionIdx, dayIdx, day.sessions.length);
    },
    collect: (m) => ({ isOverDropZone: m.isOver() }),
  });

  dragDayPreview(dropDay(colRef));
  dragDay(gripRef);
  dropSessionZone(dropZoneRef);

  const totalPlanned = day.sessions.filter(s => s.type === "running" && s.kmPlanned).reduce((a, s) => a + (s.kmPlanned ?? 0), 0);
  const totalDone = day.sessions.filter(s => s.type === "running" && s.completed && s.kmDone).reduce((a, s) => a + (s.kmDone ?? 0), 0);
  const completedCount = day.sessions.filter(s => s.completed).length;

  return (
    <div
      ref={colRef}
      className="rounded-xl flex flex-col gap-2"
      style={{
        opacity: isDraggingCol ? 0.3 : 1,
        transition: "opacity 0.15s, box-shadow 0.15s",
        boxShadow: isOverCol ? "0 0 0 2px rgba(201,255,0,0.5)" : "none",
      }}
    >
      {/* Day header - Pill-style */}
      <div
        className="rounded-full px-4 py-3 flex items-center justify-between group relative"
        style={{
          background: day.isToday
            ? "linear-gradient(135deg, rgba(0,212,255,0.2), rgba(99,102,241,0.15))"
            : "linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04))",
          border: day.isToday
            ? "2px solid rgba(0,212,255,0.5)"
            : "2px solid rgba(255,255,255,0.12)",
          boxShadow: day.isToday
            ? "0 0 20px rgba(0,212,255,0.2), inset 0 1px 0 rgba(255,255,255,0.1)"
            : "inset 0 1px 0 rgba(255,255,255,0.05)",
        }}
      >
        <div className="flex items-center gap-2 flex-1">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center font-black text-xs"
            style={{
              background: day.isToday
                ? "rgba(0,212,255,0.25)"
                : "rgba(255,255,255,0.1)",
              color: day.isToday ? "#00D4FF" : "#8B949E",
              border: day.isToday ? "1px solid rgba(0,212,255,0.4)" : "1px solid rgba(255,255,255,0.15)"
            }}
          >
            {day.dayKey.substring(0, 1)}
          </div>
          <div className="flex-1">
            <p className="text-xs font-black text-white leading-none">{day.dayKey}</p>
            <p className="text-[10px] text-[#8B949E] mt-0.5">{day.date}</p>
          </div>
        </div>
        {day.isToday && (
          <div className="mr-2">
            <span className="text-[9px] px-2 py-0.5 rounded-full font-bold bg-cyan-400/20 text-cyan-400 border border-cyan-400/30">
              HOY
            </span>
          </div>
        )}
        {completedCount > 0 && !day.isToday && (
          <div className="mr-2">
            <span className="text-[9px] px-2 py-0.5 rounded-full font-bold bg-green-400/15 text-green-400 border border-green-400/25">
              {completedCount}/{day.sessions.length} ✓
            </span>
          </div>
        )}
        <div
          ref={gripRef}
          onClick={(e) => e.stopPropagation()}
          className="opacity-0 group-hover:opacity-70 cursor-grab transition-opacity"
          title="Mover día"
        >
          <GripVertical className="h-3.5 w-3.5 text-[#8B949E]" />
        </div>
      </div>

      {/* Sessions */}
      <div className="flex flex-col gap-1.5">
        {day.sessions.map((session, sIdx) => (
          <SessionCard
            key={session.id}
            session={session}
            dayIdx={dayIdx}
            sessionIdx={sIdx}
            isSelected={selectedKey === `${dayIdx}-${sIdx}`}
            onSelect={onSelectSession}
            onToggleComplete={onToggleComplete}
            onMoveSession={onMoveSession}
          />
        ))}

        {/* Drop zone at end of day - only visible when dragging over or when day is empty */}
        {(isOverDropZone || day.sessions.length === 0) && (
          <div
            ref={dropZoneRef}
            className="rounded-lg border-2 border-dashed transition-all min-h-[40px] flex items-center justify-center"
            style={{
              borderColor: isOverDropZone ? "rgba(0,212,255,0.6)" : "rgba(255,255,255,0.08)",
              background: isOverDropZone ? "rgba(0,212,255,0.1)" : "transparent",
            }}
          >
            {isOverDropZone ? (
              <span className="text-[10px] text-cyan-400">Soltar aquí</span>
            ) : (
              <span className="text-[10px] text-[#8B949E]">Sin sesiones</span>
            )}
          </div>
        )}
        {/* Hidden drop zone when not visible */}
        {!isOverDropZone && day.sessions.length > 0 && (
          <div ref={dropZoneRef} className="h-0 w-full" />
        )}
      </div>

      {/* Running KM summary if day has running */}
      {totalPlanned > 0 && (
        <div className="text-[9px] text-[#8B949E] text-center px-1">
          {totalDone > 0 ? `${totalDone}/${totalPlanned} km` : `${totalPlanned} km plan`}
        </div>
      )}
    </div>
  );
}

// ── Strength Session Logger ────────────────────────────────────────────────────

interface StrengthLoggerProps {
  session: Session;
}

function StrengthLogger({ session }: StrengthLoggerProps) {
  const initialExercises = STRENGTH_PLANS[session.activity]?.map((e) => ({ ...e })) ?? [];
  const [exercises, setExercises] = useState<ExerciseLog[]>(
    initialExercises.length > 0 ? initialExercises : [
      { id: "new-1", name: "", sets: 3, reps: "10", weight: null, prevWeight: null },
    ]
  );
  const [note, setNote] = useState("");
  const [saved, setSaved] = useState(false);

  const updateExercise = (id: string, field: keyof ExerciseLog, value: string | number | null) => {
    setExercises((prev) => prev.map((e) => e.id === id ? { ...e, [field]: value } : e));
  };

  const addExercise = () => {
    setExercises((prev) => [...prev, { id: `ex-${Date.now()}`, name: "", sets: 3, reps: "10", weight: null, prevWeight: null }]);
  };

  const removeExercise = (id: string) => {
    setExercises((prev) => prev.filter((e) => e.id !== id));
  };

  const getProgression = (current: number | null, prev: number | null): "up" | "down" | "equal" | "new" => {
    if (prev === null) return "new";
    if (current === null) return "new";
    if (current > prev) return "up";
    if (current < prev) return "down";
    return "equal";
  };

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{
        background: "rgba(14,17,23,0.97)",
        border: "1px solid rgba(168,85,247,0.3)",
        boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
      }}
    >
      {/* Header */}
      <div className="px-5 py-4 flex items-center gap-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div className="w-1 h-8 rounded-full" style={{ background: "#A855F7", boxShadow: "0 0 8px rgba(168,85,247,0.6)" }} />
        <div>
          <p className="text-sm font-bold text-white">{session.activity}</p>
          <p className="text-xs text-[#8B949E]">{session.duration} · Logger de Fuerza</p>
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* Nota de entrenamiento */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <StickyNote className="h-3.5 w-3.5 text-purple-400" />
            <p className="text-xs font-bold text-[#8B949E] uppercase tracking-widest">Nota de Entrenamiento</p>
          </div>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Escribe aquí sensaciones, ajustes, RPE general de la sesión..."
            rows={3}
            className="w-full rounded-xl px-3 py-2.5 text-sm text-white resize-none focus:outline-none"
            style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(168,85,247,0.25)",
            }}
          />
        </div>

        {/* Exercise Logger */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Dumbbell className="h-3.5 w-3.5 text-purple-400" />
              <p className="text-xs font-bold text-[#8B949E] uppercase tracking-widest">Logger de Ejercicios</p>
            </div>
            <button
              onClick={addExercise}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all hover:opacity-90"
              style={{ background: "rgba(168,85,247,0.15)", border: "1px solid rgba(168,85,247,0.35)", color: "#C084FC" }}
            >
              <Plus className="h-3 w-3" /> Ejercicio
            </button>
          </div>

          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid rgba(168,85,247,0.2)" }}>
            {/* Table header */}
            <div
              className="grid gap-2 px-3 py-2"
              style={{ background: "rgba(168,85,247,0.08)", gridTemplateColumns: "1fr 70px 70px 80px 60px 32px" }}
            >
              {["Ejercicio", "Series", "Reps", "Peso (kg)", "Progres.", ""].map((h) => (
                <p key={h} className="text-[10px] font-bold text-[#8B949E] uppercase tracking-wide">{h}</p>
              ))}
            </div>

            {/* Rows */}
            {exercises.map((ex) => {
              const prog = getProgression(ex.weight, ex.prevWeight);
              return (
                <div
                  key={ex.id}
                  className="grid gap-2 px-3 py-2 items-center border-t"
                  style={{ gridTemplateColumns: "1fr 70px 70px 80px 60px 32px", borderColor: "rgba(255,255,255,0.05)" }}
                >
                  {/* Name */}
                  <input
                    value={ex.name}
                    onChange={(e) => updateExercise(ex.id, "name", e.target.value)}
                    placeholder="Ej: Sentadilla"
                    className="text-xs text-white bg-transparent focus:outline-none placeholder-[#8B949E]"
                  />
                  {/* Sets */}
                  <input
                    type="number"
                    min={1}
                    value={ex.sets}
                    onChange={(e) => updateExercise(ex.id, "sets", parseInt(e.target.value) || 1)}
                    className="text-xs text-white bg-transparent focus:outline-none w-full"
                    style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6, padding: "2px 6px" }}
                  />
                  {/* Reps */}
                  <input
                    value={ex.reps}
                    onChange={(e) => updateExercise(ex.id, "reps", e.target.value)}
                    placeholder="10"
                    className="text-xs text-white bg-transparent focus:outline-none w-full"
                    style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6, padding: "2px 6px" }}
                  />
                  {/* Weight */}
                  <input
                    type="number"
                    min={0}
                    step={0.5}
                    value={ex.weight ?? ""}
                    onChange={(e) => updateExercise(ex.id, "weight", e.target.value === "" ? null : parseFloat(e.target.value))}
                    placeholder="—"
                    className="text-xs text-white bg-transparent focus:outline-none w-full"
                    style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6, padding: "2px 6px" }}
                  />
                  {/* Progression */}
                  <div className="flex flex-col items-center gap-0.5">
                    {prog === "up" && (
                      <div className="flex items-center gap-1">
                        <ArrowUp className="h-3.5 w-3.5 text-green-400" />
                        <span className="text-[9px] text-green-400">+{((ex.weight ?? 0) - (ex.prevWeight ?? 0)).toFixed(1)}</span>
                      </div>
                    )}
                    {prog === "down" && (
                      <div className="flex items-center gap-1">
                        <ArrowDown className="h-3.5 w-3.5 text-red-400" />
                        <span className="text-[9px] text-red-400">{((ex.weight ?? 0) - (ex.prevWeight ?? 0)).toFixed(1)}</span>
                      </div>
                    )}
                    {prog === "equal" && <Minus className="h-3.5 w-3.5 text-[#8B949E]" />}
                    {prog === "new" && <span className="text-[9px] text-cyan-400 font-bold">NEW</span>}
                    {ex.prevWeight !== null && (
                      <span className="text-[8px] text-[#8B949E]">prev: {ex.prevWeight}kg</span>
                    )}
                  </div>
                  {/* Delete */}
                  <button
                    onClick={() => removeExercise(ex.id)}
                    className="flex items-center justify-center h-6 w-6 rounded hover:bg-red-500/20 transition-colors"
                  >
                    <Trash2 className="h-3 w-3 text-[#8B949E] hover:text-red-400 transition-colors" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Save button */}
        <button
          onClick={() => setSaved(true)}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold transition-all"
          style={{
            background: saved ? "rgba(34,197,94,0.15)" : "linear-gradient(135deg, #A855F7, #6366F1)",
            color: saved ? "#22C55E" : "#fff",
            border: saved ? "1px solid rgba(34,197,94,0.4)" : "none",
            boxShadow: saved ? "none" : "0 0 20px rgba(168,85,247,0.4)",
          }}
        >
          {saved ? "✓ Sesión guardada" : "Guardar sesión de fuerza"}
        </button>
      </div>
    </div>
  );
}

// ── Running Detail Panel ───────────────────────────────────────────────────────

function RunningDetail({ session, onClose }: { session: Session; onClose: () => void }) {
  return (
    <div className="space-y-3">
      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-xl p-3" style={{ background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.2)" }}>
          <p className="text-[10px] text-[#8B949E] mb-1 uppercase font-bold">Distancia / Duración</p>
          <p className="text-sm font-bold text-white">{session.duration}</p>
        </div>
        <div className="rounded-xl p-3" style={{ background: "rgba(168,85,247,0.08)", border: "1px solid rgba(168,85,247,0.2)" }}>
          <p className="text-[10px] text-[#8B949E] mb-1 uppercase font-bold">Zona</p>
          <p className="text-sm font-bold text-white">{session.zone ?? "—"}</p>
        </div>
        {session.completed && session.kmDone !== undefined && session.kmPlanned !== undefined ? (
          <div className="rounded-xl p-3 col-span-2" style={{ background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.3)" }}>
            <p className="text-[10px] text-[#8B949E] mb-1 uppercase font-bold">✓ km Realizados / Planeados</p>
            <div className="flex items-baseline gap-1">
              <p className="text-xl font-black text-green-400">{session.kmDone}</p>
              <p className="text-sm text-[#8B949E]">/ {session.kmPlanned} km</p>
            </div>
            <div className="mt-1 h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(48,54,61,0.6)" }}>
              <div className="h-full rounded-full" style={{ width: `${Math.min(100, (session.kmDone / session.kmPlanned) * 100)}%`, background: "linear-gradient(90deg, #22C55E, #86EFAC)" }} />
            </div>
          </div>
        ) : (
          <div className="rounded-xl p-3 col-span-2" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <p className="text-[10px] text-[#8B949E] mb-1 uppercase font-bold flex items-center gap-1">
              <Sparkles className="h-3 w-3 text-cyan-400" /> Instrucciones
            </p>
            <p className="text-sm text-[#C8D1D9]">{session.notes}</p>
          </div>
        )}
      </div>

      <div className="rounded-xl p-4" style={{ background: "rgba(0,212,255,0.05)", border: "1px solid rgba(0,212,255,0.15)" }}>
        <p className="text-sm font-semibold text-white mb-2">Objetivos de la sesión</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          {[
            `Mantener ritmo constante en ${session.zone ?? "Z2"}`,
            "Cadencia objetivo: 175-180 spm",
            "Sensación: Conversacional / Controlado",
          ].map((obj, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="text-cyan-400 shrink-0">✓</span>
              <p className="text-xs text-white">{obj}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Day Detail Panel ───────────────────────────────────────────────────────────

function detectarGrupoFuerza(activity: string): GrupoFuerza | null {
  const s = activity.toLowerCase();
  if (s.includes("push")) return "Push";
  if (s.includes("pull")) return "Pull";
  if (s.includes("pierna")) return "Pierna";
  return null;
}

function DayDetailPanel({ day, session, onClose, onEdit }: { day: DayPlan; session: Session; onClose: () => void; onEdit?: () => void }) {
  const { userId } = useUser();
  const [showModalFuerza, setShowModalFuerza] = useState(false);
  const [fuerzaGuardada, setFuerzaGuardada] = useState(false);
  const colors = TYPE_COLORS[session.type] ?? TYPE_COLORS.running;
  const typeLabel = session.type === "running" ? "Carrera" : "Fuerza";
  const typeColor = session.type === "running" ? "#00D4FF" : "#A855F7";
  const grupoFuerza = session.type === "strength" ? detectarGrupoFuerza(session.activity) : null;

  return (
    <div
      className="rounded-2xl overflow-hidden mt-4"
      style={{
        background: "rgba(14,17,23,0.97)",
        border: "1px solid rgba(201,255,0,0.2)",
        boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div className="flex items-center gap-3">
          <div className="w-1 h-10 rounded-full" style={{ background: typeColor, boxShadow: `0 0 8px ${typeColor}80` }} />
          <div>
            <div className="flex items-center gap-2">
              <p className="text-base font-bold text-white">{session.activity}</p>
              <Badge className={colors.badgeClass}>{typeLabel}</Badge>
              {session.completed && <Badge className="bg-green-500/20 text-green-300 border-green-500/30">✓ Completada</Badge>}
            </div>
            <p className="text-xs text-[#8B949E] mt-0.5">{day.dayKey} · {day.date}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {onEdit && (
            <button
              onClick={onEdit}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={{ background: "rgba(201,255,0,0.12)", border: "1px solid rgba(201,255,0,0.3)", color: "#C9FF00" }}
            >
              <Pencil className="h-3.5 w-3.5" /> Editar
            </button>
          )}
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
            <X className="h-4 w-4 text-[#8B949E]" />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="p-5">
        {session.type === "running" && <RunningDetail session={session} onClose={onClose} />}
        {session.type === "strength" && (
          <div className="space-y-4">
            {/* Botón registrar desde biblioteca */}
            {grupoFuerza && (
              <button
                onClick={() => setShowModalFuerza(true)}
                disabled={fuerzaGuardada}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold transition-all"
                style={{
                  background: fuerzaGuardada
                    ? "rgba(34,197,94,0.12)"
                    : "rgba(168,85,247,0.15)",
                  border: fuerzaGuardada
                    ? "1px solid rgba(34,197,94,0.35)"
                    : "1px solid rgba(168,85,247,0.4)",
                  color: fuerzaGuardada ? "#22C55E" : "#C084FC",
                }}
              >
                {fuerzaGuardada ? "✓ Sesión registrada en biblioteca" : `Registrar ejercicios ${grupoFuerza} en biblioteca`}
              </button>
            )}
            <StrengthLogger session={session} />
          </div>
        )}
      </div>

      {/* Modal registro fuerza */}
      {showModalFuerza && userId !== null && grupoFuerza && (
        <ModalRegistroFuerza
          usuarioId={userId}
          grupo={grupoFuerza}
          onClose={() => setShowModalFuerza(false)}
          onGuardado={() => setFuerzaGuardada(true)}
        />
      )}
    </div>
  );
}

// ── GenerarPlan ────────────────────────────────────────────────────────────────

function buildEmptyWeek(): DayPlan[] {
  const semana = getWeekStart(0);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(semana);
    d.setDate(d.getDate() + i);
    return {
      dayKey: DAY_KEYS[i],
      date: `${d.getDate()} ${MONTH_NAMES[d.getMonth()]}`,
      isToday: d.toISOString().slice(0, 10) === new Date().toISOString().slice(0, 10),
      sessions: [],
    };
  });
}

// ── Session Edit Modal ─────────────────────────────────────────────────────────

interface SessionEditModalProps {
  session: Session | null;
  dayIdx: number | null;
  sessionIdx: number | null;
  dayDate: string;
  onClose: () => void;
  onSave: (dayIdx: number, sessionIdx: number, updated: Partial<Session>) => void;
  onDelete: (dayIdx: number, sessionIdx: number) => void;
}

function SessionEditModal({ session, dayIdx, sessionIdx, dayDate, onClose, onSave, onDelete }: SessionEditModalProps) {
  const [form, setForm] = useState({
    activity: session?.activity ?? "",
    type: (session?.type ?? "running") as "running" | "strength",
    duration: session?.duration ?? "",
    zone: session?.zone ?? "",
    notes: session?.notes ?? "",
    kmPlanned: session?.kmPlanned?.toString() ?? "",
  });
  const [saving, setSaving] = useState(false);

  if (!session || dayIdx === null || sessionIdx === null) return null;

  const handleSave = async () => {
    setSaving(true);
    const id = parseInt(session.id);
    const kmParsed = form.kmPlanned ? parseFloat(form.kmPlanned) : undefined;
    const durParsed = form.duration ? parseInt(form.duration) : undefined;
    const updated: Partial<Session> = {
      activity: form.activity,
      type: form.type,
      duration: form.duration,
      zone: form.zone || undefined,
      notes: form.notes || undefined,
      kmPlanned: kmParsed,
    };
    if (id > 0) {
      await actualizarSesionCompleta(id, {
        sesion: form.activity,
        tipo: form.type === "running" ? "Carrera" : "Fuerza",
        detalles: form.notes || undefined,
        intensidad: form.zone || undefined,
        km_planificados: kmParsed,
        duracion_min: durParsed,
      }).catch(() => null);
    }
    onSave(dayIdx, sessionIdx, updated);
    setSaving(false);
    onClose();
  };

  const handleDelete = async () => {
    const id = parseInt(session.id);
    if (id > 0) await borrarSesion(id).catch(() => null);
    onDelete(dayIdx, sessionIdx);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.7)" }} onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-2xl overflow-hidden"
        style={{ background: "#161B22", border: "1px solid rgba(201,255,0,0.3)", boxShadow: "0 20px 60px rgba(0,0,0,0.6)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
          <p className="text-sm font-bold text-white flex items-center gap-2">
            <Pencil className="h-4 w-4 text-[#C9FF00]" /> Editar sesión — {dayDate}
          </p>
          <button onClick={onClose} className="p-1 rounded hover:bg-white/10"><X className="h-4 w-4 text-[#8B949E]" /></button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="text-[10px] text-[#8B949E] uppercase font-bold tracking-wider">Nombre de la sesión</label>
            <input
              value={form.activity}
              onChange={(e) => setForm({ ...form, activity: e.target.value })}
              className="mt-1 w-full rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)" }}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-[#8B949E] uppercase font-bold tracking-wider">Tipo</label>
              <select
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value as "running" | "strength" })}
                className="mt-1 w-full rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)" }}
              >
                <option value="running">Carrera</option>
                <option value="strength">Fuerza</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] text-[#8B949E] uppercase font-bold tracking-wider">Duración (min)</label>
              <input
                type="number"
                value={form.duration.replace(" min", "")}
                onChange={(e) => setForm({ ...form, duration: e.target.value ? `${e.target.value} min` : "" })}
                className="mt-1 w-full rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)" }}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-[#8B949E] uppercase font-bold tracking-wider">Km planificados</label>
              <input
                type="number" step="0.5"
                value={form.kmPlanned}
                onChange={(e) => setForm({ ...form, kmPlanned: e.target.value })}
                placeholder="—"
                className="mt-1 w-full rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)" }}
              />
            </div>
            <div>
              <label className="text-[10px] text-[#8B949E] uppercase font-bold tracking-wider">Zona / Intensidad</label>
              <input
                value={form.zone}
                onChange={(e) => setForm({ ...form, zone: e.target.value })}
                placeholder="Z2, Alta, Moderada…"
                className="mt-1 w-full rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)" }}
              />
            </div>
          </div>
          <div>
            <label className="text-[10px] text-[#8B949E] uppercase font-bold tracking-wider">Instrucciones / Detalles</label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={3}
              className="mt-1 w-full rounded-lg px-3 py-2 text-sm text-white resize-none focus:outline-none"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)" }}
            />
          </div>
          <div className="flex items-center gap-3 pt-1">
            <button
              onClick={handleDelete}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold transition-all"
              style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.3)", color: "#F87171" }}
            >
              <Trash2 className="h-3.5 w-3.5" /> Eliminar
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold transition-all"
              style={{ background: "linear-gradient(135deg, #C9FF00, #86EFAC)", color: "#0E1117" }}
            >
              <Save className="h-4 w-4" /> {saving ? "Guardando…" : "Guardar cambios"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Add Session Modal ──────────────────────────────────────────────────────────

interface AddSessionModalProps {
  dayIdx: number | null;
  dayDate: string;
  weekStart: string;
  userId: number;
  onClose: () => void;
  onAdded: (dayIdx: number, session: Session) => void;
}

function AddSessionModal({ dayIdx, dayDate, weekStart, userId, onClose, onAdded }: AddSessionModalProps) {
  const [form, setForm] = useState({
    activity: "",
    type: "running" as "running" | "strength",
    duration: "",
    zone: "",
    notes: "",
    kmPlanned: "",
  });
  const [saving, setSaving] = useState(false);

  if (dayIdx === null) return null;

  const handleSave = async () => {
    if (!form.activity.trim()) return;
    setSaving(true);

    const weekStartDate = new Date(weekStart);
    const fecha = new Date(weekStartDate);
    fecha.setDate(fecha.getDate() + dayIdx);
    const fechaStr = `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, "0")}-${String(fecha.getDate()).padStart(2, "0")}`;

    const kmParsed = form.kmPlanned ? parseFloat(form.kmPlanned) : undefined;
    const durParsed = form.duration ? parseInt(form.duration) : undefined;

    const tipoMap = { running: "Carrera", strength: "Fuerza" };
    const result = await crearSesion({
      usuario_id: userId,
      fecha: fechaStr,
      tipo: tipoMap[form.type],
      sesion: form.activity,
      detalles: form.notes || undefined,
      duracion_min: durParsed,
      intensidad: form.zone || undefined,
      km_planificados: kmParsed,
    }).catch(() => null);

    if (result) {
      // Re-fetch to get the real ID — for now create a temp session
      const newSession: Session = {
        id: `temp-${Date.now()}`,
        activity: form.activity,
        type: form.type,
        duration: form.duration ? `${form.duration} min` : "",
        zone: form.zone || undefined,
        notes: form.notes || undefined,
        completed: false,
        kmPlanned: kmParsed,
      };
      onAdded(dayIdx, newSession);
    }
    setSaving(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.7)" }} onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-2xl overflow-hidden"
        style={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.3)", boxShadow: "0 20px 60px rgba(0,0,0,0.6)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
          <p className="text-sm font-bold text-white flex items-center gap-2">
            <Plus className="h-4 w-4 text-cyan-400" /> Añadir sesión — {dayDate}
          </p>
          <button onClick={onClose} className="p-1 rounded hover:bg-white/10"><X className="h-4 w-4 text-[#8B949E]" /></button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="text-[10px] text-[#8B949E] uppercase font-bold tracking-wider">Nombre de la sesión</label>
            <input
              value={form.activity}
              onChange={(e) => setForm({ ...form, activity: e.target.value })}
              placeholder="Ej: Rodaje Base Z2, Fuerza Pierna…"
              className="mt-1 w-full rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)" }}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-[#8B949E] uppercase font-bold tracking-wider">Tipo</label>
              <select
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value as "running" | "strength" })}
                className="mt-1 w-full rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)" }}
              >
                <option value="running">Carrera</option>
                <option value="strength">Fuerza</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] text-[#8B949E] uppercase font-bold tracking-wider">Duración (min)</label>
              <input
                type="number"
                value={form.duration}
                onChange={(e) => setForm({ ...form, duration: e.target.value })}
                className="mt-1 w-full rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)" }}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-[#8B949E] uppercase font-bold tracking-wider">Km planificados</label>
              <input type="number" step="0.5" value={form.kmPlanned} onChange={(e) => setForm({ ...form, kmPlanned: e.target.value })} placeholder="—"
                className="mt-1 w-full rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)" }} />
            </div>
            <div>
              <label className="text-[10px] text-[#8B949E] uppercase font-bold tracking-wider">Zona / Intensidad</label>
              <input value={form.zone} onChange={(e) => setForm({ ...form, zone: e.target.value })} placeholder="Z2, Alta…"
                className="mt-1 w-full rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)" }} />
            </div>
          </div>
          <div>
            <label className="text-[10px] text-[#8B949E] uppercase font-bold tracking-wider">Instrucciones</label>
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2}
              className="mt-1 w-full rounded-lg px-3 py-2 text-sm text-white resize-none focus:outline-none"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)" }} />
          </div>
          <button
            onClick={handleSave}
            disabled={saving || !form.activity.trim()}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold transition-all disabled:opacity-50"
            style={{ background: "linear-gradient(135deg, #00D4FF, #0EA5E9)", color: "#0E1117" }}
          >
            <Plus className="h-4 w-4" /> {saving ? "Añadiendo…" : "Añadir sesión"}
          </button>
        </div>
      </div>
    </div>
  );
}

function GenerarPlanInner() {
  const { userId } = useUser();
  const [days, setDays] = useState<DayPlan[]>(buildEmptyWeek);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [currentWeek, setCurrentWeek] = useState(0);
  const [planData, setPlanData] = useState<PlanSemana | null>(null);
  const weekStartRef = useRef<string>("");
  const [coachTip, setCoachTip] = useState<string>("");
  const [loadingRegen, setLoadingRegen] = useState<"semana" | "total" | null>(null);
  const [editModal, setEditModal] = useState<{ dayIdx: number; sessionIdx: number } | null>(null);
  const [addModal, setAddModal] = useState<{ dayIdx: number } | null>(null);
  const [kmEditValue, setKmEditValue] = useState<string>("");
  const [kmEditing, setKmEditing] = useState(false);
  const [regenMsg, setRegenMsg] = useState<string | null>(null);

  const loadPlan = (weekOffset: number) => {
    if (!userId) return;
    const semanaInicio = getWeekStart(weekOffset);
    weekStartRef.current = semanaInicio;
    getPlanSemana(userId, semanaInicio)
      .then((plan) => {
        setPlanData(plan);
        setDays(apiPlanToDayPlans(plan));
        setCoachTip(plan.coach_tip);
      })
      .catch(() => {
        setDays(buildEmptyWeek());
      });
  };

  useEffect(() => {
    loadPlan(currentWeek);
  }, [userId, currentWeek]);

  // Computed KPIs
  const kmPlanned = days.flatMap((d) => d.sessions).filter((s) => s.type === "running" && s.kmPlanned).reduce((a, s) => a + (s.kmPlanned ?? 0), 0);
  const kmDone = days.flatMap((d) => d.sessions).filter((s) => s.type === "running" && (s.completed || s.autoCompleted)).reduce((a, s) => {
    // Usar km reales: garminKm (auto-detect), kmDone (manual), o kmPlanned como fallback
    const km = s.garminKm ?? s.kmDone ?? s.kmPlanned ?? 0;
    return a + km;
  }, 0);
  const totalSessions = days.flatMap((d) => d.sessions).length;
  const fuerzaSessions = days.flatMap((d) => d.sessions).filter((s) => s.type === "strength").length;

  // Handlers
  const handleRegenerarSemana = async () => {
    if (!userId) return;
    setLoadingRegen("semana");
    setRegenMsg(null);
    try {
      const semanaInicio = getWeekStart(currentWeek);
      const result = await generarPlanSemana(userId, semanaInicio);
      setRegenMsg(`Semana regenerada: ${result.km_total} km · ${result.tipo_semana}`);
      loadPlan(currentWeek);
    } catch (e: any) {
      setRegenMsg(`Error: ${e.message}`);
    } finally {
      setLoadingRegen(null);
    }
  };

  const handleRegenerarTotal = async () => {
    if (!userId) return;
    setLoadingRegen("total");
    setRegenMsg(null);
    try {
      const result = await regenerarPlanTotal(userId, 4);
      setRegenMsg(`Plan total regenerado: ${result.semanas_regeneradas} semanas · base ${result.km_base_real} km/sem`);
      loadPlan(currentWeek);
    } catch (e: any) {
      setRegenMsg(`Error: ${e.message}`);
    } finally {
      setLoadingRegen(null);
    }
  };

  const handleKmEdit = async () => {
    if (!userId || !kmEditValue) return;
    const km = parseFloat(kmEditValue);
    if (isNaN(km) || km < 5) return;
    setKmEditing(false);
    setLoadingRegen("semana");
    setRegenMsg(null);
    try {
      const semanaInicio = getWeekStart(currentWeek);
      const result = await generarPlanSemana(userId, semanaInicio, km);
      setRegenMsg(`Semana recalculada a ${km} km · distribución ajustada`);
      loadPlan(currentWeek);
    } catch (e: any) {
      setRegenMsg(`Error: ${e.message}`);
    } finally {
      setLoadingRegen(null);
    }
  };

  const handleSaveEditedSession = (dayIdx: number, sessionIdx: number, updated: Partial<Session>) => {
    setDays((prev) =>
      prev.map((d, di) =>
        di !== dayIdx ? d : {
          ...d,
          sessions: d.sessions.map((s, si) =>
            si !== sessionIdx ? s : { ...s, ...updated }
          ),
        }
      )
    );
  };

  const handleDeleteSession = (dayIdx: number, sessionIdx: number) => {
    setDays((prev) =>
      prev.map((d, di) =>
        di !== dayIdx ? d : { ...d, sessions: d.sessions.filter((_, si) => si !== sessionIdx) }
      )
    );
  };

  const handleAddSession = (dayIdx: number, session: Session) => {
    setDays((prev) =>
      prev.map((d, di) =>
        di !== dayIdx ? d : { ...d, sessions: [...d.sessions, session] }
      )
    );
  };

  const moveDay = useCallback((from: number, to: number) => {
    setDays((prev) => {
      const updated = [...prev];
      const [moved] = updated.splice(from, 1);
      updated.splice(to, 0, moved);
      return updated;
    });
    setSelectedKey(null);
  }, []);

  const moveSession = useCallback((fromDayIdx: number, fromSessionIdx: number, toDayIdx: number, toSessionIdx: number) => {
    setDays((prev) => {
      const updated = [...prev];

      const sessionToMove = updated[fromDayIdx].sessions[fromSessionIdx];

      // Persistir cambio de día en el backend
      if (fromDayIdx !== toDayIdx) {
        const id = parseInt(sessionToMove.id);
        if (id > 0 && weekStartRef.current) {
          const d = new Date(weekStartRef.current + "T12:00:00");
          d.setDate(d.getDate() + toDayIdx);
          const newFecha = [
            d.getFullYear(),
            String(d.getMonth() + 1).padStart(2, "0"),
            String(d.getDate()).padStart(2, "0"),
          ].join("-");
          actualizarSesionCompleta(id, { fecha: newFecha }).catch(() => null);
        }
      }

      updated[fromDayIdx] = {
        ...updated[fromDayIdx],
        sessions: updated[fromDayIdx].sessions.filter((_, idx) => idx !== fromSessionIdx),
      };

      let targetIdx = toSessionIdx;
      if (fromDayIdx === toDayIdx && fromSessionIdx < toSessionIdx) {
        targetIdx = toSessionIdx - 1;
      }

      const targetSessions = [...updated[toDayIdx].sessions];
      targetSessions.splice(targetIdx, 0, sessionToMove);
      updated[toDayIdx] = {
        ...updated[toDayIdx],
        sessions: targetSessions,
      };

      return updated;
    });
  }, []);

  const toggleComplete = useCallback((dayIdx: number, sessionIdx: number) => {
    setDays((prev) => {
      const session = prev[dayIdx]?.sessions[sessionIdx];
      const newCompleted = !session?.completed;
      const sesionId = parseInt(session?.id ?? "0");
      if (sesionId > 0) {
        actualizarSesion(sesionId, newCompleted).catch(() => null);
      }
      return prev.map((d, dI) => {
        if (dI !== dayIdx) return d;
        return {
          ...d,
          sessions: d.sessions.map((s, sI) =>
            sI === sessionIdx ? { ...s, completed: newCompleted } : s
          ),
        };
      });
    });
  }, []);

  const handleSelectSession = (dayIdx: number, sessionIdx: number) => {
    const key = `${dayIdx}-${sessionIdx}`;
    setSelectedKey((prev) => (prev === key ? null : key));
  };

  const selectedDayIdx = selectedKey ? parseInt(selectedKey.split("-")[0]) : null;
  const selectedSessionIdx = selectedKey ? parseInt(selectedKey.split("-")[1]) : null;
  const selectedDay = selectedDayIdx !== null ? days[selectedDayIdx] : null;
  const selectedSession = selectedDayIdx !== null && selectedSessionIdx !== null ? days[selectedDayIdx]?.sessions[selectedSessionIdx] : null;

  return (
    <div className="space-y-8">
      {/* Hero Banner */}
      <div
        className="rounded-2xl p-8 relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, rgba(0,212,255,0.12) 0%, rgba(34,197,94,0.06) 50%, rgba(168,85,247,0.1) 100%)",
          border: "1px solid rgba(0,212,255,0.25)",
        }}
      >
        <div className="absolute top-0 right-0 w-64 h-64 rounded-full opacity-8 blur-3xl" style={{ background: "radial-gradient(circle, #00D4FF, transparent)" }} />
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Badge className="bg-cyan-400/20 text-cyan-300 border-cyan-500/30 text-xs">
                ⚡ Acondicionamiento
              </Badge>
              <Badge className="bg-green-400/20 text-green-300 border-green-500/30 text-xs">
                Plan Activo ✓
              </Badge>
            </div>
            <h2 className="text-2xl font-bold text-white mb-1">
              Plan Semanal — {planData?.semana_inicio
                ? new Date(planData.semana_inicio).toLocaleDateString("es-ES", { day: "numeric", month: "long" })
                : "Esta semana"}
            </h2>
            <p className="text-[#8B949E] text-sm">{coachTip || "Fase: " + (planData?.fase ?? "Acondicionamiento")}</p>
          </div>
          {userId !== 2 && (
          <div className="flex flex-col gap-2">
            <button
              onClick={handleRegenerarSemana}
              disabled={loadingRegen !== null}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all hover:scale-105 disabled:opacity-60"
              style={{ background: "linear-gradient(135deg, #00D4FF, #0EA5E9)", color: "#0E1117", boxShadow: "0 0 20px rgba(0,212,255,0.4)" }}
              title="Regenera la semana actual basándose en el historial real"
            >
              {loadingRegen === "semana" ? <RefreshCw className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Regenerar semana
            </button>
            <button
              onClick={handleRegenerarTotal}
              disabled={loadingRegen !== null}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all hover:scale-105 disabled:opacity-60"
              style={{ background: "rgba(201,255,0,0.12)", border: "1px solid rgba(201,255,0,0.4)", color: "#C9FF00" }}
              title="Regenera el plan completo de las próximas 4 semanas"
            >
              {loadingRegen === "total" ? <RotateCcw className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
              Regenerar plan total
            </button>
          </div>
          )}
        </div>
      </div>

      {/* Regen feedback */}
      {regenMsg && (
        <div className="rounded-xl px-4 py-3 flex items-center gap-3" style={{ background: "rgba(201,255,0,0.1)", border: "1px solid rgba(201,255,0,0.3)" }}>
          <Sparkles className="h-4 w-4 text-[#C9FF00] shrink-0" />
          <p className="text-sm text-[#C9FF00] font-medium">{regenMsg}</p>
          <button onClick={() => setRegenMsg(null)} className="ml-auto p-1 rounded hover:bg-white/10"><X className="h-3.5 w-3.5 text-[#8B949E]" /></button>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* KM ratio — editable */}
        <div className="rounded-xl p-4" style={{ background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.25)" }}>
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-4 w-4 text-cyan-400" />
            <span className="text-xs text-[#8B949E] font-medium">KM SEMANA</span>
          </div>
          <div className="flex items-baseline gap-1">
            <p className="text-xl font-bold text-white">{kmDone.toFixed(1)}</p>
            <p className="text-sm text-[#8B949E]">/ </p>
            {kmEditing ? (
              <form onSubmit={(e) => { e.preventDefault(); handleKmEdit(); }} className="inline-flex items-center gap-1">
                <input
                  autoFocus
                  type="number" step="0.5" min="5"
                  value={kmEditValue}
                  onChange={(e) => setKmEditValue(e.target.value)}
                  onBlur={() => { if (!kmEditValue) setKmEditing(false); }}
                  className="w-16 text-lg font-bold text-cyan-400 bg-transparent focus:outline-none border-b border-cyan-400"
                />
                <button type="submit" className="text-[10px] text-cyan-400 font-bold px-1">OK</button>
              </form>
            ) : (
              <button
                onClick={() => { setKmEditValue(kmPlanned.toFixed(1)); setKmEditing(true); }}
                className="flex items-center gap-1 text-sm text-[#8B949E] hover:text-white transition-colors group"
                title="Click para editar km totales de la semana"
              >
                {kmPlanned.toFixed(1)} km
                <Pencil className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            )}
          </div>
          <div className="mt-1.5 h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(48,54,61,0.6)" }}>
            <div className="h-full rounded-full" style={{ width: `${kmPlanned > 0 ? Math.min(100, (kmDone / kmPlanned) * 100) : 0}%`, background: "linear-gradient(90deg, #00D4FF, #22D3EE)" }} />
          </div>
          <p className="text-[9px] text-[#8B949E] mt-1">Click en km para editar y recalcular</p>
        </div>

        <div className="rounded-xl p-4" style={{ background: "rgba(201,255,0,0.08)", border: "1px solid rgba(201,255,0,0.25)" }}>
          <div className="flex items-center gap-2 mb-2">
            <Calendar className="h-4 w-4 text-[#C9FF00]" />
            <span className="text-xs text-[#8B949E] font-medium">SESIONES</span>
          </div>
          <p className="text-2xl font-bold text-white">{totalSessions}</p>
        </div>

        <div className="rounded-xl p-4" style={{ background: "rgba(168,85,247,0.08)", border: "1px solid rgba(168,85,247,0.25)" }}>
          <div className="flex items-center gap-2 mb-2">
            <Dumbbell className="h-4 w-4 text-purple-400" />
            <span className="text-xs text-[#8B949E] font-medium">FUERZA</span>
          </div>
          <p className="text-2xl font-bold text-white">{fuerzaSessions}</p>
        </div>

        {/* Fase Actual replacing Carga */}
        <div className="rounded-xl p-4" style={{ background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.25)" }}>
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-4 w-4 text-green-400" />
            <span className="text-xs text-[#8B949E] font-medium">FASE ACTUAL</span>
          </div>
          <p className="text-sm font-bold text-green-400">Acondiciona-miento</p>
        </div>
      </div>

      {/* Week Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Calendar className="h-4 w-4 text-cyan-400" />
              Distribución Semanal
            </h3>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentWeek(currentWeek - 1)}
                className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                style={{ border: "1px solid rgba(255,255,255,0.1)" }}
                title="Semana anterior"
              >
                <ChevronLeft className="h-4 w-4 text-[#8B949E] hover:text-white transition-colors" />
              </button>
              <span className="text-sm font-bold text-white px-3 py-1 rounded-lg" style={{ background: "rgba(0,212,255,0.15)", border: "1px solid rgba(0,212,255,0.3)" }}>
                {planData?.semana_inicio ? new Date(planData.semana_inicio).toLocaleDateString("es-ES", { day: "numeric", month: "short" }) : getWeekStart(currentWeek)}
              </span>
              <button
                onClick={() => setCurrentWeek(currentWeek + 1)}
                className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                style={{ border: "1px solid rgba(255,255,255,0.1)" }}
                title="Semana siguiente"
              >
                <ChevronRight className="h-4 w-4 text-[#8B949E] hover:text-white transition-colors" />
              </button>
            </div>
          </div>
        </div>
        <p className="text-[11px] text-[#8B949E] mb-4 flex items-center gap-1.5">
          <GripVertical className="h-3 w-3" />
          Arrastra columnas para reorganizar días · Arrastra sesiones entre días o dentro del mismo día · Click para ver detalles
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-7 gap-3">
          {days.map((day, dayIdx) => (
            <div key={`${day.dayKey}-${day.date}`} className="flex flex-col gap-1">
              <DayColumn
                day={day}
                dayIdx={dayIdx}
                selectedKey={selectedKey}
                onSelectSession={handleSelectSession}
                onToggleComplete={toggleComplete}
                onMoveSession={moveSession}
                onMoveDay={moveDay}
              />
              {/* Add session button per day */}
              <button
                onClick={() => setAddModal({ dayIdx })}
                className="w-full flex items-center justify-center gap-1 py-1.5 rounded-lg text-[10px] text-[#8B949E] hover:text-white transition-colors group"
                style={{ border: "1px dashed rgba(255,255,255,0.08)" }}
              >
                <Plus className="h-3 w-3 group-hover:text-cyan-400 transition-colors" />
                Añadir
              </button>
            </div>
          ))}
        </div>

        {/* Detail panel below grid */}
        {selectedDay && selectedSession && selectedDayIdx !== null && selectedSessionIdx !== null && (
          <DayDetailPanel
            day={selectedDay}
            session={selectedSession}
            onClose={() => setSelectedKey(null)}
            onEdit={() => {
              setEditModal({ dayIdx: selectedDayIdx, sessionIdx: selectedSessionIdx });
              setSelectedKey(null);
            }}
          />
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 px-1">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-3.5 w-3.5 text-green-400" />
          <span className="text-xs text-[#8B949E]">Sesión completada</span>
        </div>
        <div className="flex items-center gap-2">
          <Circle className="h-3.5 w-3.5 text-[#8B949E]" />
          <span className="text-xs text-[#8B949E]">Sesión pendiente</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ background: "rgba(0,212,255,0.2)", border: "2px solid #22D3EE" }} />
          <span className="text-xs text-[#8B949E]">Carrera</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ background: "rgba(168,85,247,0.2)", border: "2px solid #C084FC" }} />
          <span className="text-xs text-[#8B949E]">Fuerza</span>
        </div>
      </div>

      {/* Coach tip */}
      {coachTip && (
        <div
          className="rounded-2xl p-5 flex items-start gap-4"
          style={{ background: "linear-gradient(135deg, rgba(168,85,247,0.1), rgba(0,212,255,0.05))", border: "1px solid rgba(168,85,247,0.25)" }}
        >
          <Sparkles className="h-5 w-5 text-purple-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-bold text-white mb-1">Tip del entrenador</p>
            <p className="text-sm text-[#8B949E]">{coachTip}</p>
          </div>
        </div>
      )}

      {/* Session Edit Modal */}
      {editModal && (
        <SessionEditModal
          session={days[editModal.dayIdx]?.sessions[editModal.sessionIdx] ?? null}
          dayIdx={editModal.dayIdx}
          sessionIdx={editModal.sessionIdx}
          dayDate={days[editModal.dayIdx]?.date ?? ""}
          onClose={() => setEditModal(null)}
          onSave={handleSaveEditedSession}
          onDelete={handleDeleteSession}
        />
      )}

      {/* Add Session Modal */}
      {addModal && userId && (
        <AddSessionModal
          dayIdx={addModal.dayIdx}
          dayDate={days[addModal.dayIdx]?.date ?? ""}
          weekStart={getWeekStart(currentWeek)}
          userId={userId}
          onClose={() => setAddModal(null)}
          onAdded={handleAddSession}
        />
      )}
    </div>
  );
}

function GenerarPlan() {
  return (
    <DndProvider backend={HTML5Backend}>
      <GenerarPlanInner />
    </DndProvider>
  );
}

// ── Datos tab ─────────────────────────────────────────────────────────────────

const MAC_INFO: Record<number, { nombre: string; objetivo: string; meses: string; kmMin: number; kmMax: number; calidad: string; fuerza: string; hitos: string[] }> = {
  1: {
    nombre: "Macrociclo 1 — BASE Y ADAPTACIÓN ANATÓMICA",
    objetivo: "Construir la base aeróbica. Pasar de 20 km a 45 km/semana sin molestias articulares.",
    meses: "Mayo – Agosto",
    kmMin: 20, kmMax: 45,
    calidad: "Fartlek (semanas impares) / Progresivas (semanas pares)",
    fuerza: "3 días/semana — Pull + Push + Pierna (hipertrofia base, 3×12-15, 65-70% 1RM)",
    hitos: [
      "Correr 45 km/semana sin molestias articulares",
      "Ritmo Z2 estable a 6:20-6:30 min/km",
      "FC reposo normal al día siguiente de la Tirada Larga",
    ],
  },
  2: {
    nombre: "Macrociclo 2 — CONSTRUCCIÓN Y UMBRAL",
    objetivo: "Desplazar el umbral de lactato para que 5:00/km sea sostenible. De 45 km a 60 km.",
    meses: "Septiembre – Noviembre",
    kmMin: 45, kmMax: 60,
    calidad: "Intervalos Largos (2000m @ 4:40-4:45) + Tempo Run (a 5:10-5:15/km) — ambos en la misma semana",
    fuerza: "2 días/semana — 1 día pierna pesado + 1 día Core y Tren Superior",
    hitos: [
      "10 km de Tempo a 5:10 min/km sin agotamiento máximo",
      "Series de 2000m a 4:45/km estables (última serie no más lenta que la primera)",
    ],
  },
  3: {
    nombre: "Macrociclo 3 — ESPECÍFICO DE MARATÓN",
    objetivo: "Resistencia a la fatiga y eficiencia a ritmo objetivo 5:00/km. De 60 km a 75 km.",
    meses: "Diciembre – Enero",
    kmMin: 60, kmMax: 75,
    calidad: "Intervalos VO2max (800-1000m @ 4:25-4:35) + Tempo Largo (12-16km @ 5:05-5:10)",
    fuerza: "1 día/semana — Pierna ligero (pliometría/saltos). Prioridad: core y prevención de lesiones.",
    hitos: [
      "Bloque de 18 km a 4:58/km dentro de una tirada larga de 28 km",
      "Tolerar 60-90g de carbohidratos/hora en tiradas largas sin problemas digestivos",
      "Ritmo 5:00/km mecánicamente 'natural'",
    ],
  },
  4: {
    nombre: "Macrociclo 4 — TAPERING (PUESTA A PUNTO)",
    objetivo: "Eliminar la fatiga acumulada manteniendo la intensidad específica.",
    meses: "3 semanas antes del maratón",
    kmMin: 20, kmMax: 50,
    calidad: "Sem -3: 1 sesión intervalos cortos · Sem -2: solo rodajes suaves · Sem carrera: activaciones mínimas",
    fuerza: "Sin fuerza de pierna. Solo movilidad y activación.",
    hitos: [
      "Sensación de 'piernas inquietas' y muchas ganas de correr",
      "Confianza total en los ritmos entrenados",
    ],
  },
};

function getMacrocicloActual(mes: number, dia: number): number {
  if (mes >= 5 && mes <= 8) return 1;
  if (mes >= 9 && mes <= 11) return 2;
  if (mes === 12 || mes === 1) return 3;
  return 4;
}

function getSemaforo(color: string) {
  if (color === "rojo")  return { bg: "rgba(239,68,68,0.08)",   border: "rgba(239,68,68,0.35)",   dot: "#EF4444", label: "ROJO",  text: "text-red-400" };
  if (color === "ambar") return { bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.35)",  dot: "#F59E0B", label: "ÁMBAR", text: "text-yellow-400" };
  return                        { bg: "rgba(34,197,94,0.08)",   border: "rgba(34,197,94,0.35)",   dot: "#22C55E", label: "VERDE", text: "text-green-400" };
}

function InfoChip({ label, value, color, bg, border }: { label: string; value: string; color: string; bg: string; border: string }) {
  return (
    <div className="rounded-xl p-4" style={{ background: bg, border: `1px solid ${border}` }}>
      <p className="text-[10px] font-bold text-[#8B949E] mb-1.5 uppercase tracking-wider">{label}</p>
      <p className="text-lg font-black leading-tight" style={{ color }}>{value}</p>
    </div>
  );
}

function SectionH({ title }: { title: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="w-1 h-5 rounded-full" style={{ background: "#C9FF00" }} />
      <h3 className="text-sm font-bold text-white uppercase tracking-wide">{title}</h3>
    </div>
  );
}

function Datos() {
  const { userId } = useUser();
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [plan, setPlan] = useState<PlanSemana | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) return;
    const semanaInicio = getWeekStart(0);
    Promise.all([
      getDashboard(userId).catch(() => null),
      getPlanSemana(userId, semanaInicio).catch(() => null),
    ]).then(([d, p]) => {
      setDash(d);
      setPlan(p);
      setLoading(false);
    });
  }, [userId]);

  const hoy = new Date();
  const macNum = getMacrocicloActual(hoy.getMonth() + 1, hoy.getDate());
  const macInfo = MAC_INFO[macNum];

  const hrv0       = dash?.hrv_data?.[0] ?? null;
  const sleep0     = dash?.sleep_data?.[dash.sleep_data.length - 1] ?? null;
  const semaforo   = dash?.semaforo ?? { color: "verde", mensaje: "Sin datos" };
  const sf         = getSemaforo(semaforo.color);
  const fase       = dash?.fase_macrociclo ?? { nombre: macInfo.nombre, km_max: macInfo.kmMax, dias_fuerza: 3 };
  const semana     = dash?.semana_actual ?? { km_realizados: 0, km_planificados: 0, sesiones_fuerza: 0 };
  const actRunning = (dash?.actividades_recientes ?? []).filter(a => a.tipo_deporte?.includes("running") || a.tipo_deporte?.includes("correr"));

  // Cálculo volumen: semana pasada → esta semana
  const kmAnt = semana.km_realizados > 0 ? semana.km_realizados : null;
  const kmEst = kmAnt ? Math.round(kmAnt * 1.10 * 10) / 10 : null;

  // Sesiones del plan actual
  const sesionesPlan = plan?.sesiones ?? [];
  const sesRunning = sesionesPlan.filter(s => s.tipo === "Carrera" || s.tipo === "carrera");
  const sesFuerza  = sesionesPlan.filter(s => s.tipo === "Fuerza" || s.tipo === "fuerza");
  const kmTL  = sesRunning.find(s => s.sesion?.includes("Tirada"))?.km_planificados;
  const kmRG  = sesRunning.find(s => s.sesion?.includes("Regenerativo") || s.sesion?.includes("Regen"))?.km_planificados;
  const kmCal = sesRunning.find(s => !s.sesion?.includes("Tirada") && !s.sesion?.includes("Regen") && !s.sesion?.includes("Base"))?.km_planificados;
  const kmRB  = sesRunning.find(s => s.sesion?.includes("Base"))?.km_planificados;

  // Zonas FC
  const zonas = [
    { zona: "Z1 — Recuperación", fc: "< 130-135 ppm",  color: "#6B7280", desc: "Trote muy suave · Regenerativo" },
    { zona: "Z2 — Aeróbico",     fc: "135-150 ppm",    color: "#22C55E", desc: "80% del total semanal (regla de oro)" },
    { zona: "Z3 — Transición",   fc: "144-151 ppm",    color: "#F59E0B", desc: "Puente entre Z2 y Z4" },
    { zona: "Z4 — Umbral",       fc: "152-159 ppm",    color: "#F97316", desc: "Ritmo objetivo maratón (5:00/km)" },
    { zona: "Z5 — VO2max",       fc: "> 160 ppm",      color: "#EF4444", desc: "Series cortas / esfuerzo máximo" },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-[#8B949E] text-sm">
        Cargando datos...
      </div>
    );
  }

  return (
    <div className="space-y-8">

      {/* ── CABECERA ── */}
      <div className="rounded-2xl p-6" style={{ background: "linear-gradient(135deg, rgba(201,255,0,0.08), rgba(0,212,255,0.06))", border: "1px solid rgba(201,255,0,0.2)" }}>
        <h2 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-[#C9FF00]" />
          Cómo se genera tu plan — Manual de entrenamiento
        </h2>
        <p className="text-[#8B949E] text-sm">
          Aquí puedes ver exactamente qué variables analiza el sistema, qué reglas aplica y por qué cada sesión de tu semana está diseñada así.
        </p>
      </div>

      {/* ── 1. MACROCICLO ACTIVO ── */}
      <div className="rounded-2xl p-6" style={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.2)" }}>
        <SectionH title={`Macrociclo ${macNum} — Fase Actual`} />
        <div className="rounded-xl p-4 mb-4" style={{ background: "rgba(0,212,255,0.06)", border: "1px solid rgba(0,212,255,0.2)" }}>
          <p className="text-sm font-bold text-cyan-300 mb-1">{fase.nombre ?? macInfo.nombre}</p>
          <p className="text-xs text-[#8B949E] mb-3">{macInfo.meses} · {macInfo.objetivo}</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <InfoChip label="KM mín/sem" value={`${macInfo.kmMin} km`} color="#C9FF00" bg="rgba(201,255,0,0.06)" border="rgba(201,255,0,0.2)" />
            <InfoChip label="KM máx/sem" value={`${fase.km_max ?? macInfo.kmMax} km`} color="#00D4FF" bg="rgba(0,212,255,0.06)" border="rgba(0,212,255,0.2)" />
            <InfoChip label="Días carrera" value="4 días/sem" color="#A855F7" bg="rgba(168,85,247,0.06)" border="rgba(168,85,247,0.2)" />
            <InfoChip label="Días fuerza" value={`${fase.dias_fuerza ?? 3} días/sem`} color="#F97316" bg="rgba(249,115,22,0.06)" border="rgba(249,115,22,0.2)" />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-xl p-4" style={{ background: "rgba(168,85,247,0.06)", border: "1px solid rgba(168,85,247,0.15)" }}>
            <p className="text-[10px] font-bold text-purple-400 uppercase tracking-wider mb-2">Sesiones de Calidad</p>
            <p className="text-xs text-white">{macInfo.calidad}</p>
          </div>
          <div className="rounded-xl p-4" style={{ background: "rgba(249,115,22,0.06)", border: "1px solid rgba(249,115,22,0.15)" }}>
            <p className="text-[10px] font-bold text-orange-400 uppercase tracking-wider mb-2">Fuerza este macrociclo</p>
            <p className="text-xs text-white">{macInfo.fuerza}</p>
          </div>
        </div>
        <div className="mt-4 rounded-xl p-4" style={{ background: "rgba(201,255,0,0.04)", border: "1px solid rgba(201,255,0,0.12)" }}>
          <p className="text-[10px] font-bold text-[#C9FF00] uppercase tracking-wider mb-2">Hitos a conseguir</p>
          <ul className="space-y-1">
            {macInfo.hitos.map((h, i) => (
              <li key={i} className="text-xs text-[#8B949E] flex gap-2">
                <span className="text-[#C9FF00] shrink-0">→</span>{h}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* ── 2. CÓMO SE CALCULA EL VOLUMEN ── */}
      <div className="rounded-2xl p-6" style={{ background: "#161B22", border: "1px solid rgba(34,197,94,0.2)" }}>
        <SectionH title="Cómo se calcula el volumen semanal" />
        <div className="space-y-3">
          {/* Regla de progresión */}
          <div className="rounded-xl p-4" style={{ background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.2)" }}>
            <p className="text-xs font-bold text-green-400 mb-2">Ciclo de carga: 3 semanas de aumento + 1 semana de descarga</p>
            <div className="grid grid-cols-3 gap-2 text-center">
              {[
                { label: "Sem. Aumento 1",  formula: "km × 1.10", color: "#22C55E" },
                { label: "Sem. Aumento 2",  formula: "km × 1.10", color: "#22C55E" },
                { label: "Sem. Descarga",   formula: "km × 0.70", color: "#F59E0B" },
              ].map((s) => (
                <div key={s.label} className="rounded-lg p-2" style={{ background: "rgba(0,0,0,0.3)" }}>
                  <p className="text-[10px] text-[#8B949E]">{s.label}</p>
                  <p className="text-sm font-black" style={{ color: s.color }}>{s.formula}</p>
                </div>
              ))}
            </div>
          </div>
          {/* Aplicado esta semana */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <InfoChip
              label="KM semana anterior (Garmin)"
              value={kmAnt !== null ? `${kmAnt} km` : "Sin datos Garmin"}
              color="#00D4FF" bg="rgba(0,212,255,0.06)" border="rgba(0,212,255,0.2)"
            />
            <InfoChip
              label="KM planificados esta semana"
              value={semana.km_planificados > 0 ? `${semana.km_planificados} km` : (kmEst ? `~${kmEst} km (est.)` : "—")}
              color="#C9FF00" bg="rgba(201,255,0,0.06)" border="rgba(201,255,0,0.2)"
            />
            <InfoChip
              label="KM realizados esta semana"
              value={semana.km_realizados > 0 ? `${semana.km_realizados} km` : "—"}
              color="#A855F7" bg="rgba(168,85,247,0.06)" border="rgba(168,85,247,0.2)"
            />
          </div>
          <p className="text-[11px] text-[#8B949E] rounded-xl px-4 py-3" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <span className="text-white font-semibold">Reglas de seguridad:</span>{" "}
            Si ACWR &gt; 1.3 → mantener volumen. Si ACWR &gt; 1.5 o hay lesión → reducir -50%. La Tirada Larga nunca supera 32 km.
          </p>
        </div>
      </div>

      {/* ── 3. SESIONES ESTA SEMANA — POR QUÉ CADA UNA ── */}
      <div className="rounded-2xl p-6" style={{ background: "#161B22", border: "1px solid rgba(168,85,247,0.2)" }}>
        <SectionH title="Distribución de sesiones — esta semana" />
        {sesionesPlan.length === 0 ? (
          <p className="text-sm text-[#8B949E] italic">No hay plan generado para esta semana. Usa "Generar Plan" para crearlo.</p>
        ) : (
          <div className="space-y-2">
            {/* Regla de distribución */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
              {[
                { label: "Tirada Larga", regla: "30-35% del total", km: kmTL ? `${kmTL} km` : "—", color: "#C9FF00" },
                { label: "Regenerativo", regla: "1/3 de la TL",     km: kmRG ? `${kmRG} km` : "—", color: "#22C55E" },
                { label: "Calidad",      regla: "~17% del total",   km: kmCal ? `${kmCal} km` : "—", color: "#F97316" },
                { label: "Rodaje Base",  regla: "Resto hasta completar", km: kmRB ? `${kmRB} km` : "—", color: "#00D4FF" },
              ].map((s) => (
                <div key={s.label} className="rounded-xl p-3" style={{ background: "rgba(255,255,255,0.03)", border: `1px solid rgba(255,255,255,0.08)` }}>
                  <p className="text-[10px] text-[#8B949E] mb-1">{s.label}</p>
                  <p className="text-lg font-black" style={{ color: s.color }}>{s.km}</p>
                  <p className="text-[10px] text-[#8B949E] mt-1">{s.regla}</p>
                </div>
              ))}
            </div>
            {/* Tabla de sesiones */}
            <div className="rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.06)" }}>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#30363D]" style={{ background: "rgba(255,255,255,0.03)" }}>
                    {["Día", "Sesión", "Tipo", "KM", "Zona", "Por qué"].map(h => (
                      <th key={h} className="text-left text-[10px] font-bold text-[#8B949E] py-2.5 px-3 uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sesionesPlan.map((s, i) => {
                    const d = new Date(s.fecha + "T12:00:00");
                    const dias = ["Dom","Lun","Mar","Mié","Jue","Vie","Sáb"];
                    const porQue = s.tipo === "Fuerza"
                      ? "Distribución fija: Lun=Pull, Mié=Push, Vie=Pierna"
                      : s.sesion?.includes("Tirada") ? "30-35% del volumen semanal (norma PDF §1.2)"
                      : s.sesion?.includes("Regen")  ? "Siempre el día después de la TL (norma PDF §1.2)"
                      : s.sesion?.includes("Base")   ? "Volumen sobrante para completar km semanales"
                      : "Sesión de calidad — alterna Fartlek/Progresiva o Tempo/Intervalos";
                    return (
                      <tr key={i} className="border-b border-[#30363D]/40 hover:bg-[#30363D]/20">
                        <td className="text-xs font-semibold text-white py-2.5 px-3">{dias[d.getDay()]} {d.getDate()}</td>
                        <td className="text-xs text-cyan-300 py-2.5 px-3">{s.sesion}</td>
                        <td className="text-[10px] py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded-full" style={{ background: s.tipo === "Fuerza" ? "rgba(168,85,247,0.15)" : "rgba(0,212,255,0.12)", color: s.tipo === "Fuerza" ? "#C084FC" : "#00D4FF" }}>{s.tipo}</span>
                        </td>
                        <td className="text-xs text-[#C9FF00] py-2.5 px-3">{s.km_planificados ? `${s.km_planificados} km` : "—"}</td>
                        <td className="text-[10px] text-[#8B949E] py-2.5 px-3">{s.intensidad ?? "—"}</td>
                        <td className="text-[10px] text-[#8B949E] py-2.5 px-3 max-w-[200px]">{porQue}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {/* Constraint de fuerza */}
        <div className="mt-3 rounded-xl px-4 py-3" style={{ background: "rgba(249,115,22,0.06)", border: "1px solid rgba(249,115,22,0.15)" }}>
          <p className="text-[11px] text-[#8B949E]">
            <span className="text-orange-400 font-semibold">Constraint de fuerza (PDF §Parte 3):</span>{" "}
            Si el día X hay fuerza de pierna pesada, el día X+1 NO puede haber Fartlek, Tempo ni Intervalos.
            El layout fijo (Vie=Pierna → Sáb=RG suave) garantiza este constraint automáticamente.
          </p>
        </div>
      </div>

      {/* ── 4. SEMÁFORO HRV — DATOS REALES ── */}
      <div className="rounded-2xl p-6" style={{ background: "#161B22", border: "1px solid rgba(34,197,94,0.2)" }}>
        <SectionH title="Semáforo de recuperación (HRV + Biometría)" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Semáforo */}
          <div className="rounded-xl p-5" style={{ background: sf.bg, border: `1px solid ${sf.border}` }}>
            <div className="flex items-center gap-2 mb-2">
              <span className="w-4 h-4 rounded-full" style={{ background: sf.dot, boxShadow: `0 0 8px ${sf.dot}` }} />
              <span className={`text-base font-black ${sf.text}`}>{sf.label}</span>
            </div>
            <p className="text-xs text-white">{semaforo.mensaje}</p>
            <p className="text-[10px] text-[#8B949E] mt-2">El semáforo no modifica el plan automáticamente — es un AVISO. Usa tu criterio para ajustar la intensidad del día.</p>
          </div>
          {/* Datos HRV reales */}
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: "HRV",          value: hrv0?.hrv_ms  ? `${Math.round(hrv0.hrv_ms)} ms`   : "—", color: "#C9FF00", bg: "rgba(201,255,0,0.06)", border: "rgba(201,255,0,0.2)" },
              { label: "Sleep Score",  value: hrv0?.sleep_score ? `${hrv0.sleep_score}/100`      : (sleep0?.score ? `${sleep0.score}/100` : "—"), color: "#A855F7", bg: "rgba(168,85,247,0.06)", border: "rgba(168,85,247,0.2)" },
              { label: "Estrés Medio", value: hrv0?.estres_medio ? `${Math.round(hrv0.estres_medio)}/100` : "—", color: "#22C55E", bg: "rgba(34,197,94,0.06)", border: "rgba(34,197,94,0.2)" },
              { label: "Body Battery", value: hrv0?.body_battery ? `${hrv0.body_battery}/100`    : "—", color: "#00D4FF", bg: "rgba(0,212,255,0.06)", border: "rgba(0,212,255,0.2)" },
              { label: "FC Reposo",    value: hrv0?.fc_reposo ? `${hrv0.fc_reposo} bpm`          : "—", color: "#F43F5E", bg: "rgba(244,63,94,0.06)", border: "rgba(244,63,94,0.2)" },
              { label: "Sueño Total",  value: sleep0?.horas_totales ? `${sleep0.horas_totales}h` : "—", color: "#6366F1", bg: "rgba(99,102,241,0.06)", border: "rgba(99,102,241,0.2)" },
            ].map(m => <InfoChip key={m.label} {...m} />)}
          </div>
        </div>
        {/* Reglas del semáforo */}
        <div className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
          <p className="text-[10px] font-bold text-[#8B949E] uppercase tracking-wider mb-2">Cómo se decide el semáforo</p>
          <div className="space-y-1">
            {[
              { color: "#22C55E", label: "VERDE",  regla: "HRV ≥ media 7d · Sleep >80 · Sin factores negativos → plan completo, PR permitido" },
              { color: "#F59E0B", label: "ÁMBAR",  regla: "HRV cae 0-10% OR Sleep 60-80 OR Estrés >55 OR Body Battery <25 → cuidado" },
              { color: "#EF4444", label: "ROJO",   regla: "HRV cae >10% OR Sleep <60 OR Sueño profundo <45min OR Estrés >75 → revisar sesión" },
            ].map(r => (
              <div key={r.label} className="flex items-start gap-2">
                <span className="w-2.5 h-2.5 rounded-full mt-0.5 shrink-0" style={{ background: r.color }} />
                <p className="text-[11px] text-[#8B949E]"><span className="font-bold" style={{ color: r.color }}>{r.label}:</span> {r.regla}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── 5. ZONAS DE ENTRENAMIENTO ── */}
      <div className="rounded-2xl p-6" style={{ background: "#161B22", border: "1px solid rgba(201,255,0,0.15)" }}>
        <SectionH title="Zonas de entrenamiento (referencia FC)" />
        <div className="space-y-2 mb-3">
          {zonas.map(z => (
            <div key={z.zona} className="flex items-center gap-3 rounded-xl px-4 py-3" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
              <div className="w-3 h-8 rounded-full shrink-0" style={{ background: z.color }} />
              <div className="flex-1">
                <p className="text-xs font-bold text-white">{z.zona}</p>
                <p className="text-[10px] text-[#8B949E]">{z.desc}</p>
              </div>
              <span className="text-xs font-mono font-bold" style={{ color: z.color }}>{z.fc}</span>
            </div>
          ))}
        </div>
        <div className="rounded-xl px-4 py-3" style={{ background: "rgba(201,255,0,0.06)", border: "1px solid rgba(201,255,0,0.2)" }}>
          <p className="text-xs text-white font-semibold">Regla de oro: el 80% del entrenamiento semanal total debe estar en Z1+Z2</p>
          <p className="text-[10px] text-[#8B949E] mt-0.5">Solo el 20% puede ser Z3-Z5 (calidad, TL con bloques, intervalos)</p>
        </div>
      </div>

      {/* ── 6. ÚLTIMAS ACTIVIDADES GARMIN ── */}
      <div className="rounded-2xl p-6" style={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.15)" }}>
        <SectionH title="Últimas actividades de running (Garmin)" />
        {actRunning.length === 0 ? (
          <p className="text-sm text-[#8B949E] italic">Sin actividades recientes — sincroniza Garmin desde Perfil.</p>
        ) : (
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.06)" }}>
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#30363D]" style={{ background: "rgba(255,255,255,0.03)" }}>
                  {["Fecha", "Distancia", "Cadencia", "FC Media", "Ritmo Medio", "Z2 objetivo"].map(h => (
                    <th key={h} className="text-left text-[10px] font-bold text-[#8B949E] py-2.5 px-3 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {actRunning.slice(0, 6).map((a, i) => {
                  const km = ((a.distancia_m ?? 0) / 1000).toFixed(1);
                  const ritmo = a.ritmo_medio ?? 0;   // decimal min/km  e.g. 5.5 = 5:30/km
                  const ritmofmt = ritmo ? `${Math.floor(ritmo)}:${String(Math.round((ritmo % 1) * 60)).padStart(2,"0")}/km` : "—";
                  const enZ2 = a.fc_media ? (a.fc_media >= 130 && a.fc_media <= 150) : null;
                  return (
                    <tr key={i} className="border-b border-[#30363D]/40 hover:bg-[#30363D]/20">
                      <td className="text-xs text-white py-2.5 px-3">{a.fecha}</td>
                      <td className="text-xs text-cyan-400 py-2.5 px-3 font-bold">{km} km</td>
                      <td className="text-xs text-white py-2.5 px-3">{a.cadencia_media ? `${a.cadencia_media} spm` : "—"}</td>
                      <td className="text-xs py-2.5 px-3" style={{ color: enZ2 === true ? "#22C55E" : enZ2 === false ? "#F59E0B" : "#8B949E" }}>{a.fc_media ? `${a.fc_media} bpm` : "—"}</td>
                      <td className="text-xs text-[#C9FF00] py-2.5 px-3">{ritmofmt}</td>
                      <td className="text-[10px] py-2.5 px-3">
                        {enZ2 === null ? <span className="text-[#8B949E]">—</span>
                          : enZ2 ? <span className="text-green-400">✓ Z2</span>
                          : <span className="text-orange-400">Fuera Z2</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="text-[10px] text-[#8B949E] mt-2">Z2 objetivo: FC 130-150 ppm · Ritmo 6:20-6:30 min/km (Mac1)</p>
      </div>

      {/* ── 7. FUERZA EN ESTE MACROCICLO ── */}
      <div className="rounded-2xl p-6" style={{ background: "#161B22", border: "1px solid rgba(168,85,247,0.15)" }}>
        <SectionH title={`Fuerza — Macrociclo ${macNum}`} />
        <div className="rounded-xl p-4 mb-3" style={{ background: "rgba(168,85,247,0.06)", border: "1px solid rgba(168,85,247,0.2)" }}>
          <p className="text-xs text-white">{macInfo.fuerza}</p>
        </div>
        {sesFuerza.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {sesFuerza.map((s, i) => (
              <div key={i} className="rounded-xl p-3" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(168,85,247,0.2)" }}>
                <p className="text-xs font-bold text-purple-300">{s.sesion}</p>
                <p className="text-[10px] text-[#8B949E] mt-1">{s.detalles?.split(",").slice(0,2).join(",")}</p>
              </div>
            ))}
          </div>
        )}
        <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-2 text-[11px] text-[#8B949E]">
          <div className="rounded-xl px-3 py-2" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <span className="text-white font-semibold">Mac 1:</span> 3 días (Pull/Push/Pierna) · 65-70% 1RM · Hipertrofia base
          </div>
          <div className="rounded-xl px-3 py-2" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <span className="text-white font-semibold">Mac 2:</span> 2 días · 1 pierna pesado + 1 core/tren superior
          </div>
          <div className="rounded-xl px-3 py-2" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <span className="text-white font-semibold">Mac 3:</span> 1 día · Pierna ligero (pliometría/saltos)
          </div>
        </div>
      </div>

    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function PlanSemanal() {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const tab = params.get("tab") || "generar";

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />
      <main className="container mx-auto px-4 py-8">
        {tab === "generar" && <GenerarPlan />}
        {tab === "datos" && <Datos />}
      </main>
    </div>
  );
}
