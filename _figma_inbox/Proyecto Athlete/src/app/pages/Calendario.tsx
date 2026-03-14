import { Header } from "../components/Header";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "../components/ui/accordion";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Clock3,
  MapPin,
  Target,
} from "lucide-react";
import { useState } from "react";
import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  isToday,
  parseISO,
  startOfMonth,
  startOfWeek,
  subMonths,
} from "date-fns";
import { es } from "date-fns/locale";

type CalendarBlock = {
  label: string;
  detail: string;
};

type CalendarSession = {
  id: string;
  date: string;
  title: string;
  category: "running" | "fuerza" | "recuperacion";
  duration: string;
  objective: string;
  location: string;
  summary: string;
  blocks: CalendarBlock[];
};

const weekDays = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"];

const calendarSessions: CalendarSession[] = [
  {
    id: "cal-1",
    date: "2026-03-02",
    title: "Fuerza de pierna",
    category: "fuerza",
    duration: "70 min",
    objective: "Base de fuerza y estabilidad",
    location: "Gimnasio",
    summary: "Sentadilla, hip thrust y trabajo unilateral.",
    blocks: [
      { label: "Sentadilla", detail: "4x6 a 82.5 kg, RPE 7" },
      { label: "Hip thrust", detail: "4x8 a 90 kg" },
      { label: "Bulgaras", detail: "3x10 por pierna" },
    ],
  },
  {
    id: "cal-2",
    date: "2026-03-05",
    title: "Rodaje suave",
    category: "running",
    duration: "48 min",
    objective: "Recuperar sin fatiga",
    location: "Casa de Campo",
    summary: "Rodaje facil con 4 progresivos al final.",
    blocks: [
      { label: "Rodaje", detail: "9 km en Z2" },
      { label: "Progresivos", detail: "4x80 m con recuperacion completa" },
    ],
  },
  {
    id: "cal-3",
    date: "2026-03-08",
    title: "Tirada larga",
    category: "running",
    duration: "1 h 50 min",
    objective: "Construir resistencia especifica",
    location: "Madrid Rio",
    summary: "Salida larga estable con final progresivo.",
    blocks: [
      { label: "Bloque principal", detail: "22 km en Z2" },
      { label: "Final", detail: "Ultimos 15 min en Z3 controlada" },
      { label: "Nutricion", detail: "2 geles y 500 ml isotonic" },
    ],
  },
  {
    id: "cal-4",
    date: "2026-03-11",
    title: "Torso y core",
    category: "fuerza",
    duration: "62 min",
    objective: "Empuje, traccion y control escapular",
    location: "Gimnasio",
    summary: "Press banca, remo y accesorios de hombro.",
    blocks: [
      { label: "Press banca", detail: "4x6 a 60 kg" },
      { label: "Remo con mancuerna", detail: "4x10 por lado" },
      { label: "Pallof press", detail: "3x12 por lado" },
    ],
  },
  {
    id: "cal-5",
    date: "2026-03-14",
    title: "Series umbral",
    category: "running",
    duration: "78 min",
    objective: "Mejorar tolerancia al ritmo de umbral",
    location: "Pista",
    summary: "Sesion de calidad con recuperaciones amplias.",
    blocks: [
      { label: "Calentamiento", detail: "15 min + movilidad" },
      { label: "Serie principal", detail: "3x10 min a 4:28/km" },
      { label: "Vuelta a la calma", detail: "12 min suaves" },
    ],
  },
  {
    id: "cal-6",
    date: "2026-03-18",
    title: "Movilidad y descarga",
    category: "recuperacion",
    duration: "35 min",
    objective: "Soltar cadera y descargar lumbar",
    location: "Casa",
    summary: "Sesion suave de movilidad y activacion.",
    blocks: [
      { label: "Movilidad", detail: "12 min de cadera y tobillo" },
      { label: "Activacion", detail: "Monster walks 3x15" },
      { label: "Respiracion", detail: "5 min 90/90" },
    ],
  },
  {
    id: "cal-7",
    date: "2026-03-22",
    title: "Tirada larga progresiva",
    category: "running",
    duration: "2 h 02 min",
    objective: "Acumular volumen con buen cierre",
    location: "Anillo Verde",
    summary: "Volumen alto con ultimo bloque algo mas alegre.",
    blocks: [
      { label: "Parte 1", detail: "18 km en Z2" },
      { label: "Parte 2", detail: "6 km progresivos" },
      { label: "Recuperacion", detail: "Estiramientos 10 min" },
    ],
  },
  {
    id: "cal-8",
    date: "2026-03-26",
    title: "Fuerza total body",
    category: "fuerza",
    duration: "68 min",
    objective: "Mantener fuerza sin fatigar en exceso",
    location: "Gimnasio",
    summary: "Trabajo general con cargas medias.",
    blocks: [
      { label: "Peso muerto rumano", detail: "4x8 a 70 kg" },
      { label: "Press inclinado", detail: "3x10" },
      { label: "Remo polea", detail: "3x12" },
    ],
  },
];

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function getCategoryStyles(category: CalendarSession["category"]) {
  if (category === "running") {
    return {
      badge: "bg-sky-500/15 text-sky-200 border-sky-400/25",
      accent: "border-sky-400/20",
    };
  }

  if (category === "fuerza") {
    return {
      badge: "bg-[#C9FF00]/12 text-[#E8FF8A] border-[#C9FF00]/25",
      accent: "border-[#C9FF00]/20",
    };
  }

  return {
    badge: "bg-orange-500/12 text-orange-200 border-orange-400/25",
    accent: "border-orange-400/20",
  };
}

export function Calendario() {
  const [currentMonth, setCurrentMonth] = useState(startOfMonth(new Date()));

  const calendarDays = eachDayOfInterval({
    start: startOfWeek(startOfMonth(currentMonth), { weekStartsOn: 1 }),
    end: endOfWeek(endOfMonth(currentMonth), { weekStartsOn: 1 }),
  });
  const monthSessions = calendarSessions.filter((session) =>
    isSameMonth(parseISO(session.date), currentMonth),
  );

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8">
        <h2 className="text-2xl font-semibold mb-4 text-white">Calendario de Entrenamientos</h2>
        <p className="mb-8 max-w-3xl text-[#8B949E]">
          Vista mensual limpia para revisar que se entreno cada dia. El nombre de cada sesion se
          puede abrir para ver bloques, objetivo y contexto del entrenamiento.
        </p>

        <Card className="overflow-hidden rounded-2xl border border-[#C9FF00]/20 bg-[#161B22] shadow-[0_20px_60px_rgba(0,0,0,0.25)]">
          <CardHeader className="border-b border-white/5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-white">
                  <CalendarIcon className="h-5 w-5 text-[#C9FF00]" />
                  Plan mensual visible
                </CardTitle>
                <p className="mt-2 text-sm text-[#8B949E]">
                  {monthSessions.length} sesiones registradas en {format(currentMonth, "MMMM", { locale: es })}.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="icon"
                  className="rounded-xl border-white/10 bg-[#0E1117] text-white hover:bg-[#1B2230]"
                  onClick={() => setCurrentMonth((month) => subMonths(month, 1))}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <div className="min-w-44 rounded-xl border border-white/8 bg-[#0E1117] px-4 py-2 text-center text-white">
                  <div className="text-xs uppercase tracking-[0.22em] text-[#8B949E]">Mes</div>
                  <div className="text-lg font-semibold">
                    {capitalize(format(currentMonth, "MMMM yyyy", { locale: es }))}
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  className="rounded-xl border-white/10 bg-[#0E1117] text-white hover:bg-[#1B2230]"
                  onClick={() => setCurrentMonth((month) => addMonths(month, 1))}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-4 md:p-6">
            <div className="mb-4 flex flex-wrap gap-3 text-xs text-[#8B949E]">
              <span className="rounded-full border border-sky-400/20 bg-sky-500/10 px-3 py-1 text-sky-200">Running</span>
              <span className="rounded-full border border-[#C9FF00]/20 bg-[#C9FF00]/10 px-3 py-1 text-[#E8FF8A]">Fuerza</span>
              <span className="rounded-full border border-orange-400/20 bg-orange-500/10 px-3 py-1 text-orange-200">Recuperacion</span>
              <span className="rounded-full border border-white/8 bg-white/5 px-3 py-1">Haz clic sobre el nombre para desplegar</span>
            </div>

            <div className="overflow-x-auto pb-2">
              <div className="min-w-[980px]">
                <div className="mb-3 grid grid-cols-7 gap-3">
                  {weekDays.map((day) => (
                    <div
                      key={day}
                      className="rounded-xl border border-white/6 bg-[#0E1117] px-3 py-2 text-center text-xs font-semibold uppercase tracking-[0.18em] text-[#8B949E]"
                    >
                      {day}
                    </div>
                  ))}
                </div>

                <div className="grid grid-cols-7 gap-3">
                  {calendarDays.map((day) => {
                    const daySessions = calendarSessions.filter((session) =>
                      isSameDay(parseISO(session.date), day),
                    );

                    return (
                      <div
                        key={day.toISOString()}
                        className={[
                          "min-h-[190px] rounded-2xl border p-3 transition-colors",
                          isSameMonth(day, currentMonth)
                            ? "border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0.01))]"
                            : "border-white/5 bg-white/[0.02] text-white/45",
                          isToday(day) ? "ring-1 ring-[#C9FF00]/35" : "",
                        ].join(" ")}
                      >
                        <div className="mb-3 flex items-center justify-between">
                          <span
                            className={[
                              "inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold",
                              isToday(day) ? "bg-[#C9FF00] text-[#0E1117]" : "bg-white/6 text-white",
                            ].join(" ")}
                          >
                            {format(day, "d")}
                          </span>
                          {daySessions.length > 0 && (
                            <span className="rounded-full bg-white/6 px-2 py-1 text-[11px] text-[#C9D1D9]">
                              {daySessions.length} registro{daySessions.length > 1 ? "s" : ""}
                            </span>
                          )}
                        </div>

                        {daySessions.length === 0 ? (
                          <div className="rounded-xl border border-dashed border-white/8 bg-[#0E1117]/60 px-3 py-4 text-sm text-[#66707A]">
                            Sin sesion planificada
                          </div>
                        ) : (
                          <Accordion type="multiple" className="space-y-2">
                            {daySessions.map((session) => {
                              const styles = getCategoryStyles(session.category);

                              return (
                                <AccordionItem
                                  key={session.id}
                                  value={session.id}
                                  className={`rounded-xl border bg-[#0E1117]/80 px-3 last:border-b ${styles.accent}`}
                                >
                                  <AccordionTrigger className="py-3 text-white hover:no-underline">
                                    <div className="space-y-2 text-left">
                                      <div className={`inline-flex rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${styles.badge}`}>
                                        {session.category}
                                      </div>
                                      <div className="text-sm font-semibold leading-tight text-white">
                                        {session.title}
                                      </div>
                                      <div className="text-xs leading-relaxed text-[#8B949E]">
                                        {session.summary}
                                      </div>
                                    </div>
                                  </AccordionTrigger>
                                  <AccordionContent className="space-y-4 pb-4">
                                    <div className="grid grid-cols-1 gap-2 text-xs text-[#AAB3BC]">
                                      <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2">
                                        <Clock3 className="h-3.5 w-3.5 text-[#C9FF00]" />
                                        {session.duration}
                                      </div>
                                      <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2">
                                        <Target className="h-3.5 w-3.5 text-[#C9FF00]" />
                                        {session.objective}
                                      </div>
                                      <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2">
                                        <MapPin className="h-3.5 w-3.5 text-[#C9FF00]" />
                                        {session.location}
                                      </div>
                                    </div>

                                    <div className="rounded-xl border border-white/8 bg-white/[0.03] p-3">
                                      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8B949E]">
                                        Lo que se hizo
                                      </div>
                                      <div className="mt-3 space-y-2">
                                        {session.blocks.map((block) => (
                                          <div
                                            key={`${session.id}-${block.label}`}
                                            className="rounded-lg border border-white/6 bg-[#0E1117] px-3 py-2"
                                          >
                                            <div className="text-sm font-medium text-white">{block.label}</div>
                                            <div className="mt-1 text-xs text-[#8B949E]">{block.detail}</div>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  </AccordionContent>
                                </AccordionItem>
                              );
                            })}
                          </Accordion>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <Card className="rounded-2xl border border-[#C9FF00]/20 bg-[#161B22]">
            <CardHeader>
              <CardTitle className="text-white">Resumen del mes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {monthSessions.map((session) => (
                <div
                  key={`summary-${session.id}`}
                  className="rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3"
                >
                  <div className="text-sm font-semibold text-white">{session.title}</div>
                  <div className="mt-1 text-xs text-[#8B949E]">
                    {capitalize(format(parseISO(session.date), "EEEE d 'de' MMMM", { locale: es }))}
                  </div>
                  <div className="mt-2 text-sm text-[#AAB3BC]">{session.summary}</div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="rounded-2xl border border-[#C9FF00]/20 bg-[#161B22]">
            <CardHeader>
              <CardTitle className="text-white">Proximos hitos</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-[#8B949E]">
              <div className="rounded-xl border border-white/8 bg-[#0E1117] px-4 py-3">
                Consolidar 1 tirada larga por semana con cierre progresivo.
              </div>
              <div className="rounded-xl border border-white/8 bg-[#0E1117] px-4 py-3">
                Mantener 2 sesiones de fuerza para proteger carga y prevenir lesiones.
              </div>
              <div className="rounded-xl border border-white/8 bg-[#0E1117] px-4 py-3">
                Reservar 1 bloque de movilidad y descarga despues del trabajo de calidad.
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
