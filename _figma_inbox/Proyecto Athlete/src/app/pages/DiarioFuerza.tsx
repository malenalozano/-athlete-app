import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { Dumbbell, Sparkles, History } from "lucide-react";
import { useState } from "react";

export function DiarioFuerza() {
  const [trainingNote, setTrainingNote] = useState("");
  const [parsedSessions, setParsedSessions] = useState<any[]>([]);

  // Historial de sesiones de ejemplo
  const sessionHistory = [
    {
      id: 1,
      date: "13/03/2026",
      exercises: [
        { exercise: "Sentadilla", series: "4x8", weight: "80kg", rpe: "7", muscles: "Piernas, Glúteos" },
        { exercise: "Press Banca", series: "3x10", weight: "60kg", rpe: "6", muscles: "Pecho, Tríceps" },
        { exercise: "Peso Muerto", series: "3x6", weight: "100kg", rpe: "8", muscles: "Espalda, Piernas" },
      ]
    }
  ];

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8">
        <h2 className="text-2xl font-semibold mb-6 text-white flex items-center gap-2">
          <Dumbbell className="h-6 w-6 text-[#C9FF00]" />
          Diario de Fuerza
        </h2>

        <p className="text-[#8B949E] mb-8">
          Escribe tus entrenamientos de fuerza en lenguaje natural. La IA detectará automáticamente
          fechas, ejercicios, series, repeticiones y peso para estructurar tus sesiones.
        </p>

        {/* Formulario de Entrada Libre */}
        <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl mb-8">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-[#C9FF00]" />
              Entrada Libre de Entrenamiento
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <Textarea 
                  value={trainingNote}
                  onChange={(e) => setTrainingNote(e.target.value)}
                  placeholder={"Ejemplo:\n\nHoy hice:\n- Sentadilla 4x8 con 80kg\n- Press banca 3x10 a 60kg RPE 6\n- Peso muerto 3x6 a 100kg\n\nAyer hice pierna ligera:\n- Zancadas 3x12\n- Extensiones 3x15 RPE 5"}
                  rows={12}
                  className="bg-[#0E1117] border-[#C9FF00]/30 text-white resize-none font-mono"
                />
                <p className="text-xs text-[#8B949E] mt-2">
                  💡 Puedes incluir múltiples días en un solo texto. La IA detectará "hoy", "ayer",
                  fechas específicas o días de la semana.
                </p>
              </div>

              <Button 
                className="w-full bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] hover:from-[#a8d600] hover:to-[#C9FF00] font-bold py-3"
                disabled={!trainingNote.trim()}
              >
                🤖 Procesar Entrenamiento con IA
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Previsualización de Sesiones Detectadas */}
        {parsedSessions.length > 0 && (
          <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl mb-8">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-white">
                  Sesiones Detectadas ({parsedSessions.length})
                </CardTitle>
                <Button className="bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] hover:from-[#a8d600] hover:to-[#C9FF00] font-bold">
                  💾 Guardar {parsedSessions.length} Sesiones
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {parsedSessions.map((session, idx) => (
                  <div key={idx} className="border-l-4 border-l-[#C9FF00] pl-4">
                    <h4 className="text-white font-semibold mb-3">
                      Sesión del {session.date}
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-[#C9FF00]/20">
                            <th className="text-left text-[#8B949E] pb-2">Ejercicio</th>
                            <th className="text-left text-[#8B949E] pb-2">Series x Reps</th>
                            <th className="text-left text-[#8B949E] pb-2">Peso</th>
                            <th className="text-left text-[#8B949E] pb-2">RPE</th>
                            <th className="text-left text-[#8B949E] pb-2">Grupos Musculares</th>
                          </tr>
                        </thead>
                        <tbody>
                          {session.exercises.map((ex: any, i: number) => (
                            <tr key={i} className="border-b border-[#30363D]">
                              <td className="text-white py-2">{ex.exercise}</td>
                              <td className="text-white py-2">{ex.series}</td>
                              <td className="text-white py-2">{ex.weight}</td>
                              <td className="text-white py-2">{ex.rpe}</td>
                              <td className="text-[#8B949E] py-2">{ex.muscles}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Historial de Sesiones */}
        <div>
          <h3 className="text-lg font-semibold mb-4 text-white flex items-center gap-2">
            <History className="h-5 w-5 text-[#C9FF00]" />
            Historial de Sesiones Guardadas ({sessionHistory.length})
          </h3>

          <div className="space-y-4">
            {sessionHistory.map((session) => (
              <Card key={session.id} className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-white text-base">
                      Sesión del {session.date}
                    </CardTitle>
                    <span className="text-sm text-[#8B949E]">
                      {session.exercises.length} ejercicios
                    </span>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-[#C9FF00]/20">
                          <th className="text-left text-[#8B949E] pb-2">Ejercicio</th>
                          <th className="text-left text-[#8B949E] pb-2">Series x Reps</th>
                          <th className="text-left text-[#8B949E] pb-2">Peso</th>
                          <th className="text-left text-[#8B949E] pb-2">RPE</th>
                          <th className="text-left text-[#8B949E] pb-2">Grupos Musculares</th>
                        </tr>
                      </thead>
                      <tbody>
                        {session.exercises.map((ex, i) => (
                          <tr key={i} className="border-b border-[#30363D]">
                            <td className="text-white py-2">{ex.exercise}</td>
                            <td className="text-white py-2">{ex.series}</td>
                            <td className="text-white py-2">{ex.weight}</td>
                            <td className="text-white py-2">{ex.rpe}</td>
                            <td className="text-[#8B949E] py-2">{ex.muscles}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}