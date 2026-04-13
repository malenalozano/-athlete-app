import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Dumbbell, ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";

// ── Mock session data for March 2026 ─────────────────────────────────────────
interface TrainingDay {
  type: "running" | "strength" | "combo";
  label: string;
  exercises?: { name: string; sets: string; weight: string }[];
  notes?: string;
}

// TODO: fetch training days from activity log / Supabase
const TRAINING_DAYS: Record<number, TrainingDay> = {};

// ── Calendar constants ────────────────────────────────────────────────────────
// March 1 2026 = Sunday → offset 6 in Mon-first grid
const MARCH_OFFSET = 6;
const MARCH_DAYS = 31;

const TYPE_COLORS: Record<string, { border: string; label: string; bg: string }> = {
  running: { border: "border-[#C9FF00]", label: "bg-[#C9FF00] text-[#0E1117]", bg: "bg-[#C9FF00]/10" },
  strength: { border: "border-[#C9FF00]", label: "bg-[#C9FF00] text-[#0E1117]", bg: "bg-[#C9FF00]/10" },
  combo: { border: "border-[#C9FF00]", label: "bg-[#C9FF00] text-[#0E1117]", bg: "bg-[#C9FF00]/10" },
};

export function DiarioFuerza() {
  const [freeText, setFreeText] = useState("");
  const [selectedDay, setSelectedDay] = useState<number | null>(null);

  const totalCells = Math.ceil((MARCH_OFFSET + MARCH_DAYS) / 7) * 7;
  const cells = Array.from({ length: totalCells }, (_, i) => {
    const dayNum = i - MARCH_OFFSET + 1;
    if (dayNum < 1 || dayNum > MARCH_DAYS) return null;
    return dayNum;
  });

  const trainingCount = Object.keys(TRAINING_DAYS).length;
  const selectedSession = selectedDay ? TRAINING_DAYS[selectedDay] : null;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold text-white flex items-center gap-2 mb-2">
          <Dumbbell className="h-5 w-5 text-[#C9FF00]" />
          Diario de Fuerza
        </h3>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* ── LEFT: Text Entry + Selected Session ─────────────────── */}
        <div className="space-y-5">

          {/* Free text entry */}
          <div>
            <p className="text-sm text-[#8B949E] mb-2">Entreno libre</p>
            <div className="border border-[#C9FF00]/30 rounded-xl overflow-hidden">
              <textarea
                value={freeText}
                onChange={e => setFreeText(e.target.value)}
                placeholder={`Ej: hoy hice glute bridge 4x10 80kg, y ayer remo 4x8 40kg y press militar 3x10 18kg`}
                rows={5}
                className="w-full bg-[#0E1117] text-white placeholder-[#30363D] px-4 py-3 text-sm resize-none focus:outline-none"
              />
            </div>
            <button className="mt-2 px-4 py-2 border border-[#30363D] rounded-lg text-[#8B949E] text-xs hover:border-[#C9FF00]/40 hover:text-white transition-all">
              Procesar entrada del diario
            </button>
          </div>

          {/* Selected day detail */}
          {selectedDay && (
            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white text-base flex items-center justify-between">
                  <span>📅 {selectedDay} de Marzo 2026</span>
                  {selectedSession && (
                    <span className="text-xs px-2 py-1 bg-[#C9FF00]/10 border border-[#C9FF00]/30 rounded text-[#C9FF00]">
                      {selectedSession.label}
                    </span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {selectedSession ? (
                  <div className="space-y-4">
                    {/* Notes */}
                    {selectedSession.notes && (
                      <div className="p-3 bg-[#0E1117] rounded-lg border border-[#30363D]">
                        <p className="text-sm text-[#8B949E] mb-1 text-xs font-semibold uppercase tracking-wider">Notas</p>
                        <p className="text-sm text-white">{selectedSession.notes}</p>
                      </div>
                    )}

                    {/* Exercises table */}
                    {selectedSession.exercises && selectedSession.exercises.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-[#8B949E] uppercase tracking-wider mb-2">Ejercicios</p>
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-[#C9FF00]/20">
                              <th className="text-left text-[#8B949E] text-xs pb-2">Ejercicio</th>
                              <th className="text-left text-[#8B949E] text-xs pb-2">Series</th>
                              <th className="text-left text-[#8B949E] text-xs pb-2">Peso</th>
                            </tr>
                          </thead>
                          <tbody>
                            {selectedSession.exercises.map((ex, i) => (
                              <tr key={i} className="border-b border-[#30363D]/50 last:border-0">
                                <td className="text-white py-2">{ex.name}</td>
                                <td className="text-[#C9FF00] py-2">{ex.sets}</td>
                                <td className="text-white py-2">{ex.weight}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Type badge */}
                    <div className="flex items-center gap-2 text-xs text-[#8B949E]">
                      <div className={`w-2 h-2 rounded-full ${selectedSession.type === "running" ? "bg-[#C9FF00]" : "bg-purple-400"}`} />
                      Tipo: {selectedSession.type === "running" ? "Carrera" : selectedSession.type === "combo" ? "Combinado" : "Fuerza"}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-6">
                    <p className="text-[#8B949E] text-sm">Día de descanso</p>
                    <p className="text-2xl mt-2">😴</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardContent className="pt-4 pb-4 text-center">
                <p className="text-xs text-[#8B949E] mb-1">Días entrenados</p>
                <p className="text-2xl font-bold text-[#C9FF00]">{trainingCount}</p>
              </CardContent>
            </Card>
            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardContent className="pt-4 pb-4 text-center">
                <p className="text-xs text-[#8B949E] mb-1">Sesiones fuerza</p>
                <p className="text-2xl font-bold text-purple-400">
                  {Object.values(TRAINING_DAYS).filter(d => d.type !== "running").length}
                </p>
              </CardContent>
            </Card>
            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardContent className="pt-4 pb-4 text-center">
                <p className="text-xs text-[#8B949E] mb-1">Carreras</p>
                <p className="text-2xl font-bold text-[#C9FF00]">
                  {Object.values(TRAINING_DAYS).filter(d => d.type === "running").length}
                </p>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* ── RIGHT: Monthly Calendar ───────────────────────────────── */}
        <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-white text-base">Calendario mensual</CardTitle>
            </div>
            <div className="flex items-center justify-between mt-2">
              <button className="flex items-center gap-1 px-3 py-1.5 border border-[#30363D] rounded-lg text-[#8B949E] text-xs hover:border-[#C9FF00]/40 transition-all">
                <ChevronLeft className="h-3 w-3" /> Mes anterior
              </button>
              <span className="text-white font-semibold text-sm">Marzo 2026</span>
              <button className="flex items-center gap-1 px-3 py-1.5 border border-[#30363D] rounded-lg text-[#8B949E] text-xs hover:border-[#C9FF00]/40 transition-all">
                Mes siguiente <ChevronRight className="h-3 w-3" />
              </button>
            </div>
          </CardHeader>
          <CardContent>
            {/* Day headers */}
            <div className="grid grid-cols-7 gap-1 mb-1">
              {["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"].map(d => (
                <div key={d} className="text-center text-[10px] font-semibold text-[#8B949E] py-1 border-b border-[#30363D]">
                  {d}
                </div>
              ))}
            </div>

            {/* Calendar cells */}
            <div className="grid grid-cols-7 gap-1">
              {cells.map((day, i) => {
                if (!day) return <div key={`e-${i}`} className="min-h-[72px]" />;

                const session = TRAINING_DAYS[day];
                const colors = session ? TYPE_COLORS[session.type] : null;
                const isSelected = selectedDay === day;
                const isToday = day === 15;

                return (
                  <button
                    key={day}
                    onClick={() => setSelectedDay(day === selectedDay ? null : day)}
                    className={`
                      min-h-[72px] rounded-lg border p-1.5 text-left transition-all
                      ${colors
                        ? `${colors.bg} ${colors.border} hover:ring-1 hover:ring-[#C9FF00]/60`
                        : "bg-[#0E1117] border-[#30363D] hover:border-[#8B949E]/50"}
                      ${isSelected ? "ring-2 ring-[#C9FF00] ring-offset-1 ring-offset-[#0E1117]" : ""}
                    `}
                  >
                    {/* Day number */}
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-[11px] font-bold ${colors ? "text-[#C9FF00]" : "text-[#8B949E]"}`}>
                        {day}
                      </span>
                      {isToday && (
                        <span className="text-[7px] bg-[#C9FF00] text-[#0E1117] px-0.5 rounded font-bold">HOY</span>
                      )}
                    </div>

                    {/* Session label */}
                    {session ? (
                      <div className={`text-[9px] font-semibold px-1 py-0.5 rounded ${colors?.label}`}>
                        {session.label.length > 18 ? session.label.slice(0, 17) + "…" : session.label}
                      </div>
                    ) : (
                      <div className="text-[9px] text-[#30363D]">Descanso</div>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Footer */}
            <div className="mt-3 pt-3 border-t border-[#C9FF00]/20 flex items-center justify-between">
              <p className="text-xs text-[#8B949E]">
                Días entrenados este mes: <span className="text-white font-bold">{trainingCount}</span>
              </p>
              <div className="flex items-center gap-3 text-xs">
                <div className="flex items-center gap-1">
                  <div className="w-2.5 h-2.5 rounded bg-[#C9FF00]" />
                  <span className="text-[#8B949E]">Entrenado</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-2.5 h-2.5 rounded bg-[#30363D] border border-[#30363D]" />
                  <span className="text-[#8B949E]">Descanso</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}