import { Header } from "../components/Header";
import { useState, useEffect, useCallback } from "react";
import { ChevronDown, ChevronRight, Plus, Archive, ArchiveRestore, X, Pencil, ChevronUp, Trash2 } from "lucide-react";
import {
  DndContext, closestCenter, PointerSensor, TouchSensor,
  useSensor, useSensors, type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext, verticalListSortingStrategy, useSortable, arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useUser } from "../context/UserContext";
import {
  getEjercicios,
  archivarEjercicio,
  eliminarEjercicio,
  reordenarEjercicios,
  crearEjercicio,
  editarEjercicio,
  type EjerciciosBiblioteca,
  type EjercicioBiblioteca,
  type GrupoFuerza,
} from "../api";
import { ModalHistorialEjercicio } from "../components/ModalHistorialEjercicio";

// ── Tipos ──────────────────────────────────────────────────────────────────────

interface EjercicioExtendido extends EjercicioBiblioteca {
  series_objetivo?: number | null;
  reps_objetivo?: number | null;
  peso_objetivo?: number | null;
  ultima_series?: number | null;
  ultimas_reps?: number | null;
}

// ── Configuración de grupos ────────────────────────────────────────────────────

const GRUPOS: { key: GrupoFuerza; label: string; emoji: string; color: string; bg: string; descripcion: string }[] = [
  { key: "Push",   label: "PUSH",   emoji: "🟢", color: "#C9FF00", bg: "rgba(201,255,0,0.08)",   descripcion: "Press banca, Press militar, Fondos..." },
  { key: "Pull",   label: "PULL",   emoji: "🔵", color: "#00D4FF", bg: "rgba(0,212,255,0.08)",   descripcion: "Dominadas, Remo, Jalones..." },
  { key: "Pierna", label: "PIERNA", emoji: "🟣", color: "#A855F7", bg: "rgba(168,85,247,0.08)", descripcion: "Sentadilla, Peso muerto, Hip thrust..." },
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
  ejercicio,
}: {
  onClose: () => void;
  onGuardado: () => void;
  usuarioId: number;
  grupoInicial: GrupoFuerza;
  ejercicio?: EjercicioExtendido;
}) {
  const modoEdicion = !!ejercicio;

  const [nombre,    setNombre]    = useState(ejercicio?.nombre ?? "");
  const [grupo,     setGrupo]     = useState<GrupoFuerza>(ejercicio?.grupo_muscular as GrupoFuerza ?? grupoInicial);
  const [notas,     setNotas]     = useState(ejercicio?.alias ?? "");
  const [seriesObj, setSeriesObj] = useState(ejercicio?.series_objetivo?.toString() ?? "");
  const [repsObj,   setRepsObj]   = useState(ejercicio?.reps_objetivo?.toString() ?? "");
  const [pesoObj,   setPesoObj]   = useState(ejercicio?.peso_objetivo?.toString() ?? "");
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState("");

  const handleSubmit = async () => {
    if (!nombre.trim()) { setError("El nombre es obligatorio"); return; }
    setLoading(true);
    try {
      const payload = {
        nombre:          nombre.trim(),
        grupo_muscular:  grupo,
        alias:           notas.trim() || undefined,
        series_objetivo: seriesObj ? parseInt(seriesObj) : undefined,
        reps_objetivo:   repsObj   ? parseInt(repsObj)   : undefined,
        peso_objetivo:   pesoObj   ? parseFloat(pesoObj) : undefined,
      };

      if (modoEdicion && ejercicio) {
        await editarEjercicio(ejercicio.id, payload);
      } else {
        const res = await crearEjercicio({ usuario_id: usuarioId, ...payload });
        if (res.restaurado) {
          // Estaba archivado, el backend lo restauró automáticamente
          onGuardado();
          onClose();
          return;
        }
      }

      onGuardado();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "";
      if (msg.includes("409")) {
        setError("Ya existe un ejercicio activo con ese nombre");
      } else {
        setError("Error al guardar. Inténtalo de nuevo.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: "rgba(0,0,0,0.75)" }}>
      <div className="w-full max-w-md rounded-2xl p-6" style={{ background: "#161B22", border: "1px solid rgba(255,255,255,0.12)" }}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-white">
            {modoEdicion ? "✏️ Editar ejercicio" : "➕ Nuevo ejercicio"}
          </h2>
          <button onClick={onClose} className="text-[#8B949E] hover:text-white transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Grupo */}
          <div>
            <label className="text-xs text-[#8B949E] uppercase font-semibold mb-2 block">Grupo muscular</label>
            <div className="flex gap-2">
              {GRUPOS.map((g) => (
                <button key={g.key} onClick={() => setGrupo(g.key)}
                  className="flex-1 py-2.5 rounded-xl text-sm font-bold transition-all"
                  style={{
                    background: grupo === g.key ? g.bg : "rgba(255,255,255,0.04)",
                    border: `2px solid ${grupo === g.key ? g.color : "rgba(255,255,255,0.08)"}`,
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
              Objetivo <span className="normal-case font-normal">(opcional)</span>
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

          {/* Notas */}
          <div>
            <label className="text-xs text-[#8B949E] uppercase font-semibold mb-2 block">📝 Notas (opcional)</label>
            <textarea
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
              placeholder="Recordatorios, técnica, sensaciones... Ej: Agarre cerrado, bajar controlado"
              rows={3}
              className="w-full px-3 py-2.5 rounded-lg text-sm text-white placeholder-[#30363D] outline-none resize-none"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}
            />
          </div>

          {error && <p className="text-xs text-red-400 bg-red-500/10 px-3 py-2 rounded-lg">{error}</p>}

          <div className="flex gap-2 pt-1">
            <button onClick={onClose} className="flex-1 py-3 rounded-xl text-sm font-semibold text-[#8B949E] transition-all hover:text-white"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
              Cancelar
            </button>
            <button onClick={handleSubmit} disabled={loading}
              className="flex-1 py-3 rounded-xl text-sm font-bold transition-all"
              style={{ background: "#C9FF00", color: "#0E1117", opacity: loading ? 0.6 : 1 }}>
              {loading ? "Guardando..." : modoEdicion ? "Guardar cambios" : "Añadir"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Tarjeta de ejercicio (sortable con drag handle visible) ───────────────────

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
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: ejercicio.id });

  const series = ejercicio.ultima_series ?? ejercicio.series_objetivo;
  const reps   = ejercicio.ultimas_reps  ?? ejercicio.reps_objetivo;
  const peso   = ejercicio.ultimo_peso   ?? ejercicio.peso_objetivo;
  const delHistorial = !!ejercicio.ultima_series;

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.4 : 1,
        zIndex: isDragging ? 999 : "auto",
        background: "#161B22",
        border: ejercicio.subir_peso ? "1px solid rgba(34,197,94,0.4)" : "1px solid rgba(255,255,255,0.07)",
        boxShadow: isDragging ? "0 12px 32px rgba(0,0,0,0.6)" : ejercicio.subir_peso ? "0 0 10px rgba(34,197,94,0.1)" : "none",
      }}
      className="rounded-xl overflow-hidden"
    >
      {/* ═══ DRAG HANDLE — solo icono de grip ═══ */}
      <div
        {...attributes}
        {...listeners}
        className="flex items-center justify-center py-1.5 cursor-grab active:cursor-grabbing select-none"
        style={{
          background: `${color}12`,
          borderBottom: `1px solid ${color}20`,
          touchAction: "none",
        }}
      >
        {/* 6 puntos en 2 columnas (icono grip clásico) */}
        <div className="flex gap-[5px]">
          {[0, 1].map((col) => (
            <div key={col} className="flex flex-col gap-[3px]">
              {[0, 1, 2].map((row) => (
                <div key={row} className="w-[3px] h-[3px] rounded-full" style={{ background: color, opacity: 0.5 }} />
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Contenido */}
      <div className="p-3.5">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex-1 min-w-0 cursor-pointer" onClick={() => onVerHistorial(ejercicio)}>
            <div className="flex items-center gap-1.5 flex-wrap">
              <h3 className="text-sm font-bold text-white leading-tight">{ejercicio.nombre}</h3>
              {ejercicio.subir_peso && (
                <span className="inline-flex items-center gap-0.5 text-[9px] font-bold px-1.5 py-0.5 rounded-full shrink-0"
                  style={{ background: "rgba(34,197,94,0.15)", color: "#22C55E", border: "1px solid rgba(34,197,94,0.3)" }}>
                  <ChevronUp className="h-2.5 w-2.5" />↑ SUBE PESO
                </span>
              )}
            </div>
            {ejercicio.alias && (
              <p className="text-[10px] mt-0.5 leading-tight" style={{ color: "#6B7280" }}>📝 {ejercicio.alias}</p>
            )}
          </div>
          <div className="flex gap-0.5 shrink-0">
            <button onClick={() => onEditar(ejercicio)}
              className="p-1.5 rounded-lg transition-all hover:bg-white/10 text-[#8B949E] hover:text-white" title="Editar">
              <Pencil className="h-3.5 w-3.5" />
            </button>
            <button onClick={() => onArchivar(ejercicio.id, true)}
              className="p-1.5 rounded-lg transition-all hover:bg-white/10 text-[#8B949E] hover:text-[#F97316]" title="Archivar">
              <Archive className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Stats */}
        {(series || reps || peso) ? (
          <div className="flex gap-3 items-baseline cursor-pointer" onClick={() => onVerHistorial(ejercicio)}>
            {series && <div className="text-center">
              <span className="text-lg font-black" style={{ color }}>{series}</span>
              <span className="text-[9px] text-[#8B949E] block">series</span>
            </div>}
            {reps && <div className="text-center">
              <span className="text-lg font-black" style={{ color }}>{reps}</span>
              <span className="text-[9px] text-[#8B949E] block">reps</span>
            </div>}
            {peso && <div className="text-center">
              <span className="text-lg font-black" style={{ color: delHistorial ? "#22C55E" : "#8B949E" }}>{peso}kg</span>
              <span className="text-[9px] text-[#8B949E] block">{delHistorial ? "último" : "objetivo"}</span>
            </div>}
          </div>
        ) : (
          <p className="text-xs text-[#30363D] cursor-pointer" onClick={() => onVerHistorial(ejercicio)}>Sin datos · toca para ver</p>
        )}
      </div>
    </div>
  );
}

// ── Columna de grupo ──────────────────────────────────────────────────────────

function ColumnaGrupo({
  grupo, activos, onArchivar, onEditar, onAddClick, onVerHistorial, onReorder,
}: {
  grupo: typeof GRUPOS[0];
  activos: EjercicioExtendido[];
  onArchivar: (id: number, archivar: boolean) => void;
  onEditar: (ej: EjercicioExtendido) => void;
  onAddClick: () => void;
  onVerHistorial: (ej: EjercicioExtendido) => void;
  onReorder: (nuevos: EjercicioExtendido[]) => void;
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 6 } }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIdx = activos.findIndex((e) => e.id === active.id);
    const newIdx = activos.findIndex((e) => e.id === over.id);
    if (oldIdx !== -1 && newIdx !== -1) {
      onReorder(arrayMove(activos, oldIdx, newIdx));
    }
  };

  return (
    <div className="flex flex-col rounded-2xl overflow-hidden"
      style={{ background: "rgba(22,27,34,0.6)", border: `1px solid ${grupo.color}25` }}>
      {/* Cabecera */}
      <div className="px-4 py-3 flex items-center justify-between"
        style={{ background: grupo.bg, borderBottom: `1px solid ${grupo.color}30` }}>
        <div className="flex items-center gap-2">
          <span className="text-sm font-black tracking-wider uppercase" style={{ color: grupo.color }}>
            {grupo.label}
          </span>
          <span className="text-xs text-[#8B949E]">({activos.length})</span>
        </div>
        <button onClick={onAddClick}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold transition-all hover:brightness-110"
          style={{ background: grupo.color, color: "#0E1117" }}>
          <Plus className="h-3.5 w-3.5" /> Añadir
        </button>
      </div>

      {/* Lista con DnD — sin overflow para que el drag no sea capturado por el scroll */}
      <div className="flex-1 p-3">
        {activos.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <p className="text-xs text-[#30363D]">{grupo.descripcion}</p>
            <button onClick={onAddClick}
              className="mt-3 text-xs font-semibold flex items-center gap-1"
              style={{ color: grupo.color }}>
              <Plus className="h-3 w-3" /> Añadir el primero
            </button>
          </div>
        ) : (
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={activos.map((e) => e.id)} strategy={verticalListSortingStrategy}>
              <div className="space-y-2.5">
                {activos.map((ej) => (
                  <EjercicioCard
                    key={ej.id}
                    ejercicio={ej}
                    color={grupo.color}
                    onArchivar={onArchivar}
                    onEditar={onEditar}
                    onVerHistorial={onVerHistorial}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}
      </div>
    </div>
  );
}

// ── Sección Archivados ─────────────────────────────────────────────────────────

function SeccionArchivados({
  archivados, onDesarchivar, onEditar, onEliminar,
}: {
  archivados: EjercicioExtendido[];
  onDesarchivar: (id: number) => void;
  onEditar: (ej: EjercicioExtendido) => void;
  onEliminar: (id: number, nombre: string) => void;
}) {
  const [expandido, setExpandido] = useState(false);
  if (archivados.length === 0) return null;

  return (
    <div className="mt-6 rounded-2xl overflow-hidden"
      style={{ background: "rgba(22,27,34,0.4)", border: "1px solid rgba(255,255,255,0.05)" }}>
      <div className="flex items-center px-5 py-3 gap-3">
        <button onClick={() => setExpandido(!expandido)} className="flex items-center gap-2 flex-1 text-left">
          {expandido ? <ChevronDown className="h-4 w-4 text-[#F97316]" /> : <ChevronRight className="h-4 w-4 text-[#F97316]" />}
          <Archive className="h-4 w-4 text-[#F97316]" />
          <span className="text-sm font-bold text-[#F97316] uppercase tracking-wider">Archivados</span>
          <span className="ml-1 text-xs px-2 py-0.5 rounded-full font-bold"
            style={{ background: "rgba(249,115,22,0.15)", color: "#F97316", border: "1px solid rgba(249,115,22,0.3)" }}>
            {archivados.length}
          </span>
        </button>
        <button
          onClick={() => archivados.forEach((ej) => onDesarchivar(ej.id))}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-all hover:brightness-110 shrink-0"
          style={{ background: "rgba(201,255,0,0.12)", color: "#C9FF00", border: "1px solid rgba(201,255,0,0.25)" }}
        >
          <ArchiveRestore className="h-3.5 w-3.5" /> Restaurar todos
        </button>
      </div>

      {expandido && (
        <div className="px-4 pb-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {archivados.map((ej) => {
            const color = COLOR_MAP[ej.grupo_muscular] ?? "#8B949E";
            return (
              <div key={ej.id}
                className="rounded-xl px-4 py-3 flex items-center justify-between gap-3"
                style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", opacity: 0.75 }}>
                <div className="flex items-center gap-2.5 flex-1 min-w-0">
                  <div className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-white truncate">{ej.nombre}</p>
                    <p className="text-[11px]" style={{ color }}>{ej.grupo_muscular}</p>
                  </div>
                </div>
                <div className="flex gap-1.5 shrink-0">
                  <button
                    onClick={() => onEditar(ej)}
                    className="p-1.5 rounded-lg text-[#8B949E] hover:text-white hover:bg-white/10 transition-all"
                    title="Editar"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => onDesarchivar(ej.id)}
                    className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-semibold transition-all hover:brightness-110"
                    style={{ background: "rgba(201,255,0,0.1)", color: "#C9FF00", border: "1px solid rgba(201,255,0,0.2)" }}
                    title="Restaurar"
                  >
                    <ArchiveRestore className="h-3 w-3" />
                    Restaurar
                  </button>
                  <button
                    onClick={() => onEliminar(ej.id, ej.nombre)}
                    className="p-1.5 rounded-lg text-[#8B949E] hover:text-red-400 hover:bg-red-500/10 transition-all"
                    title="Eliminar permanentemente"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
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
  const [loading, setLoading]         = useState(false);
  const [errorCarga, setErrorCarga]   = useState(false);
  const [modalGrupo, setModalGrupo]   = useState<GrupoFuerza | null>(null);
  const [editando, setEditando]       = useState<EjercicioExtendido | null>(null);
  const [verHistorial, setVerHistorial] = useState<EjercicioExtendido | null>(null);
  const [grupos, setGrupos]           = useState<Record<GrupoFuerza, { activos: EjercicioExtendido[]; archivados: EjercicioExtendido[] }>>({
    Push:   { activos: [], archivados: [] },
    Pull:   { activos: [], archivados: [] },
    Pierna: { activos: [], archivados: [] },
  });

  const cargar = useCallback(() => {
    if (!userId) return;
    setLoading(true);
    setErrorCarga(false);
    getEjercicios(userId)
      .then((data) => {
        setGrupos(data.grupos as unknown as typeof grupos);
        setErrorCarga(false);
      })
      .catch(() => setErrorCarga(true))
      .finally(() => setLoading(false));
  }, [userId]);

  useEffect(() => { cargar(); }, [cargar]);

  const handleArchivar = async (id: number, archivar: boolean) => {
    await archivarEjercicio(id, archivar);
    cargar();
  };

  const handleEliminar = async (id: number, nombre: string) => {
    if (!window.confirm(`¿Eliminar "${nombre}" permanentemente? Se borrará también todo su historial. Esta acción no se puede deshacer.`)) return;
    await eliminarEjercicio(id);
    cargar();
  };

  const handleReorder = useCallback((grupo: GrupoFuerza, nuevos: EjercicioExtendido[]) => {
    // Actualizar estado local inmediatamente (optimista)
    setGrupos((prev) => ({ ...prev, [grupo]: { ...prev[grupo], activos: nuevos } }));
    // Persistir en backend sin bloquear ni crashear si falla
    if (userId) {
      reordenarEjercicios(userId, nuevos.map((e, i) => ({ id: e.id, orden: i }))).catch(() => {
        // Silencioso: el orden visual ya se actualizó, backend sincronizará en siguiente carga
      });
    }
  }, [userId]);

  const todosArchivados = GRUPOS.flatMap((g) => grupos[g.key]?.archivados ?? []);

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />
      <main className="container mx-auto px-4 py-6">

        {/* Título */}
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">🏋️ Ejercicios</h1>
            <p className="text-sm text-[#8B949E] mt-0.5">
              Arrastra la barra para reordenar · toca para ver historial
            </p>
          </div>
          {loading && <span className="text-xs text-[#8B949E]">Actualizando...</span>}
        </div>

        {/* Banner de error cuando el backend no responde */}
        {errorCarga && !loading && (
          <div
            className="rounded-xl px-4 py-3 flex items-center justify-between gap-3 mb-4"
            style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)" }}
          >
            <div className="flex items-center gap-2.5">
              <span className="text-base">⚠️</span>
              <p className="text-sm text-red-400">
                No se pudieron cargar los ejercicios. El servidor puede estar arrancando (hasta 60 seg en la primera carga).
              </p>
            </div>
            <button
              onClick={cargar}
              className="px-3 py-1.5 rounded-lg text-xs font-bold shrink-0 transition-all hover:brightness-110"
              style={{ background: "rgba(239,68,68,0.15)", color: "#F87171", border: "1px solid rgba(239,68,68,0.35)" }}
            >
              Reintentar
            </button>
          </div>
        )}

        {/* 3 columnas — una por grupo */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {GRUPOS.map((g) => (
            <ColumnaGrupo
              key={g.key}
              grupo={g}
              activos={grupos[g.key]?.activos ?? []}
              onArchivar={handleArchivar}
              onEditar={setEditando}
              onAddClick={() => setModalGrupo(g.key)}
              onVerHistorial={setVerHistorial}
              onReorder={(nuevos) => handleReorder(g.key, nuevos)}
            />
          ))}
        </div>

        {/* Archivados */}
        <SeccionArchivados
          archivados={todosArchivados}
          onDesarchivar={(id) => handleArchivar(id, false)}
          onEditar={setEditando}
          onEliminar={handleEliminar}
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
