import { Header } from "../components/Header";
import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, Plus } from "lucide-react";
import { useUser } from "../context/UserContext";
import { getEjercicios, type EjercicioBiblioteca } from "../api";

// ── Types ──────────────────────────────────────────────────────────────────────

interface Exercise {
  id: string;
  name: string;
  lastWeight: number | null;
  bestWeight: number | null;
  series: number;
  reps: number;
  aliases: string;
  recommendation: "mantener" | "subir";
}

interface MuscleGroup {
  name: string;
  count: number;
  exercises: Exercise[];
  expanded: boolean;
}

// ── Mock Data ──────────────────────────────────────────────────────────────────

const INITIAL_GROUPS: MuscleGroup[] = [
  {
    name: "GLÚTEO",
    count: 4,
    expanded: true,
    exercises: [
      {
        id: "g1",
        name: "Abducciones en polea",
        lastWeight: null,
        bestWeight: null,
        series: 3,
        reps: 12,
        aliases: "alias: abducciones",
        recommendation: "mantener",
      },
      {
        id: "g2",
        name: "Abducción cadera",
        lastWeight: null,
        bestWeight: null,
        series: 3,
        reps: 15,
        aliases: "alias: abducción, abducción",
        recommendation: "mantener",
      },
      {
        id: "g3",
        name: "Hip Thrust",
        lastWeight: 30.0,
        bestWeight: 30.0,
        series: 3,
        reps: 12,
        aliases: "alias: HT, Hip thrust",
        recommendation: "mantener",
      },
      {
        id: "g4",
        name: "Sentadilla búlgara",
        lastWeight: 14.0,
        bestWeight: 14.0,
        series: 3,
        reps: 10,
        aliases: "alias: búlgara, búlgara, Split squat",
        recommendation: "subir",
      },
    ],
  },
  {
    name: "TREN INFERIOR",
    count: 4,
    expanded: true,
    exercises: [
      {
        id: "t1",
        name: "Gemelo de pie",
        lastWeight: null,
        bestWeight: null,
        series: 3,
        reps: 15,
        aliases: "alias: gemelo",
        recommendation: "mantener",
      },
      {
        id: "t2",
        name: "Step Up",
        lastWeight: null,
        bestWeight: null,
        series: 3,
        reps: 12,
        aliases: "alias: SU",
        recommendation: "mantener",
      },
      {
        id: "t3",
        name: "Peso Muerto Rumano",
        lastWeight: 18.0,
        bestWeight: 18.0,
        series: 3,
        reps: 10,
        aliases: "alias: rumano, PM, Peso muerto",
        recommendation: "mantener",
      },
      {
        id: "t4",
        name: "Peso muerto",
        lastWeight: null,
        bestWeight: null,
        series: 3,
        reps: 8,
        aliases: "alias: deadlift, PM, Peso muerto rumano",
        recommendation: "mantener",
      },
    ],
  },
];

function apiToMuscleGroups(apiGroups: { nombre: string; ejercicios: EjercicioBiblioteca[] }[]): MuscleGroup[] {
  return apiGroups.map((g) => ({
    name: g.nombre.toUpperCase(),
    count: g.ejercicios.length,
    expanded: true,
    exercises: g.ejercicios.map((e, i) => ({
      id: String(e.id),
      name: e.nombre,
      lastWeight: e.ultimo_peso,
      bestWeight: e.mejor_peso,
      series: 3,
      reps: 12,
      aliases: e.alias ? `alias: ${e.alias}` : "",
      recommendation: (e.mejor_peso && e.ultimo_peso && e.ultimo_peso >= e.mejor_peso) ? "subir" as const : "mantener" as const,
    })),
  }));
}

// ── Component ──────────────────────────────────────────────────────────────────

export function Ejercicios() {
  const { userId } = useUser();
  const [groups, setGroups] = useState<MuscleGroup[]>(INITIAL_GROUPS);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    getEjercicios(userId)
      .then((data) => {
        if (data.grupos.length > 0) {
          setGroups(apiToMuscleGroups(data.grupos));
        }
      })
      .catch(() => null)
      .finally(() => setLoading(false));
  }, [userId]);

  const toggleGroup = (groupName: string) => {
    setGroups((prev) =>
      prev.map((g) => (g.name === groupName ? { ...g, expanded: !g.expanded } : g))
    );
  };

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            🏋️ Ejercicios
          </h1>
        </div>

        {/* Add Exercise Button */}
        <button
          className="w-full mb-6 flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-semibold transition-all hover:opacity-90"
          style={{
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.1)",
            color: "#8B949E",
          }}
        >
          <Plus className="h-4 w-4" />
          <span>&gt; +Añadir ejercicio</span>
        </button>

        {/* Exercise Groups */}
        <div className="space-y-4">
          {groups.map((group) => (
            <div key={group.name}>
              {/* Group Header */}
              <button
                onClick={() => toggleGroup(group.name)}
                className="w-full flex items-center gap-2 mb-3 text-left group"
              >
                {group.expanded ? (
                  <ChevronDown className="h-4 w-4 text-purple-400" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-purple-400" />
                )}
                <div className="w-2 h-2 rounded-full bg-purple-400" />
                <span className="text-sm font-bold text-purple-400 uppercase tracking-wider">
                  {group.name}
                </span>
                <span className="text-xs text-[#8B949E]">({group.count})</span>
              </button>

              {/* Exercise Cards */}
              {group.expanded && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                  {group.exercises.map((exercise) => (
                    <div
                      key={exercise.id}
                      className="rounded-xl p-4 relative group/card hover:scale-[1.01] transition-all"
                      style={{
                        background: "rgba(22,27,34,0.95)",
                        border: "1px solid rgba(255,255,255,0.08)",
                        boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
                      }}
                    >
                      {/* Exercise Name */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="w-2 h-2 rounded-full bg-purple-400 mt-1.5 shrink-0" />
                        <h3 className="text-sm font-bold text-white flex-1 mx-2">
                          {exercise.name}
                        </h3>
                      </div>

                      {/* Stats Grid */}
                      <div className="grid grid-cols-3 gap-3 mb-3">
                        {/* Último */}
                        <div className="flex flex-col items-center">
                          <div className="flex items-center gap-1 mb-1">
                            <div
                              className="w-1.5 h-1.5 rounded-full"
                              style={{ background: "#22C55E" }}
                            />
                            <span className="text-[10px] text-[#8B949E] uppercase">
                              Último
                            </span>
                          </div>
                          <span
                            className="text-lg font-black"
                            style={{ color: exercise.lastWeight ? "#22C55E" : "#30363D" }}
                          >
                            {exercise.lastWeight ? `${exercise.lastWeight.toFixed(1)} kg` : "—"}
                          </span>
                        </div>

                        {/* Mejor */}
                        <div className="flex flex-col items-center">
                          <div className="flex items-center gap-1 mb-1">
                            <div
                              className="w-1.5 h-1.5 rounded-full"
                              style={{ background: "#F97316" }}
                            />
                            <span className="text-[10px] text-[#8B949E] uppercase">
                              Mejor
                            </span>
                          </div>
                          <span
                            className="text-lg font-black"
                            style={{ color: exercise.bestWeight ? "#F97316" : "#30363D" }}
                          >
                            {exercise.bestWeight ? `${exercise.bestWeight.toFixed(1)} kg` : "—"}
                          </span>
                        </div>

                        {/* Series */}
                        <div className="flex flex-col items-center">
                          <div className="flex items-center gap-1 mb-1">
                            <div
                              className="w-1.5 h-1.5 rounded-full"
                              style={{ background: "#00D4FF" }}
                            />
                            <span className="text-[10px] text-[#8B949E] uppercase">
                              Series
                            </span>
                          </div>
                          <span className="text-lg font-black text-[#00D4FF]">
                            {exercise.series}
                          </span>
                        </div>
                      </div>

                      {/* Recommendation */}
                      {exercise.lastWeight && (
                        <div className="mb-3">
                          <span
                            className="text-xs px-2 py-1 rounded-full font-semibold"
                            style={{
                              background:
                                exercise.recommendation === "subir"
                                  ? "rgba(34,197,94,0.15)"
                                  : "rgba(168,85,247,0.15)",
                              border: `1px solid ${
                                exercise.recommendation === "subir"
                                  ? "rgba(34,197,94,0.3)"
                                  : "rgba(168,85,247,0.3)"
                              }`,
                              color:
                                exercise.recommendation === "subir" ? "#22C55E" : "#A855F7",
                            }}
                          >
                            {exercise.recommendation === "subir"
                              ? "↑ Recomendar subir peso"
                              : "→ Mantener peso"}
                          </span>
                        </div>
                      )}

                      {/* Aliases */}
                      <p className="text-xs text-[#30363D] mb-3 truncate">{exercise.aliases}</p>

                      {/* Archive Button */}
                      <button
                        className="text-xs text-[#8B949E] hover:text-white transition-colors"
                        style={{
                          background: "transparent",
                          border: "none",
                        }}
                      >
                        Archivar
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
