import { useState } from "react";
import { Link } from "react-router";
import {
  Calendar, TrendingUp, Award, ChevronLeft, ChevronRight,
  ArrowLeftRight, X, Clock, Flame, Plus, Check, Save, Trash2,
  RefreshCw, ArrowRight, Zap,
} from "lucide-react";

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

type Subtype = "RB" | "CAL" | "TL" | "PUSH" | "PULL" | "PIERNA";

const SUB: Record<Subtype, { bg: string; color: string; glow: string; label: string }> = {
  RB:     { bg: "#083344", color: "#22d3ee", glow: "0 0 8px rgba(34,211,238,0.3)",   label: "RB" },
  CAL:    { bg: "#0c4a6e", color: "#38bdf8", glow: "0 0 8px rgba(56,189,248,0.3)",   label: "CAL" },
  TL:     { bg: "#172554", color: "#60a5fa", glow: "0 0 8px rgba(96,165,250,0.35)",  label: "TL" },
  PUSH:   { bg: "#431407", color: "#f97316", glow: "0 0 8px rgba(249,115,22,0.25)",  label: "PUSH" },
  PULL:   { bg: "#451a03", color: "#f59e0b", glow: "0 0 6px rgba(245,158,11,0.2)",   label: "PULL" },
  PIERNA: { bg: "#450a0a", color: "#ef4444", glow: "0 0 6px rgba(239,68,68,0.2)",    label: "PIERNA" },
};

// ─────────────────────────────────────────────────────────────────────────────
// DATA
// ─────────────────────────────────────────────────────────────────────────────
interface Session {
  id: string; week: number; dayIndex: number;
  type: "carrera" | "fuerza"; subtype: Subtype;
  title: string; duration: string; metric: string;
  notes: string; completed: boolean;
}

const INITIAL_SESSIONS: Session[] = [
  // Week 3
  { id:"w3d0f1", week:3, dayIndex:0, type:"fuerza",  subtype:"PULL",   title:"Pull",                     duration:"45 min", metric:"",      notes:"Espalda y bíceps.",                                      completed:true },
  { id:"w3d1r1", week:3, dayIndex:1, type:"carrera", subtype:"RB",     title:"Rodaje Base Zona 2",        duration:"50 min", metric:"10 km", notes:"Sensación muy cómoda. Ritmo medio Z2 5:15 min/km.",       completed:true },
  { id:"w3d2f1", week:3, dayIndex:2, type:"fuerza",  subtype:"PUSH",   title:"Push",                     duration:"50 min", metric:"",      notes:"Pecho, hombro y tríceps.",                               completed:true },
  { id:"w3d3r1", week:3, dayIndex:3, type:"carrera", subtype:"CAL",    title:"Series de Calidad",         duration:"45 min", metric:"6x1000m",notes:"Pace medio: 4:05/km en Z4. Recuperación 2 min.",        completed:true },
  { id:"w3d4f1", week:3, dayIndex:4, type:"fuerza",  subtype:"PIERNA", title:"Pierna",                   duration:"55 min", metric:"",      notes:"Sentadillas.",                                           completed:true },
  { id:"w3d6r1", week:3, dayIndex:6, type:"carrera", subtype:"TL",     title:"Tirada Larga Semanal",      duration:"1h 22m", metric:"16 km", notes:"Fondo constante. Buenas sensaciones al final.",          completed:true },
  // Week 4 (current)
  { id:"w4d0f1", week:4, dayIndex:0, type:"fuerza",  subtype:"PULL",   title:"Pull",                     duration:"45 min", metric:"",      notes:"Espalda y bíceps.",                                      completed:true },
  { id:"w4d1r1", week:4, dayIndex:1, type:"carrera", subtype:"RB",     title:"Rodaje Base Zona 2",        duration:"50 min", metric:"10 km", notes:"Mantener ritmo Z2 medio cómodo de 5:10 min/km.",         completed:true },
  { id:"w4d2f1", week:4, dayIndex:2, type:"fuerza",  subtype:"PUSH",   title:"Push",                     duration:"50 min", metric:"",      notes:"Pecho y tríceps.",                                       completed:false },
  { id:"w4d3r1", week:4, dayIndex:3, type:"carrera", subtype:"CAL",    title:"Series de Calidad",         duration:"45 min", metric:"6x1000m",notes:"Series rápidas a 4:05 min/km.",                        completed:false },
  { id:"w4d4f1", week:4, dayIndex:4, type:"fuerza",  subtype:"PIERNA", title:"Pierna",                   duration:"55 min", metric:"",      notes:"Sentadillas.",                                           completed:false },
  { id:"w4d6r1", week:4, dayIndex:6, type:"carrera", subtype:"TL",     title:"Tirada Larga Semanal",      duration:"1h 30m", metric:"18 km", notes:"Probar geles e hidratarse bien cada 20 min.",            completed:false },
  // Week 5
  { id:"w5d0f1", week:5, dayIndex:0, type:"fuerza",  subtype:"PULL",   title:"Pull",                     duration:"45 min", metric:"",      notes:"Espalda y bíceps.",                                      completed:false },
  { id:"w5d1r1", week:5, dayIndex:1, type:"carrera", subtype:"RB",     title:"Rodaje Base Zona 2",        duration:"1h 00m", metric:"12 km", notes:"Aumento progresivo de volumen en Z2 medio.",              completed:false },
  { id:"w5d2f1", week:5, dayIndex:2, type:"fuerza",  subtype:"PUSH",   title:"Push",                     duration:"50 min", metric:"",      notes:"Pecho y tríceps.",                                       completed:false },
  { id:"w5d3r1", week:5, dayIndex:3, type:"carrera", subtype:"CAL",    title:"Series de Calidad",         duration:"50 min", metric:"8x1000m",notes:"Incremento a 8 repeticiones a ritmo 4:00 min/km.",      completed:false },
  { id:"w5d4f1", week:5, dayIndex:4, type:"fuerza",  subtype:"PIERNA", title:"Pierna",                   duration:"55 min", metric:"",      notes:"Sentadillas.",                                           completed:false },
  { id:"w5d6r1", week:5, dayIndex:6, type:"carrera", subtype:"TL",     title:"Tirada Larga Semanal",      duration:"1h 40m", metric:"20 km", notes:"Objetivo de fondo máximo para el mes.",                  completed:false },
];

const DAYS = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"];
const WEEKS = [
  { id:3, label:"Semana 15 - 21 de Junio" },
  { id:4, label:"Semana 22 - 28 de Junio" },
  { id:5, label:"29 Jun - 5 de Julio" },
];
const MONTHS = [
  { name:"Mayo 2026",   days:31, offset:4 },
  { name:"Junio 2026",  days:30, offset:0 },
  { name:"Julio 2026",  days:31, offset:2 },
];
const MONTH_KMS = [
  [35,38,40,42,10],
  [38,41,44,50,12],
  [40,44,48,52,15],
];

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
function CompleteBtn({ completed, onToggle }: { completed: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onToggle(); }}
      className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-all"
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
  return (
    <div
      onClick={() => isReorderMode ? onReorderTap() : onOpen()}
      className="p-3 rounded-xl cursor-pointer transition-all relative"
      style={{
        background: session.completed ? "rgba(15,23,42,0.5)" : T.bgSurf,
        border: `1px solid ${isReorderMode ? T.reorder + "80" : T.border}`,
        opacity: session.completed ? 0.7 : 1,
        boxShadow: isReorderMode ? `0 0 0 1px ${T.reorder}60` : "none",
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
        {!isReorderMode && <CompleteBtn completed={session.completed} onToggle={onToggle} />}
      </div>
      {/* Bottom row */}
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
// CARD FUERZA
// ─────────────────────────────────────────────────────────────────────────────
function CardFuerza({ session, isReorderMode, onToggle, onReorderTap }: {
  session: Session; isReorderMode: boolean;
  onToggle: () => void; onReorderTap: () => void;
}) {
  const fuerzaLabel = session.subtype === "PIERNA" ? "Pierna" : session.subtype === "PUSH" ? "Push" : "Pull";
  return (
    <div
      onClick={() => isReorderMode ? onReorderTap() : onToggle()}
      className="p-3 rounded-xl cursor-pointer transition-all relative"
      style={{
        background: session.completed ? "rgba(15,23,42,0.5)" : T.bgSurf,
        border: `1px solid ${isReorderMode ? T.reorder + "80" : T.border}`,
        opacity: session.completed ? 0.7 : 1,
        boxShadow: isReorderMode ? `0 0 0 1px ${T.reorder}60` : "none",
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
          <span className="text-xs font-bold" style={{ color: T.text1 }}>GYM</span>
        </div>
        {!isReorderMode && <CompleteBtn completed={session.completed} onToggle={onToggle} />}
      </div>
      {/* Action hint */}
      {!isReorderMode && (
        <div className="mt-2 pt-1.5 flex items-center justify-between" style={{ borderTop: `1px solid ${T.border}` }}>
          <span className="text-[9px] font-semibold" style={{ color: T.text3 }}>Toca para completar la sesión</span>
        </div>
      )}
      <div className="mt-1 flex items-center gap-1 text-[11px]" style={{ color: T.text2 }}>
        <Clock className="w-3 h-3" style={{ color: T.text3 }} />
        <span>{session.duration}</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DAY BLOCK
// ─────────────────────────────────────────────────────────────────────────────
function DayBlock({ dayIndex, dayLabel, sessions, isReorderMode, onToggle, onOpen, onReorderTap }: {
  dayIndex: number; dayLabel: string; sessions: Session[]; isReorderMode: boolean;
  onToggle: (id: string) => void; onOpen: (s: Session) => void; onReorderTap: (s: Session) => void;
}) {
  const done = sessions.filter(s => s.completed).length;
  return (
    <div className="rounded-2xl p-3" style={{ background: "rgba(15,23,42,0.4)", border: `1px solid ${T.border}80` }}>
      {/* Day header */}
      <div className="flex items-center mb-2">
        <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: T.bgSurf, border: `1px solid ${T.border}` }}>
          <span className="text-[10px] font-black" style={{ color: "#818cf8" }}>{dayLabel}</span>
        </div>
      </div>

      {/* Session cards */}
      <div className="space-y-2">
        {sessions.map(s => s.type === "carrera"
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
            <button onClick={() => { onToggle(session.id); }}
              className="py-3 px-4 rounded-xl font-bold text-xs flex items-center gap-2 border transition-all"
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
function AddSessionModal({ weekId, days, onAdd, onClose }: {
  weekId: number; days: string[]; onAdd: (s: Session) => void; onClose: () => void;
}) {
  const [type, setType] = useState<"carrera" | "fuerza">("carrera");
  const [subtype, setSubtype] = useState<Subtype>("RB");
  const [day, setDay] = useState(0);
  const [metric, setMetric] = useState("");
  const [notes, setNotes] = useState("");

  const runSubs: Subtype[] = ["RB", "TL", "CAL"];
  const strSubs: Subtype[] = ["PUSH", "PULL", "PIERNA"];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let title = "";
    if (type === "carrera") {
      title = subtype === "RB" ? "Rodaje Base Zona 2" : subtype === "TL" ? "Tirada Larga" : "Series de Calidad";
    } else {
      title = subtype === "PIERNA" ? "Pierna" : subtype === "PUSH" ? "Push" : "Pull";
    }
    onAdd({
      id: `custom_${Date.now()}`, week: weekId, dayIndex: day,
      type, subtype, title,
      duration: type === "carrera" ? "45 min" : "50 min",
      metric: type === "carrera" ? (metric || "10 km") : "",
      notes: notes || "Sesión planificada.",
      completed: false,
    });
    onClose();
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
            <label className="text-[10px] font-black uppercase tracking-wider mb-1.5 block" style={{ color: T.text3 }}>Objetivo (Métrica)</label>
            <input value={metric} onChange={e => setMetric(e.target.value)} placeholder="Ej: 12 km @ 5:00 min/km"
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

        <button type="submit" className="w-full py-3 rounded-xl text-xs font-black text-white active:scale-[0.98]"
          style={{ background: "linear-gradient(135deg,#06b6d4,#4f46e5)" }}>
          Añadir al Calendario
        </button>
      </form>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// WEEKLY VIEW
// ─────────────────────────────────────────────────────────────────────────────
function WeeklyView({ sessions, setSessions, weekIndex, weeks }: {
  sessions: Session[]; setSessions: React.Dispatch<React.SetStateAction<Session[]>>;
  weekIndex: number; weeks: typeof WEEKS;
}) {
  const [isReorderMode, setIsReorderMode] = useState(false);
  const [editingSession, setEditingSession] = useState<Session | null>(null);
  const [reorderingSession, setReorderingSession] = useState<Session | null>(null);
  const [isAdding, setIsAdding] = useState(false);

  const weekId = weeks[weekIndex].id;
  const weekSessions = sessions.filter(s => s.week === weekId);

  const toggleCompleted = (id: string) => {
    setSessions(prev => prev.map(s => s.id === id ? { ...s, completed: !s.completed } : s));
    setEditingSession(prev => prev?.id === id ? { ...prev, completed: !prev.completed } : prev);
  };
  const saveSession = (id: string, fields: Partial<Session>) => {
    setSessions(prev => prev.map(s => s.id === id ? { ...s, ...fields } : s));
  };
  const deleteSession = (id: string) => {
    setSessions(prev => prev.filter(s => s.id !== id));
  };
  const moveSession = (id: string, dayIndex: number) => {
    setSessions(prev => prev.map(s => s.id === id ? { ...s, dayIndex } : s));
    setReorderingSession(null);
    setEditingSession(prev => prev?.id === id ? { ...prev, dayIndex } : prev);
  };
  const addSession = (s: Session) => setSessions(prev => [...prev, s]);

  return (
    <div className="flex flex-col h-full">
      {/* TopBar */}
      <header className="px-5 py-4 shrink-0" style={{ background: T.bgSurf, borderBottom: `1px solid ${T.border}80` }}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-[18px] font-black bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(90deg,#22d3ee,#818cf8)" }}>
              Proyecto Athlete
            </h1>
          </div>
          <div className="flex items-center gap-2">
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
            {/* Sync */}
            <button className="w-9 h-9 rounded-full flex items-center justify-center border" style={{ background: T.border, borderColor: "#334155" }}>
              <RefreshCw className="w-4 h-4" style={{ color: T.text2 }} />
            </button>
          </div>
        </div>
      </header>

      {/* Week navigator */}
      <div className="px-4 py-2.5 flex items-center justify-between shrink-0" style={{ background: "rgba(15,23,42,0.8)", border: `1px solid ${T.border}`, margin: "0 16px 12px", borderRadius: 16 }}>
        <button className="w-10 h-10 flex items-center justify-center rounded-xl" style={{ background: T.bgSurf, border: `1px solid ${T.border}`, color: "#22d3ee" }}>
          <ChevronLeft className="w-5 h-5" />
        </button>
        <div className="text-center">
          <p className="text-[9px] font-black uppercase tracking-widest" style={{ color: T.text3 }}>PROGRAMA SEMANAL</p>
          <p className="text-xs font-bold" style={{ color: T.text1 }}>{weeks[weekIndex].label}</p>
        </div>
        <button className="w-10 h-10 flex items-center justify-center rounded-xl" style={{ background: T.bgSurf, border: `1px solid ${T.border}`, color: "#22d3ee" }}>
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Days scroll */}
      <div className="flex-1 overflow-y-auto px-4 pb-6 space-y-3">
        {DAYS.map((d, i) => (
          <DayBlock key={d} dayIndex={i} dayLabel={d}
            sessions={weekSessions.filter(s => s.dayIndex === i)}
            isReorderMode={isReorderMode}
            onToggle={toggleCompleted}
            onOpen={s => setEditingSession(s)}
            onReorderTap={s => setReorderingSession(s)}
          />
        ))}
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
          onClose={() => setEditingSession(null)} onSave={saveSession}
          onToggle={toggleCompleted} onDelete={deleteSession} onMove={moveSession}
        />
      )}
      {reorderingSession && (
        <ReorderModal session={reorderingSession} days={DAYS}
          onMove={moveSession} onClose={() => setReorderingSession(null)} />
      )}
      {isAdding && (
        <AddSessionModal weekId={weekId} days={DAYS} onAdd={addSession} onClose={() => setIsAdding(false)} />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MONTHLY VIEW
// ─────────────────────────────────────────────────────────────────────────────
function MonthlyView({ sessions, monthIndex, setMonthIndex }: {
  sessions: Session[]; monthIndex: number; setMonthIndex: (i: number) => void;
}) {
  const [clickedDay, setClickedDay] = useState<number | null>(null);
  const month = MONTHS[monthIndex];
  const DAYS_HEADER = ["L","M","M","J","V","S","D"];
  const weekSessions = sessions.filter(s => s.week === 4);

  return (
    <div className="flex flex-col h-full">
      {/* TopBar */}
      <header className="px-5 py-4 shrink-0" style={{ background: T.bgSurf, borderBottom: `1px solid ${T.border}80` }}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-[18px] font-black bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(90deg,#22d3ee,#818cf8)" }}>
              Proyecto Athlete
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <button className="w-9 h-9 rounded-full flex items-center justify-center border" style={{ background: T.border, borderColor: "#334155" }}>
              <RefreshCw className="w-4 h-4" style={{ color: T.text2 }} />
            </button>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-4 pb-6">
        {/* Month nav */}
        <div className="flex items-center justify-between p-2 rounded-xl my-3" style={{ background: T.bgSurf, border: `1px solid ${T.border}` }}>
          <button disabled={monthIndex === 0} onClick={() => setMonthIndex(monthIndex - 1)}
            className="w-9 h-9 flex items-center justify-center rounded-lg transition-all disabled:opacity-30"
            style={{ background: T.bgApp, border: `1px solid ${T.border}`, color: "#22d3ee" }}>
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs font-black uppercase tracking-wider" style={{ color: "#818cf8" }}>{month.name}</span>
          <button disabled={monthIndex === MONTHS.length - 1} onClick={() => setMonthIndex(monthIndex + 1)}
            className="w-9 h-9 flex items-center justify-center rounded-lg transition-all disabled:opacity-30"
            style={{ background: T.bgApp, border: `1px solid ${T.border}`, color: "#22d3ee" }}>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Grid header */}
        <div className="grid grid-cols-8 text-center mb-2">
          {DAYS_HEADER.map((d, i) => (
            <span key={i} className="text-[9px] font-black uppercase" style={{ color: T.text3 }}>{d}</span>
          ))}
          <span className="text-[9px] font-black uppercase" style={{ color: "#22d3ee", borderLeft: `1px solid ${T.border}60`, paddingLeft: 2 }}>Kms</span>
        </div>

        {/* Grid rows */}
        <div className="space-y-1">
          {[0,1,2,3,4].map(weekIdx => (
            <div key={weekIdx} className="grid grid-cols-8 gap-1 items-center">
              {Array.from({ length: 7 }).map((_, dIdx) => {
                const dayNum = weekIdx * 7 + dIdx + 1 - month.offset;
                if (dayNum <= 0 || dayNum > month.days) {
                  return <div key={dIdx} className="aspect-square rounded-lg" style={{ background: "rgba(2,6,23,0.2)" }} />;
                }
                const dayName = DAYS[dIdx];
                const daySessions = weekSessions.filter(s => s.dayIndex === dIdx);
                const isToday = dayNum === 22 && monthIndex === 1;
                const isSel = clickedDay === dayNum;
                return (
                  <div key={dIdx} onClick={() => setClickedDay(isSel ? null : dayNum)}
                    className="aspect-square rounded-lg flex flex-col justify-between p-1 cursor-pointer transition-all relative"
                    style={{ background: T.bgSurf, border: `1px solid ${isSel || isToday ? "#22d3ee80" : T.border}`, borderWidth: isToday ? 2 : 1 }}>
                    <span className="text-[9px] font-bold" style={{ color: isToday ? "#22d3ee" : T.text3 }}>{dayNum}</span>
                    <div className="flex gap-0.5 justify-center pb-0.5">
                      {daySessions.slice(0, 3).map((s, i) => (
                        <span key={i} className="w-1.5 h-1.5 rounded-full" style={{ background: SUB[s.subtype].color, boxShadow: SUB[s.subtype].glow }} />
                      ))}
                    </div>
                  </div>
                );
              })}
              {/* Km column */}
              <div className="aspect-square rounded-lg flex flex-col justify-center items-center p-1"
                style={{ background: "rgba(15,23,42,0.5)", borderLeft: "2px solid #06b6d4" }}>
                <span className="text-[8px] font-bold uppercase" style={{ color: T.text3 }}>Sem</span>
                <span className="text-xs font-black" style={{ color: "#22d3ee" }}>{MONTH_KMS[monthIndex]?.[weekIdx] ?? 0}k</span>
              </div>
            </div>
          ))}
        </div>

        {/* Day detail */}
        {clickedDay && (
          <div className="mt-4 rounded-2xl overflow-hidden" style={{ background: T.bgSurf, border: `1px solid ${T.border}` }}>
            <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: `1px solid ${T.border}`, background: "rgba(255,255,255,0.02)" }}>
              <p className="text-sm font-black" style={{ color: T.text1 }}>Día {clickedDay} · {MONTHS[monthIndex].name.split(" ")[0]}</p>
              <button onClick={() => setClickedDay(null)} className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: T.border }}>
                <X className="w-3.5 h-3.5" style={{ color: T.text2 }} />
              </button>
            </div>
            <div className="p-3 space-y-2">
              {weekSessions.filter(s => s.dayIndex === (clickedDay - 1) % 7).length > 0
                ? weekSessions.filter(s => s.dayIndex === (clickedDay - 1) % 7).map(s => (
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
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// PROGRESS VIEW
// ─────────────────────────────────────────────────────────────────────────────
const BAR_DATA = [
  { label:"Sem 1", km:28, active:false }, { label:"Sem 2", km:34, active:false },
  { label:"Sem 3", km:38, active:false }, { label:"Sem 4", km:41, active:false },
  { label:"Sem 5", km:44, active:false }, { label:"Sem 6", km:50, active:true },
];

function ProgressView({ weeklyKms }: { weeklyKms: number }) {
  return (
    <div className="flex flex-col h-full">
      <header className="px-5 py-4 shrink-0" style={{ background: T.bgSurf, borderBottom: `1px solid ${T.border}80` }}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.08em]" style={{ color: T.text2 }}>MIS ENTRENOS</p>
            <h1 className="text-[18px] font-black bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(90deg,#22d3ee,#818cf8)" }}>Proyecto Athlete</h1>
          </div>
          <button className="w-9 h-9 rounded-full flex items-center justify-center border" style={{ background: T.border, borderColor: "#334155" }}>
            <RefreshCw className="w-4 h-4" style={{ color: T.text2 }} />
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        <h2 className="text-base font-bold flex items-center gap-2" style={{ color: T.text1 }}>
          <Award className="w-4 h-4" style={{ color: "#22d3ee" }} /> Rendimiento y Volumen
        </h2>

        {/* Bar chart */}
        <div className="rounded-2xl p-4" style={{ background: "rgba(2,6,23,0.5)", border: `1px solid ${T.border}80` }}>
          <h3 className="text-xs font-black uppercase tracking-wide mb-4" style={{ color: T.text2 }}>Progreso de Volumen (km / semana)</h3>
          <div className="h-40 w-full flex items-end justify-between px-2 relative">
            {/* Guide lines */}
            <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
              <div className="border-b text-[8px] pt-1" style={{ borderColor: T.border + "80", color: T.text3 }}>50 km</div>
              <div className="border-b text-[8px]" style={{ borderColor: T.border + "80", color: T.text3 }}>25 km</div>
              <div className="text-[8px]" style={{ color: T.text3 }}>0 km</div>
            </div>
            {BAR_DATA.map((b, i) => {
              const h = Math.round((b.km / 55) * 140);
              return (
                <div key={i} className="flex flex-col items-center z-10 group">
                  <span className="text-[9px] font-black mb-1 opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: "#22d3ee" }}>{b.km}k</span>
                  <div className="w-8 rounded-t-lg" style={{
                    height: h,
                    background: b.active ? "linear-gradient(to top,#06b6d4,#4f46e5)" : T.border,
                    boxShadow: b.active ? "0 0 12px rgba(6,182,212,0.3)" : "none",
                  }} />
                  <span className="text-[10px] font-medium mt-2" style={{ color: T.text2 }}>{b.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Line chart (SVG) */}
        <div className="rounded-2xl p-4" style={{ background: "rgba(2,6,23,0.5)", border: `1px solid ${T.border}80` }}>
          <h3 className="text-xs font-black uppercase tracking-wide mb-4" style={{ color: T.text2 }}>Evolución Ritmo en Zona 2 Medio (min / km)</h3>
          <div className="h-40 w-full relative">
            <div className="absolute inset-y-0 left-0 right-0 flex flex-col justify-between pointer-events-none text-[8px]" style={{ color: T.text3 }}>
              <div className="border-b w-full" style={{ borderColor: T.border + "60" }}>4:30</div>
              <div className="border-b w-full" style={{ borderColor: T.border + "60" }}>5:15</div>
              <div className="w-full">6:00</div>
            </div>
            <svg className="w-full h-full absolute inset-0 z-10" viewBox="0 0 300 120">
              <defs>
                <linearGradient id="line-grad-lp" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.35" />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path d="M 10 100 Q 70 80 130 75 T 250 45 L 250 120 L 10 120 Z" fill="url(#line-grad-lp)" />
              <path d="M 10 100 Q 70 80 130 75 T 250 45" fill="none" stroke="#22d3ee" strokeWidth="3.5" strokeLinecap="round" />
              <circle cx="10" cy="100" r="4" fill="#0891b2" stroke="#fff" strokeWidth="1.5" />
              <circle cx="70" cy="80" r="4" fill="#0891b2" stroke="#fff" strokeWidth="1.5" />
              <circle cx="130" cy="75" r="4" fill="#0891b2" stroke="#fff" strokeWidth="1.5" />
              <circle cx="250" cy="45" r="5" fill="#10b981" stroke="#fff" strokeWidth="2" />
              <text x="5" y="115" fill={T.text3} fontSize="8" fontWeight="bold">S1 (5:45)</text>
              <text x="65" y="95" fill={T.text3} fontSize="8" fontWeight="bold">S3 (5:15)</text>
              <text x="125" y="90" fill={T.text3} fontSize="8" fontWeight="bold">S4 (5:10)</text>
              <text x="220" y="38" fill="#34d399" fontSize="9" fontWeight="bold">Hoy (4:50)</text>
            </svg>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-4 rounded-xl" style={{ background: "rgba(2,6,23,0.4)", border: `1px solid ${T.border}` }}>
            <p className="text-[10px] font-black uppercase" style={{ color: T.text3 }}>KMS TOTALES MES</p>
            <p className="text-xl font-black mt-1" style={{ color: "#22d3ee" }}>186.4 km</p>
            <span className="text-[9px] font-bold" style={{ color: T.success }}>▲ +12% vs. anterior</span>
          </div>
          <div className="p-4 rounded-xl" style={{ background: "rgba(2,6,23,0.4)", border: `1px solid ${T.border}` }}>
            <p className="text-[10px] font-black uppercase" style={{ color: T.text3 }}>KMS SEMANA ACTUAL</p>
            <p className="text-xl font-black mt-1" style={{ color: "#818cf8" }}>{weeklyKms.toFixed(1)} km</p>
            <div className="w-full h-1.5 rounded-full mt-2 overflow-hidden" style={{ background: T.border }}>
              <div className="h-full rounded-full" style={{ width: `${Math.min((weeklyKms/45)*100,100)}%`, background: "linear-gradient(90deg,#22d3ee,#4f46e5)" }} />
            </div>
            <span className="text-[8px] font-bold mt-1 block" style={{ color: T.text3 }}>Planificado: 45.0 km</span>
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
// COMPARATOR VIEW
// ─────────────────────────────────────────────────────────────────────────────
const COMP_CARDS = [
  {
    sub: "RB" as Subtype, title: "Rodajes Base",
    tag: "Ritmo en Zona 2",
    prev: { label:"10.0 km", note:"Ritmo Z2: 5:15/km", status:"Completado" },
    curr: { label:"12.0 km", note:"Plan ritmo Z2: 5:10/km", status:"Programado" },
  },
  {
    sub: "CAL" as Subtype, title: "Series de Calidad",
    tag: "Zonas 4 y 5",
    prev: { label:"6x1000m", note:"Pace medio: 4:05/km", status:"" },
    curr: { label:"8x1000m", note:"Pace objetivo: 4:00/km", status:"+2 Repeticiones" },
  },
  {
    sub: "TL" as Subtype, title: "Tirada Larga (Fondo)",
    tag: "Resistencia",
    prev: { label:"16.0 km", note:"", status:"Completado" },
    curr: { label:"18.0 km", note:"", status:"Crecimiento +2k" },
  },
];

function ComparatorView() {
  return (
    <div className="flex flex-col h-full">
      <header className="px-5 py-4 shrink-0" style={{ background: T.bgSurf, borderBottom: `1px solid ${T.border}80` }}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.08em]" style={{ color: T.text2 }}>MIS ENTRENOS</p>
            <h1 className="text-[18px] font-black bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(90deg,#22d3ee,#818cf8)" }}>Proyecto Athlete</h1>
          </div>
          <button className="w-9 h-9 rounded-full flex items-center justify-center border" style={{ background: T.border, borderColor: "#334155" }}>
            <RefreshCw className="w-4 h-4" style={{ color: T.text2 }} />
          </button>
        </div>
      </header>
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {COMP_CARDS.map((card) => {
          const c = SUB[card.sub];
          return (
            <div key={card.sub} className="rounded-2xl overflow-hidden" style={{ border: `1px solid ${T.border}80`, background: "rgba(15,23,42,0.6)" }}>
              <div className="px-4 py-2.5 flex items-center justify-between" style={{ background: `${c.bg}60`, borderBottom: `1px solid ${T.border}80` }}>
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${c.color}20`, border: `1px solid ${c.color}50` }}>
                    <span className="text-[9px] font-black" style={{ color: c.color }}>{card.sub}</span>
                  </div>
                  <span className="text-xs font-black" style={{ color: T.text1 }}>{card.title}</span>
                </div>
                <span className="text-[9px] font-bold px-2 py-0.5 rounded-full" style={{ background: `${c.color}15`, color: c.color }}>{card.tag}</span>
              </div>
              <div className="p-3.5 grid grid-cols-2 gap-4" style={{ borderLeft: "none" }}>
                <div className="space-y-1" style={{ borderRight: `1px solid ${T.border}` }}>
                  <p className="text-[9px] font-black uppercase tracking-widest" style={{ color: T.text3 }}>SEMANA ANTERIOR</p>
                  <p className={`font-black ${card.sub === "CAL" ? "text-xs" : "text-base"}`} style={{ color: T.text2 }}>{card.prev.label}</p>
                  {card.prev.note && <p className="text-[10px] italic" style={{ color: T.text3 }}>{card.prev.note}</p>}
                  {card.prev.status && <span className="inline-flex text-[9px] font-bold px-1.5 py-0.5 rounded mt-1" style={{ color: T.success, background: `${T.success}15` }}>{card.prev.status}</span>}
                </div>
                <div className="space-y-1 pl-3">
                  <p className="text-[9px] font-black uppercase tracking-widest" style={{ color: c.color }}>{`SEMANA ACTUAL`}</p>
                  <p className={`font-black ${card.sub === "CAL" ? "text-xs" : "text-base"}`} style={{ color: T.text1 }}>{card.curr.label}</p>
                  {card.curr.note && <p className="text-[10px] italic" style={{ color: c.color }}>{card.curr.note}</p>}
                  {card.curr.status && <span className="inline-flex text-[9px] font-bold px-1.5 py-0.5 rounded mt-1" style={{ color: c.color, background: `${c.color}15` }}>{card.curr.status}</span>}
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
  const [sessions, setSessions] = useState<Session[]>(INITIAL_SESSIONS);
  const [activeTab, setActiveTab] = useState<"calendario" | "progreso" | "comparador">("calendario");
  const [calView, setCalView] = useState<"semanal" | "mensual">("semanal");
  const [weekIndex, setWeekIndex] = useState(1);
  const [monthIndex, setMonthIndex] = useState(1);
  const [toast, setToast] = useState("");

  const weekId = WEEKS[weekIndex].id;
  const weekSessions = sessions.filter(s => s.week === weekId);
  const weeklyKms = weekSessions.filter(s => s.type === "carrera").reduce((a, s) => a + (parseFloat(s.metric) || 0), 0);

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

        {/* Status bar (desktop only) */}
        <div className="hidden md:flex h-9 px-6 justify-between items-center text-xs font-medium shrink-0" style={{ background: T.bgApp, color: T.text2 }}>
          <span>10:30</span>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] px-1.5 py-0.5 rounded font-bold" style={{ background: "rgba(99,102,241,0.2)", color: "#818cf8" }}>5G</span>
            <div className="w-5 h-2.5 border rounded-sm p-[1px] flex" style={{ borderColor: T.text3 }}>
              <div className="w-4 h-full rounded-sm" style={{ background: T.text3 }} />
            </div>
          </div>
        </div>

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
          {activeTab === "calendario" && calView === "semanal" && (
            <WeeklyView sessions={sessions} setSessions={setSessions} weekIndex={weekIndex} weeks={WEEKS} />
          )}
          {activeTab === "calendario" && calView === "mensual" && (
            <MonthlyView sessions={sessions} monthIndex={monthIndex} setMonthIndex={setMonthIndex} />
          )}
          {activeTab === "progreso" && <ProgressView weeklyKms={weeklyKms} />}
          {activeTab === "comparador" && <ComparatorView />}
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
