import { Header } from "../components/Header";
import { KPICard } from "../components/KPICard";
import { CheckpointCard } from "../components/CheckpointCard";
import { Progress } from "../components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { useUser } from "../context/UserContext";
import { 
  Activity, 
  Heart, 
  Moon, 
  Dumbbell, 
  AlertCircle,
  TrendingUp,
  Calendar as CalendarIcon
} from "lucide-react";

export function Home() {
  const { userId, userName } = useUser();

  // Datos mock - serán reemplazados con datos reales de Garmin/caché
  const kpis = [
    { label: "KM", value: "0.0", period: "Últimos 7 días" },
    { label: "CARRERAS", value: "0", period: "Últimos 7 días" },
    { label: "FUERZA", value: "0", period: "Sesiones" },
    { label: "SUEÑO MEDIO", value: "-", period: "h/noche" },
  ];

  const checkpoints = [
    {
      distance: "5K",
      time: "Sub 22:30",
      description: "Demuestra la velocidad máxima necesaria",
      status: "pending" as const,
    },
    {
      distance: "10K",
      time: "Sub 46:30",
      description: "Confirma umbral y capacidad de sostener el ritmo",
      status: "pending" as const,
    },
    {
      distance: "Media Maratón",
      time: "Sub 1h42",
      description: "El checkpoint definitivo para el ritmo de maratón",
      status: "pending" as const,
    },
  ];

  const weekDays = [
    { day: "Lun", date: "10 Mar", activity: "Descanso" },
    { day: "Mar", date: "11 Mar", activity: "Descanso" },
    { day: "Mié", date: "12 Mar", activity: "Descanso" },
    { day: "Jue", date: "13 Mar", activity: "Hoy" },
    { day: "Vie", date: "14 Mar", activity: "-" },
    { day: "Sáb", date: "15 Mar", activity: "-" },
    { day: "Dom", date: "16 Mar", activity: "-" },
  ];

  // Datos de biométricos para semáforo Garmin
  const garminMetrics = [
    { label: "HRV", value: "-", status: "neutral" },
    { label: "READINESS", value: "-", status: "neutral" },
    { label: "BODY BATTERY", value: "-", status: "neutral" },
    { label: "RECUPERACIÓN", value: "-", status: "neutral" },
    { label: "FC REPOSO", value: "-", status: "neutral" },
    { label: "SpO2", value: "-", status: "neutral" },
  ];

  // Datos de técnica de carrera
  const runningTechnique = [
    { label: "Cadencia", value: "-", unit: "spm" },
    { label: "Zancada", value: "-", unit: "cm" },
    { label: "Tiempo Contacto", value: "-", unit: "ms" },
    { label: "Oscilación Vertical", value: "-", unit: "cm" },
    { label: "Potencia", value: "-", unit: "W" },
  ];

  const completedCheckpoints = checkpoints.filter(
    (c) => c.status === "completed"
  ).length;
  const totalCheckpoints = checkpoints.length;
  const progressPercentage = (completedCheckpoints / totalCheckpoints) * 100;

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8 space-y-10">
        {/* Panel de Métricas Rápidas */}
        <section>
          <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
            <Activity className="h-5 w-5 text-[#C9FF00]" />
            Resumen Últimos 7 Días
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {kpis.map((kpi) => (
              <KPICard
                key={kpi.label}
                label={kpi.label}
                value={kpi.value}
                period={kpi.period}
              />
            ))}
          </div>
        </section>

        {/* Bloque Estado Ciclo de Malena (solo visible para Dani) */}
        {userId === 2 && (
          <section>
            <Card className="bg-gradient-to-br from-pink-500/10 to-purple-500/10 border border-pink-500/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Heart className="h-5 w-5 text-pink-400" />
                  Estado del Ciclo de Malena
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-pink-300 mb-1">Fase Actual</p>
                    <p className="text-lg font-bold text-white">-</p>
                  </div>
                  <div>
                    <p className="text-sm text-pink-300 mb-1">Próxima Regla</p>
                    <p className="text-lg font-bold text-white">- días</p>
                  </div>
                  <div>
                    <p className="text-sm text-pink-300 mb-1">Energía</p>
                    <p className="text-lg font-bold text-white">-</p>
                  </div>
                </div>
                <div className="bg-[#0E1117]/50 rounded-lg p-4">
                  <p className="text-sm text-pink-200">
                    💡 <strong>Consejo:</strong> Sincroniza los datos para ver recomendaciones de entrenamiento conjunto.
                  </p>
                </div>
              </CardContent>
            </Card>
          </section>
        )}

        {/* Sección de Objetivos y Checkpoints */}
        <section>
          <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-[#C9FF00]" />
            Objetivo: Maratón
          </h2>

          {/* Barra de Progreso */}
          <div className="bg-[#161B22] rounded-xl border border-[#C9FF00]/30 p-6 mb-6">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-white">
                <span className="font-bold">{completedCheckpoints}</span> de{" "}
                <span className="font-bold">{totalCheckpoints}</span>{" "}
                checkpoints completados para el objetivo Maratón
              </p>
              <span className="text-sm font-bold text-[#C9FF00]">
                {progressPercentage.toFixed(0)}%
              </span>
            </div>
            <Progress 
              value={progressPercentage} 
              className="h-3 bg-[#30363D]" 
            />
          </div>

          {/* Tarjetas de Checkpoints */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {checkpoints.map((checkpoint, index) => (
              <CheckpointCard key={index} {...checkpoint} />
            ))}
          </div>
        </section>

        {/* Calendario Semanal de Actividades */}
        <section>
          <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
            <CalendarIcon className="h-5 w-5 text-[#C9FF00]" />
            Esta Semana
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {weekDays.map((day, index) => (
              <Card 
                key={index} 
                className={`bg-[#161B22] border ${
                  day.activity === "Hoy" 
                    ? "border-[#C9FF00] shadow-lg shadow-[#C9FF00]/20" 
                    : "border-[#C9FF00]/30"
                } rounded-xl`}
              >
                <CardContent className="pt-4 pb-4 text-center">
                  <p className="text-xs text-[#8B949E] font-semibold mb-1">{day.day}</p>
                  <p className="text-sm text-white font-bold mb-2">{day.date}</p>
                  <p className="text-xs text-[#C9FF00]">{day.activity}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Progreso de Running */}
        <section>
          <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
            <CardHeader>
              <CardTitle className="text-white">Progreso de Running</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64 flex items-center justify-center">
                <p className="text-[#8B949E]">
                  Sincroniza tus datos de Garmin para ver el gráfico de kilómetros semanales
                </p>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Radar Antilesiones y Técnica */}
        <section>
          <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-[#C9FF00]" />
            Radar Antilesiones y Técnica
          </h2>
          <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
            <CardContent className="pt-6">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {runningTechnique.map((metric, index) => (
                  <div key={index} className="text-center">
                    <p className="text-sm text-[#8B949E] mb-2">{metric.label}</p>
                    <p className="text-2xl font-bold text-white">{metric.value}</p>
                    <p className="text-xs text-[#8B949E] mt-1">{metric.unit}</p>
                  </div>
                ))}
              </div>
              <div className="mt-6 pt-6 border-t border-[#C9FF00]/20">
                <p className="text-sm text-[#8B949E] text-center">
                  No hay alertas de técnica registradas
                </p>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Semáforo Diario Garmin */}
        <section>
          <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
            <Heart className="h-5 w-5 text-[#C9FF00]" />
            Semáforo Diario Garmin
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {garminMetrics.map((metric, index) => (
              <Card key={index} className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
                <CardContent className="pt-4 pb-4 text-center">
                  <p className="text-xs text-[#8B949E] font-semibold mb-2">{metric.label}</p>
                  <p className="text-2xl font-bold text-white">{metric.value}</p>
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="mt-4">
            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardContent className="pt-4 pb-4">
                <p className="text-sm text-[#8B949E] text-center">
                  No hay alertas de banderas rojas registradas
                </p>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Progreso de Gimnasio */}
        <section>
          <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
            <Dumbbell className="h-5 w-5 text-[#C9FF00]" />
            Progreso de Gimnasio por Grupo Muscular
          </h2>
          <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
            <CardContent className="pt-6">
              <div className="h-64 flex items-center justify-center">
                <p className="text-[#8B949E]">
                  Registra tus entrenamientos de fuerza para ver el progreso por grupo muscular
                </p>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Calidad del Sueño */}
        <section>
          <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
            <Moon className="h-5 w-5 text-[#C9FF00]" />
            Calidad del Sueño (Última Semana)
          </h2>
          <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
            <CardContent className="pt-6">
              <div className="h-64 flex items-center justify-center">
                <p className="text-[#8B949E]">
                  Sincroniza tus datos de Garmin para ver métricas de sueño detalladas
                </p>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Entrenamientos Conjuntos Malena & Dani */}
        <section>
          <h2 className="text-xl font-semibold mb-4 text-white">
            Entrenamientos Conjuntos — Malena & Dani
          </h2>
          <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
            <CardHeader>
              <CardTitle className="text-white text-base">Vista Semanal Comparada</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-48 flex items-center justify-center mb-6">
                <p className="text-[#8B949E]">
                  Sincroniza los datos para ver la coordinación de entrenamientos
                </p>
              </div>
              
              {/* Leyenda de colores */}
              <div className="flex flex-wrap gap-4 justify-center pt-4 border-t border-[#C9FF00]/20">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-pink-500"></div>
                  <span className="text-xs text-[#8B949E]">Solo Malena</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-blue-500"></div>
                  <span className="text-xs text-[#8B949E]">Solo Dani</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-[#C9FF00]"></div>
                  <span className="text-xs text-[#8B949E]">Entrenan Ambos</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-[#30363D] border border-[#8B949E]"></div>
                  <span className="text-xs text-[#8B949E]">Descanso</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}