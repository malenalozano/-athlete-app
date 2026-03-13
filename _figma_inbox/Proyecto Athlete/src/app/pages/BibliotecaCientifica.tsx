import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { BookOpen, Upload, FileText } from "lucide-react";

export function BibliotecaCientifica() {
  // Estudios de ejemplo (mock data)
  const studies = [
    {
      id: 1,
      title: "Fisiología del Entrenamiento de Resistencia",
      category: "Fisiología",
      scope: "Compartido",
      date: "10/03/2026",
      summary: "Estudio sobre adaptaciones cardiovasculares y musculares en deportes de resistencia..."
    }
  ];

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8">
        <h2 className="text-2xl font-semibold mb-6 text-white flex items-center gap-2">
          <BookOpen className="h-6 w-6 text-[#C9FF00]" />
          Biblioteca Científica
        </h2>

        <p className="text-[#8B949E] mb-8">
          Carga estudios científicos en formato PDF, TXT o MD para que la IA pueda utilizar
          este conocimiento al generar planes de entrenamiento y responder consultas.
        </p>

        {/* Formulario de Carga */}
        <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl mb-8">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Upload className="h-5 w-5 text-[#C9FF00]" />
              Cargar Nuevo Estudio
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label className="text-white mb-2 block">Alcance del Estudio</Label>
                  <select className="w-full bg-[#0E1117] border border-[#C9FF00]/30 rounded-lg px-3 py-2 text-white">
                    <option value="perfil">Solo este perfil</option>
                    <option value="compartido">Compartido para ambos</option>
                  </select>
                </div>

                <div>
                  <Label className="text-white mb-2 block">Categoría</Label>
                  <select className="w-full bg-[#0E1117] border border-[#C9FF00]/30 rounded-lg px-3 py-2 text-white">
                    <option value="">Seleccionar categoría</option>
                    <option value="fisiologia">Fisiología del Ejercicio</option>
                    <option value="nutricion">Nutrición Deportiva</option>
                    <option value="psicologia">Psicología del Deporte</option>
                    <option value="fuerza">Entrenamiento de Fuerza</option>
                    <option value="recuperacion">Recuperación y Adaptación</option>
                    <option value="ciclo">Ciclo Menstrual y Rendimiento</option>
                    <option value="tecnica">Técnica de Carrera</option>
                    <option value="otro">Otro</option>
                  </select>
                </div>
              </div>

              <div>
                <Label className="text-white mb-2 block">Archivo (PDF, TXT, MD)</Label>
                <div className="border-2 border-dashed border-[#C9FF00]/30 rounded-lg p-8 text-center hover:border-[#C9FF00]/60 transition-colors cursor-pointer bg-[#0E1117]">
                  <Upload className="h-10 w-10 text-[#C9FF00] mx-auto mb-3" />
                  <p className="text-white mb-1">Arrastra un archivo aquí o haz clic para seleccionar</p>
                  <p className="text-sm text-[#8B949E]">Formatos soportados: PDF, TXT, MD</p>
                  <input 
                    type="file" 
                    accept=".pdf,.txt,.md"
                    className="hidden"
                  />
                </div>
              </div>

              <div>
                <Label className="text-white mb-2 block">
                  Resumen Manual (opcional)
                </Label>
                <Textarea 
                  placeholder="Si lo dejas vacío, la IA generará un resumen automático del contenido..."
                  rows={4}
                  className="bg-[#0E1117] border-[#C9FF00]/30 text-white resize-none"
                />
                <p className="text-xs text-[#8B949E] mt-2">
                  💡 Un resumen manual ayuda a la IA a entender mejor el contexto del estudio
                </p>
              </div>

              <Button className="w-full bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] hover:from-[#a8d600] hover:to-[#C9FF00] font-bold py-3">
                📚 Guardar Estudio
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Listado de Estudios */}
        <div>
          <h3 className="text-lg font-semibold mb-4 text-white">
            Estudios Guardados ({studies.length})
          </h3>

          {studies.length === 0 ? (
            <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
              <CardContent className="pt-12 pb-12 text-center">
                <FileText className="h-12 w-12 text-[#8B949E] mx-auto mb-4" />
                <p className="text-[#8B949E]">
                  No hay estudios guardados aún. Comienza cargando tu primer estudio científico.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {studies.map((study) => (
                <Card key={study.id} className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl hover:border-[#C9FF00]/60 transition-colors">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-white text-base mb-2">
                          {study.title}
                        </CardTitle>
                        <div className="flex flex-wrap gap-2 mb-3">
                          <span className="px-2 py-1 bg-[#C9FF00]/20 text-[#C9FF00] text-xs rounded-full border border-[#C9FF00]/40">
                            {study.category}
                          </span>
                          <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded-full border border-blue-500/40">
                            {study.scope}
                          </span>
                          <span className="px-2 py-1 bg-[#30363D] text-[#8B949E] text-xs rounded-full">
                            {study.date}
                          </span>
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-[#8B949E] mb-4">
                      {study.summary}
                    </p>
                    <Button variant="ghost" size="sm" className="text-[#C9FF00] hover:bg-[#C9FF00]/10">
                      Ver Detalles →
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}