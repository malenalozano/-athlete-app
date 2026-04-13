import { useLocation } from "react-router";
import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  Watch,
  RefreshCw,
  CheckCircle2,
  Clock,
  Wifi,
  Heart,
  Zap,
  Moon,
  Activity,
  TrendingUp,
  TrendingDown,
  BarChart3,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";
import { useState } from "react";

// ── Mock data ──────────────────────────────────────────────────────────────────

const garminMetrics = [
  { label: "HRV", value: "58", unit: "ms", status: "good", icon: Activity, color: "#C9FF00", bg: "rgba(201,255,0,0.1)", border: "rgba(201,255,0,0.25)" },
  { label: "Sueño", value: "7h 12m", unit: "", status: "good", icon: Moon, color: "#A855F7", bg: "rgba(168,85,247,0.1)", border: "rgba(168,85,247,0.25)" },
  { label: "FC Reposo", value: "48", unit: "bpm", status: "good", icon: Heart, color: "#F43F5E", bg: "rgba(244,63,94,0.1)", border: "rgba(244,63,94,0.25)" },
  { label: "Body Battery", value: "74", unit: "/100", status: "good", icon: Zap, color: "#00D4FF", bg: "rgba(0,212,255,0.1)", border: "rgba(0,212,255,0.25)" },
  { label: "Estrés", value: "32", unit: "/100", status: "good", icon: Activity, color: "#F97316", bg: "rgba(249,115,22,0.1)", border: "rgba(249,115,22,0.25)" },
  { label: "Score Sueño", value: "82", unit: "/100", status: "good", icon: Moon, color: "#6366F1", bg: "rgba(99,102,241,0.1)", border: "rgba(99,102,241,0.25)" },
];

const hrvData = [
  { day: "Lun", hrv: 52, sleep: 7.5 },
  { day: "Mar", hrv: 48, sleep: 6.8 },
  { day: "Mié", hrv: 61, sleep: 7.2 },
  { day: "Jue", hrv: 65, sleep: 7.8 },
  { day: "Vie", hrv: 55, sleep: 6.5 },
  { day: "Sáb", hrv: 70, sleep: 8.2 },
  { day: "Dom", hrv: 58, sleep: 7.3 },
];

const historialActividades = [
  {
    id: 1,
    fecha: "Dom 13 Abr",
    tipo: "Carrera",
    nombre: "Tirada Larga Base",
    duracion: "1:32:14",
    distancia: "15.4 km",
    pace: "6:00 /km",
    fc_media: "142 bpm",
    vo2: 48.2,
    color: "#00D4FF",
  },
  {
    id: 2,
    fecha: "Vie 11 Abr",
    tipo: "Carrera",
    nombre: "Tempo Run",
    duracion: "55:02",
    distancia: "10.2 km",
    pace: "5:24 /km",
    fc_media: "162 bpm",
    vo2: 52.1,
    color: "#00D4FF",
  },
  {
    id: 3,
    fecha: "Sáb 12 Abr",
    tipo: "Fuerza",
    nombre: "Fuerza Piernas",
    duracion: "58:30",
    distancia: "—",
    pace: "—",
    fc_media: "118 bpm",
    vo2: null,
    color: "#A855F7",
  },
  {
    id: 4,
    fecha: "Mié 9 Abr",
    tipo: "Carrera",
    nombre: "Series 400m",
    duracion: "40:15",
    distancia: "6.1 km",
    pace: "6:35 /km",
    fc_media: "172 bpm",
    vo2: 54.0,
    color: "#00D4FF",
  },
  {
    id: 5,
    fecha: "Lun 7 Abr",
    tipo: "Carrera",
    nombre: "Rodaje Suave",
    duracion: "45:44",
    distancia: "7.9 km",
    pace: "5:47 /km",
    fc_media: "138 bpm",
    vo2: 47.8,
    color: "#00D4FF",
  },
];

// ── Sincronización tab ─────────────────────────────────────────────────────────

function Sincronizacion() {
  const [syncing, setSyncing] = useState(false);
  const [lastSync] = useState("Hace 2 horas · 13 Abr 11:32");

  const handleSync = () => {
    setSyncing(true);
    setTimeout(() => setSyncing(false), 2500);
  };

  return (
    <div className="space-y-8">
      {/* Device card */}
      <div
        className="rounded-2xl p-8 relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, rgba(96,165,250,0.12), rgba(99,102,241,0.08))",
          border: "1px solid rgba(96,165,250,0.25)",
          boxShadow: "0 0 40px rgba(96,165,250,0.08)",
        }}
      >
        <div
          className="absolute -right-10 -top-10 w-60 h-60 rounded-full opacity-10 blur-3xl"
          style={{ background: "#3B82F6" }}
        />
        <div className="flex flex-col md:flex-row items-center gap-8 relative">
          {/* Garmin watch icon */}
          <div
            className="h-28 w-28 rounded-2xl flex items-center justify-center shrink-0"
            style={{
              background: "linear-gradient(135deg, #1e3a5f, #0f172a)",
              border: "2px solid rgba(96,165,250,0.4)",
              boxShadow: "0 0 30px rgba(96,165,250,0.2), inset 0 1px 0 rgba(96,165,250,0.1)",
            }}
          >
            <Watch className="h-14 w-14 text-blue-400" />
          </div>

          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Badge className="bg-green-400/20 text-green-300 border-green-500/30 text-xs">
                ● Conectado
              </Badge>
              <Badge className="bg-blue-400/20 text-blue-300 border-blue-500/30 text-xs">
                Garmin Forerunner 965
              </Badge>
            </div>
            <h2 className="text-2xl font-bold text-white mb-1">Tu dispositivo Garmin</h2>
            <p className="text-[#8B949E] text-sm mb-4">Última sincronización: {lastSync}</p>
            <div className="flex items-center gap-3">
              <button
                onClick={handleSync}
                disabled={syncing}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-[#0E1117] transition-all disabled:opacity-70"
                style={{
                  background: syncing
                    ? "rgba(96,165,250,0.5)"
                    : "linear-gradient(135deg, #3B82F6, #6366F1)",
                  boxShadow: "0 0 20px rgba(96,165,250,0.4)",
                }}
              >
                <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
                {syncing ? "Sincronizando..." : "Sincronizar ahora"}
              </button>
              <div className="flex items-center gap-1.5 text-xs text-[#8B949E]">
                <Wifi className="h-3.5 w-3.5" />
                Bluetooth activo
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics grid */}
      <div>
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Zap className="h-4 w-4 text-blue-400" />
          Métricas de hoy
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {garminMetrics.map((m) => (
            <div
              key={m.label}
              className="rounded-xl p-4 text-center transition-all hover:scale-105"
              style={{ background: m.bg, border: `1px solid ${m.border}` }}
            >
              <m.icon className="h-5 w-5 mx-auto mb-2" style={{ color: m.color }} />
              <p className="text-xs text-[#8B949E] mb-1">{m.label}</p>
              <p className="text-lg font-bold text-white">{m.value}</p>
              {m.unit && <p className="text-[10px]" style={{ color: m.color }}>{m.unit}</p>}
            </div>
          ))}
        </div>
      </div>

      {/* HRV chart */}
      <Card
        className="rounded-2xl"
        style={{ background: "#161B22", border: "1px solid rgba(201,255,0,0.15)" }}
      >
        <CardHeader>
          <CardTitle className="text-white text-base flex items-center gap-2">
            <Activity className="h-4 w-4 text-[#C9FF00]" />
            HRV últimos 7 días
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={hrvData}>
              <defs>
                <linearGradient id="hrvGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#C9FF00" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#C9FF00" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="day" stroke="#8B949E" fontSize={12} />
              <YAxis stroke="#8B949E" fontSize={12} />
              <Tooltip
                contentStyle={{ background: "#161B22", border: "1px solid rgba(201,255,0,0.3)", borderRadius: 8 }}
                labelStyle={{ color: "#fff" }}
              />
              <Area
                type="monotone"
                dataKey="hrv"
                name="HRV (ms)"
                stroke="#C9FF00"
                strokeWidth={2.5}
                fill="url(#hrvGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Sync status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: "Actividades sincronizadas", value: "127", icon: CheckCircle2, color: "#C9FF00" },
          { label: "Última actividad", value: "Hace 2h", icon: Clock, color: "#00D4FF" },
          { label: "Datos de sueño", value: "31 días", icon: Moon, color: "#A855F7" },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-xl p-4 flex items-center gap-3"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
          >
            <s.icon className="h-8 w-8 shrink-0" style={{ color: s.color }} />
            <div>
              <p className="text-xs text-[#8B949E]">{s.label}</p>
              <p className="text-lg font-bold text-white">{s.value}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Historial tab ──────────────────────────────────────────────────────────────

function Historial() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div
        className="rounded-2xl p-6"
        style={{
          background: "linear-gradient(135deg, rgba(96,165,250,0.12), rgba(99,102,241,0.08))",
          border: "1px solid rgba(96,165,250,0.25)",
        }}
      >
        <h2 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-blue-400" />
          Historial de Actividades
        </h2>
        <p className="text-[#8B949E] text-sm">Todas las actividades sincronizadas desde tu Garmin</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total actividades", value: "127", trend: +8, color: "#00D4FF" },
          { label: "KM totales", value: "534 km", trend: +12, color: "#C9FF00" },
          { label: "Tiempo total", value: "94h 20m", trend: +5, color: "#A855F7" },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-xl p-4"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
          >
            <p className="text-xs text-[#8B949E] mb-2">{s.label}</p>
            <p className="text-xl font-bold text-white mb-1">{s.value}</p>
            <div className="flex items-center gap-1 text-xs" style={{ color: s.color }}>
              <TrendingUp className="h-3 w-3" />
              +{s.trend}% este mes
            </div>
          </div>
        ))}
      </div>

      {/* Activity list */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Clock className="h-4 w-4 text-blue-400" />
          Recientes
        </h3>
        {historialActividades.map((act) => (
          <Card
            key={act.id}
            className="rounded-2xl transition-all hover:scale-[1.01] cursor-pointer"
            style={{
              background: "#161B22",
              border: `1px solid ${act.color}20`,
            }}
          >
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div
                    className="h-12 w-12 rounded-xl flex items-center justify-center shrink-0"
                    style={{ background: `${act.color}15`, border: `1px solid ${act.color}30` }}
                  >
                    {act.tipo === "Carrera" ? (
                      <Activity className="h-6 w-6" style={{ color: act.color }} />
                    ) : (
                      <Zap className="h-6 w-6" style={{ color: act.color }} />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-bold text-white">{act.nombre}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-[#8B949E]">{act.fecha}</span>
                      <Badge
                        className="text-[10px] px-1.5 py-0"
                        style={{
                          background: `${act.color}15`,
                          color: act.color,
                          border: `1px solid ${act.color}30`,
                        }}
                      >
                        {act.tipo}
                      </Badge>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-6 text-right">
                  <div>
                    <p className="text-xs text-[#8B949E]">Tiempo</p>
                    <p className="text-sm font-bold text-white">{act.duracion}</p>
                  </div>
                  {act.distancia !== "—" && (
                    <div>
                      <p className="text-xs text-[#8B949E]">Distancia</p>
                      <p className="text-sm font-bold text-white">{act.distancia}</p>
                    </div>
                  )}
                  {act.pace !== "—" && (
                    <div>
                      <p className="text-xs text-[#8B949E]">Pace</p>
                      <p className="text-sm font-bold" style={{ color: act.color }}>{act.pace}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs text-[#8B949E]">FC Media</p>
                    <p className="text-sm font-bold text-pink-400">{act.fc_media}</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function Garmin() {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const tab = params.get("tab") || "sincronizacion";

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />
      <main className="container mx-auto px-4 py-8">
        {tab === "sincronizacion" && <Sincronizacion />}
        {tab === "historial" && <Historial />}
      </main>
    </div>
  );
}
