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

// ── Phase styles — dark neon themed ───────────────────────────────────────────
const PHASE_STYLES: Record<Phase, { bg: string; border: string; text: string; dot: string; glow: string }> = {
  Menstrual: {
    bg: "rgba(244,63,94,0.15)",
    border: "rgba(244,63,94,0.5)",
    text: "#F43F5E",
    dot: "bg-[#F43F5E]",
    glow: "0 0 8px rgba(244,63,94,0.3)",
  },
  Folicular: {
    bg: "rgba(0,212,255,0.12)",
    border: "rgba(0,212,255,0.45)",
    text: "#00D4FF",
    dot: "bg-[#00D4FF]",
    glow: "0 0 8px rgba(0,212,255,0.25)",
  },
  Ovulación: {
    bg: "rgba(201,255,0,0.12)",
    border: "rgba(201,255,0,0.45)",
    text: "#C9FF00",
    dot: "bg-[#C9FF00]",
    glow: "0 0 8px rgba(201,255,0,0.25)",
  },
  Lútea: {
    bg: "rgba(168,85,247,0.15)",
    border: "rgba(168,85,247,0.5)",
    text: "#A855F7",
    dot: "bg-[#A855F7]",
    glow: "0 0 8px rgba(168,85,247,0.3)",
  },
};

// ── Predicted phase coloring by day (example data) ────────────────────────────
const DAY_PHASES: Record<number, Phase> = {
  1: "Menstrual", 2: "Menstrual", 3: "Menstrual", 4: "Menstrual", 5: "Menstrual",
  6: "Folicular", 7: "Folicular", 8: "Folicular", 9: "Folicular", 10: "Folicular",
  11: "Folicular", 12: "Folicular", 13: "Ovulación", 14: "Ovulación", 15: "Ovulación",
  16: "Lútea", 17: "Lútea", 18: "Lútea", 19: "Lútea", 20: "Lútea",
  21: "Lútea", 22: "Lútea", 23: "Lútea", 24: "Lútea", 25: "Lútea",
  26: "Lútea", 27: "Lútea", 28: "Lútea",
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
  label, emoji, active, activeStyle, onClick,
}: {
  label: string; emoji?: string; active: boolean;
  activeStyle: { bg: string; border: string; text: string }; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-sm transition-all whitespace-nowrap"
      style={
        active
          ? {
              background: activeStyle.bg,
              borderColor: activeStyle.border,
              color: activeStyle.text,
              boxShadow: `0 0 8px ${activeStyle.border}`,
            }
          : {
              background: "rgba(14,17,23,0.6)",
              borderColor: "rgba(48,54,61,0.8)",
              color: "#8B949E",
            }
      }
    >
      {emoji && <span>{emoji}</span>}
      <span>{label}</span>
    </button>
  );
}

// ── March 2026 calendar data ──────────────────────────────────────────────────
const MARCH_OFFSET = 6; // March 1 2026 is Sunday → 6 empty cells before day 1
const MARCH_DAYS = 31;

export function CicloMenstrual() {
  const { userId } = useUser();

  // Form state
  const [fecha, setFecha] = useState("2026-04-14");
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
          {(Object.entries(PHASE_STYLES) as [Phase, typeof PHASE_STYLES[Phase]][]).map(([phase, s]) => (
            <div key={phase} className="flex items-center gap-1.5">
              <div
                className="w-3 h-3 rounded-full"
                style={{ background: s.text, boxShadow: s.glow }}
              />
              <span className="text-xs" style={{ color: s.text }}>{phase}</span>
            </div>
          ))}
        </div>

        {/* Main layout: Form LEFT | Calendar RIGHT */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

          {/* ── LEFT: Registration Form ─────────────────────────────────── */}
          <Card className="bg-[#161B22] border border-pink-500/30 rounded-xl">
            <CardHeader>
              <CardTitle className="text-white text-base">Registro Diario</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">

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
                      activeStyle={opt.activeStyle}
                      onClick={() => setSangre(opt.label)}
                    />
                  ))}
                </div>
              </div>

              {/* Síntomas Físicos */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[#C9FF00] mb-1">
                  Síntomas
                </p>
                <p className="text-[10px] text-[#8B949E] mb-3">(puedes elegir varios)</p>
                <div className="flex flex-wrap gap-2">
                  {SINTOMA_OPTIONS.map((s) => (
                    <PillBtn
                      key={s.label}
                      label={s.label}
                      emoji={s.emoji}
                      active={sintomas.includes(s.label)}
                      activeStyle={{ bg: "rgba(249,115,22,0.15)", border: "#F97316", text: "#F97316" }}
                      onClick={() => toggleSintoma(s.label)}
                    />
                  ))}
                </div>
              </div>

              {/* Estado de Ánimo */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[#C9FF00] mb-1">
                  Ánimo
                </p>
                <p className="text-[10px] text-[#8B949E] mb-3">(vacío = Normal)</p>
                <div className="flex flex-wrap gap-2">
                  {ANIMO_OPTIONS.map((a) => (
                    <PillBtn
                      key={a.label}
                      label={a.label}
                      emoji={a.emoji}
                      active={animo === a.label}
                      activeStyle={{ bg: "rgba(168,85,247,0.15)", border: "#A855F7", text: "#A855F7" }}
                      onClick={() => setAnimo(animo === a.label ? "" : a.label)}
                    />
                  ))}
                </div>
              </div>

              {/* Feedback de Entreno */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-[#C9FF00] mb-3">
                  Entreno
                </p>
                <div className="flex flex-wrap gap-2">
                  {ENTRENO_OPTIONS.map((opt) => (
                    <PillBtn
                      key={opt.label}
                      label={opt.label}
                      emoji={opt.emoji}
                      active={entreno === opt.label}
                      activeStyle={opt.activeStyle}
                      onClick={() => setEntreno(entreno === opt.label ? "" : opt.label)}
                    />
                  ))}
                </div>
              </div>

              {/* Guardar */}
              <button
                className="w-full py-3 rounded-xl text-sm font-bold transition-all"
                style={{
                  background: "linear-gradient(135deg, #C9FF00, #a3e635)",
                  color: "#0E1117",
                  boxShadow: "0 0 20px rgba(201,255,0,0.4)",
                }}
              >
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
                  const predictedPhase = DAY_PHASES[day];
                  const phase = rec?.phase || predictedPhase;
                  const isToday = day === TODAY_DAY;
                  const phaseStyle = phase ? PHASE_STYLES[phase] : null;
                  const isPredicted = !rec?.phase && !!predictedPhase;

                  return (
                    <div
                      key={day}
                      className="relative min-h-[60px] rounded-lg p-1.5 transition-all cursor-pointer"
                      style={{
                        background: phaseStyle ? phaseStyle.bg : "rgba(22,27,34,0.8)",
                        border: phaseStyle
                          ? `1px solid ${phaseStyle.border}${isPredicted ? "80" : ""}`
                          : "1px solid rgba(48,54,61,0.6)",
                        boxShadow: !isPredicted && phaseStyle ? phaseStyle.glow : "none",
                        opacity: isPredicted ? 0.7 : 1,
                        outline: isToday ? "2px solid #EC4899" : "none",
                        outlineOffset: isToday ? "2px" : "0",
                      }}
                    >
                      {/* Day number */}
                      <div className="flex items-center justify-between mb-0.5">
                        <span
                          className="text-[11px] font-bold"
                          style={{ color: phaseStyle ? phaseStyle.text : "#8B949E" }}
                        >
                          {day}
                        </span>
                        {isToday && (
                          <span className="text-[7px] font-black px-1 rounded" style={{ background: "#EC4899", color: "#fff" }}>HOY</span>
                        )}
                      </div>

                      {/* Phase label */}
                      {phase && (
                        <div
                          className="text-[8px] font-bold mb-1"
                          style={{ color: phaseStyle?.text, opacity: isPredicted ? 0.8 : 1 }}
                        >
                          {isPredicted ? "~" : ""}{phase.slice(0, 3).toUpperCase()}
                        </div>
                      )}

                      {/* Symptom emojis for registered days */}
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
                  <p className="text-sm font-bold" style={{ color: PHASE_STYLES["Lútea"].text }}>Lútea</p>
                </div>
                <div>
                  <p className="text-xs text-[#8B949E]">Próx. regla</p>
                  <p className="text-sm font-bold text-[#8B949E]">~7 días</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}