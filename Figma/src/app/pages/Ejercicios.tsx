import { Header } from "../components/Header";
import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, Plus, Archive, ArchiveRestore, X, Pencil, ChevronUp } from "lucide-react";
import { useUser } from "../context/UserContext";
import {
  getEjercicios,
  archivarEjercicio,
  crearEjercicio,
  editarEjercicio,
  type EjerciciosBiblioteca,
  type EjercicioBiblioteca,
  type GrupoFuerza,
} from "../api";
import { ModalHistorialEjercicio } from "../components/ModalHistorialEjercicio";

// ── Tipos extendidos ───────────────────────────────────────────────────────────

interface EjercicioExtendido extends EjercicioBiblioteca {
  series_objetivo?: number | null;
  reps_objetivo?: number | null;
  peso_objetivo?: number | null;
  ultima_series?: number | null;
  ultimas_reps?: number | null;
}

// ── Configuración de grupos ────────────────────────────────────────────────────

const GRUPOS: { key: GrupoFuerza; label: string; color: string; bg: string; descripcion: string }[] = [
  { key: "Push",   label: "PUSH",   color: "#C9FF00", bg: "rgba(201,255,0,0.08)",   descripcion: "Press banca, Press militar, Fondos..." },
  { key: "Pull",   label: "PULL",   color: "#00D4FF", bg: "rgba(0,212,255,0.08)",   descripcion: "Dominadas, Remo, Jalones..." },
  { key: "Pierna", label: "PIERNA", color: "#A855F7", bg: "rgba(168,85,247,0.08)", descripcion: "Sentadilla, Peso muerto, Hip thrust..." },
];

const COLOR_MAP: Record<string, string> = {
  Push: "#C9FF00", Pull: "#00D4FF", Pierna: "#A855F7",
};

// ── Modal Añadir / Editar Ejercicio ────────────────────────────────────────────

function ModalEjercicio({
  onClose,
  onGuardado,
  usuarioId,
  grupoInicial,
  ejercicio,          // Si viene → modo edición
}: {
  onClose: () => void;
  onGuardado: () => void;
  usuarioId: number;
  grupoInicial: GrupoFuerza;
  ejercicio?: EjercicioExtendido;
}) {
  const modoEdicion = !!ejercicio;

  const [nombre,        setNombre]        = useState(ejercicio?.nombre ?? "");
  const [grupo,         setGrupo]         = useState<GrupoFuerza>(ejercicio?.grupo_muscular as GrupoFuerza ?? grupoInicial);
  const [alias,         setAlias]         = useState(ejercicio?.alias ?? "");
  const [seriesObj,     setSeriesObj]     = useState(ejercicio?.series_objetivo?.toString() ?? "");
  const [repsObj,       setRepsObj]       = useState(ejercicio?.reps_objetivo?.toString() ?? "");
  const [pesoObj,       setPesoObj]       = useState(ejercicio?.peso_objetivo?.toString() ?? "");
  const [loading,       setLoading]       = useState(false);
  const [error,         setError]         = useState("");

  const handleSubmit = async () => {
    if (!nombre.trim()) { setError("El nombre es obligatorio"); return; }
    setLoading(true);
    try {
      const payload = {
        nombre:          nombre.trim(),
        grupo_muscular:  grupo,
        alias:           alias.trim() || undefined,
        series_objetivo: seriesObj ? parseInt(seriesObj) : undefined,
        reps_objetivo:   repsObj   ? parseInt(repsObj)   : undefined,
        peso_objetivo:   pesoObj   ? parseFloat(pesoObj) : undefined,
      };

      if (modoEdicion && ejercicio) {
        await editarEjercicio(ejercicio.id, payload);
      } else {
        await crearEjercicio({ usuario_id: usuarioId, ...payload });
      }

      onGuardado();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "";
      if (msg.includes("409")) {
        setError(`Ya existe un ejercicio con ese nombre`);
      } else {
        setError("Error al guardar el ejercicio. Inténtalo de nuevo.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: "rgba(0,0,0,0.7)" }}>
      <div className="w-full max-w-md rounded-2xl p-6" style={{ background: "#161B22", border: "1px solid rgba(255,255,255,0.1)" }}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-white">
            {modoEdicion ? "Editar ejercicio" : "Nuevo ejercicio"}
          </h2>
          <button onClick={onClose} className="text-[#8B949E] hover:text-white transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Grupo */}
          <div>
            <label className="text-xs text-[#8B949E] uppercase font-semibold mb-2 block">Grupo</label>
            <div className="flex gap-2">
              {GRUPOS.map((g) => (
                <button key={g.key} onClick={() => setGrupo(g.key)}
                  className="flex-1 py-2 rounded-lg text-sm font-bold transition-all"
                  style={{
                    background: grupo === g.key ? g.bg : "rgba(255,255,255,0.04)",
                    border: `1px solid ${grupo === g.key ? g.color : "rgba(255,255,255,0.08)"}`,
                    color: grupo === g.key ? g.color : "#8B949E",
                  }}
                >{g.label}</button>
              ))}
            </div>
          </div>

          {/* Nombre */}
          <div>
            <label className="text-xs text-[#8B949E] uppercase font-semibold mb-2 block">Nombre *</label>
            <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Ej: Press banca"
              className="w-full px-3 py-2.5 rounded-lg text-sm text-white placeholder-[#30363D] outline-none"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()} autoFocus={!modoEdicion}
            />
          </div>

          {/* Series, Reps, Peso objetivo */}
          <div>
            <label className="text-xs text-[#8B949E] uppercase font-semibold mb-2 block">
              Objetivo <span className="normal-case font-normal">(opcional — si lo dejas en blanco usa el historial)</span>
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: "Series", value: seriesObj, set: setSeriesObj, placeholder: "4" },
                { label: "Reps",   value: repsObj,   set: setRepsObj,   placeholder: "8" },
                { label: "Peso kg",value: pesoObj,   set: setPesoObj,   placeholder: "40" },
              ].map(({ label, value, set, placeholder }) => (
                <div key={label}>
                  <p className="text-[10px] text-[#8B949E] mb-1">{label}</p>
                  <input value={value} onChange={(e) => set(e.target.value)} placeholder={placeholder} type="number"
                    className="w-full px-2 py-2 rounded-lg text-sm text-white placeholder-[#30363D] outline-none text-center"
                    style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Alias */}
          <div>
            <label className="text-xs text-[#8B949E] uppercase font-semibold mb-2 block">Alias / notas (opcional)</label>
            <input value={alias} onChange={(e) => setAlias(e.target.value)} placeholder="Ej: BP, banco plano"
              className="w-full px-3 py-2.5 rounded-lg text-sm text-white placeholder-[#30363D] outline-none"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}
            />
          </div>

          {error && <p className="text-xs text-red-400">{error}</p>}

          <button onClick={handleSubmit} disabled={loading}
            className="w-full py-3 rounded-xl text-sm font-bold transition-all"
            style={{ background: "#C9FF00", color: "#0E1117", opacity: loading ? 0.6 : 1 }}
          >
            {loading ? "Guardando..." : modoEdicion ? "Guardar cambios" : "Añadir ejercicio"}
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
  onEditar,
  onVerHistorial,
}: {
  ejercicio: EjercicioExtendido;
  color: string;
  onArchivar: (id: number, archivar: boolean) => void;
  onEditar: (ej: EjercicioExtendido) => void;
  onVerHistorial: (ej: EjercicioExtendido) => void;
}) {
  // Mostrar historial si existe, sino objetivo
  const series = ejercicio.ultima_series ?? ejercicio.series_objetivo;
  const reps   = ejercicio.ultimas_reps  ?? ejercicio.reps_objetivo;
  const peso   = ejercicio.ultimo_peso   ?? ejercicio.peso_objetivo;
  const esFuente = ejercicio.ultima_series ? "historial" : "objetivo";

  return (
    <div
      className="rounded-xl p-4 transition-all cursor-pointer hover:scale-[1.01]"
      style={{
        background: "rgba(22,27,34,0.95)",
        border: ejercicio.subir_peso
          ? `1px solid rgba(34,197,94,0.35)`
          : `1px solid rgba(255,255,255,0.08)`,
        boxShadow: ejercicio.subir_peso ? "0 0 12px rgba(34,197,94,0.12)" : "none",
      }}
      onClick={() => onVerHistorial(ejercicio)}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3 gap-2">
        <div className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ background: color }} />
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-bold text-white">{ejercicio.nombre}</h3>
          {/* Badge subir peso */}
          {ejercicio.subir_peso && (
            <span
              className="inline-flex items-center gap-0.5 text-[9px] font-bold px-1.5 py-0.5 rounded-full mt-1"
              style={{ background: "rgba(34,197,94,0.15)", color: "#22C55E", border: "1px solid rgba(34,197,94,0.3)" }}
            >
              <ChevronUp className="h-2.5 w-2.5" />
              SUBE PESO
            </span>
          )}
        </div>
        <div className="flex gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
          <button onClick={() => onEditar(ejercicio)} className="text-[#8B949E] hover:text-white transition-colors p-0.5" title="Editar">
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button onClick={() => onArchivar(ejercicio.id, true)} className="text-[#8B949E] hover:text-white transition-colors p-0.5" title="Archivar">
            <Archive className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Stats */}
      {(series || reps || peso) ? (
        <div className="grid grid-cols-3 gap-2 mb-2">
          <div className="flex flex-col items-center">
            <span className="text-[10px] text-[#8B949E] uppercase mb-0.5">Series</span>
            <span className="text-base font-black" style={{ color }}>{series ?? "—"}</span>
          </div>
          <div className="flex flex-col items-center">
            <span className="text-[10px] text-[#8B949E] uppercase mb-0.5">Reps</span>
            <span className="text-base font-black" style={{ color }}>{reps ?? "—"}</span>
          </div>
          <div className="flex flex-col items-center">
            <span className="text-[10px] text-[#8B949E] uppercase mb-0.5">Peso</span>
            <span className="text-base font-black" style={{ color: ejercicio.ultimo_peso ? "#22C55E" : "#8B949E" }}>
              {peso ? `${peso}kg` : "—"}
            </span>
          </div>
        </div>
      ) : (
        <p className="text-xs text-[#30363D] mb-2">Sin datos aún · toca para ver historial</p>
      )}

      {/* Fuente */}
      {(series || reps || peso) && (
        <p className="text-[10px] text-[#30363D]">
          {esFuente === "historial" ? "Del historial · toca para ver más" : "→ objetivo"}
        </p>
      )}

      {/* Alias */}
      {ejercicio.alias && <p className="text-[10px] text-[#30363D] mt-1 truncate">{ejercicio.alias}</p>}
    </div>
  );
}

// ── Sección de grupo (solo activos) ───────────────────────────────────────────

function GrupoSection({
  grupo, activos, onArchivar, onEditar, onAddClick, onVerHistorial,
}: {
  grupo: typeof GRUPOS[0];
  activos: EjercicioExtendido[];
  onArchivar: (id: number, archivar: boolean) => void;
  onEditar: (ej: EjercicioExtendido) => void;
  onAddClick: () => void;
  onVerHistorial: (ej: EjercicioExtendido) => void;
}) {
  const [expandido, setExpandido] = useState(true);

  return (
    <div className="mb-6">
      <div className="flex items-center gap-3 mb-3">
        <button onClick={() => setExpandido(!expandido)} className="flex items-center gap-2 flex-1 text-left">
          {expandido
            ? <ChevronDown className="h-4 w-4" style={{ color: grupo.color }} />
            : <ChevronRight className="h-4 w-4" style={{ color: grupo.color }} />
          }
          <div className="w-2 h-2 rounded-full" style={{ background: grupo.color }} />
          <span className="text-sm font-bold uppercase tracking-wider" style={{ color: grupo.color }}>{grupo.label}</span>
          <span className="text-xs text-[#8B949E]">({activos.length})</span>
        </button>
        <button onClick={onAddClick}
          className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs transition-all hover:opacity-80"
          style={{ background: grupo.bg, border: `1px solid ${grupo.color}30`, color: grupo.color }}
        >
          <Plus className="h-3 w-3" /> Añadir
        </button>
      </div>

      {expandido && (
        activos.length === 0 ? (
          <div className="rounded-xl p-4 text-center mb-3"
            style={{ background: grupo.bg, border: `1px dashed ${grupo.color}40` }}>
            <p className="text-xs text-[#8B949E]">Sin ejercicios activos · {grupo.descripcion}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-3">
            {activos.map((ej) => (
              <EjercicioCard key={ej.id} ejercicio={ej} color={grupo.color}
                onArchivar={onArchivar} onEditar={onEditar} onVerHistorial={onVerHistorial} />
            ))}
          </div>
        )
      )}
    </div>
  );
}

// ── Sección Archivados ─────────────────────────────────────────────────────────

function SeccionArchivados({
  archivados, onDesarchivar, onEditar,
}: {
  archivados: EjercicioExtendido[];
  onDesarchivar: (id: number) => void;
  onEditar: (ej: EjercicioExtendido) => void;
}) {
  const [expandido, setExpandido] = useState(true);
  if (archivados.length === 0) return null;

  return (
    <div className="mt-8 pt-6" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
      <button onClick={() => setExpandido(!expandido)} className="flex items-center gap-2 mb-4 w-full text-left">
        {expandido ? <ChevronDown className="h-4 w-4 text-[#8B949E]" /> : <ChevronRight className="h-4 w-4 text-[#8B949E]" />}
        <Archive className="h-4 w-4 text-[#8B949E]" />
        <span className="text-sm font-bold text-[#8B949E] uppercase tracking-wider">Archivados</span>
        <span className="text-xs text-[#30363D]">({archivados.length})</span>
      </button>

      {expandido && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {archivados.map((ej) => {
            const color = COLOR_MAP[ej.grupo_muscular] ?? "#8B949E";
            return (
              <div key={ej.id} className="rounded-xl p-4 transition-all"
                style={{ background: "rgba(22,27,34,0.5)", border: "1px solid rgba(255,255,255,0.04)", opacity: 0.7 }}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <div className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-white truncate">{ej.nombre}</p>
                      <p className="text-xs" style={{ color }}>{ej.grupo_muscular}</p>
                    </div>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button onClick={() => onEditar(ej)} className="text-[#8B949E] hover:text-white transition-colors p-0.5" title="Editar">
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button onClick={() => onDesarchivar(ej.id)}
                      className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs transition-all hover:opacity-80"
                      style={{ background: "rgba(255,255,255,0.06)", color: "#8B949E", border: "1px solid rgba(255,255,255,0.08)" }}
                      title="Desarchivar"
                    >
                      <ArchiveRestore className="h-3.5 w-3.5" />
                      Restaurar
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Página principal ───────────────────────────────────────────────────────────

export function Ejercicios() {
  const { userId } = useUser();
  const [data, setData]           = useState<EjerciciosBiblioteca | null>(null);
  const [loading, setLoading]     = useState(false);
  const [modalGrupo, setModalGrupo] = useState<GrupoFuerza | null>(null);
  const [editando, setEditando]   = useState<EjercicioExtendido | null>(null);
  const [verHistorial, setVerHistorial] = useState<EjercicioExtendido | null>(null);

  const cargar = () => {
    if (!userId) return;
    setLoading(true);
    getEjercicios(userId)
      .then(setData)
      .catch(() => null)
      .finally(() => setLoading(false));
  };

  useEffect(() => { cargar(); }, [userId]);

  const handleArchivar = async (id: number, archivar: boolean) => {
    await archivarEjercicio(id, archivar);
    cargar();
  };

  const grupos = (data?.grupos as unknown as Record<GrupoFuerza, { activos: EjercicioExtendido[]; archivados: EjercicioExtendido[] }>) ?? {
    Push:   { activos: [], archivados: [] },
    Pull:   { activos: [], archivados: [] },
    Pierna: { activos: [], archivados: [] },
  };

  const todosArchivados = GRUPOS.flatMap((g) => grupos[g.key]?.archivados ?? []);

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white">🏋️ Ejercicios</h1>
          <p className="text-sm text-[#8B949E] mt-1">
            Los ejercicios activos de cada grupo aparecen en tu notificación diaria.
          </p>
        </div>

        {loading && <div className="text-center py-4 text-[#8B949E] text-sm">Actualizando...</div>}

        {GRUPOS.map((g) => (
          <GrupoSection
            key={g.key}
            grupo={g}
            activos={grupos[g.key]?.activos ?? []}
            onArchivar={handleArchivar}
            onEditar={setEditando}
            onAddClick={() => setModalGrupo(g.key)}
            onVerHistorial={setVerHistorial}
          />
        ))}

        <SeccionArchivados
          archivados={todosArchivados}
          onDesarchivar={(id) => handleArchivar(id, false)}
          onEditar={setEditando}
        />
      </main>

      {/* Modal crear */}
      {modalGrupo !== null && userId !== null && (
        <ModalEjercicio
          onClose={() => setModalGrupo(null)}
          onGuardado={cargar}
          usuarioId={userId}
          grupoInicial={modalGrupo}
        />
      )}

      {/* Modal editar */}
      {editando !== null && userId !== null && (
        <ModalEjercicio
          onClose={() => setEditando(null)}
          onGuardado={cargar}
          usuarioId={userId}
          grupoInicial={editando.grupo_muscular as GrupoFuerza}
          ejercicio={editando}
        />
      )}

      {/* Modal historial */}
      {verHistorial !== null && userId !== null && (
        <ModalHistorialEjercicio
          usuarioId={userId}
          ejercicioId={verHistorial.id}
          ejercicioNombre={verHistorial.nombre}
          color={COLOR_MAP[verHistorial.grupo_muscular] ?? "#C9FF00"}
          onClose={() => setVerHistorial(null)}
        />
      )}
    </div>
  );
}
