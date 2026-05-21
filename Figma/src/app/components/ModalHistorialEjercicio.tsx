import { useState, useEffect } from "react";
import { X, TrendingUp } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getHistorialEjercicio, type HistorialEntrada } from "../api";

interface Props {
  usuarioId: number;
  ejercicioId: number;
  ejercicioNombre: string;
  color: string;
  onClose: () => void;
}

export function ModalHistorialEjercicio({ usuarioId, ejercicioId, ejercicioNombre, color, onClose }: Props) {
  const [historial, setHistorial] = useState<HistorialEntrada[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getHistorialEjercicio(usuarioId, ejercicioId)
      .then(setHistorial)
      .catch(() => setHistorial([]))
      .finally(() => setLoading(false));
  }, [usuarioId, ejercicioId]);

  const chartData = [...historial]
    .reverse()
    .filter((h) => h.peso != null)
    .map((h) => ({
      fecha: h.fecha?.slice(5) ?? "", // MM-DD
      peso: h.peso,
      label: `${h.series ?? "?"}×${h.repeticiones ?? "?"} ${h.peso}kg`,
    }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: "rgba(0,0,0,0.75)" }}>
      <div
        className="w-full max-w-lg rounded-2xl flex flex-col"
        style={{ background: "#161B22", border: `1px solid ${color}30`, maxHeight: "85vh" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4" style={{ color }} />
            <h2 className="text-base font-bold text-white truncate">{ejercicioNombre}</h2>
          </div>
          <button onClick={onClose} className="text-[#8B949E] hover:text-white transition-colors shrink-0">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-4">
          {loading && <p className="text-center text-[#8B949E] text-sm py-8">Cargando historial...</p>}

          {!loading && historial.length === 0 && (
            <p className="text-center text-[#8B949E] text-sm py-8">Sin registros aún.</p>
          )}

          {!loading && chartData.length > 1 && (
            <div>
              <p className="text-xs text-[#8B949E] uppercase font-semibold mb-3">Progresión de peso</p>
              <div style={{ height: 140 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="fecha" tick={{ fill: "#8B949E", fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "#8B949E", fontSize: 10 }} axisLine={false} tickLine={false} width={30} />
                    <Tooltip
                      contentStyle={{ background: "#0E1117", border: `1px solid ${color}40`, borderRadius: 8, fontSize: 12 }}
                      formatter={(v) => [`${v} kg`, "Peso"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="peso"
                      stroke={color}
                      strokeWidth={2}
                      dot={{ fill: color, r: 3 }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {!loading && historial.length > 0 && (
            <div>
              <p className="text-xs text-[#8B949E] uppercase font-semibold mb-3">Últimas sesiones</p>
              <div className="space-y-2">
                {historial.map((h, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded-xl px-3 py-2.5"
                    style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
                  >
                    <span className="text-xs text-[#8B949E]">{h.fecha}</span>
                    <div className="flex items-center gap-3">
                      {h.series && h.repeticiones && (
                        <span className="text-xs text-white font-semibold">
                          {h.series}×{h.repeticiones}
                        </span>
                      )}
                      {h.peso != null && (
                        <span className="text-sm font-bold" style={{ color }}>
                          {h.peso} kg
                        </span>
                      )}
                      {h.rpe != null && (
                        <span className="text-[10px] text-[#8B949E]">RPE {h.rpe}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
