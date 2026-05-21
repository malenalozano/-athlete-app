import { useState, useEffect } from "react";
import { X, Check, TrendingUp, ChevronUp } from "lucide-react";
import {
  getSesionFuerzaHoy,
  registrarSesionFuerza,
  type EjercicioFuerzaHoy,
  type GrupoFuerza,
  type RegistroEjercicioInput,
} from "../api";

// ── Colores por grupo ──────────────────────────────────────────────────────────

const GRUPO_COLOR: Record<GrupoFuerza, string> = {
  Push:   "#C9FF00",
  Pull:   "#00D4FF",
  Pierna: "#A855F7",
};

const GRUPO_BG: Record<GrupoFuerza, string> = {
  Push:   "rgba(201,255,0,0.08)",
  Pull:   "rgba(0,212,255,0.08)",
  Pierna: "rgba(168,85,247,0.08)",
};

// ── Fila de un ejercicio ───────────────────────────────────────────────────────

interface RegistroRow {
  ejercicio_id: number;
  series: string;
  repeticiones: string;
  peso: string;
  completado: boolean;
}

function EjercicioRow({
  ejercicio,
  row,
  color,
  onChange,
}: {
  ejercicio: EjercicioFuerzaHoy;
  row: RegistroRow;
  color: string;
  onChange: (updated: RegistroRow) => void;
}) {
  const hint =
    ejercicio.ultima_series && ejercicio.ultimas_reps && ejercicio.ultimo_peso
      ? `${ejercicio.ultima_series}×${ejercicio.ultimas_reps} · ${ejercicio.ultimo_peso}kg`
      : ejercicio.series_objetivo && ejercicio.reps_objetivo
      ? `obj: ${ejercicio.series_objetivo}×${ejercicio.reps_objetivo}${ejercicio.peso_objetivo ? ` ${ejercicio.peso_objetivo}kg` : ""}`
      : null;

  return (
    <div
      className="rounded-xl p-3"
      style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}
    >
      {/* Nombre + badge subir peso */}
      <div className="flex items-center gap-2 mb-3">
        <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: color }} />
        <span className="text-sm font-semibold text-white flex-1">{ejercicio.nombre}</span>
        {ejercicio.subir_peso && (
          <span
            className="flex items-center gap-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded-full"
            style={{ background: "rgba(34,197,94,0.15)", color: "#22C55E", border: "1px solid rgba(34,197,94,0.3)" }}
          >
            <ChevronUp className="h-3 w-3" />
            Sube peso
          </span>
        )}
        {hint && <span className="text-[10px] text-[#8B949E] shrink-0">{hint}</span>}
      </div>

      {/* Campos */}
      <div className="grid grid-cols-4 gap-2 items-end">
        {[
          { label: "Series", key: "series" as const, placeholder: ejercicio.ultima_series?.toString() ?? ejercicio.series_objetivo?.toString() ?? "4" },
          { label: "Reps",   key: "repeticiones" as const, placeholder: ejercicio.ultimas_reps?.toString() ?? ejercicio.reps_objetivo?.toString() ?? "8" },
          { label: "Peso kg",key: "peso" as const, placeholder: ejercicio.ultimo_peso?.toString() ?? ejercicio.peso_objetivo?.toString() ?? "0" },
        ].map(({ label, key, placeholder }) => (
          <div key={key}>
            <p className="text-[9px] text-[#8B949E] uppercase mb-1">{label}</p>
            <input
              type="number"
              value={row[key]}
              placeholder={placeholder}
              onChange={(e) => onChange({ ...row, [key]: e.target.value })}
              className="w-full px-2 py-1.5 rounded-lg text-sm text-white text-center outline-none"
              style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}
            />
          </div>
        ))}

        {/* Toggle completado */}
        <div>
          <p className="text-[9px] text-[#8B949E] uppercase mb-1">¿Todo?</p>
          <button
            onClick={() => onChange({ ...row, completado: !row.completado })}
            className="w-full py-1.5 rounded-lg text-xs font-bold transition-all"
            style={
              row.completado
                ? { background: "rgba(34,197,94,0.2)", color: "#22C55E", border: "1px solid rgba(34,197,94,0.4)" }
                : { background: "rgba(255,255,255,0.04)", color: "#8B949E", border: "1px solid rgba(255,255,255,0.1)" }
            }
          >
            {row.completado ? <Check className="h-4 w-4 mx-auto" /> : "—"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Modal principal ─────────────────────────────────────────────────────────────

export function ModalRegistroFuerza({
  usuarioId,
  grupo: grupoProp,
  ejerciciosProp,
  onClose,
  onGuardado,
}: {
  usuarioId: number;
  /** Si se pasa grupo+ejercicios directamente (desde Calendario/PlanSemanal) */
  grupo?: GrupoFuerza;
  ejerciciosProp?: EjercicioFuerzaHoy[];
  onClose: () => void;
  onGuardado?: () => void;
}) {
  const [grupo, setGrupo] = useState<GrupoFuerza | null>(grupoProp ?? null);
  const [ejercicios, setEjercicios] = useState<EjercicioFuerzaHoy[]>(ejerciciosProp ?? []);
  const [rows, setRows] = useState<RegistroRow[]>([]);
  const [loading, setLoading] = useState(!grupoProp);
  const [saving, setSaving] = useState(false);
  const [guardado, setGuardado] = useState(false);
  const [error, setError] = useState("");

  // Si no se pasaron ejercicios, cargarlos desde la API
  useEffect(() => {
    if (grupoProp && ejerciciosProp) {
      initRows(ejerciciosProp);
      return;
    }
    setLoading(true);
    getSesionFuerzaHoy(usuarioId)
      .then((data) => {
        if (data.tiene_fuerza && data.grupo) {
          setGrupo(data.grupo);
          setEjercicios(data.ejercicios);
          initRows(data.ejercicios);
        }
      })
      .catch(() => setError("Error cargando sesión"))
      .finally(() => setLoading(false));
  }, [usuarioId, grupoProp]);

  function initRows(ejs: EjercicioFuerzaHoy[]) {
    setRows(
      ejs.map((ej) => ({
        ejercicio_id: ej.id,
        series: ej.ultima_series?.toString() ?? ej.series_objetivo?.toString() ?? "",
        repeticiones: ej.ultimas_reps?.toString() ?? ej.reps_objetivo?.toString() ?? "",
        peso: ej.ultimo_peso?.toString() ?? ej.peso_objetivo?.toString() ?? "",
        completado: false,
      }))
    );
  }

  const handleGuardar = async () => {
    const registros: RegistroEjercicioInput[] = rows
      .filter((r) => r.peso && r.series && r.repeticiones)
      .map((r) => ({
        ejercicio_id: r.ejercicio_id,
        series: parseInt(r.series),
        repeticiones: parseInt(r.repeticiones),
        peso: parseFloat(r.peso),
        completado: r.completado,
      }));

    if (registros.length === 0) {
      setError("Introduce al menos un ejercicio con series, reps y peso.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      await registrarSesionFuerza(usuarioId, registros);
      setGuardado(true);
      onGuardado?.();
      setTimeout(onClose, 1200);
    } catch {
      setError("Error al guardar la sesión. Inténtalo de nuevo.");
    } finally {
      setSaving(false);
    }
  };

  const color = grupo ? GRUPO_COLOR[grupo] : "#C9FF00";
  const bg = grupo ? GRUPO_BG[grupo] : "rgba(201,255,0,0.08)";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: "rgba(0,0,0,0.75)" }}>
      <div
        className="w-full max-w-lg rounded-2xl flex flex-col"
        style={{
          background: "#161B22",
          border: `1px solid ${color}30`,
          maxHeight: "90vh",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4" style={{ color }} />
            <h2 className="text-base font-bold text-white">
              Registrar sesión{grupo ? ` · ${grupo}` : ""}
            </h2>
          </div>
          <button onClick={onClose} className="text-[#8B949E] hover:text-white transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-3">
          {loading && (
            <p className="text-center text-[#8B949E] text-sm py-8">Cargando ejercicios...</p>
          )}

          {!loading && ejercicios.length === 0 && (
            <div
              className="rounded-xl p-4 text-center"
              style={{ background: bg, border: `1px dashed ${color}40` }}
            >
              <p className="text-sm text-[#8B949E]">
                Sin ejercicios activos{grupo ? ` para ${grupo}` : ""}.
              </p>
              <p className="text-xs text-[#30363D] mt-1">Añade ejercicios en la pestaña /ejercicios.</p>
            </div>
          )}

          {!loading && ejercicios.map((ej, i) => (
            <EjercicioRow
              key={ej.id}
              ejercicio={ej}
              row={rows[i] ?? { ejercicio_id: ej.id, series: "", repeticiones: "", peso: "", completado: false }}
              color={color}
              onChange={(updated) =>
                setRows((prev) => prev.map((r, idx) => (idx === i ? updated : r)))
              }
            />
          ))}

          {error && <p className="text-xs text-red-400 text-center">{error}</p>}
        </div>

        {/* Footer */}
        {!loading && ejercicios.length > 0 && (
          <div className="px-5 py-4" style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}>
            <p className="text-[10px] text-[#8B949E] mb-3">
              Marca ✓ en "¿Todo?" si completaste todas las series → se marcará subir peso la próxima vez.
            </p>
            <button
              onClick={handleGuardar}
              disabled={saving || guardado}
              className="w-full py-3 rounded-xl text-sm font-bold transition-all"
              style={{
                background: guardado
                  ? "rgba(34,197,94,0.2)"
                  : `linear-gradient(135deg, ${color}, ${color}cc)`,
                color: guardado ? "#22C55E" : "#0E1117",
                opacity: saving ? 0.7 : 1,
              }}
            >
              {guardado ? "✓ Sesión guardada" : saving ? "Guardando..." : "Guardar sesión"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
