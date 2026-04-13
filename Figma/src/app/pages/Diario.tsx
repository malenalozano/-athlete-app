import { useLocation } from "react-router";
import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
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

function EntrenoLibre() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div
        className="rounded-2xl p-6 relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, rgba(168,85,247,0.12), rgba(0,212,255,0.05))",
          border: "1px solid rgba(168,85,247,0.25)",
        }}
      >
        <div
          className="absolute -right-10 -top-10 w-40 h-40 rounded-full opacity-10 blur-3xl"
          style={{ background: "#A855F7" }}
        />
        <div className="flex items-center justify-between relative">
          <div>
            <h2 className="text-xl font-bold text-white mb-1">Entreno Libre</h2>
            <p className="text-[#8B949E] text-sm">Registro de entrenamientos no programados</p>
          </div>
          <button
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-[#0E1117] transition-all"
            style={{
              background: "linear-gradient(135deg, #A855F7, #7C3AED)",
              boxShadow: "0 0 20px rgba(168,85,247,0.4)",
            }}
          >
            <Plus className="h-4 w-4" />
            Registrar Entreno
          </button>
        </div>
      </div>

      {/* Entries */}
      <div className="space-y-4">
        {entrenosLibres.map((entreno) => (
          <Card
            key={entreno.id}
            className="rounded-2xl transition-all hover:scale-[1.01] cursor-pointer"
            style={{
              background: "#161B22",
              border: "1px solid rgba(168,85,247,0.15)",
            }}
          >
            <CardContent className="p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge className="bg-purple-400/15 text-purple-300 border-purple-500/30 text-xs">
                      {entreno.tipo}
                    </Badge>
                    <span className="text-xs text-[#8B949E]">{entreno.fecha}</span>
                  </div>
                  <p className="text-sm font-semibold text-white">{entreno.descripcion}</p>
                </div>
                <span className="text-lg">{entreno.sensacion}</span>
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
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function CicloMenstrualDiario() {
  const cyclePhases = [
    { name: "Menstrual", days: "1–5", active: false, color: "#F43F5E", emoji: "🌑" },
    { name: "Folicular", days: "6–13", active: true, color: "#A855F7", emoji: "🌒" },
    { name: "Ovulación", days: "14–16", active: false, color: "#C9FF00", emoji: "🌕" },
    { name: "Lútea", days: "17–28", active: false, color: "#F97316", emoji: "🌖" },
  ];

  const symptoms = [
    { label: "Energía", value: 8, color: "#C9FF00" },
    { label: "Ánimo", value: 7, color: "#A855F7" },
    { label: "Dolor", value: 2, color: "#F43F5E" },
    { label: "Sueño", value: 7, color: "#00D4FF" },
  ];

  return (
    <div className="space-y-6">
      {/* Phase circle banner */}
      <div
        className="rounded-2xl p-6"
        style={{
          background: "linear-gradient(135deg, rgba(244,63,94,0.12), rgba(168,85,247,0.1))",
          border: "1px solid rgba(244,63,94,0.25)",
        }}
      >
        <div className="flex flex-col md:flex-row items-center gap-6">
          <div className="flex-1">
            <Badge className="bg-purple-400/20 text-purple-300 border-purple-500/30 mb-3 text-xs">
              Fase Folicular · Día 8 de 28
            </Badge>
            <h2 className="text-xl font-bold text-white mb-2">Tu ciclo menstrual</h2>
            <p className="text-[#8B949E] text-sm">
              Estás en tu fase de mayor energía y recuperación. Ideal para entrenamientos de alta intensidad.
            </p>
          </div>
          <div className="flex gap-3">
            {cyclePhases.map((phase) => (
              <div
                key={phase.name}
                className="text-center p-3 rounded-xl transition-all"
                style={{
                  background: phase.active ? `${phase.color}20` : "rgba(255,255,255,0.03)",
                  border: `1px solid ${phase.active ? phase.color + "50" : "rgba(255,255,255,0.05)"}`,
                  boxShadow: phase.active ? `0 0 16px ${phase.color}30` : "none",
                }}
              >
                <span className="text-2xl">{phase.emoji}</span>
                <p className="text-[10px] font-bold mt-1" style={{ color: phase.active ? phase.color : "#8B949E" }}>
                  {phase.name}
                </p>
                <p className="text-[9px] text-[#8B949E]">{phase.days}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Today log */}
      <Card
        className="rounded-2xl"
        style={{ background: "#161B22", border: "1px solid rgba(168,85,247,0.2)" }}
      >
        <CardHeader>
          <CardTitle className="text-white text-base flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-purple-400" />
            Registro de hoy — 13 Abr
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {symptoms.map((s) => (
              <div
                key={s.label}
                className="rounded-xl p-3 text-center"
                style={{ background: `${s.color}10`, border: `1px solid ${s.color}30` }}
              >
                <p className="text-xs text-[#8B949E] mb-2">{s.label}</p>
                <div className="flex items-center justify-center gap-0.5">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <div
                      key={i}
                      className="h-1.5 flex-1 rounded-full transition-all"
                      style={{ background: i < s.value ? s.color : "rgba(255,255,255,0.08)" }}
                    />
                  ))}
                </div>
                <p className="text-xs font-bold text-white mt-2">{s.value}/10</p>
              </div>
            ))}
          </div>

          <div
            className="rounded-xl p-4"
            style={{ background: "rgba(201,255,0,0.05)", border: "1px solid rgba(201,255,0,0.15)" }}
          >
            <p className="text-xs font-semibold text-[#C9FF00] mb-1">💡 Recomendación de entrenamiento</p>
            <p className="text-sm text-white">
              Alta energía disponible. Hoy es perfecto para series de velocidad o un tempo run intenso.
            </p>
          </div>
        </CardContent>
      </Card>
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
