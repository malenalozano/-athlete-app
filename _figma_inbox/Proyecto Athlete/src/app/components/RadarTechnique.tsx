import React from "react";

// Puedes reemplazar esto por una librería de gráficos como 'react-chartjs-2' o 'recharts' para el radar
export const RadarTechnique = () => {
  return (
    <div className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl p-6 flex-1 flex flex-col items-center">
      <h3 className="text-lg font-semibold text-[#C9FF00] mb-4 flex items-center gap-2">
        <span className="text-[#C9FF00] text-xl">&#9432;</span>
        Radar Antilesiones y Técnica
      </h3>
      <div className="w-full h-[350px] flex items-center justify-center mb-4 bg-[#23272F] rounded-xl">
        {/* Aquí iría el radar chart real */}
        <img src="/radar-demo.png" alt="Radar Chart" className="w-80 h-80" />
      </div>
      <p className="text-xs text-[#8B949E]">Análisis Técnico</p>
    </div>
  );
};

export const MetricsDetail = () => (
  <div className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl p-6 flex-1">
    <h3 className="text-lg font-semibold text-[#C9FF00] mb-4">Métricas Detalladas</h3>
    <ul className="space-y-3">
      <li className="flex justify-between items-center">
        <span className="text-white font-bold">Cadencia</span>
        <span className="text-[#C9FF00] font-bold">172 spm</span>
        <span className="ml-2 text-xs text-green-400">✓ OK</span>
      </li>
      <li className="flex justify-between items-center">
        <span className="text-white font-bold">Zancada</span>
        <span className="text-[#C9FF00] font-bold">118 cm</span>
        <span className="ml-2 text-xs text-yellow-400">⚠ Revisar</span>
      </li>
      <li className="flex justify-between items-center">
        <span className="text-white font-bold">Tiempo Contacto</span>
        <span className="text-[#C9FF00] font-bold">248 ms</span>
        <span className="ml-2 text-xs text-green-400">✓ OK</span>
      </li>
      <li className="flex justify-between items-center">
        <span className="text-white font-bold">Oscilación Vertical</span>
        <span className="text-[#C9FF00] font-bold">8.2 cm</span>
        <span className="ml-2 text-xs text-green-400">✓ OK</span>
      </li>
      <li className="flex justify-between items-center">
        <span className="text-white font-bold">Potencia</span>
        <span className="text-[#C9FF00] font-bold">245 W</span>
        <span className="ml-2 text-xs text-green-400">✓ OK</span>
      </li>
    </ul>
    <div className="mt-6">
      <div className="bg-yellow-900 border border-yellow-400 rounded-lg p-3 mb-2 text-yellow-200 text-sm flex items-center gap-2">
        <span>⚠</span> Zancada ligeramente larga - Riesgo de overstride
      </div>
      <div className="bg-[#23272F] border border-[#C9FF00]/30 rounded-lg p-3 text-[#C9FF00] text-sm flex items-center gap-2">
        <span>✓</span> Cadencia óptima mantenida
      </div>
    </div>
  </div>
);
