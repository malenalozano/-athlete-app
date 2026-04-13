import { useLocation, useNavigate } from "react-router";
import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { useUser } from "../context/UserContext";
import {
  Sparkles,
  Calendar,
  Activity,
  Dumbbell,
  Moon,
  Zap,
  ChevronRight,
  BarChart3,
  TrendingUp,
  Target,
  Clock,
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

// ── Mock data ──────────────────────────────────────────────────────────────────

const weekPlan = [
  {
    day: "LUN",
    date: "14 Abr",
    activity: "Rodaje Suave",
    type: "running",
    duration: "8 km · 45 min",
    zone: "Zona 2",
    notes: "Ritmo conversacional, RPE 5-6",
  },
  {
    day: "MAR",
    date: "15 Abr",
    activity: "Fuerza Core",
    type: "strength",
    duration: "45 min",
    zone: "—",
    notes: "Plancha, dead bug, pallof press",
  },
  {
    day: "MIÉ",
    date: "16 Abr",
    activity: "Series 400m",
    type: "running",
    duration: "6 km · 40 min",
    zone: "Zona 4-5",
    notes: "8×400m con 90s recuperación",
  },
  {
    day: "JUE",
    date: "17 Abr",
    activity: "Descanso Activo",
    type: "rest",
    duration: "20 min",
    zone: "—",
    notes: "Movilidad, estiramientos",
  },
  {
    day: "VIE",
    date: "18 Abr",
    activity: "Tempo Run",
    type: "running",
    duration: "10 km · 55 min",
    zone: "Zona 3",
    notes: "Ritmo de umbral sostenido",
  },
  {
    day: "SÁB",
    date: "19 Abr",
    activity: "Fuerza Piernas",
    type: "strength",
    duration: "60 min",
    zone: "—",
    notes: "Sentadillas, peso muerto rumano, zancadas",
  },
  {
    day: "DOM",
    date: "20 Abr",
    activity: "Tirada Larga",
    type: "running",
    duration: "18 km · 1h50",
    zone: "Zona 2",
    notes: "Pace objetivo maratón +45s/km",
  },
];

const weeksData = [
  { semana: "S1", km: 28, fuerza: 2, objetivo: 30 },
  { semana: "S2", km: 32, fuerza: 3, objetivo: 32 },
  { semana: "S3", km: 35, fuerza: 3, objetivo: 35 },
  { semana: "S4", km: 38, fuerza: 2, objetivo: 38 },
  { semana: "S5", km: 40, fuerza: 3, objetivo: 40 },
  { semana: "S6", km: 42, fuerza: 3, objetivo: 42 },
  { semana: "S7", km: 45, fuerza: 3, objetivo: 45 },
  { semana: "S8", km: 43, fuerza: 2, objetivo: 48 },
];

const TYPE_COLORS: Record<string, { border: string; bg: string; text: string; badge: string }> = {
  running: {
    border: "border-l-cyan-400",
    bg: "from-cyan-500/5 to-blue-500/5",
    text: "text-cyan-400",
    badge: "bg-cyan-400/15 text-cyan-300 border-cyan-500/30",
  },
  strength: {
    border: "border-l-purple-400",
    bg: "from-purple-500/5 to-pink-500/5",
    text: "text-purple-400",
    badge: "bg-purple-400/15 text-purple-300 border-purple-500/30",
  },
  rest: {
    border: "border-l-green-400",
    bg: "from-green-500/5 to-emerald-500/5",
    text: "text-green-400",
    badge: "bg-green-400/15 text-green-300 border-green-500/30",
  },
};

// ── Generar Plan tab ───────────────────────────────────────────────────────────

function GenerarPlan() {
  const { userId } = useUser();

  return (
    <div className="space-y-8">
      {/* Hero Banner */}
      <div
        className="rounded-2xl p-8 relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, rgba(0,212,255,0.15) 0%, rgba(34,197,94,0.08) 50%, rgba(168,85,247,0.1) 100%)",
          border: "1px solid rgba(0,212,255,0.25)",
          boxShadow: "0 0 40px rgba(0,212,255,0.08), inset 0 1px 0 rgba(0,212,255,0.15)",
        }}
      >
        <div
          className="absolute top-0 right-0 w-64 h-64 rounded-full opacity-10 blur-3xl"
          style={{ background: "radial-gradient(circle, #00D4FF, transparent)" }}
        />
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Badge className="bg-cyan-400/20 text-cyan-300 border-cyan-500/30 text-xs">
                Semana 8 · Pre-Específico
              </Badge>
              <Badge className="bg-green-400/20 text-green-300 border-green-500/30 text-xs">
                Plan Activo ✓
              </Badge>
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">
              Plan Semanal — 14 al 20 Abril
            </h2>
            <p className="text-[#8B949E] text-sm">
              62 días para el maratón · 52 km objetivo esta semana
            </p>
          </div>
          <button
            className="flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm transition-all"
            style={{
              background: "linear-gradient(135deg, #00D4FF, #0EA5E9)",
              color: "#0E1117",
              boxShadow: "0 0 20px rgba(0,212,255,0.4)",
            }}
          >
            <Sparkles className="h-4 w-4" />
            Regenerar con IA
          </button>
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "KM Semana", value: "52", icon: Activity, color: "#00D4FF", bg: "rgba(0,212,255,0.1)", border: "rgba(0,212,255,0.25)" },
          { label: "Sesiones", value: "7", icon: Calendar, color: "#C9FF00", bg: "rgba(201,255,0,0.1)", border: "rgba(201,255,0,0.25)" },
          { label: "Fuerza", value: "2", icon: Dumbbell, color: "#A855F7", bg: "rgba(168,85,247,0.1)", border: "rgba(168,85,247,0.25)" },
          { label: "Carga", value: "Alta", icon: Zap, color: "#F97316", bg: "rgba(249,115,22,0.1)", border: "rgba(249,115,22,0.25)" },
        ].map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-xl p-4"
            style={{ background: kpi.bg, border: `1px solid ${kpi.border}` }}
          >
            <div className="flex items-center gap-2 mb-2">
              <kpi.icon className="h-4 w-4" style={{ color: kpi.color }} />
              <span className="text-xs text-[#8B949E] font-medium">{kpi.label}</span>
            </div>
            <p className="text-2xl font-bold text-white">{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Week Grid */}
      <div>
        <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <Calendar className="h-4 w-4 text-cyan-400" />
          Distribución Semanal
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-7 gap-3">
          {weekPlan.map((day) => {
            const colors = TYPE_COLORS[day.type] ?? TYPE_COLORS.rest;
            return (
              <Card
                key={day.day}
                className={`border-l-4 ${colors.border} bg-gradient-to-br ${colors.bg} rounded-xl transition-all hover:scale-[1.02] cursor-pointer group`}
                style={{ background: "rgba(22,27,34,0.8)", borderRight: "1px solid rgba(255,255,255,0.05)", borderTop: "1px solid rgba(255,255,255,0.05)", borderBottom: "1px solid rgba(255,255,255,0.05)" }}
              >
                <CardContent className="p-4">
                  <p className="text-[10px] text-[#8B949E] font-bold mb-1">{day.day}</p>
                  <p className="text-xs text-white font-semibold mb-2">{day.date}</p>
                  <p className={`text-xs font-bold mb-1 ${colors.text}`}>{day.activity}</p>
                  <p className="text-[10px] text-[#8B949E] mb-2">{day.duration}</p>
                  {day.zone !== "—" && (
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${colors.badge}`}>
                      {day.zone}
                    </span>
                  )}
                  <p className="text-[10px] text-[#8B949E] mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    {day.notes}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* AI Suggestions */}
      <Card
        className="rounded-2xl"
        style={{
          background: "linear-gradient(135deg, rgba(168,85,247,0.1), rgba(0,212,255,0.05))",
          border: "1px solid rgba(168,85,247,0.25)",
        }}
      >
        <CardHeader>
          <CardTitle className="text-white text-base flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-purple-400" />
            Recomendaciones IA para esta semana
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {[
            { icon: "🚀", title: "Semana de carga alta", desc: "Asegúrate de dormir 8h mínimo y aumentar proteínas a 1.8g/kg.", color: "text-cyan-300" },
            { icon: "💜", title: "Técnica de zancada", desc: "Incluye 4×100m de \"strides\" al final del rodaje del lunes.", color: "text-purple-300" },
            { icon: "⚡", title: "Activación pre-largo", desc: "El domingo, realiza 10 min de movilidad dinámica antes de salir.", color: "text-[#C9FF00]" },
          ].map((tip, i) => (
            <div
              key={i}
              className="flex items-start gap-3 p-3 rounded-xl"
              style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)" }}
            >
              <span className="text-xl">{tip.icon}</span>
              <div>
                <p className={`text-sm font-semibold ${tip.color}`}>{tip.title}</p>
                <p className="text-xs text-[#8B949E] mt-0.5">{tip.desc}</p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Datos tab ─────────────────────────────────────────────────────────────────

function Datos() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div
        className="rounded-2xl p-6"
        style={{
          background: "linear-gradient(135deg, rgba(201,255,0,0.08), rgba(0,212,255,0.05))",
          border: "1px solid rgba(201,255,0,0.2)",
        }}
      >
        <h2 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-[#C9FF00]" />
          Progresión de Entrenamiento
        </h2>
        <p className="text-[#8B949E] text-sm">Últimas 8 semanas de datos reales vs objetivo</p>
      </div>

      {/* Main chart */}
      <Card
        className="rounded-2xl"
        style={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.2)" }}
      >
        <CardHeader>
          <CardTitle className="text-white text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-cyan-400" />
            Kilómetros semanales
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={weeksData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="semana" stroke="#8B949E" fontSize={12} />
              <YAxis stroke="#8B949E" fontSize={12} />
              <Tooltip
                contentStyle={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.3)", borderRadius: 8 }}
                labelStyle={{ color: "#fff" }}
              />
              <Legend />
              <Bar dataKey="km" name="KM Reales" fill="#00D4FF" radius={[4, 4, 0, 0]} fillOpacity={0.85} />
              <Bar dataKey="objetivo" name="Objetivo" fill="rgba(201,255,0,0.4)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: "Total KM acumulados", value: "303 km", sub: "+5.3% vs semana anterior", color: "#00D4FF", bg: "rgba(0,212,255,0.08)", border: "rgba(0,212,255,0.2)", icon: Activity },
          { label: "Mejor semana", value: "45 km", sub: "Semana 7", color: "#C9FF00", bg: "rgba(201,255,0,0.08)", border: "rgba(201,255,0,0.2)", icon: Target },
          { label: "Consistencia", value: "87%", sub: "Sesiones completadas", color: "#A855F7", bg: "rgba(168,85,247,0.08)", border: "rgba(168,85,247,0.2)", icon: Clock },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl p-5"
            style={{ background: stat.bg, border: `1px solid ${stat.border}` }}
          >
            <div className="flex items-center gap-2 mb-3">
              <stat.icon className="h-4 w-4" style={{ color: stat.color }} />
              <p className="text-xs text-[#8B949E] font-medium">{stat.label}</p>
            </div>
            <p className="text-2xl font-bold text-white mb-1">{stat.value}</p>
            <p className="text-xs" style={{ color: stat.color }}>{stat.sub}</p>
          </div>
        ))}
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
