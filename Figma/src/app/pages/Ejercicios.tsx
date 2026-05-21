import { Header } from "../components/Header";
import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, Plus, Archive, ArchiveRestore, X } from "lucide-react";
import { useUser } from "../context/UserContext";
import {
  getEjercicios,
  archivarEjercicio,
  crearEjercicio,
  type EjerciciosBiblioteca,
  type EjercicioBiblioteca,
  type GrupoFuerza,
} from "../api";

// ── Configuración de grupos ────────────────────────────────────────────────────

const GRUPOS: { key: GrupoFuerza; label: string; color: string; bg: string; descripcion: string }[] = [
  { key: "Push",   label: "PUSH",   color: "#C9FF00", bg: "rgba(201,255,0,0.08)",   descripcion: "Press banca, Press militar, Fondos..." },
  { key: "Pull",   label: "PULL",   color: "#00D4FF", bg: "rgba(0,212,255,0.08)",   descripcion: "Dominadas, Remo, Jalones..." },
  { key: "Pierna", label: "PIERNA", color: "#A855F7", bg: "rgba(168,85,247,0.08)", descripcion: "Sentadilla, Peso muerto, Hip thrust..." },
];

// ── Modal Añadir Ejercicio ─────────────────────────────────────────────────────

function ModalNuevoEjercicio({
  onClose,
  onCreado,
  usuarioId,
  grupoInicial,
}: {
  onClose: () => void;
  onCreado: () => void;
  usuarioId: number;
  grupoInicial: GrupoFuerza;
}) {
  const [nombre, setNombre] = useState("");
  const [grupo, setGrupo] = useState<GrupoFuerza>(grupoInicial);
  const [alias, setAlias] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!nombre.trim()) { setError("El nombre es obligatorio"); return; }
    setLoading(true);
    try {
      await crearEjercicio({ usuario_id: usuarioId, nombre: nombre.trim(), grupo_muscular: grupo, alias: alias.trim() || undefined });
      onCreado();
      onClose();
    } catch {
      setError("Error al crear el ejercicio");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: "rgba(0,0,0,0.7)" }}>
      <div className="w-full max-w-md rounded-2xl p-6" style={{ background: "#161B22", border: "1px solid rgba(255,255,255,0.1)" }}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-white">Nuevo ejercicio</h2>
          <button onClick={onClose} className="text-[#8B949E] hover:text-white transition-colors"><X className="h-5 w-5" /></button>
        </div>

        <div className="space-y-4">
          {/* Grupo */}
          <div>
            <label className="text-xs text-[#8B949E] uppercase font-semibold mb-2 block">Grupo</label>
            <div className="flex gap-2">
              {GRUPOS.map((g) => (
                <button
                  key={g.key}
                  onClick={() => setGrupo(g.key)}
                  className="flex-1 py-2 rounded-lg text-sm font-bold transition-all"
                  style={{
                    background: grupo === g.key ? g.bg : "rgba(255,255,255,0.04)",
                    border: `1px solid ${grupo === g.key ? g.color : "rgba(255,255,255,0.08)"}`,
                    color: grupo === g.key ? g.color : "#8B949E",
                  }}
                >
                  {g.label}
                </button>
              ))}
            </div>
          </div>

          {/* Nombre */}
          <div>
            <label className="text-xs text-[#8B949E] uppercase font-semibold mb-2 block">Nombre *</label>
            <input
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Ej: Press banca"
              className="w-full px-3 py-2.5 rounded-lg text-sm text-white placeholder-[#30363D] outline-none"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              autoFocus
            />
          </div>

          {/* Alias */}
          <div>
            <label className="text-xs text-[#8B949E] uppercase font-semibold mb-2 block">Alias / notas (opcional)</label>
            <input
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              placeholder="Ej: BP, banco plano"
              className="w-full px-3 py-2.5 rounded-lg text-sm text-white placeholder-[#30363D] outline-none"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}
            />
          </div>

          {error && <p className="text-xs text-red-400">{error}</p>}

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full py-3 rounded-xl text-sm font-bold transition-all"
            style={{ background: "#C9FF00", color: "#0E1117", opacity: loading ? 0.6 : 1 }}
          >
            {loading ? "Guardando..." : "Añadir ejercicio"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Tarjeta de ejercicio ───────────────────────────────────────────────────────

function EjercicioCard({
  ejercicio,
  color,
  onArchivar,
}: {
  ejercicio: EjercicioBiblioteca;
  color: string;
  onArchivar: (id: number, archivar: boolean) => void;
}) {
  const archivado = ejercicio.archivado;

  return (
    <div
      className="rounded-xl p-4 transition-all"
      style={{
        background: archivado ? "rgba(22,27,34,0.5)" : "rgba(22,27,34,0.95)",
        border: `1px solid ${archivado ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.08)"}`,
        opacity: archivado ? 0.6 : 1,
      }}
    >
      {/* Nombre */}
      <div className="flex items-start justify-between mb-3">
        <div className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ background: color }} />
        <h3 className="text-sm font-bold text-white flex-1 mx-2">{ejercicio.nombre}</h3>
        <button
          onClick={() => onArchivar(ejercicio.id, !archivado)}
          className="text-[#8B949E] hover:text-white transition-colors shrink-0"
          title={archivado ? "Desarchivar" : "Archivar"}
        >
          {archivado
            ? <ArchiveRestore className="h-4 w-4" />
            : <Archive className="h-4 w-4" />
          }
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col items-center">
          <span className="text-[10px] text-[#8B949E] uppercase mb-1">Último</span>
          <span className="text-base font-black" style={{ color: ejercicio.ultimo_peso ? "#22C55E" : "#30363D" }}>
            {ejercicio.ultimo_peso ? `${ejercicio.ultimo_peso} kg` : "—"}
          </span>
        </div>
        <div className="flex flex-col items-center">
          <span className="text-[10px] text-[#8B949E] uppercase mb-1">Mejor</span>
          <span className="text-base font-black" style={{ color: ejercicio.mejor_peso ? "#F97316" : "#30363D" }}>
            {ejercicio.mejor_peso ? `${ejercicio.mejor_peso} kg` : "—"}
          </span>
        </div>
      </div>

      {/* Alias */}
      {ejercicio.alias && (
        <p className="text-[10px] text-[#30363D] mt-2 truncate">{ejercicio.alias}</p>
      )}
    </div>
  );
}

// ── Sección de grupo ───────────────────────────────────────────────────────────

function GrupoSection({
  grupo,
  activos,
  archivados,
  onArchivar,
  onAddClick,
}: {
  grupo: typeof GRUPOS[0];
  activos: EjercicioBiblioteca[];
  archivados: EjercicioBiblioteca[];
  onArchivar: (id: number, archivar: boolean) => void;
  onAddClick: () => void;
}) {
  const [expandido, setExpandido] = useState(true);
  const [verArchivados, setVerArchivados] = useState(false);

  return (
    <div className="mb-6">
      {/* Header del grupo */}
      <div className="flex items-center gap-3 mb-3">
        <button onClick={() => setExpandido(!expandido)} className="flex items-center gap-2 flex-1 text-left">
          {expandido
            ? <ChevronDown className="h-4 w-4" style={{ color: grupo.color }} />
            : <ChevronRight className="h-4 w-4" style={{ color: grupo.color }} />
          }
          <div className="w-2 h-2 rounded-full" style={{ background: grupo.color }} />
          <span className="text-sm font-bold uppercase tracking-wider" style={{ color: grupo.color }}>
            {grupo.label}
          </span>
          <span className="text-xs text-[#8B949E]">({activos.length} activos)</span>
        </button>

        {/* Botón añadir */}
        <button
          onClick={onAddClick}
          className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs transition-all hover:opacity-80"
          style={{ background: grupo.bg, border: `1px solid ${grupo.color}30`, color: grupo.color }}
        >
          <Plus className="h-3 w-3" />
          Añadir
        </button>
      </div>

      {expandido && (
        <>
          {/* Activos */}
          {activos.length === 0 ? (
            <div
              className="rounded-xl p-4 text-center mb-3"
              style={{ background: grupo.bg, border: `1px dashed ${grupo.color}40` }}
            >
              <p className="text-xs text-[#8B949E]">
                Sin ejercicios activos · {grupo.descripcion}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-3">
              {activos.map((ej) => (
                <EjercicioCard key={ej.id} ejercicio={ej} color={grupo.color} onArchivar={onArchivar} />
              ))}
            </div>
          )}

          {/* Archivados (desplegable) */}
          {archivados.length > 0 && (
            <div>
              <button
                onClick={() => setVerArchivados(!verArchivados)}
                className="flex items-center gap-1.5 text-xs text-[#8B949E] hover:text-white transition-colors mb-2"
              >
                {verArchivados ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                <Archive className="h-3 w-3" />
                {archivados.length} archivado{archivados.length > 1 ? "s" : ""}
              </button>
              {verArchivados && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-3">
                  {archivados.map((ej) => (
                    <EjercicioCard key={ej.id} ejercicio={ej} color={grupo.color} onArchivar={onArchivar} />
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Página principal ───────────────────────────────────────────────────────────

export function Ejercicios() {
  const { userId } = useUser();
  const [data, setData] = useState<EjerciciosBiblioteca | null>(null);
  const [loading, setLoading] = useState(true);
  const [modalGrupo, setModalGrupo] = useState<GrupoFuerza | null>(null);

  const cargar = () => {
    if (!userId) return;
    setLoading(true);
    getEjercicios(userId)
      .then(setData)
      .catch(() => null)
      .finally(() => setLoading(false));
  };

  useEffect(() => { cargar(); }, [userId]);

  const handleArchivar = async (ejercicioId: number, archivar: boolean) => {
    await archivarEjercicio(ejercicioId, archivar);
    cargar(); // Recargar para reflejar el cambio
  };

  const grupos = data?.grupos ?? {
    Push:   { activos: [], archivados: [] },
    Pull:   { activos: [], archivados: [] },
    Pierna: { activos: [], archivados: [] },
  };

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            🏋️ Ejercicios
          </h1>
          <p className="text-sm text-[#8B949E] mt-1">
            Los ejercicios activos de cada grupo se incluyen en la notificación del día de entreno.
          </p>
        </div>

        {loading ? (
          <div className="text-center py-12 text-[#8B949E] text-sm">Cargando...</div>
        ) : (
          GRUPOS.map((g) => (
            <GrupoSection
              key={g.key}
              grupo={g}
              activos={grupos[g.key]?.activos ?? []}
              archivados={grupos[g.key]?.archivados ?? []}
              onArchivar={handleArchivar}
              onAddClick={() => setModalGrupo(g.key)}
            />
          ))
        )}
      </main>

      {modalGrupo && userId && (
        <ModalNuevoEjercicio
          onClose={() => setModalGrupo(null)}
          onCreado={cargar}
          usuarioId={userId}
          grupoInicial={modalGrupo}
        />
      )}
    </div>
  );
}
