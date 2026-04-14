import { useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
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
  X,
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
  const [selectedDay, setSelectedDay] = useState<typeof weekPlan[0] | null>(null);

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
                onClick={() => setSelectedDay(day)}
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
                    Click para ver detalles
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Modal de detalles de sesión */}
        <Dialog open={!!selectedDay} onOpenChange={() => setSelectedDay(null)}>
          <DialogContent className="bg-[#161B22] border border-cyan-400/25 max-w-2xl">
            {selectedDay && (
              <>
                <DialogHeader>
                  <DialogTitle className="text-xl font-bold text-white flex items-center gap-2">
                    {selectedDay.activity}
                    <Badge className={TYPE_COLORS[selectedDay.type]?.badge || "bg-gray-400/15 text-gray-300"}>
                      {selectedDay.type === "running" ? "Carrera" : selectedDay.type === "strength" ? "Fuerza" : "Descanso"}
                    </Badge>
                  </DialogTitle>
                  <p className="text-sm text-[#8B949E]">{selectedDay.day} {selectedDay.date}</p>
                </DialogHeader>
                <div className="space-y-4 mt-4">
                  {/* Resumen */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl p-4" style={{ background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.2)" }}>
                      <p className="text-xs text-[#8B949E] mb-1">Duración</p>
                      <p className="text-lg font-bold text-white">{selectedDay.duration}</p>
                    </div>
                    <div className="rounded-xl p-4" style={{ background: "rgba(168,85,247,0.08)", border: "1px solid rgba(168,85,247,0.2)" }}>
                      <p className="text-xs text-[#8B949E] mb-1">Zona</p>
                      <p className="text-lg font-bold text-white">{selectedDay.zone}</p>
                    </div>
                  </div>

                  {/* Instrucciones */}
                  <div className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                    <p className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-cyan-400" />
                      Instrucciones
                    </p>
                    <p className="text-sm text-[#8B949E]">{selectedDay.notes}</p>
                  </div>

                  {/* Objetivos específicos */}
                  {selectedDay.type === "running" && (
                    <div className="rounded-xl p-4" style={{ background: "rgba(0,212,255,0.05)", border: "1px solid rgba(0,212,255,0.15)" }}>
                      <p className="text-sm font-semibold text-white mb-3">Objetivos de la sesión</p>
                      <div className="space-y-2">
                        <div className="flex items-start gap-2">
                          <span className="text-cyan-400 mt-0.5">✓</span>
                          <p className="text-sm text-white">Mantener ritmo constante en {selectedDay.zone}</p>
                        </div>
                        <div className="flex items-start gap-2">
                          <span className="text-cyan-400 mt-0.5">✓</span>
                          <p className="text-sm text-white">Cadencia objetivo: 175-180 spm</p>
                        </div>
                        <div className="flex items-start gap-2">
                          <span className="text-cyan-400 mt-0.5">✓</span>
                          <p className="text-sm text-white">Sensación: Conversacional / Controlado</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {selectedDay.type === "strength" && (
                    <div className="rounded-xl p-4" style={{ background: "rgba(168,85,247,0.05)", border: "1px solid rgba(168,85,247,0.15)" }}>
                      <p className="text-sm font-semibold text-white mb-3">Enfoque de la sesión</p>
                      <div className="space-y-2">
                        <div className="flex items-start gap-2">
                          <span className="text-purple-400 mt-0.5">•</span>
                          <p className="text-sm text-white">Fuerza específica para running</p>
                        </div>
                        <div className="flex items-start gap-2">
                          <span className="text-purple-400 mt-0.5">•</span>
                          <p className="text-sm text-white">Prevención de lesiones</p>
                        </div>
                        <div className="flex items-start gap-2">
                          <span className="text-purple-400 mt-0.5">•</span>
                          <p className="text-sm text-white">Economía de carrera mejorada</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </DialogContent>
        </Dialog>
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

const lastRunningActivities = [
  { fecha: "2026-04-11 18:37:18", km: 7.02, cadencia_media: 0, fc_media: 149, ritmo_medio: 7.5 },
  { fecha: "2026-04-09 15:10:30", km: 0.59, cadencia_media: 133.06, fc_media: 150, ritmo_medio: 36.31 },
  { fecha: "2026-04-07 17:29:21", km: 3.17, cadencia_media: 136.31, fc_media: 132, ritmo_medio: 9.75 },
];

const fuerzaProuesta = [
  { ejercicio: "Hip Thrust", grupo: "Glúteos", series: 2, reps: "12-15", peso: "32.5", nota: "65-70% 1RM, hipertrofia funcional · Semáforo rojo — -20% peso, -series" },
  { ejercicio: "Sentadilla Búlgara", grupo: "Glúteos/Cuádriceps", series: 2, reps: "12-15", peso: "10.0", nota: "65-70% 1RM, hipertrofia funcional · Semáforo rojo — -20% peso, -series" },
  { ejercicio: "Dominadas", grupo: "Espalda/Bíceps", series: 2, reps: "12-15", peso: "Peso corporal", nota: "65-70% 1RM, hipertrofia funcional · Semáforo rojo — -20% peso, -series" },
  { ejercicio: "Peso Muerto Rumano", grupo: "Isquios/Glúteos", series: 2, reps: "12-15", peso: "25.0", nota: "65-70% 1RM, hipertrofia funcional · Semáforo rojo — -20% peso, -series" },
  { ejercicio: "Press Banca", grupo: "Pecho/Tríceps", series: 2, reps: "12-15", peso: "15.0", nota: "65-70% 1RM, hipertrofia funcional · Semáforo rojo — -20% peso, -series" },
  { ejercicio: "Prensa 45°", grupo: "Cuádriceps", series: 2, reps: "12-15", peso: "47.5", nota: "65-70% 1RM, hipertrofia funcional · Semáforo rojo — -20% peso, -series" },
];

function Datos() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div
        className="rounded-2xl p-6"
        style={{
          background: "linear-gradient(135deg, rgba(168,85,247,0.12), rgba(0,212,255,0.08))",
          border: "1px solid rgba(168,85,247,0.25)",
        }}
      >
        <h2 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-purple-400" />
          Análisis Completo — Datos que Generan tu Plan
        </h2>
        <p className="text-[#8B949E] text-sm">Todas las variables que el sistema analiza para construir tu semana</p>
      </div>

      {/* BIOMÉTRICOS ACTUALES */}
      <div>
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <span className="text-blue-400">🔵</span> BIOMÉTRICOS ACTUALES
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "HRV", value: "39 ms", color: "#C9FF00", bg: "rgba(201,255,0,0.08)", border: "rgba(201,255,0,0.2)" },
            { label: "SLEEP SCORE", value: "92.0/100", color: "#00D4FF", bg: "rgba(0,212,255,0.08)", border: "rgba(0,212,255,0.2)" },
            { label: "ESTRÉS MEDIO", value: "21/100", color: "#F97316", bg: "rgba(249,115,22,0.08)", border: "rgba(249,115,22,0.2)" },
            { label: "BODY BATTERY", value: "—", color: "#8B949E", bg: "rgba(139,148,158,0.05)", border: "rgba(139,148,158,0.15)" },
            { label: "SUEÑO TOTAL", value: "8.8h", color: "#A855F7", bg: "rgba(168,85,247,0.08)", border: "rgba(168,85,247,0.2)" },
            { label: "PROFUNDO", value: "1.1h", color: "#6366F1", bg: "rgba(99,102,241,0.08)", border: "rgba(99,102,241,0.2)" },
            { label: "REM", value: "2.2h", color: "#EC4899", bg: "rgba(236,72,153,0.08)", border: "rgba(236,72,153,0.2)" },
            { label: "VIGILIA", value: "0.1h", color: "#F43F5E", bg: "rgba(244,63,94,0.08)", border: "rgba(244,63,94,0.2)" },
          ].map((m) => (
            <div key={m.label} className="rounded-xl p-4" style={{ background: m.bg, border: `1px solid ${m.border}` }}>
              <p className="text-[10px] font-bold text-[#8B949E] mb-2 uppercase tracking-wider">{m.label}</p>
              <p className="text-xl font-black" style={{ color: m.color }}>{m.value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ANÁLISIS DE CARRERA & RENDIMIENTO */}
      <div>
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <span>🏃</span> ANÁLISIS DE CARRERA & RENDIMIENTO
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <div className="rounded-xl p-4" style={{ background: "rgba(201,255,0,0.08)", border: "1px solid rgba(201,255,0,0.2)" }}>
            <p className="text-[10px] font-bold text-[#8B949E] uppercase tracking-wider mb-2">CADENCIA MEDIA</p>
            <p className="text-2xl font-black text-[#C9FF00]">68 spm</p>
            <p className="text-[10px] text-[#8B949E] mt-1">↓ Mejorar técnica</p>
          </div>
          <div className="rounded-xl p-4" style={{ background: "rgba(0,212,255,0.05)", border: "1px solid rgba(0,212,255,0.15)" }}>
            <p className="text-[10px] font-bold text-[#8B949E] uppercase tracking-wider mb-2">VO2MAX</p>
            <p className="text-xl font-black text-[#8B949E]">—</p>
            <p className="text-[10px] text-[#8B949E] mt-1">No disponible</p>
          </div>
          <div className="rounded-xl p-4" style={{ background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.2)" }}>
            <p className="text-[10px] font-bold text-[#8B949E] uppercase tracking-wider mb-2">ACWR</p>
            <p className="text-2xl font-black text-green-400">1.00</p>
            <div className="flex items-center gap-1 mt-1">
              <span className="w-2 h-2 rounded-full bg-green-400" />
              <p className="text-[10px] text-green-400">Normal</p>
            </div>
          </div>
        </div>
        <p className="text-xs text-[#8B949E] mb-2">Últimas actividades de running (7 días)</p>
        <div className="rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.06)" }}>
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#30363D]" style={{ background: "rgba(255,255,255,0.03)" }}>
                {["fecha", "km", "cadencia_media", "fc_media", "ritmo_medio"].map(h => (
                  <th key={h} className="text-left text-[10px] font-bold text-[#8B949E] py-2.5 px-3 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {lastRunningActivities.map((row, i) => (
                <tr key={i} className="border-b border-[#30363D]/40 hover:bg-[#30363D]/20 transition-colors">
                  <td className="text-xs text-white py-2.5 px-3">{row.fecha}</td>
                  <td className="text-xs text-cyan-400 py-2.5 px-3">{row.km}</td>
                  <td className="text-xs text-white py-2.5 px-3">{row.cadencia_media}</td>
                  <td className="text-xs text-white py-2.5 px-3">{row.fc_media}</td>
                  <td className="text-xs text-[#C9FF00] py-2.5 px-3">{row.ritmo_medio}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* FASE DEL MACROCICLO */}
      <div>
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <span className="text-blue-400">🔵</span> FASE DEL MACROCICLO
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
          {[
            { label: "FASE ACTUAL", value: "Acondicionamiento", color: "#C9FF00" },
            { label: "KM MÁX/SEMANA", value: "30 km", color: "#00D4FF" },
            { label: "DÍAS FUERZA", value: "4 días", color: "#A855F7" },
            { label: "DÍAS HASTA OBJETIVO", value: "312", color: "#F97316" },
            { label: "SEMANAS HASTA OBJETIVO", value: "44", color: "#F43F5E" },
          ].map((m) => (
            <div key={m.label} className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
              <p className="text-[10px] font-bold text-[#8B949E] uppercase tracking-wider mb-2">{m.label}</p>
              <p className="text-lg font-black" style={{ color: m.color }}>{m.value}</p>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="rounded-xl p-4" style={{ background: "rgba(0,212,255,0.05)", border: "1px solid rgba(0,212,255,0.15)" }}>
            <p className="text-xs text-[#8B949E] mb-1 font-semibold">Enfoque Running:</p>
            <p className="text-sm text-white">Base aeróbica Z2. Bici/elíptica en días de tibia.</p>
          </div>
          <div className="rounded-xl p-4" style={{ background: "rgba(168,85,247,0.05)", border: "1px solid rgba(168,85,247,0.15)" }}>
            <p className="text-xs text-[#8B949E] mb-1 font-semibold">Enfoque Fuerza:</p>
            <p className="text-sm text-white">Hipertrofia base y glúteo (3×12-15, 65-70% 1RM)</p>
          </div>
        </div>
      </div>

      {/* SEMÁFORO DE RECUPERACIÓN */}
      <div>
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <span>🚦</span> SEMÁFORO DE RECUPERACIÓN
        </h3>
        <div className="rounded-xl p-5" style={{ background: "rgba(244,63,94,0.08)", border: "1px solid rgba(244,63,94,0.3)" }}>
          <div className="flex items-center gap-2 mb-2">
            <span className="w-4 h-4 rounded-full bg-red-500 shadow-[0_0_8px_rgba(244,63,94,0.8)]" />
            <span className="text-base font-black text-red-400">ROJO</span>
          </div>
          <p className="text-sm text-white mb-3">Adaptación fallida — HRV caído 25%. Considera regenerativo.</p>
          <div className="flex flex-wrap items-center gap-4 text-xs">
            <span className="text-[#8B949E]">Multiplicador volumen: <span className="text-white font-bold">1.00x</span></span>
            <span className="text-[#8B949E]">Calidad permitida: <span className="text-green-400 font-bold">Sí</span></span>
          </div>
          <p className="text-xs text-orange-400 mt-3 flex items-center gap-1">
            <span>⚠</span> Recuperación baja — el plan no se modifica automáticamente. Considera reducir intensidad manualmente.
          </p>
        </div>
      </div>

      {/* CICLO MENSTRUAL */}
      <div>
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <span>🩸</span> CICLO MENSTRUAL
        </h3>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "FASE", value: "Lútea", color: "#EC4899" },
            { label: "MULTIPLICADOR VOL.", value: "1.00x", color: "#C9FF00" },
            { label: "¿CALIDAD PERMITIDA?", value: "Sí", color: "#22C55E" },
          ].map((m) => (
            <div key={m.label} className="rounded-xl p-4" style={{ background: "rgba(236,72,153,0.06)", border: "1px solid rgba(236,72,153,0.2)" }}>
              <p className="text-[10px] font-bold text-[#8B949E] uppercase tracking-wider mb-2">{m.label}</p>
              <p className="text-lg font-black" style={{ color: m.color }}>{m.value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* RESTRICCIONES & LESIONES */}
      <div>
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <span>⚠️</span> RESTRICCIONES & LESIONES ACTIVAS
        </h3>
        <div className="rounded-xl p-4 flex items-center gap-2" style={{ background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.3)" }}>
          <span className="text-green-400">✅</span>
          <p className="text-sm text-green-400 font-semibold">Sin lesiones activas</p>
        </div>
      </div>

      {/* EVALUACIONES ESPECIALIZADAS */}
      <div>
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <span>📊</span> EVALUACIONES ESPECIALIZADAS
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-xl p-4" style={{ background: "rgba(201,255,0,0.08)", border: "1px solid rgba(201,255,0,0.2)" }}>
            <p className="text-[10px] font-bold text-[#8B949E] uppercase tracking-wider mb-2">CADENCIA</p>
            <div className="rounded-lg p-3" style={{ background: "rgba(201,255,0,0.08)", border: "1px solid rgba(201,255,0,0.2)" }}>
              <p className="text-xs text-[#C9FF00]">✏️ Cadencia 68 spm — añadir 5min drills técnica antes de cada rodaje.</p>
            </div>
          </div>
          <div className="rounded-xl p-4" style={{ background: "rgba(0,212,255,0.05)", border: "1px solid rgba(0,212,255,0.15)" }}>
            <p className="text-[10px] font-bold text-[#8B949E] uppercase tracking-wider mb-2">EFICIENCIA AERÓBICA</p>
            <div className="rounded-lg p-3" style={{ background: "rgba(0,212,255,0.05)", border: "1px solid rgba(0,212,255,0.15)" }}>
              <p className="text-xs text-cyan-400">Sin datos suficientes (mín. 4 sesiones Z2 en 28 días).</p>
            </div>
          </div>
          <div className="rounded-xl p-4" style={{ background: "rgba(201,255,0,0.08)", border: "1px solid rgba(201,255,0,0.2)" }}>
            <p className="text-[10px] font-bold text-[#8B949E] uppercase tracking-wider mb-2">VOLUMEN ESTIMADO SEMANA</p>
            <p className="text-3xl font-black text-[#C9FF00]">11.2 km</p>
          </div>
        </div>
      </div>

      {/* SESIÓN DE FUERZA PROPUESTA */}
      <div>
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <span>💪</span> SESIÓN DE FUERZA PROPUESTA
        </h3>
        <div className="rounded-xl overflow-hidden" style={{ border: "1px solid rgba(168,85,247,0.2)" }}>
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#30363D]" style={{ background: "rgba(168,85,247,0.08)" }}>
                {["Ejercicio", "Grupo", "Series", "Reps", "Peso (kg)", "Nota"].map(h => (
                  <th key={h} className="text-left text-[10px] font-bold text-[#8B949E] py-3 px-3 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {fuerzaProuesta.map((row, i) => (
                <tr key={i} className="border-b border-[#30363D]/40 hover:bg-[#30363D]/20 transition-colors">
                  <td className="text-sm text-cyan-400 py-3 px-3 font-semibold">{row.ejercicio}</td>
                  <td className="text-xs text-[#8B949E] py-3 px-3">{row.grupo}</td>
                  <td className="text-sm text-white py-3 px-3">{row.series}</td>
                  <td className="text-sm text-white py-3 px-3">{row.reps}</td>
                  <td className="text-sm text-white py-3 px-3">{row.peso}</td>
                  <td className="text-xs text-[#8B949E] py-3 px-3">{row.nota}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* RESUMEN EJECUTIVO */}
      <div>
        <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <span>🚀</span> RESUMEN EJECUTIVO
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-xl p-5" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <p className="text-xs font-bold text-[#8B949E] uppercase tracking-wider mb-3">ESTADO DE ENTRENAMIENTO</p>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#8B949E]">Recuperación:</span>
                <span className="text-xs font-bold text-red-400">ROJO</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#8B949E]">Volumen objetivo:</span>
                <span className="text-xs font-bold text-cyan-400">19.0 km</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#8B949E]">Calidad permitida:</span>
                <span className="text-xs font-bold text-green-400">Sí</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#8B949E]">ACWR:</span>
                <span className="text-xs font-bold text-white">1.00</span>
              </div>
            </div>
          </div>
          <div className="rounded-xl p-5" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <p className="text-xs font-bold text-[#8B949E] uppercase tracking-wider mb-3">AJUSTES APLICADOS</p>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#8B949E]">Ciclo menstrual:</span>
                <span className="text-xs font-bold text-pink-400">Lútea</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#8B949E]">Drills cadencia:</span>
                <span className="text-xs font-bold text-[#C9FF00]">Sí — 5min técnica</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#8B949E]">Lesiones:</span>
                <span className="text-xs font-bold text-green-400">Ninguna</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#8B949E]">Fase:</span>
                <span className="text-xs font-bold text-[#C9FF00]">Acondicionamiento</span>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-3 rounded-xl p-4 flex items-center gap-2" style={{ background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.3)" }}>
          <span className="text-green-400">✅</span>
          <p className="text-sm text-green-400 font-semibold">Datos listos para generar tu plan semanal personalizado.</p>
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