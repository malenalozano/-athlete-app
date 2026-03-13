import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Activity, Brain, HeartPulse, MessageSquare } from "lucide-react";
import { KPICard } from "../components/KPICard";

export function PersonalTrainer() {
  // Datos mock de biométricos
  const biometricData = [
    { label: "HRV", value: "-" },
    { label: "READINESS", value: "-" },
    { label: "BODY BATTERY", value: "-" },
    { label: "RHR", value: "-" },
  ];

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8">
        <h2 className="text-2xl font-semibold mb-6 text-white">Entrenador Personal Premium</h2>

        <Tabs defaultValue="checkin" className="space-y-6">
          <TabsList className="bg-[#161B22] border border-[#C9FF00]/30 p-1 rounded-xl">
            <TabsTrigger 
              value="checkin"
              className="data-[state=active]:bg-[#C9FF00]/20 data-[state=active]:text-white data-[state=active]:border data-[state=active]:border-[#C9FF00]/60 text-[#8B949E] rounded-lg"
            >
              <Activity className="h-4 w-4 mr-2" />
              Check-in Diario
            </TabsTrigger>
            <TabsTrigger 
              value="plan"
              className="data-[state=active]:bg-[#C9FF00]/20 data-[state=active]:text-white data-[state=active]:border data-[state=active]:border-[#C9FF00]/60 text-[#8B949E] rounded-lg"
            >
              <Brain className="h-4 w-4 mr-2" />
              Generar Plan Semanal
            </TabsTrigger>
            <TabsTrigger 
              value="lesiones"
              className="data-[state=active]:bg-[#C9FF00]/20 data-[state=active]:text-white data-[state=active]:border data-[state=active]:border-[#C9FF00]/60 text-[#8B949E] rounded-lg"
            >
              <HeartPulse className="h-4 w-4 mr-2" />
              Lesiones y Prevención
            </TabsTrigger>
            <TabsTrigger 
              value="asistente"
              className="data-[state=active]:bg-[#C9FF00]/20 data-[state=active]:text-white data-[state=active]:border data-[state=active]:border-[#C9FF00]/60 text-[#8B949E] rounded-lg"
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              Asistente Virtual
            </TabsTrigger>
          </TabsList>

          {/* Tab: Check-in Diario */}
          <TabsContent value="checkin" className="space-y-6">
            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white">Dashboard Biométricos</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {biometricData.map((metric) => (
                    <KPICard
                      key={metric.label}
                      label={metric.label}
                      value={metric.value}
                      period="Hoy"
                    />
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white">Últimos 7 Días - Biométricos</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-[#8B949E]">
                  Sincroniza tus datos de Garmin para ver el historial completo
                  de HRV, readiness, body battery, recuperación y más.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white">Calidad del Sueño</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-[#8B949E]">
                  Los datos de sueño detallado se mostrarán aquí una vez sincronizado.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Generar Plan Semanal */}
          <TabsContent value="plan" className="space-y-6">
            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white">Señales de Estado</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-[#8B949E]">HRV Promedio:</span>
                    <span className="text-white font-semibold">-</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8B949E]">Nivel de Estrés:</span>
                    <span className="text-white font-semibold">-</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8B949E]">Calidad del Sueño:</span>
                    <span className="text-white font-semibold">-</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8B949E]">RPE Última Semana:</span>
                    <span className="text-white font-semibold">-</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white">Generar Plan Premium</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-[#8B949E] mb-4">
                  El plan semanal se generará basándose en tus métricas actuales,
                  objetivos y disponibilidad. Puedes coordinar con tu pareja
                  para entrenamientos conjuntos.
                </p>
                <button className="w-full py-3 px-6 bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] font-bold rounded-lg hover:from-[#a8d600] hover:to-[#C9FF00] transition-all">
                  🚀 Generar Plan de Esta Semana
                </button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Lesiones y Prevención */}
          <TabsContent value="lesiones" className="space-y-6">
            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white">Registrar Nueva Lesión</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-[#8B949E]">
                  Formulario para registrar lesiones, zona afectada, tipo, fecha y notas.
                  Próximamente disponible.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white">Lesiones Activas</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-[#8B949E]">
                  No hay lesiones registradas actualmente.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Asistente Virtual */}
          <TabsContent value="asistente" className="space-y-6">
            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white">Chat Conversacional</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="h-96 bg-[#0E1117] rounded-lg p-4 overflow-y-auto">
                    <p className="text-[#8B949E] text-center mt-20">
                      El asistente virtual construye contexto desde tus últimas actividades,
                      estado fisiológico y estudios científicos cargados.
                      <br /><br />
                      Próximamente disponible.
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Escribe tu pregunta..."
                      className="flex-1 bg-[#0E1117] border border-[#C9FF00]/30 rounded-lg px-4 py-2 text-white placeholder:text-[#8B949E]"
                      disabled
                    />
                    <button 
                      className="px-6 py-2 bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] font-bold rounded-lg"
                      disabled
                    >
                      Enviar
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}