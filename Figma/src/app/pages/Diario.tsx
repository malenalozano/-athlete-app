import { useLocation, useNavigate } from "react-router";
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
  ChevronDown,
  Activity,
  Zap,
  X,
  Pencil,
  Archive,
  ArchiveRestore,
} from "lucide-react";
import { useState, useEffect } from "react";
import { crearEntradaDiario, getActividades, getEjercicios, getResumenEntrenador, getSesionFuerzaHoy, archivarEjercicio, crearEjercicio, editarEjercicio, type ActividadGarmin, type EjercicioBiblioteca, type SesionFuerzaHoy, type GrupoFuerza } from "../api";
import { ModalRegistroFuerza } from "../components/ModalRegistroFuerza";

// ── Tabs ───────────────────────────────────────────────────────────────────────

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
  const { userId } = useUser();
  const [currentMonth, setCurrentMonth] = useState(() => { const d = new Date(); d.setDate(1); return d; });
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [nota, setNota] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [apiActividades, setApiActividades] = useState<ActividadGarmin[]>([]);
  const [sesionFuerza, setSesionFuerza] = useState<SesionFuerzaHoy | null>(null);
  const [showModalFuerza, setShowModalFuerza] = useState(false);
  const [fuerzaGuardada, setFuerzaGuardada] = useState(false);

  useEffect(() => {
    if (!userId) return;
    getActividades(userId, 60).then(setApiActividades).catch(() => null);
    getSesionFuerzaHoy(userId)
      .then((data) => { if (data.tiene_fuerza) setSesionFuerza(data); })
      .catch(() => null);
  }, [userId]);

  const handleProcesar = async () => {
    if (!nota.trim() || !userId) return;
    setSubmitting(true);
    try {
      await crearEntradaDiario({ usuario_id: userId, fecha: new Date().toISOString().split("T")[0], feedback_entreno: nota, fatiga_subjetiva: null, dolor_notas: null, estado_animo: null, fase_ciclo: null });
      setNota("");
    } catch { /* silent */ }
    finally { setSubmitting(false); }
  };

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

  // Build activity map from API data for current month
  const apiActividadesPorDia = (() => {
    const map: Record<number, Array<{ id: number; fecha: string; tipo: string; descripcion: string; duracion: string; distancia: string; fc: string; sensacion: string; notas: string; gymType?: string; runType?: string }>> = {};
    apiActividades.forEach(a => {
      const d = new Date(a.fecha + "T12:00:00");
      if (d.getMonth() !== currentMonth.getMonth() || d.getFullYear() !== currentMonth.getFullYear()) return;
      const day = d.getDate();
      const isRunning = a.tipo_deporte?.toLowerCase().includes("running") || a.tipo_deporte?.toLowerCase().includes("carrera");
      if (!map[day]) map[day] = [];
      map[day].push({
        id: parseInt(a.id || "0") || day,
        fecha: a.fecha,
        tipo: isRunning ? "Carrera" : "Fuerza",
        descripcion: `${a.tipo_deporte} — ${a.km?.toFixed(1) || "?"} km`,
        duracion: a.duracion_fmt || "--",
        distancia: a.km ? `${a.km.toFixed(1)} km` : "—",
        fc: a.fc_media ? `${a.fc_media} bpm` : "—",
        sensacion: "—",
        notas: "",
        runType: isRunning ? "Carrera" : undefined,
        gymType: !isRunning ? a.tipo_deporte : undefined,
      });
    });
    return map;
  })();

  const mergedActividades = apiActividadesPorDia;

  // Stats del mes
  const diasEntrenados = Object.keys(mergedActividades).length;
  const todasActs = Object.values(mergedActividades).flat();
  const statsDelMes = [
    { label: "DÍAS", value: String(diasEntrenados), icon: Activity, color: "#C9FF00", bg: "rgba(201,255,0,0.1)", border: "rgba(201,255,0,0.25)" },
    { label: "FUERZA", value: String(todasActs.filter(a => a.tipo === "Fuerza").length), icon: Dumbbell, color: "#F97316", bg: "rgba(249,115,22,0.1)", border: "rgba(249,115,22,0.25)" },
    { label: "CARRERAS", value: String(todasActs.filter(a => a.tipo === "Carrera").length), icon: Zap, color: "#00D4FF", bg: "rgba(0,212,255,0.1)", border: "rgba(0,212,255,0.25)" },
  ];

  const getActivityColorForDay = (day: number) => {
    const activities = mergedActividades[day];
    if (!activities || activities.length === 0) return null;
    const hasRunning = activities.some(a => a.tipo === "Carrera");
    const hasStrength = activities.some(a => a.tipo === "Fuerza");
    if (hasRunning && hasStrength) return "#C9FF00";
    if (hasRunning) return "#00D4FF";
    if (hasStrength) return "#A855F7";
    return null;
  };

  const getTypeLabelForDay = (day: number): { label: string; color: string } | null => {
    const activities = mergedActividades[day];
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

  const TODAY = new Date().getDate();
  const TODAY_MONTH = new Date().getMonth();

  const GRUPO_COLOR_MAP: Record<string, string> = { Push: "#C9FF00", Pull: "#00D4FF", Pierna: "#A855F7" };
  const grupoColor = sesionFuerza?.grupo ? GRUPO_COLOR_MAP[sesionFuerza.grupo] ?? "#C9FF00" : "#C9FF00";

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

      {/* Banner sesión de fuerza de hoy */}
      {sesionFuerza?.tiene_fuerza && sesionFuerza.grupo && (
        <div
          className="rounded-2xl p-5 flex items-center justify-between gap-4"
          style={{
            background: `${grupoColor}10`,
            border: `1px solid ${grupoColor}35`,
            boxShadow: `0 0 20px ${grupoColor}12`,
          }}
        >
          <div>
            <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: grupoColor }}>
              HOY TOCA FUERZA
            </p>
            <p className="text-lg font-black text-white">{sesionFuerza.sesion_nombre ?? sesionFuerza.grupo}</p>
            <p className="text-sm text-[#8B949E] mt-0.5">
              {sesionFuerza.ejercicios.length} ejercicio{sesionFuerza.ejercicios.length !== 1 ? "s" : ""}
              {sesionFuerza.ejercicios.some(e => e.subir_peso) && (
                <span className="ml-2 text-[#22C55E] font-semibold">↑ Sube peso en alguno</span>
              )}
            </p>
          </div>
          <button
            onClick={() => setShowModalFuerza(true)}
            disabled={fuerzaGuardada}
            className="flex-shrink-0 px-5 py-2.5 rounded-xl text-sm font-bold transition-all"
            style={{
              background: fuerzaGuardada
                ? "rgba(34,197,94,0.15)"
                : `linear-gradient(135deg, ${grupoColor}, ${grupoColor}cc)`,
              color: fuerzaGuardada ? "#22C55E" : "#0E1117",
            }}
          >
            {fuerzaGuardada ? "✓ Registrado" : "Registrar sesión"}
          </button>
        </div>
      )}

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
              <p className="text-sm font-bold text-white">{new Date().toLocaleDateString("es-ES", { day: "numeric", month: "long", year: "numeric" })}</p>
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
                onClick={handleProcesar}
                disabled={submitting || !nota.trim()}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold transition-all disabled:opacity-50"
                style={{
                  background: "linear-gradient(135deg, #22c55e, #16a34a)",
                  color: "#0E1117",
                  boxShadow: "0 0 20px rgba(34,197,94,0.4)",
                }}
              >
                <Plus className="h-4 w-4" />
                {submitting ? "Guardando..." : "Procesar nota"}
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
                  const hasActivity = day ? mergedActividades[day] : null;
                  const activityColor = day ? getActivityColorForDay(day) : null;
                  const typeLabel = day ? getTypeLabelForDay(day) : null;
                  const isToday = day === TODAY && currentMonth.getMonth() === TODAY_MONTH;
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

      {/* Modal registro de fuerza */}
      {showModalFuerza && userId !== null && sesionFuerza?.grupo && (
        <ModalRegistroFuerza
          usuarioId={userId}
          grupo={sesionFuerza.grupo}
          ejerciciosProp={sesionFuerza.ejercicios}
          onClose={() => setShowModalFuerza(false)}
          onGuardado={() => setFuerzaGuardada(true)}
        />
      )}

      {/* Modal de actividades del día */}
      <Dialog open={selectedDay !== null} onOpenChange={() => setSelectedDay(null)}>
        <DialogContent className="bg-[#161B22] border border-green-400/25 max-w-3xl max-h-[80vh] overflow-y-auto">
          {selectedDay && mergedActividades[selectedDay] && (
            <>
              <DialogHeader>
                <DialogTitle className="text-xl font-bold text-white">
                  Actividades del {selectedDay} de {monthNames[currentMonth.getMonth()]}
                </DialogTitle>
                <p className="text-sm text-[#8B949E]">{mergedActividades[selectedDay].length} {mergedActividades[selectedDay].length === 1 ? "actividad" : "actividades"} registradas</p>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                {mergedActividades[selectedDay].map((entreno) => {
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
  const [currentMonth, setCurrentMonth] = useState(() => { const d = new Date(); d.setDate(1); return d; });
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

  const TODAY_DAY = new Date().getDate();
  const TODAY_DAY_MONTH = new Date().getMonth();

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
                  const isToday = day === TODAY_DAY && currentMonth.getMonth() === TODAY_DAY_MONTH;
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

// Color por grupo muscular
const GRUPO_COLORS: Record<string, string> = {
  "Pierna": "#EC4899",
  "Piernas": "#EC4899",
  "Core": "#00D4FF",
  "Pull": "#A855F7",
  "Push": "#F97316",
  "Espalda": "#A855F7",
  "Pecho": "#F97316",
  "Hombros": "#F97316",
  "Bíceps": "#6366F1",
  "Tríceps": "#6366F1",
};

function getGrupoColor(grupo: string): string {
  for (const key of Object.keys(GRUPO_COLORS)) {
    if (grupo?.toLowerCase().includes(key.toLowerCase())) return GRUPO_COLORS[key];
  }
  return "#C9FF00";
}

// Mini-modal crear/editar ejercicio (igual que en /ejercicios pero más simple)
function MiniModalEjercicio({
  usuarioId,
  grupoInicial,
  ejercicio,
  onClose,
  onGuardado,
}: {
  usuarioId: number;
  grupoInicial: GrupoFuerza;
  ejercicio?: EjercicioBiblioteca;
  onClose: () => void;
  onGuardado: () => void;
}) {
  const modoEdicion = !!ejercicio;
  const GRUPOS_MINI: { key: GrupoFuerza; label: string; color: string }[] = [
    { key: "Push",   label: "Push",   color: "#C9FF00" },
    { key: "Pull",   label: "Pull",   color: "#00D4FF" },
    { key: "Pierna", label: "Pierna", color: "#A855F7" },
  ];
  const [nombre, setNombre] = useState(ejercicio?.nombre ?? "");
  const [grupo, setGrupo]   = useState<GrupoFuerza>(ejercicio?.grupo_muscular ?? grupoInicial);
  const [notas, setNotas]   = useState(ejercicio?.alias ?? "");
  const [seriesObj, setSeriesObj] = useState(ejercicio?.series_objetivo?.toString() ?? "");
  const [repsObj,   setRepsObj]   = useState(ejercicio?.reps_objetivo?.toString() ?? "");
  const [pesoObj,   setPesoObj]   = useState(ejercicio?.peso_objetivo?.toString() ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!nombre.trim()) { setError("El nombre es obligatorio"); return; }
    setLoading(true);
    setError("");
    try {
      const payload = {
        nombre: nombre.trim(),
        grupo_muscular: grupo,
        alias: notas.trim() || undefined,
        series_objetivo: seriesObj ? parseInt(seriesObj) : undefined,
        reps_objetivo:   repsObj   ? parseInt(repsObj)   : undefined,
        peso_objetivo:   pesoObj   ? parseFloat(pesoObj) : undefined,
      };
      if (modoEdicion && ejercicio) {
        await editarEjercicio(ejercicio.id, payload);
      } else {
        const res = await crearEjercicio({ usuario_id: usuarioId, ...payload });
        if (res.restaurado) {
          onGuardado();
          onClose();
          return;
        }
      }
      onGuardado();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "";
      setError(msg.includes("409") ? "Ya existe un ejercicio activo con ese nombre" : "Error al guardar");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: "rgba(0,0,0,0.7)" }}>
      <div className="w-full max-w-sm rounded-2xl p-5" style={{ background: "#161B22", border: "1px solid rgba(255,255,255,0.1)" }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-bold text-white">{modoEdicion ? "Editar ejercicio" : "Nuevo ejercicio"}</h3>
          <button onClick={onClose} className="text-[#8B949E] hover:text-white"><X className="h-5 w-5" /></button>
        </div>
        <div className="space-y-3">
          <div className="flex gap-2">
            {GRUPOS_MINI.map((g) => (
              <button key={g.key} onClick={() => setGrupo(g.key)}
                className="flex-1 py-1.5 rounded-lg text-xs font-bold"
                style={{
                  background: grupo === g.key ? `${g.color}18` : "rgba(255,255,255,0.04)",
                  border: `1px solid ${grupo === g.key ? g.color : "rgba(255,255,255,0.08)"}`,
                  color: grupo === g.key ? g.color : "#8B949E",
                }}
              >{g.label}</button>
            ))}
          </div>
          <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Nombre del ejercicio *"
            autoFocus className="w-full px-3 py-2 rounded-lg text-sm text-white outline-none"
            style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          />
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: "Series", value: seriesObj, set: setSeriesObj, ph: "4" },
              { label: "Reps",   value: repsObj,   set: setRepsObj,   ph: "8" },
              { label: "Peso kg",value: pesoObj,   set: setPesoObj,   ph: "40" },
            ].map(({ label, value, set, ph }) => (
              <div key={label}>
                <p className="text-[9px] text-[#8B949E] mb-1">{label} (opcional)</p>
                <input type="number" value={value} onChange={(e) => set(e.target.value)} placeholder={ph}
                  className="w-full px-2 py-1.5 rounded-lg text-sm text-white text-center outline-none"
                  style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}
                />
              </div>
            ))}
          </div>
          <div>
            <p className="text-[9px] text-[#8B949E] mb-1">📝 Notas (opcional)</p>
            <textarea
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
              placeholder="Técnica, recordatorios, sensaciones..."
              rows={2}
              className="w-full px-3 py-2 rounded-lg text-sm text-white outline-none resize-none"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button onClick={handleSubmit} disabled={loading}
            className="w-full py-2.5 rounded-xl text-sm font-bold"
            style={{ background: "#C9FF00", color: "#0E1117", opacity: loading ? 0.6 : 1 }}
          >
            {loading ? "Guardando..." : modoEdicion ? "Guardar cambios" : "Añadir ejercicio"}
          </button>
        </div>
      </div>
    </div>
  );
}

const GRUPOS_EJ = [
  { key: "Push"   as GrupoFuerza, label: "PUSH",   color: "#C9FF00", bg: "rgba(201,255,0,0.08)",   desc: "Press banca, Press militar..." },
  { key: "Pull"   as GrupoFuerza, label: "PULL",   color: "#00D4FF", bg: "rgba(0,212,255,0.08)",   desc: "Dominadas, Remo..." },
  { key: "Pierna" as GrupoFuerza, label: "PIERNA", color: "#A855F7", bg: "rgba(168,85,247,0.08)", desc: "Sentadilla, Peso muerto..." },
] as const;

function Ejercicios() {
  const { userId } = useUser();
  const [grupos, setGrupos] = useState<Record<string, { activos: EjercicioBiblioteca[]; archivados: EjercicioBiblioteca[] }>>({
    Push: { activos: [], archivados: [] },
    Pull: { activos: [], archivados: [] },
    Pierna: { activos: [], archivados: [] },
  });
  const [loading, setLoading]         = useState(false);
  const [modalGrupo, setModalGrupo]   = useState<GrupoFuerza | null>(null);
  const [editando, setEditando]       = useState<EjercicioBiblioteca | null>(null);
  const [archivadosAbiertos, setArchivadosAbiertos] = useState(true);

  const cargar = () => {
    if (!userId) return;
    setLoading(true);
    getEjercicios(userId)
      .then((data) => setGrupos(data.grupos as unknown as Record<string, { activos: EjercicioBiblioteca[]; archivados: EjercicioBiblioteca[] }>))
      .catch(() => null)
      .finally(() => setLoading(false));
  };

  useEffect(() => { cargar(); }, [userId]);

  const todosArchivados = GRUPOS_EJ.flatMap((g) => grupos[g.key]?.archivados ?? []);

  return (
    <div className="space-y-4">
      {/* 3 columnas */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {GRUPOS_EJ.map((g) => {
          const activos = grupos[g.key]?.activos ?? [];
          return (
            <div key={g.key} className="flex flex-col rounded-2xl overflow-hidden"
              style={{ background: "rgba(22,27,34,0.6)", border: `1px solid ${g.color}25` }}>
              {/* Cabecera columna */}
              <div className="px-3 py-2.5 flex items-center justify-between"
                style={{ background: g.bg, borderBottom: `1px solid ${g.color}30` }}>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-black tracking-wider uppercase" style={{ color: g.color }}>{g.label}</span>
                  <span className="text-[10px] text-[#8B949E]">({activos.length})</span>
                </div>
                <button onClick={() => { setEditando(null); setModalGrupo(g.key); }}
                  className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-bold transition-all hover:brightness-110"
                  style={{ background: g.color, color: "#0E1117" }}>
                  <Plus className="h-3 w-3" /> Añadir
                </button>
              </div>

              {/* Ejercicios */}
              <div className="flex-1 p-2 space-y-1.5">
                {loading && activos.length === 0 ? (
                  <p className="text-[11px] text-[#30363D] p-2">Cargando...</p>
                ) : activos.length === 0 ? (
                  <div className="py-6 text-center">
                    <p className="text-[11px] text-[#30363D]">{g.desc}</p>
                    <button onClick={() => { setEditando(null); setModalGrupo(g.key); }}
                      className="mt-2 text-[11px] font-semibold flex items-center gap-1 mx-auto"
                      style={{ color: g.color }}>
                      <Plus className="h-3 w-3" /> Añadir el primero
                    </button>
                  </div>
                ) : (
                  activos.map((ej) => (
                    <div key={ej.id} className="rounded-xl px-3 py-2.5 flex items-center gap-2"
                      style={{
                        background: "#161B22",
                        border: ej.subir_peso ? "1px solid rgba(34,197,94,0.35)" : "1px solid rgba(255,255,255,0.07)"
                      }}>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white truncate">{ej.nombre}</p>
                        <p className="text-[10px] text-[#8B949E]">
                          {ej.ultimo_peso != null
                            ? `${ej.ultimo_peso}kg · ${ej.ultima_series ?? "—"}×${ej.ultimas_reps ?? "—"}`
                            : (ej.series_objetivo ? `obj: ${ej.series_objetivo}×${ej.reps_objetivo ?? "—"}` : "Sin datos aún")}
                        </p>
                        {ej.alias && (
                          <p className="text-[10px] mt-0.5 leading-tight" style={{ color: "#6B7280" }}>📝 {ej.alias}</p>
                        )}
                      </div>
                      {ej.subir_peso && (
                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full shrink-0"
                          style={{ background: "rgba(34,197,94,0.15)", color: "#22C55E", border: "1px solid rgba(34,197,94,0.3)" }}>
                          ↑
                        </span>
                      )}
                      <div className="flex gap-0.5 shrink-0">
                        <button onClick={() => setEditando(ej)}
                          className="p-1.5 rounded-lg text-[#8B949E] hover:text-white hover:bg-white/10 transition-all" title="Editar">
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button onClick={async () => { await archivarEjercicio(ej.id, true); cargar(); }}
                          className="p-1.5 rounded-lg text-[#8B949E] hover:text-[#F97316] hover:bg-white/10 transition-all" title="Archivar">
                          <Archive className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Archivados */}
      {todosArchivados.length > 0 && (
        <div className="rounded-2xl overflow-hidden"
          style={{ background: "rgba(22,27,34,0.4)", border: "1px solid rgba(255,255,255,0.05)" }}>
          <div className="flex items-center px-4 py-3 gap-2">
            <button onClick={() => setArchivadosAbiertos(!archivadosAbiertos)}
              className="flex items-center gap-2 flex-1 text-left">
              {archivadosAbiertos
                ? <ChevronDown className="h-4 w-4 text-[#F97316]" />
                : <ChevronRight className="h-4 w-4 text-[#F97316]" />}
              <Archive className="h-4 w-4 text-[#F97316]" />
              <span className="text-sm font-bold text-[#F97316] uppercase tracking-wider">Archivados</span>
              <span className="ml-1 text-xs px-2 py-0.5 rounded-full font-bold"
                style={{ background: "rgba(249,115,22,0.15)", color: "#F97316", border: "1px solid rgba(249,115,22,0.3)" }}>
                {todosArchivados.length}
              </span>
            </button>
            <button
              onClick={async () => {
                if (window.confirm(`¿Restaurar todos los ${todosArchivados.length} ejercicios archivados?`)) {
                  for (const ej of todosArchivados) { await archivarEjercicio(ej.id, false); }
                  cargar();
                }
              }}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold transition-all hover:brightness-110 shrink-0"
              style={{ background: "rgba(201,255,0,0.12)", color: "#C9FF00", border: "1px solid rgba(201,255,0,0.25)" }}
            >
              <ArchiveRestore className="h-3.5 w-3.5" /> Restaurar todos
            </button>
          </div>
          {archivadosAbiertos && (
            <div className="px-3 pb-3 space-y-1.5">
              {todosArchivados.map((ej) => {
                const color = getGrupoColor(ej.grupo_muscular);
                return (
                  <div key={ej.id} className="rounded-xl px-3 py-2.5 flex items-center gap-2 opacity-70"
                    style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                    <div className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-white truncate">{ej.nombre}</p>
                      <p className="text-[10px]" style={{ color }}>{ej.grupo_muscular}</p>
                    </div>
                    <div className="flex gap-1 shrink-0">
                      <button onClick={() => setEditando(ej)}
                        className="p-1.5 rounded-lg text-[#8B949E] hover:text-white hover:bg-white/10 transition-all" title="Editar">
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={async () => { await archivarEjercicio(ej.id, false); cargar(); }}
                        className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold transition-all hover:brightness-110"
                        style={{ background: "rgba(201,255,0,0.1)", color: "#C9FF00", border: "1px solid rgba(201,255,0,0.2)" }}>
                        <ArchiveRestore className="h-3 w-3" /> Restaurar
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Modal crear/editar */}
      {(modalGrupo !== null || editando) && userId !== null && (
        <MiniModalEjercicio
          usuarioId={userId}
          grupoInicial={editando?.grupo_muscular ?? modalGrupo ?? "Push"}
          ejercicio={editando ?? undefined}
          onClose={() => { setModalGrupo(null); setEditando(null); }}
          onGuardado={cargar}
        />
      )}
    </div>
  );
}

function Lesiones() {
  const { userId } = useUser();
  const [lesionesActivas, setLesionesActivas] = useState<{ tipo: string; grado: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    getResumenEntrenador(userId)
      .then((r) => setLesionesActivas(r.lesiones_activas || []))
      .catch(() => setLesionesActivas([]))
      .finally(() => setLoading(false));
  }, [userId]);

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
      <div>
        <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-orange-400" />
          Lesiones activas
        </h3>
        {loading ? (
          <p className="text-[#8B949E] text-sm">Cargando...</p>
        ) : lesionesActivas.length === 0 ? (
          <div
            className="rounded-xl p-4"
            style={{ background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.2)" }}
          >
            <p className="text-sm text-[#22C55E] font-semibold">Sin lesiones activas</p>
            <p className="text-xs text-[#8B949E] mt-1">El plan se genera sin restricciones de lesión.</p>
          </div>
        ) : (
          lesionesActivas.map((l, i) => (
            <Card
              key={i}
              className="rounded-2xl mb-3"
              style={{
                background: "linear-gradient(135deg, rgba(249,115,22,0.1), rgba(22,27,34,1))",
                border: "1px solid rgba(249,115,22,0.25)",
              }}
            >
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-base font-bold text-white mb-1">{l.tipo}</p>
                    <Badge className="bg-orange-400/15 text-orange-300 border-orange-500/30 text-xs">
                      Activa
                    </Badge>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-[#8B949E]">Grado</p>
                    <p className="text-2xl font-bold text-orange-400">{l.grado}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

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