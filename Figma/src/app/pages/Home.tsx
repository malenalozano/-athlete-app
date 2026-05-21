// v2026-05-21d
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

const DAY_ABBR = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

function isoToDay(fecha: string) {
  return DAY_ABBR[new Date(fecha + "T12:00:00").getDay()];
}

function localIso(d: Date) {
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0"),
  ].join("-");
}

function buildSleepChartData(sleepData: DashboardData["sleep_data"]) {
  const map = new Map((sleepData ?? []).map((d) => [d.fecha, d]));
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    const iso = localIso(d);
    const entry = map.get(iso);
    return {
      dia: isoToDay(iso),
      horas: entry?.horas_totales ?? null,
      score: entry?.score ?? null,
    };
  });
}

function buildHrvChartData(hrvData: DashboardData["hrv_data"]) {
  if (!hrvData?.length) return [];
  return [...hrvData].reverse().map((d, i) => ({
    semana: isoToDay(d.fecha),
    hrv: d.hrv_ms ? Math.round(d.hrv_ms) : null,
    fc: d.fc_reposo ?? null,
  }));
}

function calcMacrocicloFases(fechaObjetivoStr: string) {
  const hoy = new Date();
  const fechaObj = new Date(fechaObjetivoStr + "T12:00:00");
  const year = fechaObj.getFullYear();
  const prevYear = year - 1;

  const mac1Start = new Date(`${prevYear}-05-01`);
  const mac1End   = new Date(`${prevYear}-08-31`);
  const mac2Start = new Date(`${prevYear}-09-01`);
  const mac2End   = new Date(`${prevYear}-11-30`);
  const mac3Start = new Date(`${prevYear}-12-01`);
  const mac3End   = new Date(`${year}-01-31`);
  const mac4Start = new Date(`${year}-02-01`);
  const mac4End   = fechaObj;

  function pct(s: Date, e: Date) {
    if (hoy < s) return 0;
    if (hoy >= e) return 100;
    return Math.round(((hoy.getTime() - s.getTime()) / (e.getTime() - s.getTime())) * 100);
  }
  function status(s: Date, e: Date): "completed" | "in-progress" | "pending" {
    if (hoy >= e) return "completed";
    if (hoy >= s) return "in-progress";
    return "pending";
  }

  const phases = [
    { name: `MAC 1 — BASE  May-Ago ${prevYear}`,       progress: pct(mac1Start, mac1End), status: status(mac1Start, mac1End), color: "green"  as const },
    { name: `MAC 2 — UMBRAL  Sep-Nov ${prevYear}`,      progress: pct(mac2Start, mac2End), status: status(mac2Start, mac2End), color: "cyan"   as const },
    { name: `MAC 3 — ESPECÍFICO  Dic ${prevYear}-Ene ${year}`, progress: pct(mac3Start, mac3End), status: status(mac3Start, mac3End), color: "blue"   as const },
    { name: `MAC 4 — TAPERING  Feb ${year}`,            progress: pct(mac4Start, mac4End), status: status(mac4Start, mac4End), color: "purple" as const },
  ];
  const globalProgress = Math.round(phases.reduce((a, p) => a + p.progress, 0) / phases.length);
  return { phases, globalProgress };
}

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

// Helper: decimal hours → "6h 15min"
function fmtHorasSueno(h: number | null | undefined): string {
  if (h == null || h <= 0) return "—";
  const hrs = Math.floor(h);
  const mins = Math.round((h - hrs) * 60);
  if (mins === 0) return `${hrs}h`;
  if (hrs === 0) return `${mins}min`;
  return `${hrs}h ${mins}min`;
}

// Sleep Donut Card
function SleepAnalysis({ score: scoreProp, hours: hoursProp }: { score?: number | null; hours?: number | null } = {}) {
  const score = scoreProp ?? null;
  const totalHoras = hoursProp ?? null;
  if (score === null || totalHoras === null) {
    return (
      <div className="rounded-2xl p-5 flex flex-col gap-4 items-center justify-center text-center" style={{ background: "rgba(22,27,34,0.9)", border: "1px solid rgba(168,85,247,0.25)", minHeight: 160 }}>
        <Moon className="h-8 w-8 text-[#30363D]" />
        <p className="text-xs text-[#8B949E]">Sueño anoche</p>
        <p className="text-[#30363D] text-xs">Sin datos · Sincroniza Garmin</p>
      </div>
    );
  }
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
            <span className="text-2xl font-black text-white">{fmtHorasSueno(totalHoras)}</span>
          </div>
          {phases.map((p) => (
            <div key={p.label} className="flex items-center gap-2">
              <span className="text-[10px] text-[#8B949E] w-14 shrink-0">{p.label}</span>
              <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(48,54,61,0.6)" }}>
                <div className="h-full rounded-full" style={{ width: `${p.pct}%`, background: p.color }} />
              </div>
              <span className="text-[10px] font-bold w-12 text-right" style={{ color: p.color }}>
                {fmtHorasSueno(p.hours)}
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
  const hrv = hrvProp ?? null;
  if (hrv === null) {
    return (
      <div className="rounded-2xl p-5 flex flex-col gap-4 items-center justify-center text-center" style={{ background: "rgba(22,27,34,0.9)", border: "1px solid rgba(34,197,94,0.25)", minHeight: 160 }}>
        <Brain className="h-8 w-8 text-[#30363D]" />
        <p className="text-xs text-[#8B949E]">HRV / Readiness</p>
        <p className="text-[#30363D] text-xs">Sin datos · Sincroniza Garmin</p>
      </div>
    );
  }
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
  const stress = stressProp ?? null;
  const battery = batteryProp ?? null;
  const fcReposo = fcRepProp ?? null;
  if (stress === null && battery === null && fcReposo === null) {
    return (
      <div className="rounded-2xl p-5 flex flex-col gap-4 items-center justify-center text-center" style={{ background: "rgba(22,27,34,0.9)", border: "1px solid rgba(249,115,22,0.2)", minHeight: 160 }}>
        <Zap className="h-8 w-8 text-[#30363D]" />
        <p className="text-xs text-[#8B949E]">Estrés & Energía</p>
        <p className="text-[#30363D] text-xs">Sin datos · Sincroniza Garmin</p>
      </div>
    );
  }
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
          <span className="text-sm font-bold text-green-400">{stress !== null ? `${Math.round(stress)}/100` : "—"}</span>
        </div>
        <div className="h-2.5 rounded-full overflow-hidden" style={{ background: "rgba(48,54,61,0.7)" }}>
          <div
            className="h-full rounded-full"
            style={{ width: `${stress ?? 0}%`, background: "linear-gradient(90deg, #22C55E, #86EFAC)" }}
          />
        </div>
        <p className="text-[10px] text-green-400 mt-1">{stress !== null && stress < 30 ? "Muy bajo · Óptimo" : stress !== null ? `${Math.round(stress)}/100` : "Sin datos"}</p>
      </div>

      {/* Body Battery */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <BatteryMedium className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-xs text-[#8B949E]">Body Battery</span>
          </div>
          <span className="text-sm font-bold text-cyan-400">{battery !== null ? `${battery}/100` : "—"}</span>
        </div>
        <div className="h-2.5 rounded-full overflow-hidden" style={{ background: "rgba(48,54,61,0.7)" }}>
          <div
            className="h-full rounded-full"
            style={{ width: `${battery ?? 0}%`, background: "linear-gradient(90deg, #00D4FF, #0EA5E9)" }}
          />
        </div>
        <p className="text-[10px] text-cyan-400 mt-1">{battery !== null && battery >= 75 ? "Cargada · Buena recuperación" : battery !== null ? `${battery}/100` : "Sin datos"}</p>
      </div>

      {/* FC Reposo */}
      <div className="flex items-center justify-between rounded-xl px-3 py-2.5" style={{ background: "rgba(244,63,94,0.08)", border: "1px solid rgba(244,63,94,0.2)" }}>
        <div className="flex items-center gap-2">
          <Heart className="h-3.5 w-3.5 text-pink-400" />
          <span className="text-xs text-[#8B949E]">FC Reposo</span>
        </div>
        <span className="text-sm font-bold text-pink-400">{fcReposo !== null ? `${fcReposo} bpm` : "—"}</span>
      </div>
    </div>
  );
}

function buildSevenDayMetrics(data?: DashboardData | null) {
  const hasData = data != null;
  const km = hasData ? (data.semana_actual?.km_realizados ?? 0) : null;
  const fuerza = hasData ? (data.semana_actual?.sesiones_fuerza ?? 0) : null;
  const hrv = data?.hrv_data?.[0]?.hrv_ms ?? null;
  const sleepArr = data?.sleep_data ?? [];
  const sleepAvg = sleepArr.length
    ? Math.round(sleepArr.reduce((s, d) => s + (d.score ?? 0), 0) / sleepArr.length)
    : null;
  const fcReposo = data?.hrv_data?.[0]?.fc_reposo ?? null;
  const estres = data?.hrv_data?.[0]?.estres_medio ?? null;
  const cadTrend = data?.cadencia_trend ?? [];
  const cadenciaVal = cadTrend.length ? cadTrend[cadTrend.length - 1].cadencia : null;
  return [
    { label: "KM TOTALES", value: km !== null ? km.toFixed(1) : "—", unit: "km", color: "#00D4FF", bg: "rgba(0,212,255,0.08)", border: "rgba(0,212,255,0.2)", icon: Footprints, delta: "—", up: null },
    { label: "SESIONES FUERZA", value: fuerza !== null ? String(fuerza) : "—", unit: "sesiones", color: "#A855F7", bg: "rgba(168,85,247,0.08)", border: "rgba(168,85,247,0.2)", icon: Dumbbell, delta: "—", up: null },
    { label: "SLEEP SCORE", value: sleepAvg !== null ? String(sleepAvg) : "—", unit: "/100", color: "#6366F1", bg: "rgba(99,102,241,0.08)", border: "rgba(99,102,241,0.2)", icon: Moon, delta: "—", up: null },
    { label: "SCORE ESTRÉS", value: estres !== null ? String(Math.round(estres)) : "—", unit: "/100", color: "#22C55E", bg: "rgba(34,197,94,0.08)", border: "rgba(34,197,94,0.2)", icon: Wind, delta: "—", up: null },
    { label: "CADENCIA MEDIA", value: cadenciaVal !== null ? String(cadenciaVal) : "—", unit: "spm", color: "#C9FF00", bg: "rgba(201,255,0,0.08)", border: "rgba(201,255,0,0.2)", icon: Activity, delta: "—", up: null },
    { label: "HRV", value: hrv !== null ? Math.round(hrv).toString() : "—", unit: "ms", color: "#F43F5E", bg: "rgba(244,63,94,0.08)", border: "rgba(244,63,94,0.2)", icon: Brain, delta: "—", up: null },
    { label: "FC REPOSO", value: fcReposo !== null ? String(fcReposo) : "—", unit: "bpm", color: "#F97316", bg: "rgba(249,115,22,0.08)", border: "rgba(249,115,22,0.2)", icon: Heart, delta: "—", up: null },
  ];
}

// Checkpoints: objetivos reales del plan, sin marcas hardcodeadas
const CHECKPOINTS_DEF = [
  { distance: "5K",           targetTime: "Sub 22:30", description: "Velocidad máxima necesaria (ritmo 4:30/km)" },
  { distance: "10K",          targetTime: "Sub 46:30", description: "Umbral y capacidad de sostener ritmo (4:39/km)" },
  { distance: "Media Maratón",targetTime: "Sub 1h42",  description: "Checkpoint definitivo para el ritmo de maratón" },
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
  const todayIso = new Date().toISOString().slice(0, 10);
  const yesterdayIso = (() => { const d = new Date(); d.setDate(d.getDate() - 1); return d.toISOString().slice(0, 10); })();
  const mostRecentHrv = dashData?.hrv_data?.[0] ?? null;
  const latestHrv = dashData?.hrv_data?.find(h => h.fecha === yesterdayIso) ?? null;
  const todayHrv = dashData?.hrv_data?.find(h => h.fecha === todayIso) ?? null;
  const latestSleep = dashData?.sleep_data?.find(s => s.fecha === yesterdayIso) ?? null;
  const fase = dashData?.fase_macrociclo?.nombre ?? "Acondicionamiento";
  const objetivo = dashData?.perfil?.objetivo ?? "Maratón de Sevilla";
  const fechaObj = dashData?.perfil?.fecha_objetivo ?? "2027-02-21";
  const runTrend = dashData?.running_trend?.length ? dashData.running_trend : [];
  const ritmoTrend = dashData?.ritmo_trend ?? [];
  const sleepChartData = buildSleepChartData(dashData?.sleep_data ?? []);
  const bioChartData = buildHrvChartData(dashData?.hrv_data ?? []);
  const cadenciaTrend = dashData?.cadencia_trend ?? [];
  const fuerzaData = dashData?.fuerza_reciente ?? [];
  const actRecientes = dashData?.actividades_recientes ?? [];

  // Semana de entrenamiento calculada desde fecha_inicio
  const semanaNum = (() => {
    const inicio = dashData?.perfil?.fecha_inicio_entrenamiento;
    if (!inicio) return null;
    const diff = new Date().getTime() - new Date(inicio).getTime();
    return Math.max(1, Math.ceil(diff / (7 * 24 * 60 * 60 * 1000)));
  })();

  // Fecha objetivo formateada
  const fechaObjFmt = (() => {
    if (!fechaObj) return null;
    const d = new Date(fechaObj + "T12:00:00");
    const months = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
    return `${d.getDate()} ${months[d.getMonth()]} · ${d.getFullYear()}`;
  })();

  // Macrociclo calculado dinámicamente
  const { phases: macrocicloPhases, globalProgress: globalMacrocicloProgress } = calcMacrocicloFases(fechaObj);

  // Checkpoints: best marks from Garmin activities (best pace × distance estimate)
  type CheckpointStatus = "completed" | "pending";
  const checkpoints = CHECKPOINTS_DEF.map((cp) => {
    const distTarget = cp.distance === "5K" ? 5000 : cp.distance === "10K" ? 10000 : 21097;
    const bestAct = (dashData?.actividades_recientes ?? [])
      .filter((a) => a.tipo_deporte?.includes("running") || a.tipo_deporte?.includes("correr"))
      .filter((a) => (a.distancia_m ?? 0) >= distTarget * 0.9)
      .sort((a, b) => (a.ritmo_medio ?? 9999) - (b.ritmo_medio ?? 9999))[0];
    const bestSec = bestAct ? (bestAct.ritmo_medio ?? 0) * (distTarget / 1000) * 60 : null;
    const fmtTime = (sec: number) => {
      const h = Math.floor(sec / 3600);
      const m = Math.floor((sec % 3600) / 60);
      const s = Math.round(sec % 60);
      return h > 0 ? `${h}h${String(m).padStart(2,"0")}` : `${m}:${String(s).padStart(2,"0")}`;
    };
    // Target seconds
    const targetMap: Record<string, number> = { "5K": 22*60+30, "10K": 46*60+30, "Media Maratón": 102*60 };
    const targetSec = targetMap[cp.distance];
    const status: CheckpointStatus = (bestSec !== null && bestSec < targetSec) ? "completed" : "pending";
    return { ...cp, bestMark: bestSec ? fmtTime(bestSec) : null, status, bestSec, targetSec };
  });
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
                <Badge className="bg-cyan-500/20 text-cyan-300 border-cyan-500/30">
                  ⚡ {fase}
                </Badge>
                {semanaNum !== null && (
                  <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/30">
                    🗓 Semana {semanaNum} de entrenamiento
                  </Badge>
                )}
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
              {fechaObjFmt && <p className="text-[10px] text-[#8B949E] mt-2">{fechaObjFmt}</p>}
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
            <StressBatteryCard stress={(todayHrv ?? latestHrv)?.estres_medio} battery={(todayHrv ?? latestHrv)?.body_battery} fcReposo={(todayHrv ?? latestHrv)?.fc_reposo} />
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
          <SectionTitle icon={<TrendingUp className="h-4 w-4 text-cyan-400" />} title={`Macrociclo — ${objetivo}${fechaObjFmt ? ` · ${fechaObjFmt}` : ""}`} color="#00D4FF" />
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
            {checkpoints.map((cp, i) => {
              const achieved = cp.status === "completed";
              const hasMark = cp.bestMark !== null;
              const diff = hasMark && cp.bestSec != null
                ? Math.abs(cp.targetSec - cp.bestSec)
                : null;
              const diffFmt = diff !== null
                ? `${Math.floor(diff / 60)}'${String(Math.round(diff % 60)).padStart(2,"0")}"`
                : null;
              return (
                <div
                  key={i}
                  className="rounded-2xl p-5 flex flex-col gap-3 relative overflow-hidden"
                  style={{
                    background: achieved
                      ? "linear-gradient(135deg, rgba(34,197,94,0.12), rgba(201,255,0,0.06))"
                      : "rgba(22,27,34,0.9)",
                    border: achieved ? "1px solid rgba(34,197,94,0.35)" : "1px solid rgba(48,54,61,0.6)",
                    boxShadow: achieved ? "0 0 20px rgba(34,197,94,0.08)" : "none",
                  }}
                >
                  {achieved && (
                    <div className="absolute top-3 right-3">
                      <CheckCircle2 className="h-5 w-5 text-green-400" />
                    </div>
                  )}
                  <div>
                    <p className="text-2xl font-black text-white">{cp.distance}</p>
                    <p className="text-xs text-[#8B949E] mt-0.5">{cp.description}</p>
                  </div>

                  <div className="rounded-xl px-3 py-2" style={{ background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.2)" }}>
                    <p className="text-[10px] text-[#8B949E] uppercase tracking-wide mb-0.5">Objetivo</p>
                    <p className="text-sm font-bold text-cyan-300">{cp.targetTime}</p>
                  </div>

                  <div
                    className="rounded-xl px-3 py-2"
                    style={{
                      background: achieved ? "rgba(34,197,94,0.08)" : "rgba(255,255,255,0.03)",
                      border: achieved ? "1px solid rgba(34,197,94,0.3)" : "1px solid rgba(255,255,255,0.06)",
                    }}
                  >
                    <p className="text-[10px] text-[#8B949E] uppercase tracking-wide mb-0.5">Mejor Marca</p>
                    {hasMark ? (
                      <>
                        <p className="text-sm font-bold" style={{ color: achieved ? "#22C55E" : "#C9FF00" }}>
                          {cp.bestMark}
                        </p>
                        {achieved && diffFmt && <p className="text-[10px] text-green-400 mt-0.5">✓ {diffFmt} mejor que el objetivo</p>}
                        {!achieved && diffFmt && <p className="text-[10px] text-orange-400 mt-0.5">↑ {diffFmt} por mejorar</p>}
                      </>
                    ) : (
                      <p className="text-xs text-[#8B949E] italic">Sin marca — sincroniza Garmin</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── Ciclo para Malena ─────────────────────────────────────────────── */}
        {userId === 1 && dashData?.ciclo && (
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
                    { label: "Fase Actual", value: dashData.ciclo.fase, sub: `Día ${dashData.ciclo.dia_ciclo} de ${dashData.ciclo.duracion_ciclo}`, color: "#00D4FF", bg: "rgba(0,212,255,0.1)", border: "rgba(0,212,255,0.3)" },
                    { label: "Próxima Regla", value: `En ${dashData.ciclo.dias_para_regla} días`, sub: dashData.ciclo.proxima_fecha, color: "#F43F5E", bg: "rgba(244,63,94,0.1)", border: "rgba(244,63,94,0.3)" },
                    { label: "Nivel Energía", value: dashData.ciclo.energia.split("—")[0].trim(), sub: dashData.ciclo.energia.split("—")[1]?.trim() ?? "", color: "#C9FF00", bg: "rgba(201,255,0,0.08)", border: "rgba(201,255,0,0.2)" },
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
                    💡 <span className="font-semibold text-pink-300">Consejo:</span> {dashData.ciclo.energia}
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
              {fuerzaData.length === 0 ? (
                <div className="col-span-3 text-center py-8 text-[#8B949E] text-sm">
                  Sin datos de fuerza registrados aún. Registra una sesión en el Diario.
                </div>
              ) : fuerzaData.map((exercise, idx) => (
                <div
                  key={idx}
                  className="rounded-xl p-4 relative overflow-hidden group hover:scale-[1.02] transition-all cursor-default"
                  style={{
                    background: "rgba(22,27,34,0.9)",
                    border: "1px solid rgba(168,85,247,0.2)",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.2)"
                  }}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h4 className="text-sm font-bold text-white mb-0.5">{exercise.ejercicio}</h4>
                      <p className="text-xs text-[#8B949E]">{exercise.series}x{exercise.repeticiones}</p>
                    </div>
                  </div>
                  <div className="flex items-end justify-between">
                    <div>
                      <p className="text-xs text-[#8B949E] mb-1">Carga</p>
                      <p className="text-2xl font-black text-purple-300">
                        {exercise.peso ?? "—"}
                        {exercise.peso != null && <span className="text-sm text-[#8B949E]"> kg</span>}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
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

            {/* Ritmo medio semanal */}
            <div className="rounded-2xl overflow-hidden flex flex-col" style={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.2)" }}>
              <div className="px-4 py-3 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                <h3 className="text-sm font-bold text-white">Ritmo Medio — Evolución</h3>
                <p className="text-xs text-[#8B949E] mt-0.5">Min/km media semanal en running</p>
              </div>
              <div className="p-4 flex-1 flex flex-col">
                <div className="flex-1">
                  {ritmoTrend.length === 0 ? (
                    <div className="h-[220px] flex items-center justify-center text-[#8B949E] text-sm">Sin datos — sincroniza Garmin</div>
                  ) : (
                    <ResponsiveContainer width="100%" height={220}>
                      <LineChart data={ritmoTrend} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                        <XAxis dataKey="semana" stroke="#8B949E" fontSize={11} />
                        <YAxis stroke="#8B949E" fontSize={11} tickFormatter={(v) => `${Math.floor(v)}:${String(Math.round((v % 1) * 60)).padStart(2,"0")}`} />
                        <Tooltip
                          contentStyle={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.3)", borderRadius: 8, fontSize: 12 }}
                          labelStyle={{ color: "#fff" }}
                          formatter={(value: number) => {
                            const mins = Math.floor(value);
                            const secs = Math.round((value % 1) * 60);
                            return [`${mins}:${String(secs).padStart(2, "0")}/km`, "Ritmo"];
                          }}
                        />
                        <Line type="monotone" dataKey="ritmo" name="Ritmo" stroke="#00D4FF" strokeWidth={3}
                          dot={{ fill: "#00D4FF", r: 4, strokeWidth: 2, stroke: "#0E1117" }} activeDot={{ r: 6 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  )}
                </div>
                <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[#8B949E]">Semanas con datos</span>
                    <span className="font-bold text-cyan-400">{ritmoTrend.length}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Últimas actividades */}
            <div className="rounded-2xl overflow-hidden flex flex-col" style={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.2)" }}>
              <div className="px-4 py-3 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                <h3 className="text-sm font-bold text-white">Últimas Actividades</h3>
                <p className="text-xs text-[#8B949E] mt-0.5">Ritmo y FC de los últimos entrenos</p>
              </div>
              <div className="p-4 flex-1 flex flex-col justify-between">
                {actRecientes.length === 0 ? (
                  <div className="flex-1 flex items-center justify-center text-[#8B949E] text-sm">Sin datos — sincroniza Garmin</div>
                ) : (
                  <div className="space-y-2.5">
                    {actRecientes.slice(0, 5).map((act, i) => {
                      const km = ((act.distancia_m || 0) / 1000).toFixed(1);
                      const ritmo = act.ritmo_medio;   // decimal min/km  e.g. 5.5 = 5:30/km
                      const ritmofmt = ritmo
                        ? `${Math.floor(ritmo)}:${String(Math.round((ritmo % 1) * 60)).padStart(2, "0")}/km`
                        : "—";
                      return (
                        <div key={i} className="flex items-center justify-between py-1.5 border-b border-[#30363D]/40 last:border-0">
                          <div>
                            <p className="text-xs font-semibold text-white capitalize">{act.tipo_deporte?.replace(/_/g, " ")}</p>
                            <p className="text-[10px] text-[#8B949E]">{act.fecha} · {km} km</p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs font-bold text-cyan-400">{ritmofmt}</p>
                            {act.fc_media && <p className="text-[10px] text-pink-400">{act.fc_media} bpm</p>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
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
                      <p className="text-[#8B949E]">KM esta semana</p>
                      <p className="font-bold text-cyan-400">{dashData?.semana_actual?.km_realizados ?? "—"} km</p>
                    </div>
                    <div>
                      <p className="text-[#8B949E]">Plan semana</p>
                      <p className="font-bold text-[#C9FF00]">{dashData?.semana_actual?.km_planificados ?? "—"} km</p>
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
                {bioChartData.length === 0 ? (
                  <div className="h-[200px] flex items-center justify-center text-[#8B949E] text-sm">Sin datos — sincroniza Garmin</div>
                ) : (
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={bioChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="semana" stroke="#8B949E" fontSize={11} />
                      <YAxis stroke="#8B949E" fontSize={11} />
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
                        connectNulls
                      />
                    </LineChart>
                  </ResponsiveContainer>
                )}
                <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-[#8B949E]">Actual</p>
                      <p className="font-bold text-green-400">
                        {mostRecentHrv?.hrv_ms ? `${Math.round(mostRecentHrv.hrv_ms)} ms` : "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-[#8B949E]">Días con datos</p>
                      <p className="font-bold text-green-400">{bioChartData.filter(d => d.hrv).length}</p>
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
                {cadenciaTrend.length === 0 ? (
                  <div className="h-[200px] flex items-center justify-center text-[#8B949E] text-sm">Sin datos — sincroniza Garmin</div>
                ) : (
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={cadenciaTrend}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="semana" stroke="#8B949E" fontSize={11} />
                      <YAxis stroke="#8B949E" fontSize={11} />
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
                )}
                <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-[#8B949E]">Última semana</p>
                      <p className="font-bold text-[#C9FF00]">
                        {cadenciaTrend.length ? `${cadenciaTrend[cadenciaTrend.length - 1].cadencia} spm` : "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-[#8B949E]">Semanas</p>
                      <p className="font-bold text-green-400">{cadenciaTrend.length}</p>
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
                {bioChartData.length === 0 ? (
                  <div className="h-[200px] flex items-center justify-center text-[#8B949E] text-sm">Sin datos — sincroniza Garmin</div>
                ) : (
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={bioChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="semana" stroke="#8B949E" fontSize={11} />
                      <YAxis stroke="#8B949E" fontSize={11} />
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
                        connectNulls
                      />
                    </LineChart>
                  </ResponsiveContainer>
                )}
                <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-[#8B949E]">Actual</p>
                      <p className="font-bold text-pink-400">
                        {mostRecentHrv?.fc_reposo ? `${mostRecentHrv.fc_reposo} bpm` : "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-[#8B949E]">Días con datos</p>
                      <p className="font-bold text-green-400">{bioChartData.filter(d => d.fc).length}</p>
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
                <ComposedChart data={sleepChartData.length ? sleepChartData : []}>
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
                      if (name === "Horas de sueño") return [fmtHorasSueno(value), name];
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