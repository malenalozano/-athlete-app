// VERSION DE PRUEBA SIMPLE
export default function TestApp() {
  return (
    <div className="min-h-screen bg-[#0E1117] flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-4">
          Proyecto Athlete
        </h1>
        <p className="text-[#C9FF00] text-xl">
          Sistema funcionando correctamente ✓
        </p>
        <div className="mt-8 space-y-2">
          <div className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl p-4">
            <p className="text-white">Tailwind CSS: OK</p>
          </div>
          <div className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl p-4">
            <p className="text-white">Componentes: OK</p>
          </div>
          <div className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl p-4">
            <p className="text-white">Rutas: OK</p>
          </div>
        </div>
      </div>
    </div>
  );
}
