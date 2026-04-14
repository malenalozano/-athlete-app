import { useLocation } from "react-router";
import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { useUser } from "../context/UserContext";
import {
  Dumbbell,
  Heart,
  BookOpen,
  AlertTriangle,
  Plus,
  Clock,
  Flame,
  CheckCircle2,
  Circle,
  ChevronLeft,
  ChevronRight,
  Activity,
  Zap,
} from "lucide-react";
import { useState } from "react";

// ── Mock data ──────────────────────────────────────────────────────────────────

const entrenosLibres = [
  {
    id: 1,
    fecha: "Dom 13 Abr",
    tipo: "Carrera",
    descripcion: "Tirada larga base — Parque del Retiro",
    duracion: "1h 32min",
    distancia: "15.4 km",
    fc: "142 bpm",
    sensacion: "😊 Bien",
    notas: "Buenas sensaciones, cadencia estable. Zona 2 perfecta.",
  },
  {
    id: 2,
    fecha: "Vie 11 Abr",
    tipo: "Carrera",
    descripcion: "Tempo Run — Ritmo umbral",
    duracion: "55 min",
    distancia: "10.2 km",
    fc: "162 bpm",
    sensacion: "💪 Fuerte",
    notas: "Últimos 2km algo pesados, pero mantuve el ritmo objetivo.",
  },
  {
    id: 3,
    fecha: "Jue 10 Abr",
    tipo: "Movilidad",
    descripcion: "Descanso activo — Yoga Runner",
    duracion: "20 min",
    distancia: "—",
    fc: "—",
    sensacion: "😌 Relajada",
    notas: "Piernas cargadas. Estiramientos de cadera y gemelos.",
  },
];

const ejercicios = [
  {
    nombre: "Sentadilla",
    series: 4,
    reps: "8",
    peso: "65 kg",
    notas: "Aumentar 5kg próxima semana",
    tipo: "Piernas",
    color: "#A855F7",
  },
  {
    nombre: "Peso Muerto Rumano",
    series: 3,
    reps: "10",
    peso: "55 kg",
    notas: "Foco en activación de glúteos",
    tipo: "Piernas",
    color: "#A855F7",
  },
  {
    nombre: "Plancha Lateral",
    series: 3,
    reps: "30s",
    peso: "—",
    notas: "Añadir elevación de cadera",
    tipo: "Core",
    color: "#00D4FF",
  },
  {
    nombre: "Zancada búlgara",
    series: 3,
    reps: "12",
    peso: "20 kg",
    notas: "Equilibrio estable",
    tipo: "Piernas",
    color: "#A855F7",
  },
  {
    nombre: "Dead Bug",
    series: 3,
    reps: "12",
    peso: "—",
    notas: "Lento y controlado",
    tipo: "Core",
    color: "#00D4FF",
  },
];

const lesiones = [
  {
    id: 1,
    zona: "Tibial anterior derecho",
    tipo: "Sobrecarga",
    inicio: "28 Mar",
    estado: "En seguimiento",
    dolor: 3,
    tratamiento: "Hielo, antiinflamatorio, reducción de volume",
    color: "#F97316",
    stateColor: "bg-orange-400/15 text-orange-300 border-orange-500/30",
  },
];

// ── Tabs ───────────────────────────────────────────────────────────────────────

// Datos de actividades por día (simulado)
const actividadesPorDia: Record<number, Array<{
  id: number; fecha: string; tipo: string; descripcion: string;
  duracion: string; distancia: string; fc: string; sensacion: string;
  notas: string; gymType?: string; runType?: string;
}>> = {
  7: [
    {
      id: 1, fecha: "Dom 7 Abr", tipo: "Carrera",
      descripcion: "Rodaje regenerativo — Madrid Río",
      duracion: "45 min", distancia: "7.2 km", fc: "135 bpm",
      sensacion: "😊 Recuperado",
      notas: "Piernas ligeras después del descanso del sábado",
      runType: "Regenerativo",
    },
    {
      id: 4, fecha: "Dom 7 Abr", tipo: "Fuerza",
      descripcion: "Core y estabilidad",
      duracion: "30 min", distancia: "—", fc: "110 bpm",
      sensacion: "💪 Fuerte",
      notas: "Plancha frontal, lateral, bird-dog",
      gymType: "Core",
    },
  ],
  10: [
    {
      id: 2, fecha: "Mié 10 Abr", tipo: "Carrera",
      descripcion: "Series 1000m — Pista",
      duracion: "52 min", distancia: "8.5 km", fc: "168 bpm",
      sensacion: "🔥 Intenso",
      notas: "4×1000m a ritmo 10K. Últimas dos series costaron",
      runType: "Intervalos",
    },
  ],
  12: [
    {
      id: 5, fecha: "Sáb 12 Abr", tipo: "Fuerza",
      descripcion: "Fuerza piernas — Gym",
      duracion: "60 min", distancia: "—", fc: "120 bpm",
      sensacion: "💪 Fuerte",
      notas: "Sentadillas, peso muerto rumano, zancadas búlgaras",
      gymType: "Pierna",
    },
  ],
  13: [
    {
      id: 3, fecha: "Dom 13 Abr", tipo: "Carrera",
      descripcion: "Tirada larga base — Parque del Retiro",
      duracion: "1h 32min", distancia: "15.4 km", fc: "142 bpm",
      sensacion: "😊 Bien",
      notas: "Buenas sensaciones, cadencia estable. Zona 2 perfecta.",
      runType: "Tirada Larga",
    },
  ],
  9: [
    {
      id: 6, fecha: "Mié 9 Abr", tipo: "Fuerza",
      descripcion: "Tren superior — Gym",
      duracion: "55 min", distancia: "—", fc: "115 bpm",
      sensacion: "💪 Fuerte",
      notas: "Press banca, dominadas, remo con mancuerna",
      gymType: "Push",
    },
  ],
  5: [
    {
      id: 7, fecha: "Dom 5 Abr", tipo: "Carrera",
      descripcion: "Cambios de ritmo — Parque",
      duracion: "40 min", distancia: "7.5 km", fc: "155 bpm",
      sensacion: "⚡ Activada",
      notas: "8×200m progresivos. Buena respuesta neuromuscular.",
      runType: "Cambios de Ritmo",
    },
    {
      id: 8, fecha: "Dom 5 Abr", tipo: "Fuerza",
      descripcion: "Espalda y bíceps — Gym",
      duracion: "50 min", distancia: "—", fc: "112 bpm",
      sensacion: "😊 Bien",
      notas: "Dominadas, remo, curl. Foco en contracción.",
      gymType: "Pull",
    },
  ],
  2: [
    {
      id: 9, fecha: "Jue 2 Abr", tipo: "Carrera",
      descripcion: "Progresivas — Circuito urbano",
      duracion: "50 min", distancia: "9.0 km", fc: "158 bpm",
      sensacion: "💪 Fuerte",
      notas: "Salida suave, último tercio a ritmo de umbral.",
      runType: "Progresivas",
    },
  ],
};

const GYM_TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  Pull:   { bg: "rgba(168,85,247,0.2)", text: "#A855F7", border: "rgba(168,85,247,0.4)" },
  Push:   { bg: "rgba(249,115,22,0.2)", text: "#F97316", border: "rgba(249,115,22,0.4)" },
  Pierna: { bg: "rgba(236,72,153,0.2)", text: "#EC4899", border: "rgba(236,72,153,0.4)" },
  Core:   { bg: "rgba(99,102,241,0.2)", text: "#6366F1", border: "rgba(99,102,241,0.4)" },
};

const RUN_TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "Tirada Larga":    { bg: "rgba(0,212,255,0.2)",  text: "#00D4FF", border: "rgba(0,212,255,0.4)" },
  "Progresivas":     { bg: "rgba(34,197,94,0.2)",  text: "#22C55E", border: "rgba(34,197,94,0.4)" },
  "Cambios de Ritmo":{ bg: "rgba(201,255,0,0.2)",  text: "#C9FF00", border: "rgba(201,255,0,0.4)" },
  "Intervalos":      { bg: "rgba(244,63,94,0.2)",  text: "#F43F5E", border: "rgba(244,63,94,0.4)" },
  "Regenerativo":    { bg: "rgba(96,165,250,0.2)", text: "#60A5FA", border: "rgba(96,165,250,0.4)" },
};

function EntrenoLibre() {
  const [currentMonth, setCurrentMonth] = useState(new Date(2026, 3, 1)); // April 2026
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [nota, setNota] = useState("");

  // Generate calendar days
  const getDaysInMonth = (date: Date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();

    const days: (number | null)[] = [];
    for (let i = 0; i < startingDayOfWeek; i++) {
      days.push(null);
    }
    for (let day = 1; day <= daysInMonth; day++) {
      days.push(day);
    }
    return days;
  };

  const days = getDaysInMonth(currentMonth);
  const monthNames = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
  const dayNames = ["D", "L", "M", "X", "J", "V", "S"];

  // Mock stats
  const statsDelMes = [
    { label: "DÍAS", value: "8", icon: Activity, color: "#C9FF00", bg: "rgba(201,255,0,0.1)", border: "rgba(201,255,0,0.25)" },
    { label: "FUERZA", value: "4", icon: Dumbbell, color: "#F97316", bg: "rgba(249,115,22,0.1)", border: "rgba(249,115,22,0.25)" },
    { label: "CARRERAS", value: "6", icon: Zap, color: "#00D4FF", bg: "rgba(0,212,255,0.1)", border: "rgba(0,212,255,0.25)" },
  ];

  const getActivityColorForDay = (day: number) => {
    const activities = actividadesPorDia[day];
    if (!activities || activities.length === 0) return null;
    const hasRunning = activities.some(a => a.tipo === "Carrera");
    const hasStrength = activities.some(a => a.tipo === "Fuerza");
    if (hasRunning && hasStrength) return "#C9FF00";
    if (hasRunning) return "#00D4FF";
    if (hasStrength) return "#A855F7";
    return null;
  };

  const getTypeLabelForDay = (day: number): { label: string; color: string } | null => {
    const activities = actividadesPorDia[day];
    if (!activities || activities.length === 0) return null;
    const gymAct = activities.find(a => a.gymType);
    const runAct = activities.find(a => a.runType);
    if (gymAct?.gymType) {
      const c = GYM_TYPE_COLORS[gymAct.gymType];
      return c ? { label: gymAct.gymType, color: c.text } : null;
    }
    if (runAct?.runType) {
      const c = RUN_TYPE_COLORS[runAct.runType];
      return c ? { label: runAct.runType.split(" ")[0], color: c.text } : null;
    }
    return null;
  };

  const TODAY = 14;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div
        className="rounded-2xl p-6 relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, rgba(34,197,94,0.12), rgba(0,212,255,0.08))",
          border: "1px solid rgba(34,197,94,0.25)",
        }}
      >
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Entreno Libre</h2>
          <p className="text-[#8B949E] text-sm">Registro de entrenamientos no programados</p>
        </div>
      </div>

      {/* Main layout: Note panel LEFT | Calendar RIGHT */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* LEFT: Nota del día + Stats del mes */}
        <div className="space-y-4">
          {/* HOY box */}
          <div
            className="rounded-xl px-4 py-3 flex items-center justify-between"
            style={{ background: "rgba(201,255,0,0.08)", border: "1px solid rgba(201,255,0,0.3)" }}
          >
            <div>
              <p className="text-[10px] font-bold text-[#8B949E] uppercase tracking-widest mb-0.5">Hoy</p>
              <p className="text-sm font-bold text-white">14 de Abril, 2026</p>
            </div>
            <span
              className="text-xs font-black px-2 py-1 rounded-lg"
              style={{ background: "#C9FF00", color: "#0E1117" }}
            >
              HOY
            </span>
          </div>

          {/* Nota text area */}
          <Card className="rounded-xl" style={{ background: "#161B22", border: "1px solid rgba(34,197,94,0.2)" }}>
            <CardContent className="p-4 space-y-3">
              <p className="text-xs font-bold text-[#8B949E] uppercase tracking-widest">Nota del entreno</p>
              <textarea
                value={nota}
                onChange={(e) => setNota(e.target.value)}
                placeholder="Escribe aquí tu entreno libre, sensaciones, distancia, tiempo... La IA lo procesará."
                rows={6}
                className="w-full rounded-xl px-3 py-2.5 text-sm text-white resize-none focus:outline-none"
                style={{
                  background: "rgba(14,17,23,0.8)",
                  border: "1px solid rgba(34,197,94,0.25)",
                  scrollbarWidth: "thin",
                }}
              />
              <button
                onClick={() => setNota("")}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold transition-all"
                style={{
                  background: "linear-gradient(135deg, #22c55e, #16a34a)",
                  color: "#0E1117",
                  boxShadow: "0 0 20px rgba(34,197,94,0.4)",
                }}
              >
                <Plus className="h-4 w-4" />
                Procesar nota
              </button>
            </CardContent>
          </Card>

          {/* Stats del mes */}
          <div>
            <h3 className="text-xs font-bold text-[#8B949E] uppercase tracking-widest mb-3">STATS DEL MES</h3>
            <div className="space-y-3">
              {statsDelMes.map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-xl p-4 flex items-center gap-3"
                  style={{ background: stat.bg, border: `1px solid ${stat.border}` }}
                >
                  <stat.icon className="h-6 w-6 shrink-0" style={{ color: stat.color }} />
                  <div className="flex-1">
                    <p className="text-[10px] text-[#8B949E] uppercase tracking-wide">{stat.label}</p>
                  </div>
                  <p className="text-3xl font-black text-white">{stat.value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT: Calendario */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="rounded-2xl" style={{ background: "#161B22", border: "1px solid rgba(34,197,94,0.2)" }}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <button onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1))}>
                  <ChevronLeft className="h-5 w-5 text-[#8B949E] hover:text-white transition-colors" />
                </button>
                <CardTitle className="text-white text-base">
                  {monthNames[currentMonth.getMonth()]} {currentMonth.getFullYear()}
                </CardTitle>
                <button onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1))}>
                  <ChevronRight className="h-5 w-5 text-[#8B949E] hover:text-white transition-colors" />
                </button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-7 gap-1.5 mb-2">
                {dayNames.map((name) => (
                  <div key={name} className="text-center text-xs font-bold text-[#8B949E] py-2">
                    {name}
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-7 gap-1.5">
                {days.map((day, index) => {
                  const hasActivity = day ? actividadesPorDia[day] : null;
                  const activityColor = day ? getActivityColorForDay(day) : null;
                  const typeLabel = day ? getTypeLabelForDay(day) : null;
                  const isToday = day === TODAY && currentMonth.getMonth() === 3;
                  return (
                    <div
                      key={index}
                      onClick={() => day && hasActivity && setSelectedDay(day)}
                      className={`rounded-xl flex flex-col items-center justify-start pt-1.5 pb-1 min-h-[56px] text-sm font-semibold transition-all ${day && hasActivity ? "cursor-pointer hover:scale-105" : ""}`}
                      style={{
                        background: day
                          ? activityColor
                            ? `${activityColor}20`
                            : "rgba(48,54,61,0.4)"
                          : "transparent",
                        border: isToday
                          ? `2px solid #C9FF00`
                          : activityColor
                          ? `2px solid ${activityColor}80`
                          : day
                          ? "1px solid rgba(48,54,61,0.6)"
                          : "none",
                        boxShadow: activityColor ? `0 0 8px ${activityColor}30` : "none",
                      }}
                    >
                      <span style={{ color: activityColor ? activityColor : day ? "#8B949E" : "transparent" }}>
                        {day || ""}
                      </span>
                      {typeLabel && (
                        <span
                          className="text-[8px] font-bold mt-0.5 px-1 rounded"
                          style={{ color: typeLabel.color, background: `${typeLabel.color}15` }}
                        >
                          {typeLabel.label}
                        </span>
                      )}
                      {isToday && (
                        <span className="text-[7px] font-black" style={{ color: "#C9FF00" }}>HOY</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Leyenda */}
          <div className="flex flex-wrap items-center gap-4 px-2">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded" style={{ background: "rgba(0,212,255,0.2)", border: "2px solid #00D4FF" }} />
              <span className="text-xs text-[#8B949E]">Carrera</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded" style={{ background: "rgba(168,85,247,0.2)", border: "2px solid #A855F7" }} />
              <span className="text-xs text-[#8B949E]">Fuerza (Pull/Push/Pierna)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded" style={{ background: "rgba(201,255,0,0.2)", border: "2px solid #C9FF00" }} />
              <span className="text-xs text-[#8B949E]">Ambos</span>
            </div>
          </div>
        </div>
      </div>

      {/* Modal de actividades del día */}
      <Dialog open={selectedDay !== null} onOpenChange={() => setSelectedDay(null)}>
        <DialogContent className="bg-[#161B22] border border-green-400/25 max-w-3xl max-h-[80vh] overflow-y-auto">
          {selectedDay && actividadesPorDia[selectedDay] && (
            <>
              <DialogHeader>
                <DialogTitle className="text-xl font-bold text-white">
                  Actividades del {selectedDay} de {monthNames[currentMonth.getMonth()]}
                </DialogTitle>
                <p className="text-sm text-[#8B949E]">{actividadesPorDia[selectedDay].length} {actividadesPorDia[selectedDay].length === 1 ? "actividad" : "actividades"} registradas</p>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                {actividadesPorDia[selectedDay].map((entreno) => {
                  const gymStyle = entreno.gymType ? GYM_TYPE_COLORS[entreno.gymType] : null;
                  const runStyle = entreno.runType ? RUN_TYPE_COLORS[entreno.runType] : null;
                  return (
                    <div
                      key={entreno.id}
                      className="rounded-xl p-4"
                      style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <Badge className={entreno.tipo === "Carrera" ? "bg-cyan-400/15 text-cyan-300 border-cyan-500/30" : "bg-purple-400/15 text-purple-300 border-purple-500/30"}>
                              {entreno.tipo}
                            </Badge>
                            {/* Gym Type Badge */}
                            {gymStyle && (
                              <span
                                className="text-[10px] font-bold px-2 py-0.5 rounded-full border"
                                style={{ background: gymStyle.bg, color: gymStyle.text, borderColor: gymStyle.border }}
                              >
                                {entreno.gymType}
                              </span>
                            )}
                            {/* Run Type Badge */}
                            {runStyle && (
                              <span
                                className="text-[10px] font-bold px-2 py-0.5 rounded-full border"
                                style={{ background: runStyle.bg, color: runStyle.text, borderColor: runStyle.border }}
                              >
                                {entreno.runType}
                              </span>
                            )}
                            <span className="text-xs text-[#8B949E]">{entreno.fecha}</span>
                          </div>
                          <p className="text-sm font-semibold text-white">{entreno.descripcion}</p>
                        </div>
                        <span className="text-xl">{entreno.sensacion}</span>
                      </div>
                      <div className="grid grid-cols-3 gap-3 mb-3">
                        {[
                          { icon: Clock, label: "Duración", value: entreno.duracion, color: "#A855F7" },
                          { icon: Flame, label: "Distancia", value: entreno.distancia, color: "#00D4FF" },
                          { icon: Heart, label: "FC Media", value: entreno.fc, color: "#F43F5E" },
                        ].map((m) => (
                          <div
                            key={m.label}
                            className="rounded-lg p-2.5"
                            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)" }}
                          >
                            <div className="flex items-center gap-1 mb-1">
                              <m.icon className="h-3 w-3" style={{ color: m.color }} />
                              <span className="text-[10px] text-[#8B949E]">{m.label}</span>
                            </div>
                            <p className="text-xs font-bold text-white">{m.value}</p>
                          </div>
                        ))}
                      </div>
                      {entreno.notas && (
                        <p className="text-xs text-[#8B949E] italic">"{entreno.notas}"</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CicloMenstrualDiario() {
  const [currentMonth, setCurrentMonth] = useState(new Date(2026, 3, 1)); // April 2026
  const [sangre, setSangre] = useState("Sin sangre");
  const [sintomas, setSintomas] = useState<string[]>([]);
  const [animo, setAnimo] = useState("");
  const [entreno, setEntreno] = useState("");

  const toggleSintoma = (s: string) =>
    setSintomas((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));

  // Generate calendar days
  const getDaysInMonth = (date: Date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();

    const days: (number | null)[] = [];
    for (let i = 0; i < startingDayOfWeek; i++) {
      days.push(null);
    }
    for (let day = 1; day <= daysInMonth; day++) {
      days.push(day);
    }
    return days;
  };

  const days = getDaysInMonth(currentMonth);
  const monthNames = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
  const dayNames = ["L", "M", "X", "J", "V", "S", "D"];

  // Dark neon phase colors
  const CYCLE_PHASES: Record<number, { phase: string; bg: string; border: string; text: string }> = {};
  for (let d = 1; d <= 5; d++) CYCLE_PHASES[d] = { phase: "MEN", bg: "rgba(244,63,94,0.18)", border: "rgba(244,63,94,0.5)", text: "#F43F5E" };
  for (let d = 6; d <= 12; d++) CYCLE_PHASES[d] = { phase: "FOL", bg: "rgba(0,212,255,0.12)", border: "rgba(0,212,255,0.4)", text: "#00D4FF" };
  for (let d = 13; d <= 15; d++) CYCLE_PHASES[d] = { phase: "OVU", bg: "rgba(201,255,0,0.12)", border: "rgba(201,255,0,0.4)", text: "#C9FF00" };
  for (let d = 16; d <= 30; d++) CYCLE_PHASES[d] = { phase: "LÚT", bg: "rgba(168,85,247,0.15)", border: "rgba(168,85,247,0.4)", text: "#A855F7" };

  const SANGRE_OPTIONS = [
    { label: "Sin sangre", emoji: "⚪", activeStyle: { bg: "rgba(201,255,0,0.15)", border: "#C9FF00", text: "#C9FF00" } },
    { label: "Manchado", emoji: "🩸", activeStyle: { bg: "rgba(244,63,94,0.15)", border: "#F43F5E", text: "#F43F5E" } },
    { label: "Flujo", emoji: "💧", activeStyle: { bg: "rgba(244,63,94,0.15)", border: "#F43F5E", text: "#F43F5E" } },
    { label: "Ligero", emoji: "🩸", activeStyle: { bg: "rgba(244,63,94,0.2)", border: "#F43F5E", text: "#F43F5E" } },
    { label: "Medio", emoji: "🩸🩸", activeStyle: { bg: "rgba(244,63,94,0.25)", border: "#F43F5E", text: "#F43F5E" } },
    { label: "Fuerte", emoji: "🩸🩸🩸", activeStyle: { bg: "rgba(220,38,38,0.25)", border: "#DC2626", text: "#EF4444" } },
  ];
  const SINTOMA_OPTIONS = [
    { label: "Dolor de ovarios", emoji: "🔴" },
    { label: "Dolor de senos", emoji: "🤲" },
    { label: "Antojos", emoji: "🍩" },
    { label: "Dolor de cabeza", emoji: "😵" },
    { label: "Hinchazón", emoji: "🫃" },
  ];
  const ANIMO_OPTIONS = [
    { label: "Ansiedad/Estrés", emoji: "😰" },
    { label: "Triste", emoji: "😢" },
    { label: "Enfadada", emoji: "😡" },
    { label: "Feliz", emoji: "😊" },
    { label: "Cansada", emoji: "😴" },
    { label: "Energética", emoji: "⚡" },
  ];
  const ENTRENO_OPTIONS = [
    { label: "A tope", emoji: "🚀", activeStyle: { bg: "rgba(201,255,0,0.15)", border: "#C9FF00", text: "#C9FF00" } },
    { label: "Regulero", emoji: "🟠", activeStyle: { bg: "rgba(249,115,22,0.15)", border: "#F97316", text: "#F97316" } },
    { label: "Bajito", emoji: "📉", activeStyle: { bg: "rgba(234,179,8,0.15)", border: "#EAB308", text: "#EAB308" } },
    { label: "No completo", emoji: "❌", activeStyle: { bg: "rgba(244,63,94,0.15)", border: "#F43F5E", text: "#F43F5E" } },
  ];

  const TODAY_DAY = 14;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div
        className="rounded-2xl p-6"
        style={{
          background: "linear-gradient(135deg, rgba(168,85,247,0.15), rgba(244,63,94,0.08))",
          border: "1px solid rgba(168,85,247,0.3)",
        }}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">🌙</span>
          <h2 className="text-xl font-bold text-white">Lútea</h2>
          <span className="text-sm text-[#8B949E]">— Día 21 del ciclo</span>
        </div>
        <div className="flex gap-3 mt-2">
          {[
            { phase: "Menstrual", color: "#F43F5E" },
            { phase: "Folicular", color: "#00D4FF" },
            { phase: "Ovulación", color: "#C9FF00" },
            { phase: "Lútea", color: "#A855F7" },
          ].map(p => (
            <div key={p.phase} className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full" style={{ background: p.color, boxShadow: `0 0 6px ${p.color}` }} />
              <span className="text-[10px]" style={{ color: p.color }}>{p.phase}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Layout: Form left, Calendar right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Formulario de registro */}
        <div className="lg:col-span-1">
          <Card className="rounded-2xl" style={{ background: "#161B22", border: "1px solid rgba(244,63,94,0.2)" }}>
            <CardHeader>
              <CardTitle className="text-white text-sm uppercase tracking-wider">Registro Diario</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Fecha del registro */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[#C9FF00] mb-2">Fecha</p>
                <input
                  type="date"
                  defaultValue="2026-04-14"
                  className="w-full rounded-xl px-3 py-2 text-sm text-white bg-[#0E1117] border border-[#C9FF00]/50 focus:outline-none focus:border-[#C9FF00]"
                />
              </div>

              {/* Sangre */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[#C9FF00] mb-2">Sangre</p>
                <div className="flex flex-wrap gap-1.5">
                  {SANGRE_OPTIONS.map((opt) => (
                    <button
                      key={opt.label}
                      onClick={() => setSangre(opt.label)}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-full border text-xs transition-all"
                      style={
                        sangre === opt.label
                          ? { background: opt.activeStyle.bg, borderColor: opt.activeStyle.border, color: opt.activeStyle.text, boxShadow: `0 0 8px ${opt.activeStyle.border}` }
                          : { background: "rgba(14,17,23,0.6)", borderColor: "rgba(48,54,61,0.8)", color: "#8B949E" }
                      }
                    >
                      <span>{opt.emoji}</span>
                      <span>{opt.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Síntomas */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[#C9FF00] mb-2">Síntomas</p>
                <div className="flex flex-wrap gap-1.5">
                  {SINTOMA_OPTIONS.map((s) => (
                    <button
                      key={s.label}
                      onClick={() => toggleSintoma(s.label)}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-full border text-xs transition-all"
                      style={
                        sintomas.includes(s.label)
                          ? { background: "rgba(249,115,22,0.15)", borderColor: "#F97316", color: "#F97316", boxShadow: "0 0 8px rgba(249,115,22,0.3)" }
                          : { background: "rgba(14,17,23,0.6)", borderColor: "rgba(48,54,61,0.8)", color: "#8B949E" }
                      }
                    >
                      <span>{s.emoji}</span>
                      <span>{s.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Ánimo */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[#C9FF00] mb-2">Ánimo</p>
                <div className="flex flex-wrap gap-1.5">
                  {ANIMO_OPTIONS.map((a) => (
                    <button
                      key={a.label}
                      onClick={() => setAnimo(animo === a.label ? "" : a.label)}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-full border text-xs transition-all"
                      style={
                        animo === a.label
                          ? { background: "rgba(168,85,247,0.15)", borderColor: "#A855F7", color: "#A855F7", boxShadow: "0 0 8px rgba(168,85,247,0.3)" }
                          : { background: "rgba(14,17,23,0.6)", borderColor: "rgba(48,54,61,0.8)", color: "#8B949E" }
                      }
                    >
                      <span>{a.emoji}</span>
                      <span>{a.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Entreno */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[#C9FF00] mb-2">Entreno</p>
                <div className="flex flex-wrap gap-1.5">
                  {ENTRENO_OPTIONS.map((opt) => (
                    <button
                      key={opt.label}
                      onClick={() => setEntreno(entreno === opt.label ? "" : opt.label)}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-full border text-xs transition-all"
                      style={
                        entreno === opt.label
                          ? { background: opt.activeStyle.bg, borderColor: opt.activeStyle.border, color: opt.activeStyle.text, boxShadow: `0 0 8px ${opt.activeStyle.border}` }
                          : { background: "rgba(14,17,23,0.6)", borderColor: "rgba(48,54,61,0.8)", color: "#8B949E" }
                      }
                    >
                      <span>{opt.emoji}</span>
                      <span>{opt.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Botón Guardar */}
              <button
                className="w-full py-3 rounded-xl text-sm font-bold transition-all"
                style={{
                  background: "linear-gradient(135deg, #C9FF00, #a3e635)",
                  color: "#0E1117",
                  boxShadow: "0 0 20px rgba(201,255,0,0.4)",
                }}
              >
                Guardar
              </button>
            </CardContent>
          </Card>
        </div>

        {/* Calendario grande */}
        <div className="lg:col-span-2">
          <Card className="rounded-2xl" style={{ background: "#161B22", border: "1px solid rgba(244,63,94,0.2)" }}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <button onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1))}>
                  <ChevronLeft className="h-5 w-5 text-[#8B949E] hover:text-white transition-colors" />
                </button>
                <CardTitle className="text-white text-base">
                  {monthNames[currentMonth.getMonth()]} {currentMonth.getFullYear()}
                </CardTitle>
                <button onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1))}>
                  <ChevronRight className="h-5 w-5 text-[#8B949E] hover:text-white transition-colors" />
                </button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-7 gap-1.5 mb-2">
                {dayNames.map((name) => (
                  <div key={name} className="text-center text-xs font-bold text-[#8B949E] py-2">
                    {name}
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-7 gap-1.5">
                {days.map((day, index) => {
                  const phaseInfo = day ? CYCLE_PHASES[day] : null;
                  const isToday = day === TODAY_DAY && currentMonth.getMonth() === 3;
                  return (
                    <div
                      key={index}
                      className={`min-h-[52px] rounded-xl flex flex-col items-center justify-start pt-1.5 text-sm font-semibold transition-all relative ${day ? "cursor-pointer hover:scale-105" : ""}`}
                      style={{
                        background: phaseInfo ? phaseInfo.bg : day ? "rgba(22,27,34,0.8)" : "transparent",
                        border: isToday
                          ? "2px solid #EC4899"
                          : phaseInfo
                          ? `1px solid ${phaseInfo.border}`
                          : day
                          ? "1px solid rgba(48,54,61,0.5)"
                          : "none",
                        boxShadow: phaseInfo ? `0 0 6px ${phaseInfo.border}40` : "none",
                      }}
                    >
                      <span style={{ color: phaseInfo ? phaseInfo.text : day ? "#8B949E" : "transparent" }}>
                        {day || ""}
                      </span>
                      {phaseInfo && (
                        <span className="text-[7px] font-bold mt-0.5" style={{ color: phaseInfo.text, opacity: 0.8 }}>
                          {phaseInfo.phase}
                        </span>
                      )}
                      {isToday && (
                        <span className="text-[7px] font-black absolute top-0.5 right-0.5 px-0.5 rounded" style={{ background: "#EC4899", color: "#fff" }}>
                          HOY
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Ejercicios() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div
        className="rounded-2xl p-6"
        style={{
          background: "linear-gradient(135deg, rgba(168,85,247,0.12), rgba(201,255,0,0.05))",
          border: "1px solid rgba(168,85,247,0.25)",
        }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white mb-1">Biblioteca de Ejercicios</h2>
            <p className="text-[#8B949E] text-sm">Última sesión: Fuerza Piernas — Sáb 12 Abr</p>
          </div>
          <button
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-[#0E1117] transition-all"
            style={{
              background: "linear-gradient(135deg, #A855F7, #7C3AED)",
              boxShadow: "0 0 20px rgba(168,85,247,0.4)",
            }}
          >
            <Plus className="h-4 w-4" />
            Añadir Ejercicio
          </button>
        </div>
      </div>

      {/* Exercise list */}
      <div className="space-y-3">
        {ejercicios.map((ej, i) => (
          <Card
            key={i}
            className="rounded-xl transition-all hover:scale-[1.01]"
            style={{
              background: "#161B22",
              border: `1px solid ${ej.color}25`,
            }}
          >
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="h-10 w-10 rounded-xl flex items-center justify-center"
                    style={{ background: `${ej.color}15`, border: `1px solid ${ej.color}30` }}
                  >
                    <Dumbbell className="h-5 w-5" style={{ color: ej.color }} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">{ej.nombre}</p>
                    <p className="text-xs text-[#8B949E]">{ej.tipo}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-right">
                  <div>
                    <p className="text-xs text-[#8B949E]">Series × Reps</p>
                    <p className="text-sm font-bold text-white">{ej.series} × {ej.reps}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[#8B949E]">Peso</p>
                    <p className="text-sm font-bold" style={{ color: ej.color }}>{ej.peso}</p>
                  </div>
                </div>
              </div>
              {ej.notas && (
                <p className="text-xs text-[#8B949E] mt-2 pl-13 ml-13">{ej.notas}</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function Lesiones() {
  const preventionTips = [
    { check: true, tip: "Calentamiento dinámico 10min antes de cada carrera" },
    { check: true, tip: "Estiramientos post-entreno (cadera, gemelos, isquios)" },
    { check: false, tip: "Baño frío o contraste 3x semana" },
    { check: true, tip: "Rodillo de espuma 5min diarios" },
    { check: false, tip: "Ejercicios de pie descalzo (fortalecimiento plantar)" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div
        className="rounded-2xl p-6"
        style={{
          background: "linear-gradient(135deg, rgba(249,115,22,0.12), rgba(244,63,94,0.05))",
          border: "1px solid rgba(249,115,22,0.25)",
        }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-400" />
              Lesiones y Prevención
            </h2>
            <p className="text-[#8B949E] text-sm">Seguimiento activo y protocolo preventivo</p>
          </div>
          <button
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-[#0E1117] transition-all"
            style={{
              background: "linear-gradient(135deg, #F97316, #EA580C)",
              boxShadow: "0 0 20px rgba(249,115,22,0.4)",
            }}
          >
            <Plus className="h-4 w-4" />
            Registrar Lesión
          </button>
        </div>
      </div>

      {/* Active injuries */}
      {lesiones.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-orange-400" />
            Lesiones activas
          </h3>
          {lesiones.map((l) => (
            <Card
              key={l.id}
              className="rounded-2xl"
              style={{
                background: "linear-gradient(135deg, rgba(249,115,22,0.1), rgba(22,27,34,1))",
                border: "1px solid rgba(249,115,22,0.25)",
              }}
            >
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="text-base font-bold text-white mb-1">{l.zona}</p>
                    <div className="flex items-center gap-2">
                      <Badge className="bg-orange-400/15 text-orange-300 border-orange-500/30 text-xs">
                        {l.tipo}
                      </Badge>
                      <Badge className={`text-xs ${l.stateColor}`}>
                        {l.estado}
                      </Badge>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-[#8B949E]">Dolor (1–10)</p>
                    <p className="text-2xl font-bold" style={{ color: l.color }}>{l.dolor}</p>
                  </div>
                </div>
                <div
                  className="rounded-xl p-3"
                  style={{ background: "rgba(249,115,22,0.08)", border: "1px solid rgba(249,115,22,0.15)" }}
                >
                  <p className="text-xs text-[#8B949E] mb-1">Tratamiento actual</p>
                  <p className="text-sm text-white">{l.tratamiento}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Prevention checklist */}
      <Card
        className="rounded-2xl"
        style={{ background: "#161B22", border: "1px solid rgba(201,255,0,0.15)" }}
      >
        <CardHeader>
          <CardTitle className="text-white text-base flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-[#C9FF00]" />
            Protocolo de Prevención
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {preventionTips.map((t, i) => (
            <div key={i} className="flex items-center gap-3">
              {t.check ? (
                <CheckCircle2 className="h-4 w-4 text-[#C9FF00] shrink-0" />
              ) : (
                <Circle className="h-4 w-4 text-[#30363D] shrink-0" />
              )}
              <p className={`text-sm ${t.check ? "text-white" : "text-[#8B949E]"}`}>{t.tip}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function Diario() {
  const location = useLocation();
  const { userId } = useUser();
  const params = new URLSearchParams(location.search);
  const tab = params.get("tab") || "libre";

  // If user is Dani and tries to access ciclo, redirect to libre
  const safeTab = tab === "ciclo" && userId !== 1 ? "libre" : tab;

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />
      <main className="container mx-auto px-4 py-8">
        {safeTab === "libre" && <EntrenoLibre />}
        {safeTab === "ciclo" && <CicloMenstrualDiario />}
        {safeTab === "ejercicios" && <Ejercicios />}
        {safeTab === "lesiones" && <Lesiones />}
      </main>
    </div>
  );
}