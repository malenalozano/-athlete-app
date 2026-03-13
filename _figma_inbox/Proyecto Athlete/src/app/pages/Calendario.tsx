import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Calendar as CalendarIcon } from "lucide-react";

export function Calendario() {
  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8">
        <h2 className="text-2xl font-semibold mb-6 text-white">Calendario de Entrenamientos</h2>

        <div className="grid grid-cols-1 gap-6">
          <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-white">Semana Actual</CardTitle>
                <CalendarIcon className="h-6 w-6 text-[#C9FF00]" />
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-[#8B949E]">
                No hay entrenamientos programados. El calendario se poblará
                automáticamente cuando conectes con Garmin o agregues sesiones manualmente.
              </p>
            </CardContent>
          </Card>

          <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
            <CardHeader>
              <CardTitle className="text-white">Próximos Hitos</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-[#8B949E]">
                Basado en tus checkpoints, se generarán automáticamente fechas objetivo
                para cada hito del plan de maratón.
              </p>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
