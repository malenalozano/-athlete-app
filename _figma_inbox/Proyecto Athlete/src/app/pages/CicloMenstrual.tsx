import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { useUser } from "../context/UserContext";
import { Heart, Calendar as CalendarIcon, AlertCircle } from "lucide-react";

export function CicloMenstrual() {
  const { userId } = useUser();

  // Restricción de acceso - solo Malena
  if (userId !== 1) {
    return (
      <div className="min-h-screen bg-[#0E1117]">
        <Header />
        <main className="container mx-auto px-6 py-8">
          <Card className="bg-[#161B22] border border-pink-500/30 rounded-xl">
            <CardContent className="pt-8 pb-8 text-center">
              <AlertCircle className="h-12 w-12 text-pink-400 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-white mb-2">
                Sección No Disponible
              </h2>
              <p className="text-[#8B949E]">
                Esta sección solo está disponible para Malena
              </p>
            </CardContent>
          </Card>
        </main>
      </div>
    );
  }

  const phaseColors: { [key: string]: string } = {
    "Folicular": "bg-blue-500",
    "Ovulación": "bg-green-500",
    "Lútea": "bg-yellow-500",
    "Menstrual": "bg-red-500",
  };

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8">
        <h2 className="text-2xl font-semibold mb-6 text-white flex items-center gap-2">
          <Heart className="h-6 w-6 text-pink-400" />
          Ciclo Menstrual
        </h2>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Formulario de Registro */}
          <div className="lg:col-span-2">
            <Card className="bg-[#161B22] border border-pink-500/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white">Registrar Entrada Diaria</CardTitle>
              </CardHeader>
              <CardContent>
                <form className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label className="text-white mb-2 block">Fecha</Label>
                      <Input 
                        type="date" 
                        className="bg-[#0E1117] border-pink-500/30 text-white"
                      />
                    </div>

                    <div>
                      <Label className="text-white mb-2 block">Fase del Ciclo</Label>
                      <select className="w-full bg-[#0E1117] border border-pink-500/30 rounded-lg px-3 py-2 text-white">
                        <option value="">Seleccionar fase</option>
                        <option value="Menstrual">Menstrual</option>
                        <option value="Folicular">Folicular</option>
                        <option value="Ovulación">Ovulación</option>
                        <option value="Lútea">Lútea</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <Label className="text-white mb-2 block">
                      Fatiga Subjetiva (1-10)
                    </Label>
                    <Input 
                      type="number" 
                      min="1" 
                      max="10" 
                      placeholder="1 = Muy energética, 10 = Muy fatigada"
                      className="bg-[#0E1117] border-pink-500/30 text-white"
                    />
                  </div>

                  <div>
                    <Label className="text-white mb-2 block">
                      Notas / Molestias / Dolor
                    </Label>
                    <Textarea 
                      placeholder="Describe síntomas, molestias o cualquier observación relevante..."
                      rows={4}
                      className="bg-[#0E1117] border-pink-500/30 text-white resize-none"
                    />
                  </div>

                  <Button className="w-full bg-gradient-to-r from-pink-500 to-purple-500 text-white hover:from-pink-600 hover:to-purple-600 font-bold">
                    💾 Guardar Registro
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>

          {/* Métrica de Ciclo Estimado */}
          <div>
            <Card className="bg-gradient-to-br from-pink-500/10 to-purple-500/10 border border-pink-500/30 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white text-base">Ciclo Actual</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-pink-300 mb-1">Duración Estimada</p>
                  <p className="text-3xl font-bold text-white">28 días</p>
                </div>
                <div>
                  <p className="text-sm text-pink-300 mb-1">Día del Ciclo</p>
                  <p className="text-3xl font-bold text-white">-</p>
                </div>
                <div>
                  <p className="text-sm text-pink-300 mb-1">Fase Actual</p>
                  <p className="text-lg font-semibold text-white">-</p>
                </div>
                <div>
                  <p className="text-sm text-pink-300 mb-1">Próxima Regla</p>
                  <p className="text-lg font-semibold text-white">- días</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Calendario Mensual */}
        <Card className="bg-[#161B22] border border-pink-500/30 rounded-xl mb-8">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-white flex items-center gap-2">
                <CalendarIcon className="h-5 w-5 text-pink-400" />
                Calendario del Ciclo
              </CardTitle>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" className="text-white hover:bg-[#30363D]">
                  ← Anterior
                </Button>
                <span className="text-white font-semibold">Marzo 2026</span>
                <Button variant="ghost" size="sm" className="text-white hover:bg-[#30363D]">
                  Siguiente →
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="mb-4">
              <p className="text-sm text-[#8B949E] mb-4">
                Registra tus datos diarios para ver el calendario completo con predicciones
              </p>
              
              {/* Leyenda de visualización */}
              <div className="flex flex-wrap gap-4 justify-center mb-6 p-4 bg-[#0E1117] rounded-lg">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-red-500"></div>
                  <span className="text-xs text-[#8B949E]">Menstrual</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-blue-500"></div>
                  <span className="text-xs text-[#8B949E]">Folicular</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-green-500"></div>
                  <span className="text-xs text-[#8B949E]">Ovulación</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-yellow-500"></div>
                  <span className="text-xs text-[#8B949E]">Lútea</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded border-2 border-white border-dashed"></div>
                  <span className="text-xs text-[#8B949E]">Predicción</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded border-2 border-white"></div>
                  <span className="text-xs text-[#8B949E]">Registro Real</span>
                </div>
              </div>
            </div>

            {/* Grid del calendario (ejemplo vacío) */}
            <div className="grid grid-cols-7 gap-2">
              {["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"].map((day) => (
                <div key={day} className="text-center text-xs font-semibold text-[#8B949E] py-2">
                  {day}
                </div>
              ))}
              {Array.from({ length: 35 }, (_, i) => (
                <div 
                  key={i} 
                  className="aspect-square bg-[#0E1117] rounded-lg border border-[#30363D] hover:border-pink-500/50 transition-colors cursor-pointer flex items-center justify-center"
                >
                  <span className="text-xs text-[#8B949E]">
                    {i < 31 ? i + 1 : ""}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Tabla de Próximos Ciclos */}
        <Card className="bg-[#161B22] border border-pink-500/30 rounded-xl">
          <CardHeader>
            <CardTitle className="text-white">Próximos Inicios de Ciclo (Predicción)</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-[#8B949E] mb-4">
              Basado en el promedio de tus ciclos anteriores
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-pink-500/20">
                    <th className="text-sm font-semibold text-pink-300 pb-3">Fecha Estimada</th>
                    <th className="text-sm font-semibold text-pink-300 pb-3">Fase</th>
                    <th className="text-sm font-semibold text-pink-300 pb-3">Días Restantes</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td colSpan={3} className="pt-4 text-center text-[#8B949E]">
                      Registra tus datos para generar predicciones
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}