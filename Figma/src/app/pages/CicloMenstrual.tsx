import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { useUser } from "../context/UserContext";
import { Heart, AlertCircle, ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";

// ── Types ──────────────────────────────────────────────────────────────────────
type Phase = "Menstrual" | "Folicular" | "Ovulación" | "Lútea";

interface DayRecord {
  phase: Phase;
  sangre?: string;
  sintomas?: string[];
  animo?: string;
  entreno?: string;
}

// ── Registered data — TODO: fetch from Supabase cycle tracking ────────────────
const REGISTERED: Record<number, DayRecord> = {};

// ── Phase styles ───────────────────────────────────────────────────────────────
const PHASE_STYLES: Record<Phase, { bg: string; border: string; text: string; dot: string }> = {
  Menstrual: { bg: "bg-red-600/25", border: "border-red-500/70", text: "text-red-400", dot: "bg-red-500" },
  Folicular: { bg: "bg-blue-500/20", border: "border-blue-400/70", text: "text-blue-400", dot: "bg-blue-400" },
  Ovulación: { bg: "bg-green-500/20", border: "border-green-400/70", text: "text-green-400", dot: "bg-green-400" },
  Lútea: { bg: "bg-yellow-500/20", border: "border-yellow-400/70", text: "text-yellow-400", dot: "bg-yellow-400" },
};

// ── Symptom emoji map ─────────────────────────────────────────────────────────
const SINTOMA_EMOJI: Record<string, string> = {
  "Dolor de ovarios": "🔴",
  "Dolor de senos": "🤲",
  "Antojos": "🍩",
  "Dolor de cabeza": "😵",
  "Hinchazón": "🫃",
};

const ANIMO_EMOJI: Record<string, string> = {
  "Ansiedad/Estrés": "😰", Triste: "😢", Enfadada: "😡",
  Feliz: "😊", Cansada: "😴", Energética: "⚡", Normal: "😐",
};

const ENTRENO_EMOJI: Record<string, string> = {
  "A tope": "🚀", Regulero: "🟠", Bajito: "📉", "No completo": "❌",
};

// ── Pill button component ──────────────────────────────────────────────────────
function PillBtn({
  label, emoji, active, activeColor, onClick,
}: {
  label: string; emoji?: string; active: boolean;
  activeColor: string; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-sm transition-all ${
        active
          ? `${activeColor} text-white`
          : "bg-[#0E1117] border-[#30363D] text-[#8B949E] hover:border-[#8B949E]"
      }`}
    >
      {emoji && <span>{emoji}</span>}
      <span>{label}</span>
    </button>
  );
}

// ── March 2026 calendar data ──────────────────────────────────────────────────
const MARCH_OFFSET = 6; // March 1 2026 is Sunday → 6 empty cells before day 1
const MARCH_DAYS = 31;

// Predicted phases (no registered data yet — will derive from real data)
function getPredictedPhase(_day: number): Phase | null {
  return null; // TODO: implement prediction logic based on registered cycle data
}

export function CicloMenstrual() {
  const { userId } = useUser();

  // Form state
  const [fecha, setFecha] = useState("");
  const [sangre, setSangre] = useState("Sin sangre");
  const [sintomas, setSintomas] = useState<string[]>([]);
  const [animo, setAnimo] = useState("");
  const [entreno, setEntreno] = useState("");
  const [calMonth, setCalMonth] = useState(2); // 0-indexed: 2 = March

  const toggleSintoma = (s: string) =>
    setSintomas((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));

  if (userId !== 1) {
    return (
      <div className="min-h-screen bg-[#0E1117]">
        <Header />
        <main className="container mx-auto px-6 py-8">
          <Card className="bg-[#161B22] border border-pink-500/30 rounded-xl">
            <CardContent className="pt-8 pb-8 text-center">
              <AlertCircle className="h-12 w-12 text-pink-400 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-white mb-2">Sección No Disponible</h2>
              <p className="text-[#8B949E]">Esta sección solo está disponible para Malena</p>
            </CardContent>
          </Card>
        </main>
      </div>
    );
  }

  // Build calendar cells
  const totalCells = Math.ceil((MARCH_OFFSET + MARCH_DAYS) / 7) * 7;
  const cells = Array.from({ length: totalCells }, (_, i) => {
    const dayNum = i - MARCH_OFFSET + 1;
    if (dayNum < 1 || dayNum > MARCH_DAYS) return null;
    return dayNum;
  });

  const SANGRE_OPTIONS = [
    { label: "Sin sangre", emoji: "🔴", activeColor: "border-red-500 bg-red-500/20" },
    { label: "Manchado", emoji: "🩸", activeColor: "border-red-500 bg-red-500/20" },
    { label: "Ligero", emoji: "🩸", activeColor: "border-red-400 bg-red-400/20" },
    { label: "Medio", emoji: "🩸🩸", activeColor: "border-red-500 bg-red-500/20" },
    { label: "Fuerte", emoji: "🩸🩸🩸", activeColor: "border-red-600 bg-red-600/20" },
  ];
  const SINTOMA_OPTIONS = ["Dolor de ovarios", "Dolor de senos", "Antojos", "Dolor de cabeza", "Hinchazón"];
  const ANIMO_OPTIONS = ["Ansiedad/Estrés", "Triste", "Enfadada", "Feliz", "Cansada", "Energética"];
  const ENTRENO_OPTIONS = [
    { label: "A tope", color: "border-[#C9FF00] bg-[#C9FF00]/20" },
    { label: "Regulero", color: "border-orange-500 bg-orange-500/20" },
    { label: "Bajito", color: "border-yellow-500 bg-yellow-500/20" },
    { label: "No completo", color: "border-red-500 bg-red-500/20" },
  ];

  // Compute today marker (day 16 = today)
  const TODAY_DAY = 16;

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8">
        <h2 className="text-2xl font-semibold mb-6 text-white flex items-center gap-2">
          <Heart className="h-6 w-6 text-pink-400" />
          Ciclo Menstrual
        </h2>

        {/* Phase legend */}
        <div className="flex flex-wrap gap-3 mb-6">
          {(Object.entries(PHASE_STYLES) as [Phase, any][]).map(([phase, s]) => (
            <div key={phase} className="flex items-center gap-1.5">
              <div className={`w-3 h-3 rounded-full ${s.dot}`} />
              <span className="text-xs text-[#8B949E]">{phase}</span>
            </div>
          ))}
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full border border-dashed border-[#8B949E]" />
            <span className="text-xs text-[#8B949E]">Predicción</span>
          </div>
        </div>

        {/* Main layout: Form LEFT | Calendar RIGHT */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

          {/* ── LEFT: Registration Form ─────────────────────────────────── */}
          <Card className="bg-[#161B22] border border-pink-500/30 rounded-xl">
            <CardHeader>
              <CardTitle className="text-white text-base">Registro Diario</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">

              {/* Fecha */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[#C9FF00] mb-2">Fecha</p>
                <input
                  type="date"
                  value={fecha}
                  onChange={(e) => setFecha(e.target.value)}
                  className="w-full bg-[#0E1117] border border-[#C9FF00]/50 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-[#C9FF00]"
                />
              </div>

              {/* Sangre */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[#C9FF00] mb-3">Sangre</p>
                <div className="flex flex-wrap gap-2">
                  {SANGRE_OPTIONS.map((opt) => (
                    <PillBtn
                      key={opt.label}
                      label={opt.label}
                      emoji={opt.emoji}
                      active={sangre === opt.label}
                      activeColor={opt.activeColor}
                      onClick={() => setSangre(opt.label)}
                    />
                  ))}
                </div>
              </div>

              {/* Síntomas Físicos */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[#C9FF00] mb-1">
                  Síntomas Físicos
                </p>
                <p className="text-[10px] text-[#8B949E] mb-3">(puedes elegir varios)</p>
                <div className="flex flex-wrap gap-2">
                  {SINTOMA_OPTIONS.map((s) => (
                    <PillBtn
                      key={s}
                      label={s}
                      emoji={SINTOMA_EMOJI[s]}
                      active={sintomas.includes(s)}
                      activeColor="border-orange-500 bg-orange-500/20"
                      onClick={() => toggleSintoma(s)}
                    />
                  ))}
                </div>
              </div>

              {/* Estado de Ánimo */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[#C9FF00] mb-1">
                  Estado de Ánimo
                </p>
                <p className="text-[10px] text-[#8B949E] mb-3">(vacío = Normal)</p>
                <div className="flex flex-wrap gap-2">
                  {ANIMO_OPTIONS.map((a) => (
                    <PillBtn
                      key={a}
                      label={a}
                      emoji={ANIMO_EMOJI[a]}
                      active={animo === a}
                      activeColor="border-purple-500 bg-purple-500/20"
                      onClick={() => setAnimo(animo === a ? "" : a)}
                    />
                  ))}
                </div>
              </div>

              {/* Feedback de Entreno */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[#C9FF00] mb-3">
                  Feedback de Entreno
                </p>
                <div className="flex flex-wrap gap-2">
                  {ENTRENO_OPTIONS.map((opt) => (
                    <PillBtn
                      key={opt.label}
                      label={opt.label}
                      emoji={ENTRENO_EMOJI[opt.label]}
                      active={entreno === opt.label}
                      activeColor={opt.color}
                      onClick={() => setEntreno(entreno === opt.label ? "" : opt.label)}
                    />
                  ))}
                </div>
              </div>

              {/* Guardar */}
              <button className="w-full py-3 rounded-xl border border-[#30363D] text-white text-sm font-semibold hover:border-pink-400/60 hover:bg-pink-500/5 transition-all">
                Guardar Registro
              </button>
            </CardContent>
          </Card>

          {/* ── RIGHT: Calendar ────────────────────────────────────────── */}
          <Card className="bg-[#161B22] border border-pink-500/30 rounded-xl">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-white text-base">Calendario del Ciclo</CardTitle>
                <div className="flex items-center gap-2">
                  <button
                    className="flex items-center gap-1 px-2 py-1 rounded border border-[#30363D] text-[#8B949E] text-xs hover:border-pink-400/50 transition-all"
                    onClick={() => setCalMonth((m) => m - 1)}
                  >
                    <ChevronLeft className="h-3 w-3" /> Anterior
                  </button>
                  <span className="text-white text-sm font-semibold px-2">Marzo 2026</span>
                  <button
                    className="flex items-center gap-1 px-2 py-1 rounded border border-[#30363D] text-[#8B949E] text-xs hover:border-pink-400/50 transition-all"
                    onClick={() => setCalMonth((m) => m + 1)}
                  >
                    Siguiente <ChevronRight className="h-3 w-3" />
                  </button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {/* Day headers */}
              <div className="grid grid-cols-7 gap-1 mb-1">
                {["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"].map((d) => (
                  <div key={d} className="text-center text-[10px] font-semibold text-[#8B949E] py-1">
                    {d}
                  </div>
                ))}
              </div>

              {/* Calendar cells */}
              <div className="grid grid-cols-7 gap-1">
                {cells.map((day, i) => {
                  if (!day) return <div key={`empty-${i}`} />;

                  const rec = REGISTERED[day];
                  const phase = rec?.phase;
                  const predicted = !rec ? getPredictedPhase(day) : null;
                  const isToday = day === TODAY_DAY;
                  const phaseStyle = phase ? PHASE_STYLES[phase] : null;
                  const predStyle = predicted ? PHASE_STYLES[predicted] : null;

                  return (
                    <div
                      key={day}
                      className={`relative min-h-[68px] rounded-lg border p-1.5 transition-all cursor-pointer
                        ${phaseStyle
                          ? `${phaseStyle.bg} ${phaseStyle.border}`
                          : predStyle
                          ? `${predStyle.bg} border-dashed ${predStyle.border} opacity-50`
                          : "bg-[#0E1117] border-[#30363D] hover:border-[#8B949E]/50"}
                        ${isToday ? "ring-2 ring-pink-400 ring-offset-1 ring-offset-[#0E1117]" : ""}
                      `}
                    >
                      {/* Day number */}
                      <div className="flex items-center justify-between mb-0.5">
                        <span
                          className={`text-[11px] font-bold ${
                            phaseStyle ? phaseStyle.text : predStyle ? predStyle.text : "text-[#8B949E]"
                          }`}
                        >
                          {day}
                        </span>
                        {isToday && (
                          <span className="text-[8px] bg-pink-500 text-white px-1 rounded">HOY</span>
                        )}
                      </div>

                      {/* Phase label */}
                      {phase && (
                        <div className={`text-[8px] font-semibold mb-1 ${phaseStyle?.text}`}>
                          {phase.slice(0, 3).toUpperCase()}
                        </div>
                      )}
                      {predicted && (
                        <div className={`text-[8px] font-semibold mb-1 ${predStyle?.text} opacity-70`}>
                          ~{predicted.slice(0, 3).toUpperCase()}
                        </div>
                      )}

                      {/* Symptom emojis */}
                      {rec && (
                        <div className="flex flex-wrap gap-0.5">
                          {(rec.sintomas || []).slice(0, 2).map((s) => (
                            <span key={s} className="text-[10px]" title={s}>
                              {SINTOMA_EMOJI[s]}
                            </span>
                          ))}
                          {rec.animo && ANIMO_EMOJI[rec.animo] && (
                            <span className="text-[10px]" title={rec.animo}>
                              {ANIMO_EMOJI[rec.animo]}
                            </span>
                          )}
                          {rec.entreno && ENTRENO_EMOJI[rec.entreno] && (
                            <span className="text-[10px]" title={rec.entreno}>
                              {ENTRENO_EMOJI[rec.entreno]}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Cycle stats */}
              <div className="mt-4 pt-4 border-t border-pink-500/20 grid grid-cols-3 gap-3 text-center">
                <div>
                  <p className="text-xs text-[#8B949E]">Días registrados</p>
                  <p className="text-lg font-bold text-white">{Object.keys(REGISTERED).length}</p>
                </div>
                <div>
                  <p className="text-xs text-[#8B949E]">Fase actual</p>
                  <p className="text-sm font-bold text-[#8B949E]">--</p>
                </div>
                <div>
                  <p className="text-xs text-[#8B949E]">Próx. regla</p>
                  <p className="text-sm font-bold text-[#8B949E]">--</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
