import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { KPICard } from "../components/KPICard";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { useUser } from "../context/UserContext";
import { ChevronDown, ChevronUp, Minus, Plus, Eye, EyeOff, HelpCircle } from "lucide-react";
import { useState } from "react";

export function Profile() {
  const { userName } = useUser();
  const [garminSyncOpen, setGarminSyncOpen] = useState(true);
  const [activitiesToSync, setActivitiesToSync] = useState(20);
  const [showPassword, setShowPassword] = useState(false);

  const kpis = [
    { label: "OBJETIVO", value: "--" },
    { label: "RITMO", value: "--" },
    { label: "CARRERA/SEM", value: "--" },
    { label: "FUERZA/SEM", value: "--" },
  ];

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8">
        <h2 className="text-2xl font-semibold mb-6 text-white">Perfil de {userName}</h2>

        {/* KPIs Rápidos */}
        <section className="mb-8">
          <h3 className="text-lg font-semibold mb-4 text-white">KPIs Rápidos</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {kpis.map((kpi) => (
              <div
                key={kpi.label}
                className="bg-[#161B22] border-l-4 border-l-[#C9FF00] rounded-xl p-4"
              >
                <p className="text-sm text-[#8B949E] font-semibold mb-1">{kpi.label}</p>
                <p className="text-xl font-bold text-white">{kpi.value}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Formulario de Edición */}
        <section>
          <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
            <CardHeader>
              <CardTitle className="text-white">Editar Perfil</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Columna Izquierda */}
                  <div className="space-y-4">
                    <div>
                      <Label className="text-white mb-2 block">Nombre</Label>
                      <Input
                        defaultValue={userName || ""}
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Edad</Label>
                      <Input
                        type="number"
                        placeholder="Ej: 30"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Sexo</Label>
                      <select className="w-full bg-[#0E1117] border border-[#C9FF00]/30 rounded-lg px-3 py-2 text-white">
                        <option value="">Seleccionar</option>
                        <option value="F">Femenino</option>
                        <option value="M">Masculino</option>
                      </select>
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Peso actual (kg)</Label>
                      <Input
                        type="number"
                        placeholder="Ej: 60"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Objetivo</Label>
                      <Input
                        placeholder="Ej: Maratón"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>
                  </div>

                  {/* Columna Derecha */}
                  <div className="space-y-4">
                    <div>
                      <Label className="text-white mb-2 block">Ritmo Objetivo - Límite Superior (rápido)</Label>
                      <Input
                        placeholder="min:seg/km"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Ritmo Objetivo - Límite Inferior (lento)</Label>
                      <Input
                        placeholder="min:seg/km"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Días de carrera/semana</Label>
                      <Input
                        type="number"
                        placeholder="Ej: 4"
                        min="1"
                        max="7"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Días de fuerza/semana</Label>
                      <Input
                        type="number"
                        placeholder="Ej: 2"
                        min="0"
                        max="7"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>
                  </div>
                </div>

                {/* Bloque Garmin */}
                <div className="border-t border-[#C9FF00]/30 pt-6 space-y-4">
                  {/* Título con desplegable */}
                  <button
                    type="button"
                    onClick={() => setGarminSyncOpen(!garminSyncOpen)}
                    className="flex items-center justify-between w-full text-white font-semibold hover:text-[#C9FF00] transition-colors"
                  >
                    <span>Sincronización Garmin</span>
                    {garminSyncOpen ? (
                      <ChevronUp className="h-5 w-5" />
                    ) : (
                      <ChevronDown className="h-5 w-5" />
                    )}
                  </button>

                  {garminSyncOpen && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* GARMIN CONNECT (OPCIONAL) */}
                      <Card className="bg-[#0E1117] border border-[#C9FF00]/20 rounded-xl">
                        <CardContent className="pt-6 pb-6 space-y-4">
                          <h5 className="text-[#C9FF00] font-bold uppercase text-xs mb-4">
                            GARMIN CONNECT (OPCIONAL)
                          </h5>

                          <div>
                            <Label className="text-white mb-2 block text-sm">Email Garmin</Label>
                            <Input
                              type="email"
                              placeholder="tu@email.com"
                              className="bg-[#161B22] border-[#C9FF00]/30 text-white"
                            />
                          </div>

                          <div className="relative">
                            <Label className="text-white mb-2 block text-sm flex items-center gap-2">
                              Nueva contraseña Garmin
                              <HelpCircle className="h-3 w-3 text-[#8B949E]" />
                            </Label>
                            <div className="relative">
                              <Input
                                type={showPassword ? "text" : "password"}
                                placeholder="••••••••"
                                className="bg-[#161B22] border-[#C9FF00]/30 text-white pr-10"
                              />
                              <button
                                type="button"
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8B949E] hover:text-white transition-colors"
                                onClick={() => setShowPassword(!showPassword)}
                              >
                                {showPassword ? (
                                  <EyeOff className="h-4 w-4" />
                                ) : (
                                  <Eye className="h-4 w-4" />
                                )}
                              </button>
                            </div>
                          </div>

                          <Button
                            type="button"
                            className="w-full bg-[#161B22] border border-[#C9FF00]/40 text-white hover:bg-[#C9FF00]/10"
                          >
                            Guardar conexión Garmin
                          </Button>
                        </CardContent>
                      </Card>

                      {/* SINCRONIZACIÓN MANUAL GARMIN */}
                      <Card className="bg-[#0E1117] border border-[#C9FF00]/20 rounded-xl">
                        <CardContent className="pt-6 pb-6 space-y-4">
                          <h5 className="text-[#C9FF00] font-bold uppercase text-xs mb-4">
                            SINCRONIZACIÓN MANUAL GARMIN
                          </h5>

                          <p className="text-[#8B949E] text-sm">
                            Elige cuántas actividades de running quieres sincronizar manualmente.
                          </p>

                          <div>
                            <Label className="text-white mb-2 block text-sm">
                              Número de actividades a sincronizar
                            </Label>
                            <div className="flex items-center gap-3">
                              <button
                                type="button"
                                onClick={() => setActivitiesToSync(Math.max(1, activitiesToSync - 1))}
                                className="p-2 bg-[#161B22] border border-[#C9FF00]/30 rounded-lg text-white hover:bg-[#C9FF00]/10 transition-colors"
                              >
                                <Minus className="h-4 w-4" />
                              </button>

                              <Input
                                type="number"
                                value={activitiesToSync}
                                onChange={(e) => setActivitiesToSync(Math.max(1, parseInt(e.target.value) || 1))}
                                className="bg-[#161B22] border-[#C9FF00]/30 text-white text-center flex-1"
                              />

                              <button
                                type="button"
                                onClick={() => setActivitiesToSync(activitiesToSync + 1)}
                                className="p-2 bg-[#161B22] border border-[#C9FF00]/30 rounded-lg text-white hover:bg-[#C9FF00]/10 transition-colors"
                              >
                                <Plus className="h-4 w-4" />
                              </button>
                            </div>
                          </div>

                          <Button
                            type="button"
                            className="w-full bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] hover:from-[#a8d600] hover:to-[#C9FF00] font-bold"
                          >
                            Sincronizar actividades Garmin ahora
                          </Button>
                        </CardContent>
                      </Card>
                    </div>
                  )}
                </div>

                {/* Botón Guardar */}
                <div className="flex justify-end">
                  <Button className="bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] hover:from-[#a8d600] hover:to-[#C9FF00] font-bold px-8 py-3">
                    💾 Guardar cambios de perfil
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}