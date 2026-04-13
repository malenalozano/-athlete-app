import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { useState } from "react";
import { CheckCircle, Circle, Flame, Droplets, Wind, Brain, Pill, Zap, TrendingUp, Award } from "lucide-react";

type HabitEntry = {
  completed: boolean;
  value?: number;
};

type DayLog = {
  [key: string]: HabitEntry;
};

const HABITS = [
  { id: "hidratacion", label: "Hidratación", icon: Droplets, unit: "L", color: "#3b82f6", type: "numeric", target: 2.5, emoji: "💧" },
  { id: "estiramientos", label: "Estiramientos", icon: Wind, unit: "min", color: "#C9FF00", type: "boolean", emoji: "🧘" },
  { id: "foam_roller", label: "Foam Roller", icon: Zap, unit: "", color: "#8b5cf6", type: "boolean", emoji: "🔵" },
  { id: "meditacion", label: "Meditación", icon: Brain, unit: "min", color: "#ec4899", type: "numeric", target: 10, emoji: "🧠" },
  { id: "suplementos", label: "Suplementos", icon: Pill, unit: "", color: "#f59e0b", type: "boolean", emoji: "💊" },
  { id: "pasos", label: "10k Pasos", icon: TrendingUp, unit: "pasos", color: "#10b981", type: "boolean", emoji: "👟" },
];

const WEEK_DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const DATES = ["9 Mar", "10 Mar", "11 Mar", "12 Mar", "13 Mar", "14 Mar", "15 Mar"];

// TODO: populate from real habit tracking data (Supabase / local storage)
const WEEK_DATA: { [day: string]: DayLog } = {
  "Lun": {
    hidratacion: { completed: false },
    estiramientos: { completed: false },
    foam_roller: { completed: false },
    meditacion: { completed: false },
    suplementos: { completed: false },
    pasos: { completed: false },
  },
  "Mar": {
    hidratacion: { completed: false },
    estiramientos: { completed: false },
    foam_roller: { completed: false },
    meditacion: { completed: false },
    suplementos: { completed: false },
    pasos: { completed: false },
  },
  "Mié": {
    hidratacion: { completed: false },
    estiramientos: { completed: false },
    foam_roller: { completed: false },
    meditacion: { completed: false },
    suplementos: { completed: false },
    pasos: { completed: false },
  },
  "Jue": {
    hidratacion: { completed: false },
    estiramientos: { completed: false },
    foam_roller: { completed: false },
    meditacion: { completed: false },
    suplementos: { completed: false },
    pasos: { completed: false },
  },
  "Vie": {
    hidratacion: { completed: false },
    estiramientos: { completed: false },
    foam_roller: { completed: false },
    meditacion: { completed: false },
    suplementos: { completed: false },
    pasos: { completed: false },
  },
  "Sáb": {
    hidratacion: { completed: false },
    estiramientos: { completed: false },
    foam_roller: { completed: false },
    meditacion: { completed: false },
    suplementos: { completed: false },
    pasos: { completed: false },
  },
  "Dom": {
    hidratacion: { completed: false },
    estiramientos: { completed: false },
    foam_roller: { completed: false },
    meditacion: { completed: false },
    suplementos: { completed: false },
    pasos: { completed: false },
  },
};

// TODO: populate from last 28 days of real habit data
const MONTHLY_DATA: { day: number; rate: number }[] = [];

export function Habitos() {
  const [selectedDay, setSelectedDay] = useState("Dom");
  const [todayHabits, setTodayHabits] = useState<DayLog>({ ...WEEK_DATA["Dom"] });

  const toggleHabit = (habitId: string) => {
    setTodayHabits(prev => ({
      ...prev,
      [habitId]: { ...prev[habitId], completed: !prev[habitId]?.completed }
    }));
  };

  const getDayScore = (dayData: DayLog) => {
    const total = HABITS.length;
    const completed = HABITS.filter(h => dayData[h.id]?.completed).length;
    return Math.round((completed / total) * 100);
  };

  const getStreakCount = () => {
    let streak = 0;
    const days = Object.values(WEEK_DATA);
    for (let i = days.length - 1; i >= 0; i--) {
      if (getDayScore(days[i]) >= 50) streak++;
      else break;
    }
    return streak;
  };

  const weeklyAvgScore = Math.round(
    Object.values(WEEK_DATA).reduce((acc, day) => acc + getDayScore(day), 0) / 7
  );

  const getBestHabit = () => {
    const habitScores = HABITS.map(h => ({
      ...h,
      rate: Object.values(WEEK_DATA).filter(d => d[h.id]?.completed).length / 7
    }));
    return habitScores.sort((a, b) => b.rate - a.rate)[0];
  };

  const bestHabit = getBestHabit();
  const streak = getStreakCount();

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-[#C9FF00]";
    if (score >= 60) return "text-yellow-400";
    return "text-red-400";
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return "bg-[#C9FF00]/20 border-[#C9FF00]/40";
    if (score >= 60) return "bg-yellow-500/20 border-yellow-500/40";
    return "bg-red-500/20 border-red-500/40";
  };

  const getHeatmapColor = (rate: number) => {
    if (rate >= 0.8) return "bg-[#C9FF00]";
    if (rate >= 0.6) return "bg-[#C9FF00]/60";
    if (rate >= 0.4) return "bg-[#C9FF00]/30";
    if (rate >= 0.2) return "bg-[#C9FF00]/15";
    return "bg-[#30363D]";
  };

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />
      <main className="container mx-auto px-6 py-8 space-y-8">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-white flex items-center gap-2">
            <Flame className="h-6 w-6 text-[#C9FF00]" />
            Habit Tracker
          </h2>
          <div className="flex items-center gap-2 px-4 py-2 bg-[#161B22] rounded-xl border border-[#C9FF00]/30">
            <Flame className="h-4 w-4 text-orange-400" />
            <span className="text-white font-bold">{streak}</span>
            <span className="text-[#8B949E] text-sm">días de racha</span>
          </div>
        </div>

        {/* KPIs resumen */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
            <CardContent className="pt-4 pb-4 text-center">
              <p className="text-xs text-[#8B949E] mb-1">Score Semana</p>
              <p className={`text-3xl font-bold ${getScoreColor(weeklyAvgScore)}`}>{weeklyAvgScore}%</p>
            </CardContent>
          </Card>
          <Card className="bg-[#161B22] border border-orange-500/30 rounded-xl">
            <CardContent className="pt-4 pb-4 text-center">
              <p className="text-xs text-[#8B949E] mb-1">Racha Actual</p>
              <p className="text-3xl font-bold text-orange-400">🔥 {streak}d</p>
            </CardContent>
          </Card>
          <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
            <CardContent className="pt-4 pb-4 text-center">
              <p className="text-xs text-[#8B949E] mb-1">Mejor Hábito</p>
              <p className="text-lg font-bold text-white">{bestHabit.emoji} {bestHabit.label}</p>
            </CardContent>
          </Card>
          <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
            <CardContent className="pt-4 pb-4 text-center">
              <p className="text-xs text-[#8B949E] mb-1">Mejor Día</p>
              <p className="text-3xl font-bold text-[#C9FF00]">
                {getDayScore(WEEK_DATA["Lun"])}%
              </p>
              <p className="text-xs text-[#8B949E]">Lunes</p>
            </CardContent>
          </Card>
        </div>

        {/* Vista semanal + registro de hoy */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Tabla Semanal */}
          <Card className="lg:col-span-3 bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
            <CardHeader>
              <CardTitle className="text-white text-base">Vista Semanal — Semana del 9 al 15 Mar</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr>
                      <th className="text-left text-xs text-[#8B949E] pb-4 w-32">Hábito</th>
                      {WEEK_DAYS.map((day, i) => (
                        <th key={day} className="text-center text-xs pb-4">
                          <button
                            onClick={() => setSelectedDay(day)}
                            className={`flex flex-col items-center gap-1 mx-auto px-2 py-1 rounded-lg transition-all ${
                              selectedDay === day
                                ? "bg-[#C9FF00]/20 border border-[#C9FF00]/60"
                                : "hover:bg-[#30363D]"
                            }`}
                          >
                            <span className="text-[#8B949E]">{day}</span>
                            <span className="text-white">{DATES[i].split(" ")[0]}</span>
                          </button>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="space-y-2">
                    {HABITS.map((habit) => (
                      <tr key={habit.id} className="border-t border-[#30363D]/50">
                        <td className="py-3 pr-4">
                          <div className="flex items-center gap-2">
                            <span className="text-base">{habit.emoji}</span>
                            <span className="text-xs text-[#8B949E]">{habit.label}</span>
                          </div>
                        </td>
                        {WEEK_DAYS.map((day) => {
                          const entry = WEEK_DATA[day]?.[habit.id];
                          const isToday = day === "Dom";
                          return (
                            <td key={day} className="py-3 text-center">
                              <div className="flex justify-center">
                                {entry?.completed ? (
                                  <div
                                    className="w-7 h-7 rounded-full flex items-center justify-center"
                                    style={{ backgroundColor: habit.color + "33", border: `1.5px solid ${habit.color}` }}
                                  >
                                    <span className="text-xs">✓</span>
                                  </div>
                                ) : (
                                  <div className="w-7 h-7 rounded-full border border-[#30363D] flex items-center justify-center">
                                    <span className="text-xs text-[#30363D]">–</span>
                                  </div>
                                )}
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                    {/* Fila de scores */}
                    <tr className="border-t border-[#C9FF00]/20">
                      <td className="py-3 text-xs text-[#8B949E] font-semibold">Score</td>
                      {WEEK_DAYS.map((day) => {
                        const score = getDayScore(WEEK_DATA[day]);
                        return (
                          <td key={day} className="py-3 text-center">
                            <span className={`text-xs font-bold ${getScoreColor(score)}`}>{score}%</span>
                          </td>
                        );
                      })}
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Registro de Hoy */}
          <Card className="lg:col-span-2 bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
            <CardHeader>
              <CardTitle className="text-white text-base flex items-center gap-2">
                <Award className="h-4 w-4 text-[#C9FF00]" />
                Hoy — 15 Mar 2026
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 mb-6">
                {HABITS.map((habit) => {
                  const completed = todayHabits[habit.id]?.completed;
                  return (
                    <button
                      key={habit.id}
                      onClick={() => toggleHabit(habit.id)}
                      className={`w-full flex items-center justify-between p-3 rounded-xl border transition-all ${
                        completed
                          ? "border-[#C9FF00]/50 bg-[#C9FF00]/5"
                          : "border-[#30363D] bg-[#0E1117] hover:border-[#C9FF00]/30"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{habit.emoji}</span>
                        <div className="text-left">
                          <p className={`text-sm font-medium ${completed ? "text-white" : "text-[#8B949E]"}`}>
                            {habit.label}
                          </p>
                          {habit.type === "numeric" && todayHabits[habit.id]?.value && (
                            <p className="text-xs text-[#8B949E]">
                              {todayHabits[habit.id].value} {habit.unit}
                              {" / "}{habit.target} {habit.unit}
                            </p>
                          )}
                        </div>
                      </div>
                      {completed ? (
                        <CheckCircle className="h-5 w-5 text-[#C9FF00]" />
                      ) : (
                        <Circle className="h-5 w-5 text-[#30363D]" />
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Score del día */}
              <div className={`p-4 rounded-xl border ${getScoreBg(getDayScore(todayHabits))}`}>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[#8B949E]">Score de hoy</span>
                  <span className={`text-2xl font-bold ${getScoreColor(getDayScore(todayHabits))}`}>
                    {getDayScore(todayHabits)}%
                  </span>
                </div>
                <div className="w-full bg-[#30363D] rounded-full h-2 mt-2">
                  <div
                    className="h-2 rounded-full bg-[#C9FF00] transition-all"
                    style={{ width: `${getDayScore(todayHabits)}%` }}
                  />
                </div>
                <p className="text-xs text-[#8B949E] mt-2">
                  {HABITS.filter(h => todayHabits[h.id]?.completed).length} de {HABITS.length} hábitos completados
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Mapa de calor mensual */}
        <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
          <CardHeader>
            <CardTitle className="text-white text-base">Mapa de Consistencia — Últimos 28 Días</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-7 gap-2 mb-4">
              {["L", "M", "X", "J", "V", "S", "D"].map(d => (
                <div key={d} className="text-center text-xs text-[#8B949E]">{d}</div>
              ))}
              {MONTHLY_DATA.map((d, i) => (
                <div
                  key={i}
                  className={`aspect-square rounded-md ${getHeatmapColor(d.rate)} transition-all hover:ring-1 hover:ring-[#C9FF00]/50 cursor-pointer`}
                  title={`Día ${d.day}: ${Math.round(d.rate * 100)}%`}
                />
              ))}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[#8B949E]">Menos</span>
              <div className="flex gap-1">
                {["bg-[#30363D]", "bg-[#C9FF00]/15", "bg-[#C9FF00]/30", "bg-[#C9FF00]/60", "bg-[#C9FF00]"].map((c, i) => (
                  <div key={i} className={`w-4 h-4 rounded ${c}`} />
                ))}
              </div>
              <span className="text-xs text-[#8B949E]">Más</span>
            </div>
          </CardContent>
        </Card>

        {/* Hábitos por día de la semana - análisis */}
        <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
          <CardHeader>
            <CardTitle className="text-white text-base">Análisis por Hábito</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {HABITS.map(habit => {
                const completedDays = Object.values(WEEK_DATA).filter(d => d[habit.id]?.completed).length;
                const rate = completedDays / 7;
                return (
                  <div key={habit.id} className="p-4 bg-[#0E1117] rounded-xl border border-[#30363D]">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{habit.emoji}</span>
                        <span className="text-sm text-white">{habit.label}</span>
                      </div>
                      <span className="text-sm font-bold" style={{ color: habit.color }}>
                        {completedDays}/7
                      </span>
                    </div>
                    <div className="w-full bg-[#30363D] rounded-full h-2 mb-2">
                      <div
                        className="h-2 rounded-full transition-all"
                        style={{ width: `${rate * 100}%`, backgroundColor: habit.color }}
                      />
                    </div>
                    <div className="flex gap-1">
                      {WEEK_DAYS.map(day => (
                        <div
                          key={day}
                          className="flex-1 h-2 rounded-sm"
                          style={{
                            backgroundColor: WEEK_DATA[day]?.[habit.id]?.completed
                              ? habit.color
                              : "#30363D"
                          }}
                        />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}