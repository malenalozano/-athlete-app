import { Header } from "../components/Header";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "../components/ui/accordion";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { Dumbbell, Sparkles, History, ChevronLeft, ChevronRight, Calendar as CalendarIcon } from "lucide-react";
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

type TrainingExercise = {
  exercise: string;
  series: string;
  weight: string;
  rpe: string;
  muscles: string;
};

type TrainingSession = {
  id: number;
  date: string;
  title: string;
  exercises: TrainingExercise[];
};

const weekDays = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"];

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function DiarioFuerza() {
  const [trainingNote, setTrainingNote] = useState("");
  const [parsedSessions, setParsedSessions] = useState<any[]>([]);
  const [currentMonth, setCurrentMonth] = useState(startOfMonth(new Date()));

  // Historial de sesiones de ejemplo
  const sessionHistory: TrainingSession[] = [
    {
      id: 1,
      date: "2026-03-03",
      title: "Pierna y gluteo",
      exercises: [
        { exercise: "Sentadilla", series: "4x8", weight: "80kg", rpe: "7", muscles: "Piernas, Glúteos" },
        { exercise: "Press Banca", series: "3x10", weight: "60kg", rpe: "6", muscles: "Pecho, Tríceps" },
        { exercise: "Peso Muerto", series: "3x6", weight: "100kg", rpe: "8", muscles: "Espalda, Piernas" },
      ]
    },
    {
      id: 2,
      date: "2026-03-08",
      title: "Fuerza total body",
      exercises: [
        { exercise: "Peso muerto rumano", series: "4x8", weight: "75kg", rpe: "7", muscles: "Isquios, Gluteos" },
        { exercise: "Press militar", series: "4x6", weight: "35kg", rpe: "7", muscles: "Hombros, Triceps" },
        { exercise: "Remo polea", series: "3x12", weight: "50kg", rpe: "6", muscles: "Espalda" },
      ],
    },
    {
      id: 3,
      date: "2026-03-13",
      title: "Pierna tecnica",
      exercises: [
        { exercise: "Sentadilla frontal", series: "5x5", weight: "62.5kg", rpe: "8", muscles: "Cuadriceps, Core" },
        { exercise: "Bulgaras", series: "3x10", weight: "16kg", rpe: "7", muscles: "Gluteos, Cuadriceps" },
        { exercise: "Gemelo en maquina", series: "4x15", weight: "45kg", rpe: "6", muscles: "Gemelos" },
      ],
    },
    {
      id: 4,
      date: "2026-03-21",
      title: "Empuje y tiron",
      exercises: [
        { exercise: "Press banca", series: "5x5", weight: "62.5kg", rpe: "8", muscles: "Pecho, Triceps" },
        { exercise: "Dominadas asistidas", series: "4x8", weight: "-20kg", rpe: "7", muscles: "Espalda, Biceps" },
        { exercise: "Face pull", series: "3x15", weight: "22kg", rpe: "6", muscles: "Deltoides posterior" },
      ],
    }
  ];

  const calendarDays = eachDayOfInterval({
    start: startOfWeek(startOfMonth(currentMonth), { weekStartsOn: 1 }),
    end: endOfWeek(endOfMonth(currentMonth), { weekStartsOn: 1 }),
  });

  const monthSessions = sessionHistory.filter((session) =>
    isSameMonth(parseISO(session.date), currentMonth),
  );

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8">
        <h2 className="text-2xl font-semibold mb-6 text-white flex items-center gap-2">
          <Dumbbell className="h-6 w-6 text-[#C9FF00]" />
          Diario de Fuerza
        </h2>

        <p className="text-[#8B949E] mb-8">
          Escribe tus entrenamientos de fuerza en lenguaje natural. La IA detectará automáticamente
          fechas, ejercicios, series, repeticiones y peso para estructurar tus sesiones.
        </p>

        {/* Formulario de Entrada Libre */}
        <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl mb-8">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-[#C9FF00]" />
              Entrada Libre de Entrenamiento
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <Textarea 
                  value={trainingNote}
                  onChange={(e) => setTrainingNote(e.target.value)}
                  placeholder={"Ejemplo:\n\nHoy hice:\n- Sentadilla 4x8 con 80kg\n- Press banca 3x10 a 60kg RPE 6\n- Peso muerto 3x6 a 100kg\n\nAyer hice pierna ligera:\n- Zancadas 3x12\n- Extensiones 3x15 RPE 5"}
                  rows={12}
                  className="bg-[#0E1117] border-[#C9FF00]/30 text-white resize-none font-mono"
                />
                <p className="text-xs text-[#8B949E] mt-2">
                  💡 Puedes incluir múltiples días en un solo texto. La IA detectará "hoy", "ayer",
                  fechas específicas o días de la semana.
                </p>
              </div>

              <Button 
                className="w-full bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] hover:from-[#a8d600] hover:to-[#C9FF00] font-bold py-3"
                disabled={!trainingNote.trim()}
              >
                🤖 Procesar Entrenamiento con IA
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Previsualización de Sesiones Detectadas */}
        {parsedSessions.length > 0 && (
          <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl mb-8">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-white">
                  Sesiones Detectadas ({parsedSessions.length})
                </CardTitle>
                <Button className="bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] hover:from-[#a8d600] hover:to-[#C9FF00] font-bold">
                  💾 Guardar {parsedSessions.length} Sesiones
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {parsedSessions.map((session, idx) => (
                  <div key={idx} className="border-l-4 border-l-[#C9FF00] pl-4">
                    <h4 className="text-white font-semibold mb-3">
                      Sesión del {session.date}
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-[#C9FF00]/20">
                            <th className="text-left text-[#8B949E] pb-2">Ejercicio</th>
                            <th className="text-left text-[#8B949E] pb-2">Series x Reps</th>
                            <th className="text-left text-[#8B949E] pb-2">Peso</th>
                            <th className="text-left text-[#8B949E] pb-2">RPE</th>
                            <th className="text-left text-[#8B949E] pb-2">Grupos Musculares</th>
                          </tr>
                        </thead>
                        <tbody>
                          {session.exercises.map((ex: any, i: number) => (
                            <tr key={i} className="border-b border-[#30363D]">
                              <td className="text-white py-2">{ex.exercise}</td>
                              <td className="text-white py-2">{ex.series}</td>
                              <td className="text-white py-2">{ex.weight}</td>
                              <td className="text-white py-2">{ex.rpe}</td>
                              <td className="text-[#8B949E] py-2">{ex.muscles}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Calendario mensual */}
        <div>
          <h3 className="text-lg font-semibold mb-4 text-white flex items-center gap-2">
            <CalendarIcon className="h-5 w-5 text-[#C9FF00]" />
            Calendario mensual
          </h3>

          <Card className="overflow-hidden rounded-2xl border border-[#C9FF00]/30 bg-[#161B22]">
            <CardHeader className="border-b border-white/5">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <CardTitle className="text-white">Vista por dias</CardTitle>
                  <p className="mt-2 text-sm text-[#8B949E]">
                    {monthSessions.length} sesiones en {format(currentMonth, "MMMM", { locale: es })}. Haz clic en el nombre del entrenamiento para ver el detalle del dia.
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
                      const daySessions = sessionHistory.filter((session) =>
                        isSameDay(parseISO(session.date), day),
                      );

                      return (
                        <div
                          key={day.toISOString()}
                          className={[
                            "min-h-[170px] rounded-2xl border p-3 transition-colors",
                            isSameMonth(day, currentMonth)
                              ? daySessions.length > 0
                                ? "border-[#C9FF00]/45 bg-[linear-gradient(180deg,rgba(201,255,0,0.16),rgba(201,255,0,0.06))]"
                                : "border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0.01))]"
                              : "border-white/5 bg-white/[0.02] text-white/45",
                            isToday(day) ? "ring-1 ring-[#C9FF00]/35" : "",
                          ].join(" ")}
                        >
                          <div className="mb-3 flex items-center justify-between">
                            <span
                              className={[
                                "inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold",
                                isToday(day)
                                  ? "bg-[#C9FF00] text-[#0E1117]"
                                  : daySessions.length > 0
                                    ? "bg-[#C9FF00]/20 text-[#E8FF8A]"
                                    : "bg-white/6 text-white",
                              ].join(" ")}
                            >
                              {format(day, "d")}
                            </span>

                            {daySessions.length > 0 && (
                              <span className="rounded-full border border-[#C9FF00]/30 bg-[#C9FF00]/15 px-2 py-1 text-[11px] text-[#E8FF8A]">
                                {daySessions.length} entreno{daySessions.length > 1 ? "s" : ""}
                              </span>
                            )}
                          </div>

                          {daySessions.length === 0 ? (
                            <div className="rounded-xl border border-dashed border-white/8 bg-[#0E1117]/60 px-3 py-4 text-sm text-[#66707A]">
                              Sin entrenamiento
                            </div>
                          ) : (
                            <Accordion type="multiple" className="space-y-2">
                              {daySessions.map((session) => (
                                <AccordionItem
                                  key={session.id}
                                  value={`session-${session.id}`}
                                  className="rounded-xl border border-[#C9FF00]/20 bg-[#0E1117]/80 px-3 last:border-b"
                                >
                                  <AccordionTrigger className="py-3 text-white hover:no-underline">
                                    <div className="text-left">
                                      <div className="text-sm font-semibold text-white">{session.title}</div>
                                      <div className="text-xs text-[#8B949E]">
                                        {session.exercises.length} ejercicios
                                      </div>
                                    </div>
                                  </AccordionTrigger>

                                  <AccordionContent className="pb-3">
                                    <div className="space-y-2">
                                      {session.exercises.map((exercise, idx) => (
                                        <div
                                          key={`${session.id}-${exercise.exercise}-${idx}`}
                                          className="rounded-lg border border-white/8 bg-white/[0.03] p-3"
                                        >
                                          <div className="text-sm font-semibold text-white">{exercise.exercise}</div>
                                          <div className="mt-1 text-xs text-[#8B949E]">
                                            {exercise.series} | {exercise.weight} | RPE {exercise.rpe}
                                          </div>
                                          <div className="mt-1 text-xs text-[#AAB3BC]">{exercise.muscles}</div>
                                        </div>
                                      ))}
                                    </div>
                                  </AccordionContent>
                                </AccordionItem>
                              ))}
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

          <h3 className="text-lg font-semibold mt-8 mb-4 text-white flex items-center gap-2">
            <History className="h-5 w-5 text-[#C9FF00]" />
            Historial por entrenamientos ({sessionHistory.length})
          </h3>

          <div className="space-y-4">
            {sessionHistory.map((session) => (
              <Card key={`history-${session.id}`} className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-white text-base">{session.title}</CardTitle>
                    <span className="text-sm text-[#8B949E]">
                      {capitalize(format(parseISO(session.date), "d 'de' MMMM", { locale: es }))}
                    </span>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {session.exercises.map((exercise, idx) => (
                      <div
                        key={`history-${session.id}-${exercise.exercise}-${idx}`}
                        className="rounded-lg border border-white/8 bg-[#0E1117] px-3 py-2"
                      >
                        <div className="text-sm font-medium text-white">{exercise.exercise}</div>
                        <div className="text-xs text-[#8B949E] mt-1">
                          {exercise.series} | {exercise.weight} | RPE {exercise.rpe}
                        </div>
                        <div className="text-xs text-[#AAB3BC] mt-1">{exercise.muscles}</div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}