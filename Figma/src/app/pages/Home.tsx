import React, { useState } from "react";
import { Header } from "../components/Header";
import { KPICard } from "../components/KPICard";
import { CheckpointCard } from "../components/CheckpointCard";
import { MacrocicloCard } from "../components/MacrocicloCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { useUser } from "../context/UserContext";
import {
  Activity,
  Heart,
  Moon,
  Dumbbell,
  AlertCircle,
  TrendingUp,
  Calendar as CalendarIcon,
  Plus,
  X,
  CheckSquare,
  Footprints,
  Zap,
  Sparkles,
  Target,
} from "lucide-react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  AreaChart,
  Area,
} from "recharts";

// ── Types ──────────────────────────────────────────────────────────────────────

interface Checkpoint {
  distance: string;
  time: string;
  description: string;
  status: "completed" | "pending";
  bestMark?: string;
}

interface WeekDay {
  day: string;
  date: string;
  activity: string;
  type: "running" | "strength" | "rest" | string;
  duration: string;
}

interface RunningProgressEntry {
  semana: string;
  km: number;
  objetivo: number;
}

interface TechniqueDataEntry {
  metric: string;
  value: number;
  fullMark: number;
}

interface RunningMetric {
  label: string;
  value: string;
  unit: string;
  status: "good" | "warning";
}

interface StatusAlert {
  type: "warning" | "info";
  message: string;
}

interface GarminMetric {
  label: string;
  value: string;
  status: "good" | "warning";
  unit: string;
}

interface SleepEntry {
  dia: string;
  horas: number;
  score: number | null;
}

interface WeekHabit {
  id: string;
  label: string;
  completedDays: boolean[];
}

// ── Component ─────────────────────────────────────────────────────────────────

export function Home() {
  const { userId, userName } = useUser();

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Buenos días";
    if (hour < 19) return "Buenas tardes";
    return "Buenas noches";
  };

  const getCurrentDate = () => {
    const days = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
    const months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
    const now = new Date();
    return `${days[now.getDay()]} ${now.getDate()} de ${months[now.getMonth()]} de ${now.getFullYear()}`;
  };

  // ── Habits ──────────────────────────────────────────────────────────────────
  const [weekHabits, setWeekHabits] = useState<WeekHabit[]>([
    { id: "habit-1", label: "Hidratación (2L agua)", completedDays: [true, true, false, true, true, true, false] },
    { id: "habit-2", label: "Estiramientos post-entreno", completedDays: [true, true, true, false, true, true, true] },
    { id: "habit-3", label: "Movilidad matinal (10 min)", completedDays: [true, false, true, true, true, false, true] },
  ]);
  const [newHabitLabel, setNewHabitLabel] = useState("");
  const [showAddHabitForm, setShowAddHabitForm] = useState(false);

  // ── Data ────────────────────────────────────────────────────────────────────

  const checkpoints: Checkpoint[] = [
    { distance: "5K", time: "Sub 22:30", description: "Velocidad máxima necesaria", status: "completed", bestMark: "21:45" },
    { distance: "10K", time: "Sub 46:30", description: "Umbral y capacidad de sostener ritmo", status: "pending", bestMark: "47:12" },
    { distance: "Media Maratón", time: "Sub 1h42", description: "Checkpoint definitivo para el ritmo de maratón", status: "pending", bestMark: "1:45:30" },
  ];

  const weekDays: WeekDay[] = [
    { day: "LUN", date: "14 Abr", activity: "Rodaje Suave", type: "running", duration: "8 km · 45 min" },
    { day: "MAR", date: "15 Abr", activity: "Fuerza Core", type: "strength", duration: "45 min" },
    { day: "MIÉ", date: "16 Abr", activity: "Series 400m", type: "running", duration: "6 km · 40 min" },
    { day: "JUE", date: "17 Abr", activity: "Descanso Activo", type: "rest", duration: "Movilidad 20 min" },
    { day: "VIE", date: "18 Abr", activity: "Tempo Run", type: "running", duration: "10 km · 55 min" },
    { day: "SÁB", date: "19 Abr", activity: "Fuerza Piernas", type: "strength", duration: "60 min" },
    { day: "DOM", date: "20 Abr (Hoy)", activity: "Tirada Larga", type: "running", duration: "18 km · 1h50" },
  ];

  const runningProgressData: RunningProgressEntry[] = [
    { semana: "S1", km: 28, objetivo: 30 },
    { semana: "S2", km: 32, objetivo: 32 },
    { semana: "S3", km: 35, objetivo: 35 },
    { semana: "S4", km: 38, objetivo: 38 },
    { semana: "S5", km: 40, objetivo: 40 },
    { semana: "S6", km: 42, objetivo: 42 },
    { semana: "S7", km: 45, objetivo: 45 },
    { semana: "S8", km: 43, objetivo: 48 },
  ];

  const runningTechniqueData: TechniqueDataEntry[] = [
    { metric: "Cadencia", value: 175, fullMark: 180 },
    { metric: "Oscilación", value: 85, fullMark: 100 },
    { metric: "Contacto", value: 220, fullMark: 250 },
    { metric: "Longitud", value: 120, fullMark: 140 },
    { metric: "Balance", value: 95, fullMark: 100 },
  ];

  const runningTechnique: RunningMetric[] = [
    { label: "Cadencia", value: "175", unit: "spm", status: "good" },
    { label: "Tiempo de Contacto", value: "220", unit: "ms", status: "good" },
    { label: "Longitud de Zancada", value: "1.20", unit: "m", status: "warning" },
    { label: "Balance L/R", value: "50.5/49.5", unit: "%", status: "good" },
  ];

  const technicalAlerts: StatusAlert[] = [
    { type: "warning", message: "Longitud de zancada por debajo del objetivo. Trabajar fuerza de glúteos." },
  ];

  const garminMetrics: GarminMetric[] = [
    { label: "HRV", value: "58", status: "good", unit: "ms" },
    { label: "Sueño", value: "7.2", status: "good", unit: "h" },
    { label: "Score Sueño", value: "82", status: "good", unit: "/100" },
    { label: "Cadencia", value: "175", status: "good", unit: "spm" },
    { label: "ACWR", value: "1.2", status: "good", unit: "" },
    { label: "FC Reposo", value: "48", status: "good", unit: "bpm" },
    { label: "Estrés", value: "32", status: "good", unit: "/100" },
  ];

  const sleepData: SleepEntry[] = [
    { dia: "Lun", horas: 7.5, score: 78 },
    { dia: "Mar", horas: 6.8, score: 72 },
    { dia: "Mié", horas: 7.2, score: 80 },
    { dia: "Jue", horas: 7.8, score: 85 },
    { dia: "Vie", horas: 6.5, score: 68 },
    { dia: "Sáb", horas: 8.2, score: 92 },
    { dia: "Dom", horas: 7.3, score: 81 },
  ];

  const macrocicloPhases = [
    { name: "FUNDAMENTACIÓN", progress: 100, status: "completed" as const, color: "green" as const },
    { name: "PRE-ESPECÍFICO", progress: 29, status: "in-progress" as const, color: "cyan" as const },
    { name: "ESPECÍFICO", progress: 0, status: "pending" as const, color: "blue" as const },
    { name: "PICO", progress: 0, status: "pending" as const, color: "purple" as const },
  ];

  const globalMacrocicloProgress =
    macrocicloPhases.reduce((acc, phase) => acc + phase.progress, 0) / macrocicloPhases.length;

  // ── Computed ─────────────────────────────────────────────────────────────────
  const completedCheckpoints = checkpoints.filter((c) => c.status === "completed").length;
  const totalCheckpoints = checkpoints.length;
  const progressPercentage = (completedCheckpoints / totalCheckpoints) * 100;

  const WEEK_DAY_LABELS = ["L", "M", "X", "J", "V", "S", "D"];

  // ── Habit handlers ────────────────────────────────────────────────────────────
  const handleAddHabit = () => {
    if (!newHabitLabel.trim()) return;
    setWeekHabits((prev) => [...prev, { id: `habit-${Date.now()}`, label: newHabitLabel.trim(), completedDays: Array(7).fill(false) }]);
    setNewHabitLabel("");
    setShowAddHabitForm(false);
  };
  const handleRemoveHabit = (id: string) => setWeekHabits((prev) => prev.filter((h) => h.id !== id));
  const handleToggleHabitDay = (habitId: string, dayIndex: number) => {
    setWeekHabits((prev) =>
      prev.map((h) =>
        h.id === habitId ? { ...h, completedDays: h.completedDays.map((d, i) => (i === dayIndex ? !d : d)) } : h
      )
    );
  };
  const getHabitWeekScore = (habit: WeekHabit) => `${habit.completedDays.filter(Boolean).length}/7`;

  // ── Helpers ──────────────────────────────────────────────────────────────────
  const getActivityTypeStyle = (type: string) => {
    switch (type) {
      case "running": return { border: "border-l-cyan-400", bg: "rgba(0,212,255,0.05)", glow: "rgba(0,212,255,0.1)", text: "text-cyan-400", badge: "bg-cyan-400/15 text-cyan-300" };
      case "strength": return { border: "border-l-purple-400", bg: "rgba(168,85,247,0.05)", glow: "rgba(168,85,247,0.1)", text: "text-purple-400", badge: "bg-purple-400/15 text-purple-300" };
      case "rest": return { border: "border-l-green-400", bg: "rgba(34,197,94,0.05)", glow: "rgba(34,197,94,0.1)", text: "text-green-400", badge: "bg-green-400/15 text-green-300" };
      default: return { border: "border-l-[#C9FF00]", bg: "rgba(201,255,0,0.05)", glow: "rgba(201,255,0,0.1)", text: "text-[#C9FF00]", badge: "bg-[#C9FF00]/15 text-[#C9FF00]" };
    }
  };

  const garminCardColors = [
    { color: "#F43F5E", bg: "rgba(244,63,94,0.1)", border: "rgba(244,63,94,0.25)" },
    { color: "#A855F7", bg: "rgba(168,85,247,0.1)", border: "rgba(168,85,247,0.25)" },
    { color: "#3B82F6", bg: "rgba(59,130,246,0.1)", border: "rgba(59,130,246,0.25)" },
    { color: "#00D4FF", bg: "rgba(0,212,255,0.1)", border: "rgba(0,212,255,0.25)" },
    { color: "#C9FF00", bg: "rgba(201,255,0,0.1)", border: "rgba(201,255,0,0.25)" },
    { color: "#F97316", bg: "rgba(249,115,22,0.1)", border: "rgba(249,115,22,0.25)" },
    { color: "#6366F1", bg: "rgba(99,102,241,0.1)", border: "rgba(99,102,241,0.25)" },
  ];

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-4 py-8 space-y-10">

        {/* ── Hero Greeting ─────────────────────────────────────────────────── */}
        <section
          className="relative rounded-2xl p-8 overflow-hidden"
          style={{
            background: "linear-gradient(135deg, rgba(201,255,0,0.08) 0%, rgba(0,212,255,0.06) 40%, rgba(168,85,247,0.08) 100%)",
            border: "1px solid rgba(201,255,0,0.2)",
            boxShadow: "0 0 60px rgba(201,255,0,0.05), 0 0 100px rgba(0,212,255,0.04)",
          }}
        >
          {/* Decorative blobs */}
          <div className="absolute -top-20 -right-20 w-80 h-80 rounded-full opacity-10 blur-3xl pointer-events-none" style={{ background: "radial-gradient(circle, #C9FF00, transparent)" }} />
          <div className="absolute -bottom-20 -left-20 w-60 h-60 rounded-full opacity-8 blur-3xl pointer-events-none" style={{ background: "radial-gradient(circle, #00D4FF, transparent)" }} />

          <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">
                {getGreeting()},{" "}
                <span
                  style={{
                    background: "linear-gradient(90deg, #C9FF00, #00D4FF)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                  }}
                >
                  {userName}
                </span>{" "}
                👋
              </h1>
              <p className="text-[#8B949E] mb-4 text-sm">{getCurrentDate()}</p>
              <div className="flex flex-wrap items-center gap-2">
                {userId === 1 && (
                  <>
                    <Badge className="bg-pink-500/20 text-pink-300 border-pink-500/30">🌸 Fase Folicular — Día 8</Badge>
                    <Badge className="bg-green-500/20 text-green-300 border-green-500/30">⚡ Alta Energía</Badge>
                  </>
                )}
                <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/30">🗓 Semana 8 de entrenamiento</Badge>
              </div>
            </div>

            {/* Race countdown */}
            <div
              className="flex flex-col items-center justify-center rounded-2xl px-8 py-5 shrink-0"
              style={{
                background: "linear-gradient(135deg, rgba(0,212,255,0.12), rgba(59,130,246,0.1))",
                border: "1px solid rgba(0,212,255,0.3)",
                boxShadow: "0 0 24px rgba(0,212,255,0.15)",
              }}
            >
              <p className="text-xs text-[#8B949E] mb-1 uppercase tracking-wider">Próxima carrera</p>
              <p className="text-xl font-bold text-white">10K Retiro</p>
              <p
                className="text-3xl font-black mt-1"
                style={{ background: "linear-gradient(90deg, #00D4FF, #C9FF00)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}
              >
                23 días
              </p>
            </div>
          </div>
        </section>

        {/* ── KPIs ──────────────────────────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<Activity className="h-5 w-5 text-[#C9FF00]" />} title="Resumen Últimos 7 Días" color="#C9FF00" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard label="KM" value="42.5" period="Últimos 7 días" delta={5.3} color="green" icon={<Footprints className="h-4 w-4" />} />
            <KPICard label="CARRERAS" value="5" period="Últimos 7 días" delta={1} color="blue" icon={<Activity className="h-4 w-4" />} />
            <KPICard label="FUERZA" value="3" period="Sesiones" delta={0} color="purple" icon={<Dumbbell className="h-4 w-4" />} />
            <KPICard label="SUEÑO MEDIO" value="7.2" period="h/noche" delta={-0.3} color="orange" icon={<Moon className="h-4 w-4" />} />
          </div>
        </section>

        {/* ── Macrociclo ────────────────────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<TrendingUp className="h-5 w-5 text-cyan-400" />} title="Macrociclo — Maratón • Sep 2026" color="#00D4FF" />
          <MacrocicloCard title="Progreso Global del Macrociclo" phases={macrocicloPhases} globalProgress={globalMacrocicloProgress} />
        </section>

        {/* ── Ciclo Malena for Dani ──────────────────────────────────────────── */}
        {userId === 2 && (
          <section>
            <div
              className="rounded-2xl p-6 relative overflow-hidden"
              style={{
                background: "linear-gradient(135deg, rgba(244,63,94,0.12), rgba(168,85,247,0.1))",
                border: "1px solid rgba(244,63,94,0.25)",
                boxShadow: "0 0 40px rgba(244,63,94,0.06)",
              }}
            >
              <div className="absolute -right-10 -top-10 w-40 h-40 rounded-full opacity-15 blur-3xl" style={{ background: "#F43F5E" }} />
              <div className="relative">
                <h3 className="text-base font-bold text-white flex items-center gap-2 mb-4">
                  <Heart className="h-5 w-5 text-pink-400" />
                  Estado del Ciclo de Malena
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                  {[
                    { label: "Fase Actual", value: "Folicular", sub: "Día 8 de 28", color: "#A855F7", bg: "rgba(168,85,247,0.12)", border: "rgba(168,85,247,0.3)" },
                    { label: "Próxima Regla", value: "En 20 días", sub: "3 de Mayo", color: "#F43F5E", bg: "rgba(244,63,94,0.12)", border: "rgba(244,63,94,0.3)" },
                    { label: "Nivel Energía", value: "Alto ⚡", sub: "Óptimo para entrenar", color: "#C9FF00", bg: "rgba(201,255,0,0.08)", border: "rgba(201,255,0,0.2)" },
                  ].map((item) => (
                    <div key={item.label} className="rounded-xl p-4" style={{ background: item.bg, border: `1px solid ${item.border}` }}>
                      <p className="text-xs mb-1 font-semibold uppercase tracking-wider" style={{ color: item.color }}>{item.label}</p>
                      <p className="text-lg font-bold text-white">{item.value}</p>
                      <p className="text-xs text-[#8B949E] mt-0.5">{item.sub}</p>
                    </div>
                  ))}
                </div>
                <div className="rounded-xl p-4" style={{ background: "rgba(244,63,94,0.08)", border: "1px solid rgba(244,63,94,0.2)" }}>
                  <p className="text-sm text-pink-200">
                    💡 <span className="font-semibold text-pink-300">Consejo:</span> Fase ideal para alta intensidad. Aprovecha el pico de energía para series o fuerza máxima.
                  </p>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ── Checkpoints ───────────────────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<Target className="h-5 w-5 text-[#C9FF00]" />} title="Objetivo: Maratón 2026" color="#C9FF00" />
          <div
            className="rounded-2xl p-5 mb-5"
            style={{
              background: "linear-gradient(135deg, rgba(201,255,0,0.06), rgba(0,212,255,0.04))",
              border: "1px solid rgba(201,255,0,0.2)",
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-white">
                <span className="font-bold text-[#C9FF00]">{completedCheckpoints}</span> de{" "}
                <span className="font-bold">{totalCheckpoints}</span> checkpoints completados
              </p>
              <span className="text-sm font-bold text-[#C9FF00]">{progressPercentage.toFixed(0)}%</span>
            </div>
            <div className="h-3 rounded-full overflow-hidden" style={{ background: "rgba(48,54,61,0.8)" }}>
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${progressPercentage}%`,
                  background: "linear-gradient(90deg, #C9FF00, #00D4FF)",
                  boxShadow: "0 0 10px rgba(201,255,0,0.5)",
                }}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {checkpoints.map((checkpoint, index) => (
              <CheckpointCard key={index} {...checkpoint} />
            ))}
          </div>
        </section>

        {/* ── Plan Esta Semana ──────────────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<CalendarIcon className="h-5 w-5 text-cyan-400" />} title="Plan Esta Semana" color="#00D4FF" />
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {weekDays.map((day, index) => {
              const style = getActivityTypeStyle(day.type);
              const isToday = day.date.includes("Hoy");
              return (
                <div
                  key={index}
                  className={`border-l-4 ${style.border} rounded-xl p-4 transition-all hover:scale-[1.02] cursor-pointer`}
                  style={{
                    background: isToday
                      ? "linear-gradient(135deg, rgba(0,212,255,0.15), rgba(99,102,241,0.1))"
                      : "#161B22",
                    border: isToday ? "1px solid rgba(0,212,255,0.4)" : "1px solid rgba(255,255,255,0.05)",
                    borderLeft: `4px solid ${isToday ? "#00D4FF" : (style.border.includes("cyan") ? "#22d3ee" : style.border.includes("purple") ? "#c084fc" : "#4ade80")}`,
                    boxShadow: isToday ? "0 0 20px rgba(0,212,255,0.2)" : "none",
                  }}
                >
                  <p className="text-[10px] text-[#8B949E] font-bold mb-0.5">{day.day}</p>
                  <p className="text-xs text-white font-semibold mb-2">{day.date.replace(" (Hoy)", "")}</p>
                  {isToday && <span className="text-[9px] text-cyan-400 font-bold uppercase">HOY</span>}
                  <p className={`text-xs font-bold mt-1 ${style.text}`}>{day.activity}</p>
                  <p className="text-[10px] text-[#8B949E] mt-1">{day.duration}</p>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── Hábitos ───────────────────────────────────────────────────────── */}
        <section>
          <div
            className="rounded-2xl overflow-hidden"
            style={{
              border: "1px solid rgba(34,197,94,0.25)",
              background: "#161B22",
            }}
          >
            <div
              className="p-5 flex items-center justify-between"
              style={{
                background: "linear-gradient(135deg, rgba(34,197,94,0.1), rgba(16,185,129,0.05))",
                borderBottom: "1px solid rgba(34,197,94,0.15)",
              }}
            >
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <CheckSquare className="h-5 w-5 text-green-400" />
                Hábitos — Esta Semana
              </h3>
              <button
                onClick={() => setShowAddHabitForm((v) => !v)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all"
                style={{
                  background: "rgba(34,197,94,0.15)",
                  border: "1px solid rgba(34,197,94,0.3)",
                  color: "#4ade80",
                }}
              >
                <Plus className="h-3 w-3" />
                Añadir hábito
              </button>
            </div>
            <div className="p-5">
              {showAddHabitForm && (
                <div className="flex gap-2 mb-5">
                  <input
                    type="text"
                    value={newHabitLabel}
                    onChange={(e) => setNewHabitLabel(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddHabit()}
                    placeholder="Nombre del hábito..."
                    className="flex-1 rounded-xl px-3 py-2 text-sm text-white placeholder:text-[#8B949E] focus:outline-none"
                    style={{ background: "#0E1117", border: "1px solid rgba(34,197,94,0.3)" }}
                    autoFocus
                  />
                  <button
                    onClick={handleAddHabit}
                    className="px-4 py-2 rounded-xl text-sm font-bold text-[#0E1117] transition-all"
                    style={{ background: "linear-gradient(135deg, #22c55e, #16a34a)" }}
                  >
                    Añadir
                  </button>
                  <button onClick={() => { setShowAddHabitForm(false); setNewHabitLabel(""); }} className="p-2 text-[#8B949E] hover:text-white transition-colors">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}
              {weekHabits.length === 0 ? (
                <div className="text-center py-8">
                  <CheckSquare className="h-10 w-10 text-[#30363D] mx-auto mb-3" />
                  <p className="text-[#8B949E] text-sm">No hay hábitos registrados.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr>
                        <th className="text-left text-xs text-[#8B949E] pb-3 min-w-[140px]">Hábito</th>
                        {WEEK_DAY_LABELS.map((d) => (
                          <th key={d} className="text-center text-xs text-[#8B949E] pb-3 w-9">{d}</th>
                        ))}
                        <th className="text-center text-xs text-[#8B949E] pb-3 w-12">Total</th>
                        <th className="w-6" />
                      </tr>
                    </thead>
                    <tbody>
                      {weekHabits.map((habit) => (
                        <tr key={habit.id} className="border-t border-[#30363D]/40">
                          <td className="py-2.5 pr-3">
                            <span className="text-sm text-white">{habit.label}</span>
                          </td>
                          {habit.completedDays.map((done, dayIndex) => (
                            <td key={dayIndex} className="py-2.5 text-center">
                              <button
                                onClick={() => handleToggleHabitDay(habit.id, dayIndex)}
                                className="w-7 h-7 rounded-full border transition-all mx-auto flex items-center justify-center"
                                style={{
                                  background: done ? "rgba(34,197,94,0.2)" : "transparent",
                                  borderColor: done ? "#22c55e" : "rgba(48,54,61,0.8)",
                                  boxShadow: done ? "0 0 8px rgba(34,197,94,0.4)" : "none",
                                  color: done ? "#22c55e" : "transparent",
                                }}
                              >
                                <span className="text-xs font-bold">✓</span>
                              </button>
                            </td>
                          ))}
                          <td className="py-2.5 text-center">
                            <span className="text-xs font-bold text-green-400">{getHabitWeekScore(habit)}</span>
                          </td>
                          <td className="py-2.5 text-center">
                            <button onClick={() => handleRemoveHabit(habit.id)} className="p-1 text-[#30363D] hover:text-red-400 transition-colors">
                              <X className="h-3.5 w-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* ── Running Progress ──────────────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<Activity className="h-5 w-5 text-cyan-400" />} title="Progreso de Running — Últimas 8 Semanas" color="#00D4FF" />
          <div
            className="rounded-2xl overflow-hidden"
            style={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.2)" }}
          >
            <div className="p-6">
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={runningProgressData}>
                  <defs>
                    <linearGradient id="kmGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#00D4FF" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#00D4FF" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="semana" stroke="#8B949E" fontSize={12} />
                  <YAxis stroke="#8B949E" fontSize={12} />
                  <Tooltip contentStyle={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.3)", borderRadius: 8 }} labelStyle={{ color: "#fff" }} />
                  <Legend />
                  <Area type="monotone" dataKey="km" name="Km Reales" stroke="#00D4FF" strokeWidth={3} fill="url(#kmGrad)" dot={{ fill: "#00D4FF", r: 5 }} />
                  <Line type="monotone" dataKey="objetivo" name="Objetivo" stroke="#C9FF00" strokeDasharray="5 5" strokeWidth={2} dot={{ fill: "#C9FF00", r: 3 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

        {/* ── Técnica Radar ──────────────────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<Zap className="h-5 w-5 text-orange-400" />} title="Radar Antilesiones y Técnica" color="#F97316" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="rounded-2xl overflow-hidden" style={{ background: "#161B22", border: "1px solid rgba(249,115,22,0.2)" }}>
              <div className="p-4 border-b" style={{ borderColor: "rgba(249,115,22,0.1)" }}>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Zap className="h-4 w-4 text-orange-400" />
                  Análisis Técnico
                </h3>
              </div>
              <div className="p-4">
                <ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={runningTechniqueData}>
                    <PolarGrid stroke="rgba(255,255,255,0.07)" />
                    <PolarAngleAxis dataKey="metric" stroke="#8B949E" fontSize={11} />
                    <PolarRadiusAxis stroke="#8B949E" fontSize={10} />
                    <Radar name="Técnica" dataKey="value" stroke="#F97316" fill="#F97316" fillOpacity={0.25} strokeWidth={2} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-2xl overflow-hidden" style={{ background: "#161B22", border: "1px solid rgba(249,115,22,0.2)" }}>
              <div className="p-4 border-b" style={{ borderColor: "rgba(249,115,22,0.1)" }}>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Activity className="h-4 w-4 text-orange-400" />
                  Métricas Detalladas
                </h3>
              </div>
              <div className="p-4 space-y-3">
                {runningTechnique.map((metric, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 rounded-xl"
                    style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)" }}
                  >
                    <div>
                      <p className="text-xs text-[#8B949E]">{metric.label}</p>
                      <p className="text-base font-bold text-white">{metric.value} {metric.unit}</p>
                    </div>
                    <div
                      className="px-3 py-1 rounded-full text-xs font-semibold"
                      style={
                        metric.status === "good"
                          ? { background: "rgba(34,197,94,0.15)", color: "#4ade80", border: "1px solid rgba(34,197,94,0.3)" }
                          : { background: "rgba(249,115,22,0.15)", color: "#fb923c", border: "1px solid rgba(249,115,22,0.3)" }
                      }
                    >
                      {metric.status === "good" ? "✓ OK" : "⚠ Revisar"}
                    </div>
                  </div>
                ))}
                {technicalAlerts.map((alert, index) => (
                  <div key={index} className="p-3 rounded-xl text-sm" style={{ background: "rgba(249,115,22,0.1)", border: "1px solid rgba(249,115,22,0.25)" }}>
                    ⚠️ <span className="text-orange-200">{alert.message}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── Semáforo Garmin ───────────────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<Heart className="h-5 w-5 text-pink-400" />} title="Semáforo Diario Garmin" color="#F43F5E" />
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {garminMetrics.map((metric, index) => {
              const c = garminCardColors[index % garminCardColors.length];
              return (
                <div
                  key={index}
                  className="rounded-xl p-4 text-center transition-all hover:scale-105 cursor-default"
                  style={{ background: c.bg, border: `1px solid ${c.border}` }}
                >
                  <p className="text-xs text-[#8B949E] mb-2 uppercase tracking-wide">{metric.label}</p>
                  <p className="text-2xl font-black text-white">{metric.value}</p>
                  {metric.unit && <p className="text-xs mt-0.5" style={{ color: c.color }}>{metric.unit}</p>}
                  <div
                    className="mt-2 h-1 rounded-full mx-auto w-8"
                    style={{ background: c.color, boxShadow: `0 0 6px ${c.color}` }}
                  />
                </div>
              );
            })}
          </div>
        </section>

        {/* ── Sueño ─────────────────────────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<Moon className="h-5 w-5 text-purple-400" />} title="Calidad de Sueño — Esta Semana" color="#A855F7" />
          <div className="rounded-2xl overflow-hidden" style={{ background: "#161B22", border: "1px solid rgba(168,85,247,0.2)" }}>
            <div className="p-6">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={sleepData}>
                  <defs>
                    <linearGradient id="sleepGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#A855F7" stopOpacity={0.9} />
                      <stop offset="100%" stopColor="#6366F1" stopOpacity={0.6} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="dia" stroke="#8B949E" fontSize={12} />
                  <YAxis stroke="#8B949E" fontSize={12} />
                  <Tooltip contentStyle={{ background: "#161B22", border: "1px solid rgba(168,85,247,0.3)", borderRadius: 8 }} labelStyle={{ color: "#fff" }} />
                  <Legend />
                  <Bar dataKey="horas" name="Horas" fill="url(#sleepGrad)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="score" name="Score /100" fill="rgba(201,255,0,0.6)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}

// ── Section Title helper ──────────────────────────────────────────────────────

function SectionTitle({ icon, title, color }: { icon: React.ReactNode; title: string; color: string }) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <div
        className="h-8 w-8 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: `${color}15`, border: `1px solid ${color}30` }}
      >
        {icon}
      </div>
      <h2 className="text-base font-bold text-white">{title}</h2>
      <div className="flex-1 h-px" style={{ background: `linear-gradient(90deg, ${color}30, transparent)` }} />
    </div>
  );
}