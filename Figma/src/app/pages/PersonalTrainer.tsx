import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Brain, HeartPulse, MessageSquare } from "lucide-react";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { useState, useEffect } from "react";
import { useUser } from "../context/UserContext";
import { getResumenEntrenador, getPerfil, generarPlanSemana, type ResumenEntrenador, type PerfilUsuario, type PlanGenerado, type SesionGenerada } from "../api";

export function PersonalTrainer() {
  const { userId } = useUser();
  const [injuryDate, setInjuryDate] = useState("");
  const [resumen, setResumen] = useState<ResumenEntrenador | null>(null);
  const [perfil, setPerfil] = useState<PerfilUsuario | null>(null);
  const [generando, setGenerando] = useState(false);
  const [planGenerado, setPlanGenerado] = useState<PlanGenerado | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;
    getResumenEntrenador(userId).then(setResumen).catch(() => null);
    getPerfil(userId).then(setPerfil).catch(() => null);
  }, [userId]);

  const handleGenerarPlan = async () => {
    if (!userId) return;
    setGenerando(true);
    setPlanError(null);
    setPlanGenerado(null);
    try {
      // Inicio de la semana actual (lunes)
      const hoy = new Date();
      const diaSemana = hoy.getDay(); // 0=dom, 1=lun...
      const diff = diaSemana === 0 ? -6 : 1 - diaSemana;
      const lunes = new Date(hoy);
      lunes.setDate(hoy.getDate() + diff);
      const fechaInicio = lunes.toISOString().split("T")[0];
      const plan = await generarPlanSemana(userId, fechaInicio);
      setPlanGenerado(plan);
    } catch (e: unknown) {
      setPlanError(e instanceof Error ? e.message : "Error generando el plan");
    } finally {
      setGenerando(false);
    }
  };

  const b = resumen?.biometrico;
  const planContextData: { label: string; value: string }[] = [
    { label: "Objetivo", value: perfil?.objetivo_tipo || "--" },
    { label: "Días disponibles", value: "--" },
    { label: "Nivel actual", value: perfil?.nivel || "--" },
    { label: "Lesiones activas", value: resumen ? String(resumen.lesiones_activas.length) : "--" },
    { label: "HRV promedio", value: b?.hrv_ms != null ? `${b.hrv_ms} ms` : "--" },
    { label: "Nivel de estrés", value: b?.estres_medio != null ? `${b.estres_medio}/100` : "--" },
    { label: "Calidad del sueño", value: b?.sleep_score != null ? `${b.sleep_score}/100` : "--" },
    { label: "RPE última semana", value: "--" },
  ];

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8">
        <h2 className="text-2xl font-semibold mb-6 text-white">Entrenador Personal Premium</h2>

        <Tabs defaultValue="plan" className="space-y-6">
          <TabsList className="bg-[#161B22] border border-[#C9FF00]/30 p-1 rounded-xl">
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

          {/* Tab: Generar Plan Semanal */}
          <TabsContent value="plan" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Tabla con datos que se envían a la IA */}
              <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
                <CardHeader>
                  <CardTitle className="text-white text-base">Datos para la IA</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-[#8B949E] mb-4">
                    Estos valores se toman automáticamente de tu perfil y métricas Garmin.
                  </p>
                  <div className="space-y-3">
                    {planContextData.map(({ label, value }) => (
                      <div
                        key={label}
                        className="flex justify-between py-2 border-b border-[#30363D]/50 last:border-b-0"
                      >
                        <span className="text-[#8B949E] text-sm">{label}:</span>
                        <span className="text-white font-semibold text-sm">{value}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Formulario de generación */}
              <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
                <CardHeader>
                  <CardTitle className="text-white text-base">Personalizar Plan</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className="text-white mb-2 block text-sm">Enfoque de esta semana</Label>
                    <select className="w-full bg-[#0E1117] border border-[#C9FF00]/30 rounded-lg px-3 py-2 text-white">
                      <option>Volumen (más kilómetros)</option>
                      <option>Velocidad (intervalos)</option>
                      <option>Fuerza</option>
                      <option>Recuperación</option>
                    </select>
                  </div>

                  <div>
                    <Label className="text-white mb-2 block text-sm">Días disponibles</Label>
                    <Input
                      placeholder="Ej: Lun, Mar, Mié, Vie, Sáb, Dom"
                      className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                    />
                  </div>

                  <div>
                    <Label className="text-white mb-2 block text-sm">Notas adicionales</Label>
                    <Textarea
                      placeholder="Ej: Esta semana tengo una carrera popular el domingo..."
                      rows={3}
                      className="bg-[#0E1117] border-[#C9FF00]/30 text-white resize-none"
                    />
                  </div>

                  <Button
                    onClick={handleGenerarPlan}
                    disabled={generando}
                    className="w-full bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] hover:from-[#a8d600] hover:to-[#C9FF00] font-bold py-3 disabled:opacity-60"
                  >
                    {generando ? "Generando..." : "Generar Plan de Esta Semana"}
                  </Button>
                </CardContent>
              </Card>
            </div>

            {/* Plan generado */}
            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white">Plan Generado</CardTitle>
              </CardHeader>
              <CardContent>
                {planError && (
                  <p className="text-red-400 text-sm">{planError}</p>
                )}
                {!planGenerado && !planError && (
                  <div className="flex flex-col items-center justify-center py-10 text-center">
                    <Brain className="h-10 w-10 text-[#30363D] mb-3" />
                    <p className="text-[#8B949E] text-sm">
                      El plan aparecerá aquí después de generarlo.
                    </p>
                    <p className="text-xs text-[#30363D] mt-1">
                      Pulsa "Generar Plan de Esta Semana" para comenzar.
                    </p>
                  </div>
                )}
                {planGenerado && (
                  <div className="space-y-4">
                    {/* Resumen */}
                    <div
                      className="rounded-xl p-4"
                      style={{ background: "rgba(201,255,0,0.06)", border: "1px solid rgba(201,255,0,0.2)" }}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold text-[#C9FF00] uppercase tracking-widest">{planGenerado.tipo_semana}</span>
                        <span className="text-xs text-[#8B949E]">Mac {planGenerado.macrociclo}</span>
                      </div>
                      <p className="text-sm text-white font-semibold">{planGenerado.km_total} km totales</p>
                      <p className="text-xs text-[#8B949E] mt-1">{planGenerado.coach_tip}</p>
                    </div>

                    {/* Lista de sesiones */}
                    <div className="space-y-2">
                      {planGenerado.sesiones.map((s: SesionGenerada, i: number) => {
                        const fecha = new Date(s.fecha + "T12:00:00");
                        const diaNombre = fecha.toLocaleDateString("es-ES", { weekday: "short", day: "numeric", month: "short" });
                        const isCarrera = s.tipo === "Carrera";
                        const color = isCarrera ? "#00D4FF" : "#A855F7";
                        return (
                          <div
                            key={i}
                            className="rounded-lg p-3 flex items-start gap-3"
                            style={{ background: `${color}08`, border: `1px solid ${color}20` }}
                          >
                            <div
                              className="shrink-0 rounded-lg px-2 py-1 text-center min-w-[44px]"
                              style={{ background: `${color}15` }}
                            >
                              <p className="text-[9px] font-bold uppercase" style={{ color }}>{diaNombre.split(" ")[0]}</p>
                              <p className="text-xs font-bold text-white">{diaNombre.split(" ")[1]}</p>
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-semibold text-white truncate">{s.sesion}</p>
                              {s.detalles && (
                                <p className="text-xs text-[#8B949E] mt-0.5 line-clamp-2">{s.detalles}</p>
                              )}
                            </div>
                            {s.km_planificados != null && (
                              <span className="shrink-0 text-xs font-bold" style={{ color }}>{s.km_planificados} km</span>
                            )}
                            {s.duracion_min != null && s.km_planificados == null && (
                              <span className="shrink-0 text-xs text-[#8B949E]">{s.duracion_min}min</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Lesiones y Prevención */}
          <TabsContent value="lesiones" className="space-y-6">
            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white">Historial y prevención de lesiones</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-[#8B949E] text-sm mb-6">
                  Las lesiones activas modifican automáticamente el plan: sustituye carreras, elimina cargas de impacto y añade trabajo preventivo.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Formulario de registro */}
                  <div className="space-y-4">
                    <div>
                      <Label className="text-white mb-2 block text-sm">Zona lesionada</Label>
                      <Input 
                        placeholder="Ej: rodilla izquierda, fascia plantar, isquio derecho"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block text-sm">Fecha inicio</Label>
                      <Input 
                        type="date"
                        value={injuryDate}
                        onChange={(e) => setInjuryDate(e.target.value)}
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block text-sm">Notas / contexto</Label>
                      <Textarea 
                        placeholder="Describe cómo ocurrió, síntomas, etc."
                        rows={4}
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white resize-none"
                      />
                    </div>

                    <Button className="w-full bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] hover:from-[#a8d600] hover:to-[#C9FF00] font-bold">
                      2. Registrar lesión
                    </Button>
                  </div>

                  {/* Estado actual */}
                  <div className="bg-[#0E1117] rounded-lg p-6 border border-[#30363D]">
                    <p className="text-white font-semibold mb-4">Sin lesiones registradas.</p>
                    <p className="text-[#8B949E] text-sm">
                      No hay lesiones activas en este momento. El plan de entrenamiento se genera sin restricciones.
                    </p>
                  </div>
                </div>
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