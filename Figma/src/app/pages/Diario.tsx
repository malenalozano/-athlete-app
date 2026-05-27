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
  Plus,
  Clock,
  Flame,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Activity,
  Zap,
  X,
  Pencil,
  Archive,
  ArchiveRestore,
  Trash2,
  Droplets,
  Info,
  Thermometer,
  Wind,
} from "lucide-react";
import { useState, useEffect } from "react";
import { crearEntradaDiario, getActividades, getEjercicios, getSesionFuerzaHoy, archivarEjercicio, eliminarEjercicio, crearEjercicio, editarEjercicio, getSweatRateTests, crearSweatRateTest, eliminarSweatRateTest, getIntraEntrenoTests, crearIntraEntrenoTest, eliminarIntraEntrenoTest, getIntraEntrenoAnalisis, type ActividadGarmin, type EjercicioBiblioteca, type SesionFuerzaHoy, type GrupoFuerza, type SweatRateTest, type IntraEntrenoTest, type IntraEntrenoAnalisis } from "../api";
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
  const [archivadosAbiertos, setArchivadosAbiertos] = useState(false);

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
                      <button
                        onClick={async () => {
                          if (window.confirm(`¿Eliminar "${ej.nombre}" permanentemente? No se puede deshacer.`)) {
                            await eliminarEjercicio(ej.id); cargar();
                          }
                        }}
                        className="p-1.5 rounded-lg text-[#8B949E] hover:text-red-400 hover:bg-red-500/10 transition-all" title="Eliminar">
                        <Trash2 className="h-3.5 w-3.5" />
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

// ── Intra-Entreno ─────────────────────────────────────────────────────────────

type TipoFuente = "gel" | "solido" | "liquido" | "mixto";

const FUENTE_META: Record<TipoFuente, { label: string; emoji: string; color: string; desc: string }> = {
  gel:     { label: "Gel",     emoji: "🧃", color: "#C9FF00", desc: "Maltodextrina, fructosa (fuente simple)" },
  liquido: { label: "Líquido", emoji: "💧", color: "#00D4FF", desc: "Bebida isotónica, agua con CHO" },
  solido:  { label: "Sólido",  emoji: "🍌", color: "#F97316", desc: "Pan, dátiles, barritas (fuente compleja)" },
  mixto:   { label: "Mixto",   emoji: "🔄", color: "#A855F7", desc: "Combinación gel + sólido" },
};

function malestarColor(m: number): string {
  if (m <= 3) return "#22C55E";
  if (m <= 5) return "#C9FF00";
  if (m <= 7) return "#F97316";
  return "#F43F5E";
}
function malestarLabel(m: number): string {
  if (m <= 2) return "Sin malestar";
  if (m <= 4) return "Leve";
  if (m <= 6) return "Moderado";
  if (m <= 8) return "Alto";
  return "Muy alto";
}

function IntraEntreno() {
  const { userId } = useUser();

  // Formulario
  const [fecha, setFecha]           = useState(() => new Date().toISOString().split("T")[0]);
  const [duracion, setDuracion]     = useState("");
  const [alimentos, setAlimentos]   = useState("");
  const [tipoFuente, setTipoFuente] = useState<TipoFuente>("gel");
  const [choTotal, setChoTotal]     = useState("");
  const [malestar, setMalestar]     = useState<number | null>(null);
  const [notas, setNotas]           = useState("");

  // UI
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]           = useState("");
  const [flashResult, setFlashResult] = useState<{ cho_g_hora: number } | null>(null);

  // Datos
  const [historial, setHistorial]       = useState<IntraEntrenoTest[]>([]);
  const [analisis, setAnalisis]         = useState<IntraEntrenoAnalisis | null>(null);
  const [loadingData, setLoadingData]   = useState(false);

  const cargar = () => {
    if (!userId) return;
    setLoadingData(true);
    Promise.all([
      getIntraEntrenoTests(userId),
      getIntraEntrenoAnalisis(userId),
    ])
      .then(([tests, anal]) => { setHistorial(tests); setAnalisis(anal); })
      .catch(() => null)
      .finally(() => setLoadingData(false));
  };

  useEffect(() => { cargar(); }, [userId]);

  // Preview CHO g/h
  const choPreview = (() => {
    const cho = parseFloat(choTotal);
    const dur = parseFloat(duracion);
    if (!isNaN(cho) && !isNaN(dur) && dur > 0) return cho / (dur / 60);
    return null;
  })();

  const handleGuardar = async () => {
    if (!userId) return;
    const cho = parseFloat(choTotal);
    const dur = parseFloat(duracion);
    if (isNaN(cho) || isNaN(dur) || dur <= 0 || !alimentos.trim() || malestar === null) {
      setError("Rellena todos los campos obligatorios.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const res = await crearIntraEntrenoTest({
        usuario_id: userId,
        fecha,
        duracion_min: dur,
        alimentos: alimentos.trim(),
        tipo_fuente: tipoFuente,
        cho_total_g: cho,
        malestar,
        notas: notas.trim() || undefined,
      });
      setFlashResult({ cho_g_hora: res.cho_g_hora });
      setAlimentos(""); setChoTotal(""); setDuracion(""); setMalestar(null); setNotas("");
      cargar();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEliminar = async (id: number) => {
    if (!window.confirm("¿Eliminar este registro?")) return;
    await eliminarIntraEntrenoTest(id);
    cargar();
  };

  const fuente = FUENTE_META[tipoFuente];

  return (
    <div className="space-y-6">

      {/* ── Header ── */}
      <div
        className="rounded-2xl p-6"
        style={{
          background: "linear-gradient(135deg, rgba(249,115,22,0.12), rgba(201,255,0,0.06))",
          border: "1px solid rgba(249,115,22,0.25)",
        }}
      >
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xl">🍌</span>
          <h2 className="text-xl font-bold text-white">Intra-Entreno</h2>
        </div>
        <p className="text-[#8B949E] text-sm">
          Registra qué comes en cada tirada larga. La app detecta patrones de malestar
          estomacal y te ayuda a optimizar tu estrategia de carbohidratos.
        </p>
      </div>

      {/* ── Alerta de patrón (si hay suficientes datos) ── */}
      {analisis?.alerta && (
        <div
          className="rounded-2xl p-5 space-y-2"
          style={{
            background: "rgba(244,63,94,0.08)",
            border: "1px solid rgba(244,63,94,0.4)",
            boxShadow: "0 0 24px rgba(244,63,94,0.12)",
          }}
        >
          <div className="flex items-center gap-2">
            <span className="text-lg">⚠️</span>
            <p className="text-sm font-bold text-white">Patrón detectado — Límite de absorción</p>
            <span
              className="text-[10px] font-bold px-2 py-0.5 rounded-full"
              style={{ background: "rgba(244,63,94,0.15)", color: "#F43F5E", border: "1px solid rgba(244,63,94,0.3)" }}
            >
              {analisis.alerta.muestras_mal} muestras
            </span>
          </div>
          <p className="text-sm text-[#8B949E] leading-relaxed">{analisis.alerta.mensaje}</p>
          <div className="grid grid-cols-3 gap-3 pt-1">
            {[
              { label: "Límite sólidos", value: `${analisis.alerta.limite_solidos_gh}g/h`, color: "#F97316" },
              { label: "Objetivo", value: `${analisis.alerta.objetivo_gh}g/h`, color: "#C9FF00" },
              { label: "Añadir líquido", value: `+${analisis.alerta.diferencia_liquido_gh}g/h`, color: "#00D4FF" },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-xl p-2.5 text-center" style={{ background: `${color}10`, border: `1px solid ${color}30` }}>
                <p className="text-base font-black" style={{ color }}>{value}</p>
                <p className="text-[9px] text-[#8B949E] uppercase tracking-wider mt-0.5">{label}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Resumen sin alerta ── */}
      {analisis?.suficientes_datos && !analisis.alerta && analisis.resumen && (
        <div
          className="rounded-2xl p-4 flex items-center gap-4"
          style={{ background: "rgba(34,197,94,0.07)", border: "1px solid rgba(34,197,94,0.25)" }}
        >
          <span className="text-2xl">✅</span>
          <div>
            <p className="text-sm font-bold text-white">Sin patrones de malestar detectados</p>
            <p className="text-xs text-[#8B949E]">
              Media: <span className="text-white font-semibold">{analisis.resumen.media_cho_gh}g/h</span> con malestar medio de{" "}
              <span className="text-white font-semibold">{analisis.resumen.media_malestar}/10</span> en {analisis.resumen.n_total} registros con sólidos.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

        {/* ── Formulario ── */}
        <div className="lg:col-span-2">
          <div
            className="rounded-2xl p-5 space-y-4"
            style={{ background: "#161B22", border: "1px solid rgba(249,115,22,0.2)" }}
          >
            <p className="text-xs font-bold text-[#8B949E] uppercase tracking-widest">Nuevo registro</p>

            {/* Fecha */}
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest mb-1.5 text-[#F97316]">Fecha</p>
              <input
                type="date"
                value={fecha}
                onChange={(e) => setFecha(e.target.value)}
                className="w-full rounded-xl px-3 py-2 text-sm text-white bg-[#0E1117] border focus:outline-none"
                style={{ borderColor: "rgba(249,115,22,0.3)" }}
              />
            </div>

            {/* Duración */}
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest mb-1.5 text-[#A855F7]">Duración del entreno (min)</p>
              <input
                type="number"
                step="5"
                value={duracion}
                onChange={(e) => setDuracion(e.target.value)}
                placeholder="120"
                className="w-full rounded-xl px-3 py-2 text-sm text-white bg-[#0E1117] border focus:outline-none text-center font-bold"
                style={{ borderColor: "rgba(168,85,247,0.3)" }}
              />
            </div>

            {/* Tipo de fuente */}
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest mb-2 text-[#C9FF00]">Tipo de fuente</p>
              <div className="grid grid-cols-2 gap-2">
                {(Object.entries(FUENTE_META) as [TipoFuente, typeof FUENTE_META[TipoFuente]][]).map(([key, meta]) => (
                  <button
                    key={key}
                    onClick={() => setTipoFuente(key)}
                    className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all"
                    style={
                      tipoFuente === key
                        ? { background: `${meta.color}18`, border: `1px solid ${meta.color}60`, color: meta.color, boxShadow: `0 0 10px ${meta.color}20` }
                        : { background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", color: "#8B949E" }
                    }
                  >
                    <span>{meta.emoji}</span>
                    <div className="text-left">
                      <p className="font-bold leading-tight">{meta.label}</p>
                      <p className="text-[9px] opacity-70 font-normal leading-tight">{meta.desc.split("(")[0].trim()}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Alimentos */}
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest mb-1.5" style={{ color: fuente.color }}>
                ¿Qué comiste? *
              </p>
              <textarea
                value={alimentos}
                onChange={(e) => setAlimentos(e.target.value)}
                placeholder={
                  tipoFuente === "gel"
                    ? "Ej: 3 geles Maurten 100, 1 gel SIS"
                    : tipoFuente === "solido"
                    ? "Ej: 2 trozos pan de plátano con avena, 4 dátiles"
                    : tipoFuente === "liquido"
                    ? "Ej: 500ml bebida isotónica, 2 bidones con Tailwind"
                    : "Ej: 2 geles + 1 barrita de dátiles"
                }
                rows={2}
                className="w-full rounded-xl px-3 py-2 text-sm text-white resize-none focus:outline-none"
                style={{ background: "rgba(14,17,23,0.8)", border: `1px solid ${fuente.color}30` }}
              />
            </div>

            {/* CHO total */}
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest mb-1.5 text-[#C9FF00]">
                Carbohidratos totales (g) *
              </p>
              <input
                type="number"
                step="5"
                value={choTotal}
                onChange={(e) => setChoTotal(e.target.value)}
                placeholder="180"
                className="w-full rounded-xl px-3 py-2 text-sm text-white bg-[#0E1117] border focus:outline-none text-center font-bold"
                style={{ borderColor: "rgba(201,255,0,0.35)" }}
              />
              {choPreview !== null && (
                <p className="text-[11px] mt-1.5 text-center font-bold" style={{ color: "#C9FF00" }}>
                  → {choPreview.toFixed(1)} g/h
                </p>
              )}
            </div>

            {/* Malestar */}
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest mb-2 text-white">
                Malestar estomacal *
                {malestar !== null && (
                  <span className="ml-2 font-black" style={{ color: malestarColor(malestar) }}>
                    {malestar}/10 — {malestarLabel(malestar)}
                  </span>
                )}
              </p>
              <div className="grid grid-cols-5 gap-1.5">
                {[1,2,3,4,5,6,7,8,9,10].map((n) => {
                  const col = malestarColor(n);
                  const active = malestar === n;
                  return (
                    <button
                      key={n}
                      onClick={() => setMalestar(n)}
                      className="py-2 rounded-xl text-sm font-black transition-all"
                      style={
                        active
                          ? { background: `${col}25`, border: `2px solid ${col}`, color: col, boxShadow: `0 0 12px ${col}40` }
                          : { background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "#4B5563" }
                      }
                    >
                      {n}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Notas */}
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest mb-1.5 text-[#8B949E]">Notas (opcional)</p>
              <textarea
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
                placeholder="Calor, ritmo, tipo de terreno..."
                rows={2}
                className="w-full rounded-xl px-3 py-2 text-sm text-white resize-none focus:outline-none"
                style={{ background: "rgba(14,17,23,0.8)", border: "1px solid rgba(48,54,61,0.6)" }}
              />
            </div>

            {error && <p className="text-xs text-red-400">{error}</p>}

            <button
              onClick={handleGuardar}
              disabled={submitting || malestar === null || !alimentos.trim() || choPreview === null}
              className="w-full py-3 rounded-xl text-sm font-bold transition-all disabled:opacity-40"
              style={{
                background: "linear-gradient(135deg, #F97316, #fb923c)",
                color: "#0E1117",
                boxShadow: "0 0 20px rgba(249,115,22,0.3)",
              }}
            >
              {submitting ? "Guardando..." : "💾 Guardar registro"}
            </button>
          </div>
        </div>

        {/* ── Historial ── */}
        <div className="lg:col-span-3 space-y-4">

          {/* Flash resultado */}
          {flashResult && (
            <div
              className="rounded-2xl p-4 flex items-center justify-between gap-4"
              style={{ background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.3)" }}
            >
              <div>
                <p className="text-xs font-bold text-[#22C55E] uppercase tracking-widest mb-0.5">✅ Guardado</p>
                <p className="text-2xl font-black text-white">
                  {flashResult.cho_g_hora.toFixed(1)}{" "}
                  <span className="text-sm font-bold text-[#8B949E]">g/h</span>
                </p>
              </div>
              <button onClick={() => setFlashResult(null)} className="text-[#8B949E] hover:text-white transition-colors">
                <X className="h-4 w-4" />
              </button>
            </div>
          )}

          {/* Tabla historial */}
          <div
            className="rounded-2xl overflow-hidden"
            style={{ background: "#161B22", border: "1px solid rgba(249,115,22,0.15)" }}
          >
            <div
              className="px-5 py-3 flex items-center justify-between"
              style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
            >
              <p className="text-xs font-bold uppercase tracking-widest text-[#8B949E]">Historial</p>
              <div className="flex items-center gap-2">
                {analisis && (
                  <span className="text-[10px] text-[#8B949E]">
                    {analisis.n_solido} sólido · {analisis.n_gel} gel/líq
                  </span>
                )}
                <span
                  className="text-xs px-2 py-0.5 rounded-full font-bold"
                  style={{ background: "rgba(249,115,22,0.12)", color: "#F97316", border: "1px solid rgba(249,115,22,0.25)" }}
                >
                  {historial.length} registros
                </span>
              </div>
            </div>

            {loadingData ? (
              <div className="p-8 text-center">
                <p className="text-sm text-[#8B949E]">Cargando...</p>
              </div>
            ) : historial.length === 0 ? (
              <div className="p-10 text-center space-y-2">
                <span className="text-4xl">🍌</span>
                <p className="text-sm text-[#8B949E]">Aún no hay registros.</p>
                <p className="text-xs text-[#30363D]">Añade tu próxima tirada larga para empezar a detectar patrones.</p>
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {historial.map((t) => {
                  const fm = FUENTE_META[t.tipo_fuente as TipoFuente] ?? FUENTE_META.mixto;
                  const mc = malestarColor(t.malestar);
                  return (
                    <div key={t.id} className="px-5 py-4 space-y-2">
                      <div className="flex items-start gap-3">
                        {/* CHO g/h */}
                        <div className="text-center shrink-0 w-16">
                          <p className="text-xl font-black" style={{ color: fm.color }}>
                            {t.cho_g_hora.toFixed(0)}
                          </p>
                          <p className="text-[9px] font-bold uppercase" style={{ color: fm.color }}>g/h</p>
                        </div>

                        {/* Info principal */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                            <p className="text-sm font-semibold text-white">
                              {new Date(t.fecha + "T12:00:00").toLocaleDateString("es-ES", { day: "numeric", month: "short" })}
                            </p>
                            <span
                              className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                              style={{ background: `${fm.color}18`, color: fm.color, border: `1px solid ${fm.color}35` }}
                            >
                              {fm.emoji} {fm.label}
                            </span>
                            {/* Malestar badge */}
                            <span
                              className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                              style={{ background: `${mc}18`, color: mc, border: `1px solid ${mc}35` }}
                            >
                              😣 {t.malestar}/10
                            </span>
                          </div>
                          <p className="text-xs text-white truncate">{t.alimentos}</p>
                          <div className="flex items-center gap-3 text-[10px] text-[#8B949E] mt-0.5 flex-wrap">
                            <span>⏱ {t.duracion_min} min</span>
                            <span>🍞 {t.cho_total_g}g total</span>
                          </div>
                          {t.notas && (
                            <p className="text-[10px] text-[#6B7280] italic mt-0.5 truncate">"{t.notas}"</p>
                          )}
                        </div>

                        {/* Malestar visual */}
                        <div className="shrink-0 text-center hidden sm:block w-10">
                          <div
                            className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-black mx-auto"
                            style={{ background: `${mc}20`, border: `2px solid ${mc}60`, color: mc }}
                          >
                            {t.malestar}
                          </div>
                          <p className="text-[8px] text-[#8B949E] mt-0.5">{malestarLabel(t.malestar)}</p>
                        </div>

                        {/* Eliminar */}
                        <button
                          onClick={() => handleEliminar(t.id)}
                          className="p-2 rounded-lg text-[#8B949E] hover:text-red-400 hover:bg-red-500/10 transition-all shrink-0"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Info sobre el análisis */}
          {!analisis?.suficientes_datos && historial.length > 0 && (
            <div
              className="rounded-2xl p-4"
              style={{ background: "rgba(249,115,22,0.05)", border: "1px solid rgba(249,115,22,0.2)" }}
            >
              <p className="text-xs font-bold text-[#F97316] mb-1">📊 Análisis en curso</p>
              <p className="text-xs text-[#8B949E]">
                Necesitas al menos <strong className="text-white">2 registros con sólidos o mixto</strong> para detectar patrones.
                Actualmente tienes {analisis?.n_solido ?? 0}.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


// ── Sweat Rate ────────────────────────────────────────────────────────────────

function SweatRate() {
  const { userId } = useUser();

  // Formulario
  const [fecha, setFecha] = useState(() => new Date().toISOString().split("T")[0]);
  const [pesoInicial, setPesoInicial] = useState("");
  const [pesoFinal, setPesoFinal] = useState("");
  const [liquidos, setLiquidos] = useState("");
  const [tiempo, setTiempo] = useState("");
  const [temperatura, setTemperatura] = useState("");
  const [humedad, setHumedad] = useState("");
  const [notas, setNotas] = useState("");

  // UI
  const [showProtocolo, setShowProtocolo] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [resultadoLocal, setResultadoLocal] = useState<number | null>(null);

  // Historial
  const [historial, setHistorial] = useState<SweatRateTest[]>([]);
  const [loadingHistorial, setLoadingHistorial] = useState(false);

  const cargarHistorial = () => {
    if (!userId) return;
    setLoadingHistorial(true);
    getSweatRateTests(userId)
      .then(setHistorial)
      .catch(() => null)
      .finally(() => setLoadingHistorial(false));
  };

  useEffect(() => { cargarHistorial(); }, [userId]);

  // Cálculo en tiempo real
  const tasaPreview = (() => {
    const pi = parseFloat(pesoInicial);
    const pf = parseFloat(pesoFinal);
    const liq = parseFloat(liquidos);
    const t = parseFloat(tiempo);
    if (!isNaN(pi) && !isNaN(pf) && !isNaN(liq) && !isNaN(t) && t > 0) {
      return ((pi - pf) + liq / 1000) / (t / 60);
    }
    return null;
  })();

  const handleGuardar = async () => {
    if (!userId) return;
    const pi = parseFloat(pesoInicial);
    const pf = parseFloat(pesoFinal);
    const liq = parseFloat(liquidos);
    const t = parseFloat(tiempo);
    if (isNaN(pi) || isNaN(pf) || isNaN(liq) || isNaN(t) || t <= 0) {
      setError("Rellena todos los campos obligatorios con valores válidos.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const res = await crearSweatRateTest({
        usuario_id: userId,
        fecha,
        peso_inicial_kg: pi,
        peso_final_kg: pf,
        liquidos_ml: liq,
        tiempo_min: t,
        temperatura_c: temperatura ? parseFloat(temperatura) : null,
        humedad_pct: humedad ? parseFloat(humedad) : null,
        notas: notas.trim() || undefined,
      });
      setResultadoLocal(res.tasa_sudoracion_lh);
      // Reset form
      setPesoInicial(""); setPesoFinal(""); setLiquidos("");
      setTiempo(""); setTemperatura(""); setHumedad(""); setNotas("");
      cargarHistorial();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEliminar = async (id: number) => {
    if (!window.confirm("¿Eliminar este test?")) return;
    await eliminarSweatRateTest(id);
    cargarHistorial();
  };

  const tasaColor = (tasa: number) => {
    if (tasa < 0.5) return "#60A5FA";
    if (tasa < 1.0) return "#C9FF00";
    if (tasa < 1.5) return "#F97316";
    return "#F43F5E";
  };

  const tasaLabel = (tasa: number) => {
    if (tasa < 0.5) return "Baja";
    if (tasa < 1.0) return "Normal";
    if (tasa < 1.5) return "Alta";
    return "Muy alta";
  };

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div
        className="rounded-2xl p-6 relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, rgba(0,212,255,0.12), rgba(96,165,250,0.08))",
          border: "1px solid rgba(0,212,255,0.25)",
        }}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Droplets className="h-5 w-5" style={{ color: "#00D4FF" }} />
              <h2 className="text-xl font-bold text-white">Sweat Rate</h2>
            </div>
            <p className="text-[#8B949E] text-sm">
              Calcula tu tasa de sudoración por hora para optimizar la hidratación en carrera.
            </p>
          </div>
          {/* Botón protocolo */}
          <button
            onClick={() => setShowProtocolo(!showProtocolo)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold shrink-0 transition-all"
            style={{
              background: showProtocolo ? "rgba(0,212,255,0.15)" : "rgba(255,255,255,0.05)",
              border: showProtocolo ? "1px solid rgba(0,212,255,0.5)" : "1px solid rgba(255,255,255,0.1)",
              color: showProtocolo ? "#00D4FF" : "#8B949E",
            }}
          >
            <Info className="h-3.5 w-3.5" />
            Protocolo
          </button>
        </div>

        {/* Panel de protocolo — colapsable */}
        {showProtocolo && (
          <div
            className="mt-4 rounded-xl p-4 space-y-3 text-sm"
            style={{ background: "rgba(0,212,255,0.06)", border: "1px solid rgba(0,212,255,0.2)" }}
          >
            <p className="font-bold text-white flex items-center gap-2">
              <span>📋</span> Cómo hacer la prueba correctamente
            </p>
            <div className="space-y-2 text-[#8B949E]">
              <div className="flex gap-2">
                <span className="font-bold shrink-0" style={{ color: "#00D4FF" }}>ANTES</span>
                <span>Ve al baño. Pésate completamente desnudo/a (la ropa mojada de sudor suma peso falso).</span>
              </div>
              <div className="flex gap-2">
                <span className="font-bold shrink-0" style={{ color: "#C9FF00" }}>DURANTE</span>
                <span>Entrena al ritmo e intensidad objetivo (1–2 h de volumen aeróbico). Si bebes agua, mide exactamente los mililitros. <strong className="text-white">No vayas al baño</strong> durante la prueba.</span>
              </div>
              <div className="flex gap-2">
                <span className="font-bold shrink-0" style={{ color: "#A855F7" }}>DESPUÉS</span>
                <span>Sécate bien el sudor con una toalla. Pésate de nuevo completamente desnudo/a.</span>
              </div>
            </div>
            <div
              className="rounded-lg p-3 text-xs"
              style={{ background: "rgba(201,255,0,0.07)", border: "1px solid rgba(201,255,0,0.2)", color: "#8B949E" }}
            >
              <p className="font-bold text-white mb-1">💡 Fórmula</p>
              <p>Tasa (L/h) = (Peso inicial − Peso final + Líquidos bebidos en L) ÷ Tiempo en horas</p>
              <p className="mt-1">
                Guarda también la temperatura y humedad del día.
                Así la app podrá cruzar la previsión meteorológica con tus datos
                y decirte exactamente cuánto beber en tu próxima carrera.
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* ── Formulario ── */}
        <div className="lg:col-span-2">
          <div
            className="rounded-2xl p-5 space-y-4"
            style={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.2)" }}
          >
            <p className="text-xs font-bold text-[#8B949E] uppercase tracking-widest">Nueva prueba</p>

            {/* Fecha */}
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest mb-1.5" style={{ color: "#00D4FF" }}>Fecha</p>
              <input
                type="date"
                value={fecha}
                onChange={(e) => setFecha(e.target.value)}
                className="w-full rounded-xl px-3 py-2 text-sm text-white bg-[#0E1117] border focus:outline-none"
                style={{ borderColor: "rgba(0,212,255,0.3)" }}
              />
            </div>

            {/* Pesos */}
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Peso Inicial", unit: "kg", value: pesoInicial, set: setPesoInicial, placeholder: "58.2", color: "#C9FF00" },
                { label: "Peso Final", unit: "kg", value: pesoFinal, set: setPesoFinal, placeholder: "57.5", color: "#F43F5E" },
              ].map(({ label, unit, value, set, placeholder, color }) => (
                <div key={label}>
                  <p className="text-[10px] font-semibold uppercase tracking-widest mb-1.5" style={{ color }}>{label} ({unit})</p>
                  <input
                    type="number"
                    step="0.1"
                    value={value}
                    onChange={(e) => set(e.target.value)}
                    placeholder={placeholder}
                    className="w-full rounded-xl px-3 py-2 text-sm text-white bg-[#0E1117] border focus:outline-none text-center font-bold"
                    style={{ borderColor: `${color}40` }}
                  />
                </div>
              ))}
            </div>

            {/* Líquidos y tiempo */}
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Líquidos bebidos", unit: "mL", value: liquidos, set: setLiquidos, placeholder: "500", color: "#60A5FA" },
                { label: "Duración", unit: "min", value: tiempo, set: setTiempo, placeholder: "60", color: "#A855F7" },
              ].map(({ label, unit, value, set, placeholder, color }) => (
                <div key={label}>
                  <p className="text-[10px] font-semibold uppercase tracking-widest mb-1.5" style={{ color }}>{label} ({unit})</p>
                  <input
                    type="number"
                    step="1"
                    value={value}
                    onChange={(e) => set(e.target.value)}
                    placeholder={placeholder}
                    className="w-full rounded-xl px-3 py-2 text-sm text-white bg-[#0E1117] border focus:outline-none text-center font-bold"
                    style={{ borderColor: `${color}40` }}
                  />
                </div>
              ))}
            </div>

            {/* Temperatura y humedad — opcionales */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest mb-1.5 flex items-center gap-1" style={{ color: "#F97316" }}>
                  <Thermometer className="h-3 w-3" /> Temp. (°C) <span className="text-[#30363D] normal-case font-normal">opt.</span>
                </p>
                <input
                  type="number"
                  step="0.5"
                  value={temperatura}
                  onChange={(e) => setTemperatura(e.target.value)}
                  placeholder="22"
                  className="w-full rounded-xl px-3 py-2 text-sm text-white bg-[#0E1117] border focus:outline-none text-center"
                  style={{ borderColor: "rgba(249,115,22,0.3)" }}
                />
              </div>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest mb-1.5 flex items-center gap-1" style={{ color: "#6B7280" }}>
                  <Wind className="h-3 w-3" /> Humedad (%) <span className="text-[#30363D] normal-case font-normal">opt.</span>
                </p>
                <input
                  type="number"
                  step="1"
                  value={humedad}
                  onChange={(e) => setHumedad(e.target.value)}
                  placeholder="60"
                  className="w-full rounded-xl px-3 py-2 text-sm text-white bg-[#0E1117] border focus:outline-none text-center"
                  style={{ borderColor: "rgba(107,114,128,0.3)" }}
                />
              </div>
            </div>

            {/* Notas */}
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest mb-1.5 text-[#8B949E]">Notas (opcional)</p>
              <textarea
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
                placeholder="Ej: Z2 en tapiz, calor elevado..."
                rows={2}
                className="w-full rounded-xl px-3 py-2 text-sm text-white resize-none focus:outline-none"
                style={{ background: "rgba(14,17,23,0.8)", border: "1px solid rgba(48,54,61,0.6)" }}
              />
            </div>

            {/* Preview resultado */}
            {tasaPreview !== null && (
              <div
                className="rounded-xl p-3 text-center"
                style={{
                  background: `${tasaColor(tasaPreview)}12`,
                  border: `1px solid ${tasaColor(tasaPreview)}40`,
                }}
              >
                <p className="text-[10px] text-[#8B949E] uppercase tracking-widest mb-0.5">Resultado estimado</p>
                <p className="text-3xl font-black" style={{ color: tasaColor(tasaPreview) }}>
                  {tasaPreview.toFixed(2)} <span className="text-base font-bold">L/h</span>
                </p>
                <p className="text-xs font-bold mt-0.5" style={{ color: tasaColor(tasaPreview) }}>
                  {tasaLabel(tasaPreview)}
                </p>
              </div>
            )}

            {error && <p className="text-xs text-red-400">{error}</p>}

            <button
              onClick={handleGuardar}
              disabled={submitting || tasaPreview === null}
              className="w-full py-3 rounded-xl text-sm font-bold transition-all disabled:opacity-40"
              style={{
                background: "linear-gradient(135deg, #00D4FF, #60A5FA)",
                color: "#0E1117",
                boxShadow: "0 0 20px rgba(0,212,255,0.3)",
              }}
            >
              {submitting ? "Guardando..." : "💾 Guardar test"}
            </button>
          </div>
        </div>

        {/* ── Historial ── */}
        <div className="lg:col-span-3 space-y-4">
          {/* Resultado flash tras guardar */}
          {resultadoLocal !== null && (
            <div
              className="rounded-2xl p-5 text-center"
              style={{
                background: `${tasaColor(resultadoLocal)}12`,
                border: `1px solid ${tasaColor(resultadoLocal)}40`,
              }}
            >
              <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: tasaColor(resultadoLocal) }}>
                ✅ Test guardado
              </p>
              <p className="text-4xl font-black text-white">
                {resultadoLocal.toFixed(2)}{" "}
                <span className="text-lg font-bold text-[#8B949E]">L/h</span>
              </p>
              <p className="text-sm mt-1" style={{ color: tasaColor(resultadoLocal) }}>
                {tasaLabel(resultadoLocal)} sudoración — necesitas ~{Math.round(resultadoLocal * 1000)} mL/h
              </p>
              <button
                onClick={() => setResultadoLocal(null)}
                className="mt-3 text-xs text-[#8B949E] hover:text-white transition-colors"
              >
                Cerrar
              </button>
            </div>
          )}

          {/* Tabla historial */}
          <div
            className="rounded-2xl overflow-hidden"
            style={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.15)" }}
          >
            <div className="px-5 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
              <p className="text-xs font-bold uppercase tracking-widest text-[#8B949E]">Historial de tests</p>
              <span className="text-xs px-2 py-0.5 rounded-full font-bold" style={{ background: "rgba(0,212,255,0.12)", color: "#00D4FF", border: "1px solid rgba(0,212,255,0.25)" }}>
                {historial.length} test{historial.length !== 1 ? "s" : ""}
              </span>
            </div>

            {loadingHistorial ? (
              <div className="p-8 text-center">
                <p className="text-sm text-[#8B949E]">Cargando...</p>
              </div>
            ) : historial.length === 0 ? (
              <div className="p-10 text-center space-y-2">
                <Droplets className="h-8 w-8 mx-auto text-[#30363D]" />
                <p className="text-sm text-[#8B949E]">Aún no tienes tests guardados.</p>
                <p className="text-xs text-[#30363D]">Haz tu primera prueba y descubre tu tasa de sudoración.</p>
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {historial.map((t) => {
                  const color = tasaColor(t.tasa_sudoracion_lh);
                  return (
                    <div key={t.id} className="px-5 py-4 flex items-center gap-4">
                      {/* Tasa grande */}
                      <div className="text-center shrink-0 w-16">
                        <p className="text-2xl font-black" style={{ color }}>
                          {t.tasa_sudoracion_lh.toFixed(2)}
                        </p>
                        <p className="text-[9px] font-bold uppercase" style={{ color }}>L/h</p>
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                          <p className="text-sm font-semibold text-white">
                            {new Date(t.fecha + "T12:00:00").toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" })}
                          </p>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: `${color}18`, color, border: `1px solid ${color}35` }}>
                            {tasaLabel(t.tasa_sudoracion_lh)}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-[#8B949E] flex-wrap">
                          <span>⚖️ {t.peso_inicial_kg}→{t.peso_final_kg} kg</span>
                          <span>💧 {t.liquidos_ml} mL</span>
                          <span>⏱ {t.tiempo_min} min</span>
                          {t.temperatura_c != null && (
                            <span className="flex items-center gap-0.5">
                              <Thermometer className="h-3 w-3" style={{ color: "#F97316" }} />
                              {t.temperatura_c}°C
                            </span>
                          )}
                          {t.humedad_pct != null && (
                            <span className="flex items-center gap-0.5">
                              <Wind className="h-3 w-3 text-[#6B7280]" />
                              {t.humedad_pct}%
                            </span>
                          )}
                        </div>
                        {t.notas && (
                          <p className="text-[10px] text-[#6B7280] mt-0.5 italic truncate">"{t.notas}"</p>
                        )}
                      </div>

                      {/* Hidratación recomendada */}
                      <div className="text-center shrink-0 hidden sm:block">
                        <p className="text-sm font-black text-white">{Math.round(t.tasa_sudoracion_lh * 1000)}</p>
                        <p className="text-[9px] text-[#8B949E]">mL/h</p>
                      </div>

                      {/* Eliminar */}
                      <button
                        onClick={() => handleEliminar(t.id)}
                        className="p-2 rounded-lg text-[#8B949E] hover:text-red-400 hover:bg-red-500/10 transition-all shrink-0"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Info card — futura integración meteorológica */}
          {historial.length > 0 && (
            <div
              className="rounded-2xl p-4"
              style={{ background: "rgba(201,255,0,0.04)", border: "1px solid rgba(201,255,0,0.15)" }}
            >
              <p className="text-xs font-bold text-[#C9FF00] mb-1">🔮 Próximamente</p>
              <p className="text-xs text-[#8B949E]">
                La app cruzará la previsión meteorológica del día de tu carrera con tu base de datos de sweat rate
                y te dirá exactamente cuánto beber por hora.
              </p>
            </div>
          )}
        </div>
      </div>
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
        {safeTab === "sweat-rate" && <SweatRate />}
        {safeTab === "intra-entreno" && <IntraEntreno />}
      </main>
    </div>
  );
}