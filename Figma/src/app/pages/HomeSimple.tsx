import { Header } from "../components/Header";
import { KPICard } from "../components/KPICard";
import { CheckpointCard } from "../components/CheckpointCard";
import { Progress } from "../components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

export function Home() {
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

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8 space-y-10">
        <section>
          <h2 className="text-xl font-semibold mb-4 text-white">
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

        <section>
          <h2 className="text-xl font-semibold mb-4 text-white">
            Objetivo: Maratón
          </h2>

          <div className="bg-[#161B22] rounded-xl border border-[#C9FF00]/30 p-6 mb-6">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-white">
                <span className="font-bold">0</span> de{" "}
                <span className="font-bold">3</span>{" "}
                checkpoints completados para el objetivo Maratón
              </p>
              <span className="text-sm font-bold text-[#C9FF00]">
                0%
              </span>
            </div>
            <Progress 
              value={0} 
              className="h-3 bg-[#30363D]" 
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {checkpoints.map((checkpoint, index) => (
              <CheckpointCard key={index} {...checkpoint} />
            ))}
          </div>
        </section>

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
      </main>
    </div>
  );
}
