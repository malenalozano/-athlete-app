import React, { useState, useEffect } from "react";
import { Header } from "../components/Header";
import { MacrocicloCard } from "../components/MacrocicloCard";
import { Card, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { useUser } from "../context/UserContext";
import { getDashboard, type DashboardData } from "../api";
import {
  Activity,
  Heart,
  Moon,
  Dumbbell,
  TrendingUp,
  Target,
  Footprints,
  Zap,
  Brain,
  BatteryMedium,
  Wind,
  MapPin,
  CheckCircle2,
  TrendingDown,
  Minus,
  ArrowUp,
  ArrowDown,
  ChevronDown,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
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
  AreaChart,
  Area,
  ComposedChart,
} from "recharts";

// ── Data ──────────────────────────────────────────────────────────────────────

const macrocicloPhases = [
  { name: "FUNDAMENTACIÓN", progress: 100, status: "completed" as const, color: "green" as const },
  { name: "ACONDICIONAMIENTO", progress: 45, status: "in-progress" as const, color: "cyan" as const },
  { name: "ESPECÍFICO", progress: 0, status: "pending" as const, color: "blue" as const },
  { name: "PICO", progress: 0, status: "pending" as const, color: "purple" as const },
];

const globalMacrocicloProgress =
  macrocicloPhases.reduce((acc, p) => acc + p.progress, 0) / macrocicloPhases.length;

const runningProgressData = [
  { semana: "S1", km: 28, objetivo: 30 },
  { semana: "S2", km: 32, objetivo: 32 },
  { semana: "S3", km: 35, objetivo: 35 },
  { semana: "S4", km: 38, objetivo: 38 },
  { semana: "S5", km: 40, objetivo: 40 },
  { semana: "S6", km: 42, objetivo: 42 },
  { semana: "S7", km: 45, objetivo: 45 },
  { semana: "S8", km: 43, objetivo: 48 },
];

const sleepWeekData = [
  { dia: "Lun", horas: 7.5, score: 78 },
  { dia: "Mar", horas: 6.8, score: 72 },
  { dia: "Mié", horas: 7.2, score: 80 },
  { dia: "Jue", horas: 7.8, score: 85 },
  { dia: "Vie", horas: 6.5, score: 68 },
  { dia: "Sáb", horas: 8.2, score: 92 },
  { dia: "Dom", horas: 9.2, score: 72 },
];

// Running pace evolution in Z2 (weekly average)
const z2PaceEvolution = [
  { semana: "S1", ritmo: 9.8 },
  { semana: "S2", ritmo: 9.5 },
  { semana: "S3", ritmo: 9.3 },
  { semana: "S4", ritmo: 9.1 },
  { semana: "S5", ritmo: 8.9 },
  { semana: "S6", ritmo: 8.7 },
  { semana: "S7", ritmo: 8.5 },
  { semana: "S8", ritmo: 8.4 },
];

// Average pace by HR zone
const paceByHRZone = [
  { zona: "Z5 (VO2max)", ritmo: 4.8, color: "#F43F5E" },
  { zona: "Z4 (Umbral)", ritmo: 7.23, color: "#F97316" },
  { zona: "Z3 (Tempo)", ritmo: 8.28, color: "#C9FF00" },
  { zona: "Z2 (Aeróbico)", ritmo: 9.68, color: "#00D4FF" },
  { zona: "Z1 (Recuperación)", ritmo: 8.0, color: "#22C55E" },
];

// Strength progression data
const strengthProgressionData = [
  { name: "Sentadilla", weight: 50, prevWeight: 47.5, volume: "3x10", trend: "up" as const },
  { name: "Press Banca", weight: 15, prevWeight: 14, volume: "3x8", trend: "up" as const },
  { name: "Peso Muerto Rumano", weight: 40, prevWeight: 40, volume: "3x10", trend: "equal" as const },
  { name: "Zancada Búlgara", weight: 14, prevWeight: 12, volume: "3x12", trend: "up" as const },
  { name: "Face Pull", weight: 12, prevWeight: 11, volume: "3x15", trend: "up" as const },
  { name: "Curl de bíceps", weight: 10, prevWeight: 10, volume: "3x12", trend: "equal" as const },
];

// Biometric trends data
const hrvTrendData = [
  { semana: "S1", hrv: 65 },
  { semana: "S2", hrv: 68 },
  { semana: "S3", hrv: 70 },
  { semana: "S4", hrv: 69 },
  { semana: "S5", hrv: 71 },
  { semana: "S6", hrv: 72 },
  { semana: "S7", hrv: 71 },
  { semana: "S8", hrv: 73 },
];

const cadenceTrendData = [
  { semana: "S1", cadencia: 170 },
  { semana: "S2", cadencia: 172 },
  { semana: "S3", cadencia: 171 },
  { semana: "S4", cadencia: 173 },
  { semana: "S5", cadencia: 174 },
  { semana: "S6", cadencia: 175 },
  { semana: "S7", cadencia: 176 },
  { semana: "S8", cadencia: 175 },
];

const restingHRTrendData = [
  { semana: "S1", fc: 52 },
  { semana: "S2", fc: 51 },
  { semana: "S3", fc: 50 },
  { semana: "S4", fc: 51 },
  { semana: "S5", fc: 49 },
  { semana: "S6", fc: 49 },
  { semana: "S7", fc: 48 },
  { semana: "S8", fc: 48 },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Buenos días";
  if (h < 19) return "Buenas tardes";
  return "Buenas noches";
}

function getCurrentDate() {
  const days = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
  const months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  const n = new Date();
  return `${days[n.getDay()]} ${n.getDate()} de ${months[n.getMonth()]} de ${n.getFullYear()}`;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionTitle({ icon, title, color }: { icon: React.ReactNode; title: string; color: string }) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <div
        className="h-8 w-8 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: `${color}18`, border: `1px solid ${color}40`, boxShadow: `0 0 12px ${color}20` }}
      >
        {icon}
      </div>
      <h2 className="text-base font-bold text-white">{title}</h2>
      <div className="flex-1 h-[1px]" style={{ background: `linear-gradient(90deg, ${color}30, transparent)` }} />
    </div>
  );
}

// Sleep Donut Card
function SleepAnalysis({ score: scoreProp, hours: hoursProp }: { score?: number | null; hours?: number | null } = {}) {
  const score = scoreProp ?? 72;
  const totalHoras = hoursProp ?? 9.2;
  const scoreData = [{ value: score }, { value: 100 - score }];
  const phases = [
    { label: "Profundo", hours: Math.round(totalHoras * 0.20 * 10) / 10, color: "#6366F1", pct: 20 },
    { label: "REM", hours: Math.round(totalHoras * 0.23 * 10) / 10, color: "#A855F7", pct: 23 },
    { label: "Ligero", hours: Math.round(totalHoras * 0.57 * 10) / 10, color: "#00D4FF", pct: 57 },
  ];

  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-4"
      style={{ background: "rgba(22,27,34,0.9)", border: "1px solid rgba(168,85,247,0.25)" }}
    >
      <div className="flex items-center gap-2">
        <Moon className="h-4 w-4 text-purple-400" />
        <span className="text-xs font-bold text-[#8B949E] uppercase tracking-widest">Sueño Anoche</span>
      </div>

      <div className="flex items-center gap-4">
        {/* Donut */}
        <div className="relative shrink-0" style={{ width: 120, height: 120 }}>
          <PieChart width={120} height={120}>
            <Pie
              data={scoreData}
              cx={55}
              cy={55}
              startAngle={90}
              endAngle={-270}
              innerRadius={42}
              outerRadius={56}
              dataKey="value"
              strokeWidth={0}
            >
              <Cell fill="#A855F7" />
              <Cell fill="rgba(48,54,61,0.6)" />
            </Pie>
          </PieChart>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-2xl font-black text-white leading-none">{score}</span>
            <span className="text-[10px] text-[#8B949E]">/100</span>
          </div>
        </div>

        {/* Right stats */}
        <div className="flex flex-col gap-1.5 flex-1">
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-black text-white">{totalHoras}</span>
            <span className="text-xs text-[#8B949E]">h totales</span>
          </div>
          {phases.map((p) => (
            <div key={p.label} className="flex items-center gap-2">
              <span className="text-[10px] text-[#8B949E] w-14 shrink-0">{p.label}</span>
              <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(48,54,61,0.6)" }}>
                <div className="h-full rounded-full" style={{ width: `${p.pct}%`, background: p.color }} />
              </div>
              <span className="text-[10px] font-bold w-8 text-right" style={{ color: p.color }}>
                {p.hours}h
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Readiness HRV Card
function ReadinessCard({ hrv: hrvProp }: { hrv?: number | null } = {}) {
  const hrv = hrvProp ?? 73;
  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-3"
      style={{ background: "rgba(22,27,34,0.9)", border: "1px solid rgba(34,197,94,0.25)" }}
    >
      <div className="flex items-center gap-2">
        <Brain className="h-4 w-4 text-green-400" />
        <span className="text-xs font-bold text-[#8B949E] uppercase tracking-widest">Readiness</span>
      </div>

      <div className="flex flex-col items-center justify-center py-2 gap-2">
        {/* Ring */}
        <div className="relative" style={{ width: 110, height: 110 }}>
          <PieChart width={110} height={110}>
            <Pie
              data={[{ value: hrv }, { value: Math.max(0, 150 - hrv) }]}
              cx={50}
              cy={50}
              startAngle={90}
              endAngle={-270}
              innerRadius={38}
              outerRadius={50}
              dataKey="value"
              strokeWidth={0}
            >
              <Cell fill="#22C55E" />
              <Cell fill="rgba(48,54,61,0.6)" />
            </Pie>
          </PieChart>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-xl font-black text-white leading-none">{hrv}</span>
            <span className="text-[10px] text-[#8B949E]">ms</span>
          </div>
        </div>
        <div className="text-center">
          <p className="text-xs font-bold text-green-400">HRV</p>
          <div
            className="mt-1 px-3 py-1 rounded-full text-xs font-bold"
            style={{ background: "rgba(34,197,94,0.15)", border: "1px solid rgba(34,197,94,0.4)", color: "#22C55E" }}
          >
            ✓ Lista para entrenar
          </div>
        </div>
      </div>
    </div>
  );
}

// Stress & Battery Card
function StressBatteryCard({ stress: stressProp, battery: batteryProp, fcReposo: fcRepProp }: { stress?: number | null; battery?: number | null; fcReposo?: number | null } = {}) {
  const stress = stressProp ?? 20;
  const battery = batteryProp ?? 75;
  const fcReposo = fcRepProp ?? 48;
  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-4"
      style={{ background: "rgba(22,27,34,0.9)", border: "1px solid rgba(249,115,22,0.2)" }}
    >
      <div className="flex items-center gap-2">
        <Zap className="h-4 w-4 text-orange-400" />
        <span className="text-xs font-bold text-[#8B949E] uppercase tracking-widest">Estrés & Energía</span>
      </div>

      {/* Stress */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <Wind className="h-3.5 w-3.5 text-green-400" />
            <span className="text-xs text-[#8B949E]">Score de Estrés</span>
          </div>
          <span className="text-sm font-bold text-green-400">{stress}/100</span>
        </div>
        <div className="h-2.5 rounded-full overflow-hidden" style={{ background: "rgba(48,54,61,0.7)" }}>
          <div
            className="h-full rounded-full"
            style={{ width: `${stress}%`, background: "linear-gradient(90deg, #22C55E, #86EFAC)" }}
          />
        </div>
        <p className="text-[10px] text-green-400 mt-1">Muy bajo · Óptimo</p>
      </div>

      {/* Body Battery */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <BatteryMedium className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-xs text-[#8B949E]">Body Battery</span>
          </div>
          <span className="text-sm font-bold text-cyan-400">{battery}/100</span>
        </div>
        <div className="h-2.5 rounded-full overflow-hidden" style={{ background: "rgba(48,54,61,0.7)" }}>
          <div
            className="h-full rounded-full"
            style={{ width: `${battery}%`, background: "linear-gradient(90deg, #00D4FF, #0EA5E9)" }}
          />
        </div>
        <p className="text-[10px] text-cyan-400 mt-1">Cargada · Buena recuperación</p>
      </div>

      {/* FC Reposo */}
      <div className="flex items-center justify-between rounded-xl px-3 py-2.5" style={{ background: "rgba(244,63,94,0.08)", border: "1px solid rgba(244,63,94,0.2)" }}>
        <div className="flex items-center gap-2">
          <Heart className="h-3.5 w-3.5 text-pink-400" />
          <span className="text-xs text-[#8B949E]">FC Reposo</span>
        </div>
        <span className="text-sm font-bold text-pink-400">{fcReposo} bpm</span>
      </div>
    </div>
  );
}

function buildSevenDayMetrics(data?: DashboardData | null) {
  const km = data?.semana_actual?.km_realizados ?? 42.5;
  const fuerza = data?.semana_actual?.sesiones_fuerza ?? 3;
  const hrv = data?.hrv_data?.[0]?.hrv_ms ?? 73;
  const sleep = data?.sleep_data?.length
    ? data.sleep_data.reduce((s, d) => s + (d.score ?? 0), 0) / data.sleep_data.length
    : 7.8;
  const fcReposo = data?.hrv_data?.[0]?.fc_reposo ?? 48;
  return [
    { label: "KM TOTALES", value: km.toFixed(1), unit: "km", color: "#00D4FF", bg: "rgba(0,212,255,0.08)", border: "rgba(0,212,255,0.2)", icon: Footprints, delta: "—", up: null },
    { label: "SESIONES FUERZA", value: String(fuerza), unit: "sesiones", color: "#A855F7", bg: "rgba(168,85,247,0.08)", border: "rgba(168,85,247,0.2)", icon: Dumbbell, delta: "=", up: null },
    { label: "SLEEP SCORE", value: Math.round(sleep).toString(), unit: "/100", color: "#6366F1", bg: "rgba(99,102,241,0.08)", border: "rgba(99,102,241,0.2)", icon: Moon, delta: "—", up: null },
    { label: "SCORE ESTRÉS", value: "—", unit: "/100", color: "#22C55E", bg: "rgba(34,197,94,0.08)", border: "rgba(34,197,94,0.2)", icon: Wind, delta: "—", up: null },
    { label: "CADENCIA MEDIA", value: "—", unit: "spm", color: "#C9FF00", bg: "rgba(201,255,0,0.08)", border: "rgba(201,255,0,0.2)", icon: Activity, delta: "—", up: null },
    { label: "HRV", value: hrv ? Math.round(hrv).toString() : "—", unit: "ms", color: "#F43F5E", bg: "rgba(244,63,94,0.08)", border: "rgba(244,63,94,0.2)", icon: Brain, delta: "—", up: null },
    { label: "FC REPOSO", value: fcReposo ? String(fcReposo) : "—", unit: "bpm", color: "#F97316", bg: "rgba(249,115,22,0.08)", border: "rgba(249,115,22,0.2)", icon: Heart, delta: "—", up: null },
  ];
}

// Checkpoints data
const checkpoints = [
  {
    distance: "5K",
    targetTime: "Sub 22:30",
    bestMark: "21:45",
    description: "Velocidad máxima necesaria",
    status: "completed" as const,
    improvement: "45s mejor",
  },
  {
    distance: "10K",
    targetTime: "Sub 46:30",
    bestMark: "47:12",
    description: "Umbral y capacidad de sostener ritmo",
    status: "pending" as const,
    toImprove: "42s por mejorar",
  },
  {
    distance: "Media Maratón",
    targetTime: "Sub 1h42",
    bestMark: "1:45:30",
    description: "Checkpoint definitivo para el ritmo de maratón",
    status: "pending" as const,
    toImprove: "3'30\" por mejorar",
  },
];

// ── Main Component ─────────────────────────────────────────────────────────────

export function Home() {
  const { userId, userName } = useUser();
  const [dashData, setDashData] = useState<DashboardData | null>(null);

  useEffect(() => {
    if (userId) {
      getDashboard(userId).then(setDashData).catch(() => null);
    }
  }, [userId]);

  const sevenDayMetrics = buildSevenDayMetrics(dashData);
  const latestHrv = dashData?.hrv_data?.[0];
  const latestSleep = dashData?.sleep_data?.[dashData.sleep_data.length - 1];
  const fase = dashData?.fase_macrociclo?.nombre ?? "Acondicionamiento";
  const objetivo = dashData?.perfil?.objetivo ?? "Maratón de Sevilla";
  const fechaObj = dashData?.perfil?.fecha_objetivo ?? "2027-02-21";
  const runTrend = dashData?.running_trend?.length ? dashData.running_trend : runningProgressData;

  const completedCheckpoints = checkpoints.filter((c) => c.status === "completed").length;
  const progressPercentage = (completedCheckpoints / checkpoints.length) * 100;

  // Countdown to race date from perfil
  const raceDate = new Date(fechaObj);
  const today = new Date();
  const daysLeft = Math.ceil((raceDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  const weeksLeft = Math.ceil(daysLeft / 7);

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-4 py-8 space-y-10">

        {/* ── Hero ──────────────────────────────────────────────────────────── */}
        <section
          className="relative rounded-2xl p-8 overflow-hidden"
          style={{
            background: "linear-gradient(135deg, rgba(201,255,0,0.06) 0%, rgba(0,212,255,0.05) 40%, rgba(168,85,247,0.07) 100%)",
            border: "1px solid rgba(201,255,0,0.15)",
          }}
        >
          <div className="absolute -top-16 -right-16 w-64 h-64 rounded-full opacity-10 blur-3xl pointer-events-none" style={{ background: "radial-gradient(circle, #C9FF00, transparent)" }} />
          <div className="absolute -bottom-16 -left-16 w-48 h-48 rounded-full opacity-8 blur-3xl pointer-events-none" style={{ background: "radial-gradient(circle, #00D4FF, transparent)" }} />

          <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div>
              <h1 className="text-4xl font-bold text-white mb-1">
                {getGreeting()},{" "}
                <span style={{ background: "linear-gradient(90deg, #C9FF00, #00D4FF)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                  {userName}
                </span>{" "}
                👋
              </h1>
              <p className="text-[#8B949E] text-sm mb-4">{getCurrentDate()}</p>

              <div className="flex flex-wrap items-center gap-2">
                {/* Fase de entrenamiento */}
                <Badge className="bg-cyan-500/20 text-cyan-300 border-cyan-500/30">
                  ⚡ {fase}
                </Badge>
                {/* Fase del ciclo */}
                {userId === 1 && (
                  <Badge className="bg-pink-500/20 text-pink-300 border-pink-500/30">
                    🌸 Fase Folicular · Día 8
                  </Badge>
                )}
                <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/30">
                  🗓 Semana 10 de entrenamiento
                </Badge>
              </div>
            </div>

            {/* Objetivo Principal — Maratón de Sevilla */}
            <div
              className="flex flex-col items-center justify-center rounded-2xl px-8 py-5 shrink-0 relative overflow-hidden"
              style={{
                background: "linear-gradient(135deg, rgba(201,255,0,0.12), rgba(0,212,255,0.08))",
                border: "1px solid rgba(201,255,0,0.35)",
                boxShadow: "0 0 30px rgba(201,255,0,0.1)",
              }}
            >
              <div className="flex items-center gap-2 mb-1">
                <MapPin className="h-3.5 w-3.5 text-[#C9FF00]" />
                <p className="text-[10px] text-[#8B949E] uppercase tracking-wider font-bold">Objetivo Principal</p>
              </div>
              <p className="text-base font-bold text-white mb-2">🏆 {objetivo}</p>
              <div className="flex items-center gap-4">
                <div className="text-center">
                  <p
                    className="text-3xl font-black"
                    style={{ background: "linear-gradient(90deg, #C9FF00, #00D4FF)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}
                  >
                    {daysLeft}
                  </p>
                  <p className="text-[10px] text-[#8B949E]">días</p>
                </div>
                <div className="w-px h-8" style={{ background: "rgba(255,255,255,0.1)" }} />
                <div className="text-center">
                  <p className="text-3xl font-black text-white">{weeksLeft}</p>
                  <p className="text-[10px] text-[#8B949E]">semanas</p>
                </div>
              </div>
              <p className="text-[10px] text-[#8B949E] mt-2">22 Feb · 2027</p>
            </div>
          </div>
        </section>

        {/* ── Análisis de Hoy ───────────────────────────────────────────────── */}
        <section>
          <SectionTitle
            icon={<Zap className="h-4 w-4 text-[#C9FF00]" />}
            title="Análisis de Hoy"
            color="#C9FF00"
          />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <SleepAnalysis score={latestSleep?.score} hours={latestSleep?.horas_totales} />
            <ReadinessCard hrv={latestHrv?.hrv_ms} />
            <StressBatteryCard stress={latestHrv?.estres_medio} battery={latestHrv?.body_battery} fcReposo={latestHrv?.fc_reposo} />
          </div>
        </section>

        {/* ── Métricas últimos 7 días ───────────────────────────────────────── */}
        <section>
          <SectionTitle
            icon={<Activity className="h-4 w-4 text-[#00D4FF]" />}
            title="Métricas — Últimos 7 Días"
            color="#00D4FF"
          />
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            {sevenDayMetrics.map((m) => {
              const Icon = m.icon;
              return (
                <div
                  key={m.label}
                  className="rounded-xl p-3 flex flex-col gap-2 hover:scale-105 transition-transform cursor-default"
                  style={{ background: m.bg, border: `1px solid ${m.border}` }}
                >
                  <div className="flex items-center justify-between">
                    <Icon className="h-3.5 w-3.5" style={{ color: m.color }} />
                    {m.delta !== "=" ? (
                      <div className="flex items-center gap-0.5">
                        {m.up === true ? (
                          <TrendingUp className="h-2.5 w-2.5 text-green-400" />
                        ) : m.up === false ? (
                          <TrendingDown className="h-2.5 w-2.5 text-red-400" />
                        ) : (
                          <Minus className="h-2.5 w-2.5 text-[#8B949E]" />
                        )}
                        <span className="text-[9px]" style={{ color: m.up === true ? "#22C55E" : m.up === false ? "#F43F5E" : "#8B949E" }}>
                          {m.delta}
                        </span>
                      </div>
                    ) : (
                      <Minus className="h-2.5 w-2.5 text-[#8B949E]" />
                    )}
                  </div>
                  <div>
                    <p className="text-lg font-black text-white leading-none">{m.value}</p>
                    <p className="text-[9px] mt-0.5" style={{ color: m.color }}>{m.unit}</p>
                  </div>
                  <p className="text-[9px] text-[#8B949E] uppercase tracking-wide leading-tight">{m.label}</p>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── Macrociclo ────────────────────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<TrendingUp className="h-4 w-4 text-cyan-400" />} title="Macrociclo — Maratón Sevilla · Feb 2027" color="#00D4FF" />
          <MacrocicloCard title="Progreso Global del Macrociclo" phases={macrocicloPhases} globalProgress={globalMacrocicloProgress} />
        </section>

        {/* ── Checkpoints de Rendimiento ────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<Target className="h-4 w-4 text-[#C9FF00]" />} title="Checkpoints de Rendimiento" color="#C9FF00" />

          {/* Progress bar */}
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
                <span className="font-bold">{checkpoints.length}</span> checkpoints completados
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

          {/* Checkpoint Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {checkpoints.map((cp, i) => (
              <div
                key={i}
                className="rounded-2xl p-5 flex flex-col gap-3 relative overflow-hidden"
                style={{
                  background: cp.status === "completed"
                    ? "linear-gradient(135deg, rgba(34,197,94,0.12), rgba(201,255,0,0.06))"
                    : "rgba(22,27,34,0.9)",
                  border: cp.status === "completed"
                    ? "1px solid rgba(34,197,94,0.35)"
                    : "1px solid rgba(48,54,61,0.6)",
                  boxShadow: cp.status === "completed" ? "0 0 20px rgba(34,197,94,0.08)" : "none",
                }}
              >
                {cp.status === "completed" && (
                  <div className="absolute top-3 right-3">
                    <CheckCircle2 className="h-5 w-5 text-green-400" />
                  </div>
                )}
                <div>
                  <p className="text-2xl font-black text-white">{cp.distance}</p>
                  <p className="text-xs text-[#8B949E] mt-0.5">{cp.description}</p>
                </div>

                {/* Target */}
                <div className="rounded-xl px-3 py-2" style={{ background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.2)" }}>
                  <p className="text-[10px] text-[#8B949E] uppercase tracking-wide mb-0.5">Objetivo</p>
                  <p className="text-sm font-bold text-cyan-300">{cp.targetTime}</p>
                </div>

                {/* Best mark */}
                <div
                  className="rounded-xl px-3 py-2"
                  style={{
                    background: cp.status === "completed" ? "rgba(34,197,94,0.08)" : "rgba(255,255,255,0.03)",
                    border: cp.status === "completed" ? "1px solid rgba(34,197,94,0.3)" : "1px solid rgba(255,255,255,0.06)",
                  }}
                >
                  <p className="text-[10px] text-[#8B949E] uppercase tracking-wide mb-0.5">Mejor Marca</p>
                  <p className="text-sm font-bold" style={{ color: cp.status === "completed" ? "#22C55E" : "#C9FF00" }}>
                    {cp.bestMark}
                  </p>
                  {cp.status === "completed" && cp.improvement && (
                    <p className="text-[10px] text-green-400 mt-0.5">✓ {cp.improvement}</p>
                  )}
                  {cp.status === "pending" && cp.toImprove && (
                    <p className="text-[10px] text-orange-400 mt-0.5">⬆ {cp.toImprove}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── Ciclo para Malena ─────────────────────────────────────────────── */}
        {userId === 1 && (
          <section>
            <div
              className="rounded-2xl p-6 relative overflow-hidden"
              style={{
                background: "linear-gradient(135deg, rgba(168,85,247,0.1), rgba(244,63,94,0.07))",
                border: "1px solid rgba(168,85,247,0.25)",
              }}
            >
              <div className="absolute -right-8 -top-8 w-36 h-36 rounded-full opacity-12 blur-3xl" style={{ background: "#F43F5E" }} />
              <div className="relative">
                <h3 className="text-base font-bold text-white flex items-center gap-2 mb-4">
                  <Heart className="h-4 w-4 text-pink-400" />
                  Estado del Ciclo
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[
                    { label: "Fase Actual", value: "Folicular", sub: "Día 8 de 28", color: "#00D4FF", bg: "rgba(0,212,255,0.1)", border: "rgba(0,212,255,0.3)" },
                    { label: "Próxima Regla", value: "En 20 días", sub: "27 de Mayo", color: "#F43F5E", bg: "rgba(244,63,94,0.1)", border: "rgba(244,63,94,0.3)" },
                    { label: "Nivel Energía", value: "Alto ⚡", sub: "Óptimo para entrenar", color: "#C9FF00", bg: "rgba(201,255,0,0.08)", border: "rgba(201,255,0,0.2)" },
                  ].map((item) => (
                    <div key={item.label} className="rounded-xl p-4" style={{ background: item.bg, border: `1px solid ${item.border}` }}>
                      <p className="text-[10px] mb-1 font-bold uppercase tracking-wider" style={{ color: item.color }}>{item.label}</p>
                      <p className="text-base font-bold text-white">{item.value}</p>
                      <p className="text-xs text-[#8B949E] mt-0.5">{item.sub}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-3 rounded-xl p-3" style={{ background: "rgba(244,63,94,0.06)", border: "1px solid rgba(244,63,94,0.15)" }}>
                  <p className="text-xs text-pink-200">
                    💡 <span className="font-semibold text-pink-300">Consejo:</span> Fase folicular — ideal para alta intensidad. Aprovecha el pico de energía para series o fuerza máxima.
                  </p>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ── Progresión de Fuerza ──────────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<Dumbbell className="h-4 w-4 text-purple-400" />} title="Progresión de Fuerza — Últimas Sesiones" color="#A855F7" />
          <div
            className="rounded-2xl p-6"
            style={{
              background: "linear-gradient(135deg, rgba(168,85,247,0.08), rgba(99,102,241,0.05))",
              border: "1px solid rgba(168,85,247,0.25)"
            }}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
              {strengthProgressionData.map((exercise) => {
                const trendIcon = exercise.trend === "up" ? (
                  <ArrowUp className="h-4 w-4 text-green-400" />
                ) : exercise.trend === "down" ? (
                  <ArrowDown className="h-4 w-4 text-red-400" />
                ) : (
                  <Minus className="h-4 w-4 text-[#8B949E]" />
                );
                const trendColor = exercise.trend === "up" ? "#22C55E" : exercise.trend === "down" ? "#F43F5E" : "#8B949E";
                const diff = exercise.weight - exercise.prevWeight;

                return (
                  <div
                    key={exercise.name}
                    className="rounded-xl p-4 relative overflow-hidden group hover:scale-[1.02] transition-all cursor-default"
                    style={{
                      background: "rgba(22,27,34,0.9)",
                      border: "1px solid rgba(168,85,247,0.2)",
                      boxShadow: "0 4px 12px rgba(0,0,0,0.2)"
                    }}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h4 className="text-sm font-bold text-white mb-0.5">{exercise.name}</h4>
                        <p className="text-xs text-[#8B949E]">{exercise.volume}</p>
                      </div>
                      <div className="flex items-center gap-1" style={{ color: trendColor }}>
                        {trendIcon}
                        {exercise.trend !== "equal" && (
                          <span className="text-xs font-bold">
                            {diff > 0 ? "+" : ""}{diff.toFixed(1)}kg
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-end justify-between">
                      <div>
                        <p className="text-xs text-[#8B949E] mb-1">Carga actual</p>
                        <p className="text-2xl font-black text-purple-300">{exercise.weight}<span className="text-sm text-[#8B949E]"> kg</span></p>
                      </div>
                      {exercise.prevWeight > 0 && (
                        <div className="text-right">
                          <p className="text-[10px] text-[#8B949E]">Anterior</p>
                          <p className="text-sm font-semibold text-[#8B949E]">{exercise.prevWeight} kg</p>
                        </div>
                      )}
                    </div>

                    <div className="mt-3 h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(48,54,61,0.6)" }}>
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${exercise.prevWeight > 0 ? Math.min(100, (exercise.weight / exercise.prevWeight) * 100) : 100}%`,
                          background: exercise.trend === "up" ? "linear-gradient(90deg, #A855F7, #22C55E)" : exercise.trend === "down" ? "#F43F5E" : "#8B949E"
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <button
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all hover:opacity-90"
              style={{
                background: "rgba(168,85,247,0.15)",
                border: "1px solid rgba(168,85,247,0.35)",
                color: "#C084FC"
              }}
            >
              <ChevronDown className="h-4 w-4" />
              Ver historial completo de progresión
            </button>
          </div>
        </section>

        {/* ── Análisis de Running ───────────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<Footprints className="h-4 w-4 text-cyan-400" />} title="Análisis de Running — Zona 2, Ritmo y Progreso" color="#00D4FF" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

            {/* Evolución Ritmo Z2 */}
            <div className="rounded-2xl overflow-hidden flex flex-col" style={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.2)" }}>
              <div className="px-4 py-3 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                <h3 className="text-sm font-bold text-white">Ritmo Z2 — Evolución</h3>
                <p className="text-xs text-[#8B949E] mt-0.5">Media semanal de carreras Z2</p>
              </div>
              <div className="p-4 flex-1 flex flex-col">
                <div className="flex-1">
                  <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={z2PaceEvolution} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="semana" stroke="#8B949E" fontSize={11} />
                    <YAxis
                      stroke="#8B949E"
                      fontSize={11}
                      domain={[7.5, 10]}
                      tickFormatter={(val) => `${val.toFixed(1)}`}
                    />
                    <Tooltip
                      contentStyle={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.3)", borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: "#fff" }}
                      formatter={(value: number) => {
                        const mins = Math.floor(value);
                        const secs = Math.round((value % 1) * 60);
                        return [`${mins}:${String(secs).padStart(2, '0')}/km`, "Ritmo Z2"];
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="ritmo"
                      name="Ritmo Z2"
                      stroke="#00D4FF"
                      strokeWidth={3}
                      dot={{ fill: "#00D4FF", r: 4, strokeWidth: 2, stroke: "#0E1117" }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
                </div>
                <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[#8B949E]">Mejora total</span>
                    <span className="font-bold text-green-400">-1.4 min/km ↓</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Ritmo Medio por Zona FC */}
            <div className="rounded-2xl overflow-hidden flex flex-col" style={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.2)" }}>
              <div className="px-4 py-3 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                <h3 className="text-sm font-bold text-white">Ritmo por Zona FC</h3>
                <p className="text-xs text-[#8B949E] mt-0.5">Ritmo medio en cada zona</p>
              </div>
              <div className="p-4 flex-1 flex flex-col justify-between">
                <div className="space-y-2.5">
                  {paceByHRZone.map((zone) => {
                    const minPace = 4.5;
                    const maxPace = 10;
                    const normalizedWidth = ((zone.ritmo - minPace) / (maxPace - minPace)) * 100;

                    return (
                      <div key={zone.zona} className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-semibold" style={{ color: zone.color }}>{zone.zona}</span>
                          <span className="text-[11px] font-bold text-white">{Math.floor(zone.ritmo)}:{String(Math.round((zone.ritmo % 1) * 60)).padStart(2, '0')}/km</span>
                        </div>
                        <div className="h-5 rounded-full overflow-hidden" style={{ background: "rgba(48,54,61,0.6)" }}>
                          <div
                            className="h-full flex items-center justify-end pr-2"
                            style={{
                              width: `${Math.max(15, normalizedWidth)}%`,
                              background: zone.color,
                              transition: "width 0.3s ease"
                            }}
                          >
                            <span className="text-[9px] font-bold text-white/90">{zone.ritmo.toFixed(2)}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                  <div className="grid grid-cols-3 gap-1 text-center">
                    <div>
                      <p className="text-[10px] text-[#8B949E]">Mejor</p>
                      <p className="text-xs font-bold text-green-400">4:48</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-[#8B949E]">Promedio</p>
                      <p className="text-xs font-bold text-cyan-400">7:38</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-[#8B949E]">Más lento</p>
                      <p className="text-xs font-bold text-orange-400">9:41</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Progreso de Running — Últimas 8 Semanas */}
            <div className="rounded-2xl overflow-hidden flex flex-col" style={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.2)" }}>
              <div className="px-4 py-3 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                <h3 className="text-sm font-bold text-white">Progreso Running</h3>
                <p className="text-xs text-[#8B949E] mt-0.5">Últimas 8 semanas</p>
              </div>
              <div className="p-4 flex-1">
                <ResponsiveContainer width="100%" height={220}>
                  <ComposedChart data={runTrend}>
                    <defs>
                      <linearGradient id="kmGradCompact" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00D4FF" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#00D4FF" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="semana" stroke="#8B949E" fontSize={11} />
                    <YAxis stroke="#8B949E" fontSize={11} />
                    <Tooltip
                      contentStyle={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.3)", borderRadius: 8 }}
                      labelStyle={{ color: "#fff" }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Area
                      type="monotone"
                      dataKey="km"
                      name="Km Reales"
                      stroke="#00D4FF"
                      strokeWidth={2}
                      fill="url(#kmGradCompact)"
                      dot={{ fill: "#00D4FF", r: 3 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="objetivo"
                      name="Objetivo"
                      stroke="#C9FF00"
                      strokeDasharray="5 5"
                      strokeWidth={2}
                      dot={{ fill: "#C9FF00", r: 2 }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
                <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-[#8B949E]">KM totales</p>
                      <p className="font-bold text-cyan-400">293 km</p>
                    </div>
                    <div>
                      <p className="text-[#8B949E]">Cumplimiento</p>
                      <p className="font-bold text-green-400">89.6% ✓</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </section>

        {/* ── Tendencias Biométricas ────────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<Activity className="h-4 w-4 text-green-400" />} title="Tendencias Biométricas — Últimas 8 Semanas" color="#22C55E" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

            {/* HRV Trend */}
            <div className="rounded-2xl overflow-hidden" style={{ background: "#161B22", border: "1px solid rgba(34,197,94,0.2)" }}>
              <div className="px-4 py-3 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                <h3 className="text-sm font-bold text-white">HRV — Variabilidad FC</h3>
                <p className="text-xs text-[#8B949E] mt-0.5">Evolución de recuperación</p>
              </div>
              <div className="p-4">
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={hrvTrendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="semana" stroke="#8B949E" fontSize={11} />
                    <YAxis stroke="#8B949E" fontSize={11} domain={[60, 75]} />
                    <Tooltip
                      contentStyle={{ background: "#161B22", border: "1px solid rgba(34,197,94,0.3)", borderRadius: 8 }}
                      labelStyle={{ color: "#fff" }}
                      formatter={(value: number) => [`${value} ms`, "HRV"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="hrv"
                      name="HRV"
                      stroke="#22C55E"
                      strokeWidth={3}
                      dot={{ fill: "#22C55E", r: 4, strokeWidth: 2, stroke: "#0E1117" }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
                <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-[#8B949E]">Actual</p>
                      <p className="font-bold text-green-400">73 ms</p>
                    </div>
                    <div>
                      <p className="text-[#8B949E]">Mejora</p>
                      <p className="font-bold text-green-400">+8 ms ↑</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Cadencia Trend */}
            <div className="rounded-2xl overflow-hidden" style={{ background: "#161B22", border: "1px solid rgba(201,255,0,0.2)" }}>
              <div className="px-4 py-3 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                <h3 className="text-sm font-bold text-white">Cadencia Media</h3>
                <p className="text-xs text-[#8B949E] mt-0.5">Pasos por minuto (spm)</p>
              </div>
              <div className="p-4">
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={cadenceTrendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="semana" stroke="#8B949E" fontSize={11} />
                    <YAxis stroke="#8B949E" fontSize={11} domain={[165, 180]} />
                    <Tooltip
                      contentStyle={{ background: "#161B22", border: "1px solid rgba(201,255,0,0.3)", borderRadius: 8 }}
                      labelStyle={{ color: "#fff" }}
                      formatter={(value: number) => [`${value} spm`, "Cadencia"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="cadencia"
                      name="Cadencia"
                      stroke="#C9FF00"
                      strokeWidth={3}
                      dot={{ fill: "#C9FF00", r: 4, strokeWidth: 2, stroke: "#0E1117" }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
                <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-[#8B949E]">Actual</p>
                      <p className="font-bold text-[#C9FF00]">175 spm</p>
                    </div>
                    <div>
                      <p className="text-[#8B949E]">Mejora</p>
                      <p className="font-bold text-green-400">+5 spm ↑</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* FC Reposo Trend */}
            <div className="rounded-2xl overflow-hidden" style={{ background: "#161B22", border: "1px solid rgba(244,63,94,0.2)" }}>
              <div className="px-4 py-3 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                <h3 className="text-sm font-bold text-white">FC en Reposo</h3>
                <p className="text-xs text-[#8B949E] mt-0.5">Frecuencia cardíaca basal</p>
              </div>
              <div className="p-4">
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={restingHRTrendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="semana" stroke="#8B949E" fontSize={11} />
                    <YAxis stroke="#8B949E" fontSize={11} domain={[45, 55]} />
                    <Tooltip
                      contentStyle={{ background: "#161B22", border: "1px solid rgba(244,63,94,0.3)", borderRadius: 8 }}
                      labelStyle={{ color: "#fff" }}
                      formatter={(value: number) => [`${value} bpm`, "FC Reposo"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="fc"
                      name="FC Reposo"
                      stroke="#F43F5E"
                      strokeWidth={3}
                      dot={{ fill: "#F43F5E", r: 4, strokeWidth: 2, stroke: "#0E1117" }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
                <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-[#8B949E]">Actual</p>
                      <p className="font-bold text-pink-400">48 bpm</p>
                    </div>
                    <div>
                      <p className="text-[#8B949E]">Mejora</p>
                      <p className="font-bold text-green-400">-4 bpm ↓</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </section>

        {/* ── Sueño semanal ─────────────────────────────────────────────────── */}
        <section>
          <SectionTitle icon={<Moon className="h-4 w-4 text-purple-400" />} title="Calidad de Sueño — Esta Semana" color="#A855F7" />
          <div className="rounded-2xl overflow-hidden" style={{ background: "#161B22", border: "1px solid rgba(168,85,247,0.2)" }}>
            <div className="px-6 pt-4 pb-2">
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded" style={{ background: "linear-gradient(180deg, #A855F7, #6366F1)" }} />
                  <span className="text-[#8B949E]">Horas dormidas</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-0.5 bg-[#C9FF00] rounded-full" />
                  <span className="text-[#8B949E]">Score de calidad</span>
                </div>
              </div>
            </div>
            <div className="px-6 pb-6">
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={sleepWeekData}>
                  <defs>
                    <linearGradient id="sleepGradH" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#A855F7" stopOpacity={0.9} />
                      <stop offset="100%" stopColor="#6366F1" stopOpacity={0.6} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="dia" stroke="#8B949E" fontSize={12} />
                  <YAxis
                    yAxisId="left"
                    stroke="#8B949E"
                    fontSize={12}
                    domain={[0, 10]}
                    label={{ value: 'Horas', angle: -90, position: 'insideLeft', style: { fill: '#8B949E', fontSize: 11 } }}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    stroke="#8B949E"
                    fontSize={12}
                    domain={[0, 100]}
                    label={{ value: 'Score', angle: 90, position: 'insideRight', style: { fill: '#8B949E', fontSize: 11 } }}
                  />
                  <Tooltip
                    contentStyle={{ background: "#161B22", border: "1px solid rgba(168,85,247,0.3)", borderRadius: 8 }}
                    labelStyle={{ color: "#fff" }}
                    formatter={(value: number, name: string) => {
                      if (name === "Horas de sueño") return [`${value.toFixed(1)}h`, name];
                      return [`${value}/100`, name];
                    }}
                  />
                  <Legend />
                  <Bar
                    yAxisId="left"
                    dataKey="horas"
                    name="Horas de sueño"
                    fill="url(#sleepGradH)"
                    radius={[4, 4, 0, 0]}
                    label={{
                      position: 'top',
                      formatter: (value: number) => {
                        const hours = Math.floor(value);
                        const mins = Math.round((value % 1) * 60);
                        return `${hours}h ${mins}m`;
                      },
                      fontSize: 9,
                      fill: '#A855F7',
                      offset: 5
                    }}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="score"
                    name="Score de calidad"
                    stroke="#C9FF00"
                    strokeWidth={3}
                    dot={{ fill: "#C9FF00", r: 5, strokeWidth: 2, stroke: "#0E1117" }}
                    activeDot={{ r: 7 }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}