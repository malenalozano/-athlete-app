import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { useUser } from "../context/UserContext";
import { useState } from "react";

export function Profile() {
  const { userName } = useUser();
  const [activitiesToSync, setActivitiesToSync] = useState<number>(50);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState("");

  const kpis = [
    { label: "OBJETIVO", value: "Maratón" },
    { label: "RITMO", value: "4:30-5:00" },
    { label: "CARRERA/SEM", value: "4 días" },
    { label: "FUERZA/SEM", value: "2 días" },
  ];

  const handleManualSync = async () => {
    if (!Number.isFinite(activitiesToSync) || activitiesToSync < 1) {
      setSyncFeedback("Introduce un número válido (mínimo 1 actividad).");
      return;
    }

    setIsSyncing(true);
    setSyncFeedback("");

    // Placeholder UI while backend endpoint is wired.
    await new Promise((resolve) => setTimeout(resolve, 700));

    setIsSyncing(false);
    setSyncFeedback(`Sincronización manual solicitada para ${activitiesToSync} actividades.`);
  };

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
                        defaultValue="30" 
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Sexo</Label>
                      <select className="w-full bg-[#0E1117] border border-[#C9FF00]/30 rounded-lg px-3 py-2 text-white">
                        <option value="F">Femenino</option>
                        <option value="M">Masculino</option>
                      </select>
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Peso actual (kg)</Label>
                      <Input 
                        type="number" 
                        defaultValue="60" 
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Objetivo</Label>
                      <Input 
                        defaultValue="Maratón" 
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>
                  </div>

                  {/* Columna Derecha */}
                  <div className="space-y-4">
                    <div>
                      <Label className="text-white mb-2 block">Ritmo Objetivo - Límite Superior (rápido)</Label>
                      <Input 
                        defaultValue="4:30" 
                        placeholder="min:seg/km"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Ritmo Objetivo - Límite Inferior (lento)</Label>
                      <Input 
                        defaultValue="5:00" 
                        placeholder="min:seg/km"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Días de carrera/semana</Label>
                      <Input 
                        type="number" 
                        defaultValue="4" 
                        min="1" 
                        max="7"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Días de fuerza/semana</Label>
                      <Input 
                        type="number" 
                        defaultValue="2" 
                        min="0" 
                        max="7"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>
                  </div>
                </div>

                {/* Bloque Garmin */}
                <div className="border-t border-[#C9FF00]/30 pt-6 space-y-4">
                  <h4 className="text-white font-semibold">Conexión Garmin (opcional)</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label className="text-white mb-2 block">Email Garmin</Label>
                      <Input 
                        type="email" 
                        placeholder="tu-email@ejemplo.com"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>
                    <div>
                      <Label className="text-white mb-2 block">Nueva Contraseña Garmin</Label>
                      <Input 
                        type="password" 
                        placeholder="••••••••"
                        className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                      />
                    </div>
                  </div>

                  <div className="mt-2 rounded-xl border border-[#C9FF00]/30 bg-[#0E1117]/70 p-4">
                    <h5 className="text-sm font-semibold text-white">Sincronización manual de actividades</h5>
                    <p className="mt-1 text-xs text-[#8B949E]">
                      Indica cuántas actividades quieres sincronizar al pulsar el botón.
                    </p>

                    <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-end">
                      <div className="w-full md:max-w-[240px]">
                        <Label className="mb-2 block text-white">Número de actividades</Label>
                        <Input
                          type="number"
                          min="1"
                          max="500"
                          value={activitiesToSync}
                          onChange={(e) => setActivitiesToSync(Number(e.target.value || 0))}
                          className="bg-[#0E1117] border-[#C9FF00]/30 text-white"
                        />
                      </div>

                      <Button
                        type="button"
                        onClick={handleManualSync}
                        disabled={isSyncing}
                        className="bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] hover:from-[#a8d600] hover:to-[#C9FF00] font-bold"
                      >
                        {isSyncing ? "Sincronizando..." : "Sincronizar ahora"}
                      </Button>
                    </div>

                    {syncFeedback && (
                      <p className="mt-3 text-sm text-[#C9FF00]">{syncFeedback}</p>
                    )}
                  </div>
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