import { useLocation } from "react-router";
import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { useUser } from "../context/UserContext";
import {
  ChevronDown,
  ChevronUp,
  Minus,
  Plus,
  Eye,
  EyeOff,
  HelpCircle,
  Watch,
  RefreshCw,
  CheckCircle2,
  Clock,
  Wifi,
  Heart,
  Zap,
  Moon,
  Activity,
  TrendingUp,
  BarChart3,
} from "lucide-react";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";
import { useState, useEffect } from "react";
import {
  getPerfil,
  actualizarPerfil,
  getActividades,
  getDiarioBiometrico,
  getGarminStats,
  sincronizarGarmin,
  guardarCredencialesGarmin,
  uploadGarminTokens,
  type PerfilUsuario,
  type ActividadGarmin,
  type EntradaBiometrica,
  type GarminStats,
} from "../api";

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmtPace(minPerKm: number | null): string {
  if (!minPerKm || minPerKm <= 0) return "—";
  const mins = Math.floor(minPerKm);
  const secs = Math.round((minPerKm - mins) * 60);
  return `${mins}:${String(secs).padStart(2, "0")} min/km`;
}

function fmtDate(iso: string): string {
  const d = new Date((iso || "").substring(0, 10) + "T12:00:00");
  const days = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
  const months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
  return `${days[d.getDay()]} ${d.getDate()} ${months[d.getMonth()]}`;
}

function fmtHours(h: number | null): string {
  if (!h) return "—";
  const hrs = Math.floor(h);
  const mins = Math.round((h - hrs) * 60);
  return hrs > 0 ? `${hrs}h ${mins}min` : `${mins}min`;
}

const DAY_SHORT = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

// ── Sincronización ─────────────────────────────────────────────────────────────

function Sincronizacion({ biometrico, stats, userId, perfil, onSyncComplete }: { biometrico: EntradaBiometrica[]; stats: GarminStats | null; userId: number | null; perfil: PerfilUsuario | null; onSyncComplete: () => void }) {
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const todayIso = new Date().toISOString().slice(0, 10);
  const yesterdayIso = (() => { const d = new Date(); d.setDate(d.getDate() - 1); return d.toISOString().slice(0, 10); })();
  const yesterdayEntry = biometrico.find(b => b.fecha === yesterdayIso) ?? null;
  const todayEntry = biometrico.find(b => b.fecha === todayIso) ?? null;
  const hasCredentials = !!perfil?.email_garmin;
  const hasData = hasCredentials && !!stats?.ultima_actividad;
  const lastSync = stats?.ultima_actividad
    ? `${stats.ultima_actividad.fecha} · ${stats.ultima_actividad.tipo}`
    : "Sin sincronizar";

  const garminMetrics = [
    { label: "HRV", value: yesterdayEntry?.hrv_ms != null ? String(Math.round(yesterdayEntry.hrv_ms)) : "—", unit: "ms", icon: Activity, color: "#C9FF00", bg: "rgba(201,255,0,0.1)", border: "rgba(201,255,0,0.25)" },
    { label: "Sueño", value: yesterdayEntry?.horas_totales != null ? fmtHours(yesterdayEntry.horas_totales) : "—", unit: "", icon: Moon, color: "#A855F7", bg: "rgba(168,85,247,0.1)", border: "rgba(168,85,247,0.25)" },
    { label: "FC Reposo", value: yesterdayEntry?.fc_reposo != null ? String(yesterdayEntry.fc_reposo) : "—", unit: "bpm", icon: Heart, color: "#F43F5E", bg: "rgba(244,63,94,0.1)", border: "rgba(244,63,94,0.25)" },
    { label: "Body Battery", value: (todayEntry ?? yesterdayEntry)?.body_battery != null ? String((todayEntry ?? yesterdayEntry)!.body_battery) : "—", unit: "/100", icon: Zap, color: "#00D4FF", bg: "rgba(0,212,255,0.1)", border: "rgba(0,212,255,0.25)" },
    { label: "Estrés", value: (todayEntry ?? yesterdayEntry)?.estres_medio != null ? String(Math.round((todayEntry ?? yesterdayEntry)!.estres_medio!)) : "—", unit: "/100", icon: Activity, color: "#F97316", bg: "rgba(249,115,22,0.1)", border: "rgba(249,115,22,0.25)" },
    { label: "Score Sueño", value: yesterdayEntry?.sleep_score != null ? String(yesterdayEntry.sleep_score) : "—", unit: "/100", icon: Moon, color: "#6366F1", bg: "rgba(99,102,241,0.1)", border: "rgba(99,102,241,0.25)" },
  ];

  const hrvData = biometrico.slice(0, 7).reverse().map(b => ({
    day: DAY_SHORT[new Date(b.fecha + "T12:00:00").getDay()],
    hrv: b.hrv_ms != null ? Math.round(b.hrv_ms) : 0,
    sleep: b.horas_totales != null ? Math.round(b.horas_totales * 10) / 10 : 0,
  }));

  const handleSync = async () => {
    if (!userId || syncing) return;
    setSyncing(true);
    setSyncMsg(null);
    try {
      const result = await sincronizarGarmin(userId);
      let msg = `Sincronizado: ${result.actividades_importadas} actividades, ${result.dias_biometrico} días biométricos, ${result.dias_sueno} días sueño.`;
      if (result.advertencias && result.advertencias.length > 0) {
        msg += ` ⚠️ ${result.advertencias.join(" | ")}`;
      }
      setSyncMsg(msg);
      onSyncComplete();
    } catch (e: unknown) {
      setSyncMsg(e instanceof Error ? e.message : "Error al sincronizar");
    } finally {
      setSyncing(false);
    }
  };

  // Upload tokens UI
  const [tokensText, setTokensText] = useState<string>("");
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);

  const handleFile = async (f?: File) => {
    if (!f) return;
    try {
      const txt = await f.text();
      setTokensText(txt);
      setUploadMsg("Archivo cargado, listo para subir.");
    } catch (e) {
      setUploadMsg("Error leyendo el archivo.");
    }
  };

  const handleUploadTokens = async () => {
    if (!userId) return setUploadMsg("Usuario no identificado");
    if (!tokensText) return setUploadMsg("Pega o carga el JSON de tokens antes de subir");
    setUploading(true);
    setUploadMsg(null);
    try {
      const res = await uploadGarminTokens(userId, tokensText);
      setUploadMsg(res.message || "Tokens subidos correctamente.");
      // Trigger a refresh of profile/stats outside
      onSyncComplete();
    } catch (e: unknown) {
      setUploadMsg(e instanceof Error ? e.message : "Error subiendo tokens");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Device card */}
      <div
        className="rounded-2xl p-8 relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, rgba(96,165,250,0.12), rgba(99,102,241,0.08))",
          border: "1px solid rgba(96,165,250,0.25)",
          boxShadow: "0 0 40px rgba(96,165,250,0.08)",
        }}
      >
        <div
          className="absolute -right-10 -top-10 w-60 h-60 rounded-full opacity-10 blur-3xl"
          style={{ background: "#3B82F6" }}
        />
        <div className="flex flex-col md:flex-row items-center gap-8 relative">
          <div
            className="h-28 w-28 rounded-2xl flex items-center justify-center shrink-0"
            style={{
              background: "linear-gradient(135deg, #1e3a5f, #0f172a)",
              border: "2px solid rgba(96,165,250,0.4)",
              boxShadow: "0 0 30px rgba(96,165,250,0.2), inset 0 1px 0 rgba(96,165,250,0.1)",
            }}
          >
            <Watch className="h-14 w-14 text-blue-400" />
          </div>

          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Badge className={hasData ? "bg-green-400/20 text-green-300 border-green-500/30 text-xs" : hasCredentials ? "bg-yellow-400/20 text-yellow-300 border-yellow-500/30 text-xs" : "bg-orange-400/20 text-orange-300 border-orange-500/30 text-xs"}>
                {hasData ? "● Sincronizado" : hasCredentials ? "○ Sin datos recientes" : "○ Sin configurar"}
              </Badge>
              <Badge className="bg-blue-400/20 text-blue-300 border-blue-500/30 text-xs">
                Garmin Connect
              </Badge>
            </div>
            <h2 className="text-2xl font-bold text-white mb-1">Tu dispositivo Garmin</h2>
            <p className="text-[#8B949E] text-sm mb-2">Última actividad: {lastSync}</p>
            {syncMsg && (
              <p className={`text-xs mb-3 px-3 py-2 rounded-lg ${syncMsg.includes("Error") || syncMsg.includes("error") || syncMsg.includes("incorrectas") ? "bg-red-500/10 text-red-400 border border-red-500/20" : "bg-green-500/10 text-green-400 border border-green-500/20"}`}>
                {syncMsg}
              </p>
            )}
            <div className="flex items-center gap-3">
              <button
                onClick={handleSync}
                disabled={syncing}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-[#0E1117] transition-all disabled:opacity-70"
                style={{
                  background: syncing
                    ? "rgba(96,165,250,0.5)"
                    : "linear-gradient(135deg, #3B82F6, #6366F1)",
                  boxShadow: "0 0 20px rgba(96,165,250,0.4)",
                }}
              >
                <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
                {syncing ? "Sincronizando..." : "Sincronizar ahora"}
              </button>
              <div className="flex items-center gap-1.5 text-xs font-semibold" style={{ color: hasData ? "#22C55E" : hasCredentials ? "#EAB308" : "#F97316" }}>
                <Wifi className="h-3.5 w-3.5" />
                {hasData ? "Datos disponibles" : hasCredentials ? "Sincroniza para importar datos" : "Configura credenciales abajo"}
              </div>
            </div>
            {/* Upload tokens (for cloud): paste JSON or upload file */}
            <div className="mt-4">
              <p className="text-xs text-[#8B949E] mb-2">Si ya ejecutaste el login localmente, sube aquí el archivo <span className="font-semibold">garmin_tokens.json</span> o pega su contenido:</p>
              <div className="flex gap-2 items-start">
                <input type="file" accept="application/json" onChange={e => handleFile(e.target.files?.[0])} className="text-sm text-[#8B949E]" />
                <textarea value={tokensText} onChange={e => setTokensText(e.target.value)} placeholder="Pega aquí el JSON de tokens" className="flex-1 bg-[#0E1117] p-2 rounded-md text-sm text-white" rows={4} />
              </div>
              <div className="mt-2 flex items-center gap-2">
                <button onClick={handleUploadTokens} disabled={uploading} className="px-4 py-2 rounded-xl text-sm font-semibold" style={{ background: "linear-gradient(135deg, #10B981, #059669)", color: "white" }}>
                  {uploading ? "Subiendo..." : "Subir tokens a la nube"}
                </button>
                {uploadMsg && <p className="text-xs text-[#8B949E]">{uploadMsg}</p>}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Última actividad */}
      <Card
        className="rounded-2xl"
        style={{
          background: "linear-gradient(135deg, rgba(0,212,255,0.1), rgba(22,27,34,1))",
          border: "1px solid rgba(0,212,255,0.25)",
        }}
      >
        <CardHeader>
          <CardTitle className="text-white text-base flex items-center gap-2">
            <Activity className="h-4 w-4 text-cyan-400" />
            Última actividad importada
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div
              className="h-16 w-16 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: "rgba(0,212,255,0.15)", border: "1px solid rgba(0,212,255,0.3)" }}
            >
              <Activity className="h-8 w-8 text-cyan-400" />
            </div>
            <div className="flex-1">
              <p className="text-base font-bold text-white mb-1">
                {stats?.ultima_actividad?.tipo || "Sin actividad"}
              </p>
              <div className="flex items-center gap-3 text-sm text-[#8B949E]">
                <span>{stats?.ultima_actividad?.fecha || "—"}</span>
                <Badge className="bg-cyan-400/15 text-cyan-300 border-cyan-500/30 text-xs">
                  {stats?.ultima_actividad?.tipo || "—"}
                </Badge>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-xs text-[#8B949E] mb-1">KM semana</p>
                <p className="text-lg font-bold text-white">{stats ? `${stats.km_semana} km` : "—"}</p>
              </div>
              <div>
                <p className="text-xs text-[#8B949E] mb-1">KM mes</p>
                <p className="text-lg font-bold text-white">{stats ? `${stats.km_mes} km` : "—"}</p>
              </div>
              <div>
                <p className="text-xs text-[#8B949E] mb-1">Actividades</p>
                <p className="text-lg font-bold text-cyan-400">{stats ? stats.total_actividades : "—"}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Metrics grid */}
      <div>
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Zap className="h-4 w-4 text-blue-400" />
          Métricas de hoy
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {garminMetrics.map((m) => (
            <div
              key={m.label}
              className="rounded-xl p-4 text-center transition-all hover:scale-105"
              style={{ background: m.bg, border: `1px solid ${m.border}` }}
            >
              <m.icon className="h-5 w-5 mx-auto mb-2" style={{ color: m.color }} />
              <p className="text-xs text-[#8B949E] mb-1">{m.label}</p>
              <p className="text-lg font-bold text-white">{m.value}</p>
              {m.unit && <p className="text-[10px]" style={{ color: m.color }}>{m.unit}</p>}
            </div>
          ))}
        </div>
      </div>

      {/* HRV chart */}
      <Card
        className="rounded-2xl"
        style={{ background: "#161B22", border: "1px solid rgba(201,255,0,0.15)" }}
      >
        <CardHeader>
          <CardTitle className="text-white text-base flex items-center gap-2">
            <Activity className="h-4 w-4 text-[#C9FF00]" />
            HRV últimos 7 días
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={hrvData}>
              <defs>
                <linearGradient id="hrvGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#C9FF00" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#C9FF00" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="day" stroke="#8B949E" fontSize={12} />
              <YAxis stroke="#8B949E" fontSize={12} />
              <Tooltip
                contentStyle={{ background: "#161B22", border: "1px solid rgba(201,255,0,0.3)", borderRadius: 8 }}
                labelStyle={{ color: "#fff" }}
              />
              <Area
                type="monotone"
                dataKey="hrv"
                name="HRV (ms)"
                stroke="#C9FF00"
                strokeWidth={2.5}
                fill="url(#hrvGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Sync status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: "Actividades sincronizadas", value: stats ? String(stats.total_actividades) : "—", icon: CheckCircle2, color: "#C9FF00" },
          { label: "KM esta semana", value: stats ? `${stats.km_semana} km` : "—", icon: Clock, color: "#00D4FF" },
          { label: "Datos biométricos", value: `${biometrico.length} días`, icon: Moon, color: "#A855F7" },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-xl p-4 flex items-center gap-3"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
          >
            <s.icon className="h-8 w-8 shrink-0" style={{ color: s.color }} />
            <div>
              <p className="text-xs text-[#8B949E]">{s.label}</p>
              <p className="text-lg font-bold text-white">{s.value}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Historial ──────────────────────────────────────────────────────────────────

function Historial({ actividades, biometrico, stats }: { actividades: ActividadGarmin[]; biometrico: EntradaBiometrica[]; stats: GarminStats | null }) {
  const historialActividades = actividades.slice(0, 10).map((a, i) => {
    const isRunning = a.tipo_deporte?.toLowerCase().includes("running") || a.tipo_deporte?.toLowerCase().includes("carrera");
    return {
      id: i + 1,
      fecha: fmtDate(a.fecha),
      tipo: isRunning ? "Carrera" : a.tipo_deporte || "Actividad",
      nombre: a.tipo_deporte || "Actividad",
      duracion: a.duracion_fmt || "--",
      distancia: a.km != null ? `${a.km.toFixed(1)} km` : "—",
      pace: fmtPace(a.ritmo_medio),
      fc_media: a.fc_media != null ? `${a.fc_media} bpm` : "—",
      color: isRunning ? "#00D4FF" : "#A855F7",
    };
  });

  const sleepData = biometrico.filter(b => b.horas_totales != null).slice(0, 10).map(b => ({
    fecha: b.fecha,
    horas_totales: fmtHours(b.horas_totales),
    score: b.sleep_score ?? 0,
    sleep_profundo_horas: fmtHours(b.sleep_profundo_horas),
    sleep_rem_horas: fmtHours(b.sleep_rem_horas),
  }));

  const biometricsData = biometrico.slice(0, 10).map(b => ({
    fecha: b.fecha,
    hrv_ms: b.hrv_ms != null ? Math.round(b.hrv_ms) : "—",
    fc_reposo: b.fc_reposo ?? "—",
    sleep_score: b.sleep_score ?? "—",
    estres_medio: b.estres_medio != null ? Math.round(b.estres_medio) : "—",
  }));

  return (
    <div className="space-y-8">
      <div
        className="rounded-2xl p-6"
        style={{
          background: "linear-gradient(135deg, rgba(96,165,250,0.12), rgba(99,102,241,0.08))",
          border: "1px solid rgba(96,165,250,0.25)",
        }}
      >
        <h2 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-blue-400" />
          Historial de Actividades
        </h2>
        <p className="text-[#8B949E] text-sm">Todas las actividades sincronizadas desde tu Garmin</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total actividades", value: stats ? String(stats.total_actividades) : "—", color: "#00D4FF" },
          { label: "KM este mes", value: stats ? `${stats.km_mes} km` : "—", color: "#C9FF00" },
          { label: "KM esta semana", value: stats ? `${stats.km_semana} km` : "—", color: "#A855F7" },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-xl p-4"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
          >
            <p className="text-xs text-[#8B949E] mb-2">{s.label}</p>
            <p className="text-xl font-bold text-white mb-1">{s.value}</p>
            <div className="flex items-center gap-1 text-xs" style={{ color: s.color }}>
              <TrendingUp className="h-3 w-3" />
              Garmin sync
            </div>
          </div>
        ))}
      </div>

      {/* Activity list */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Clock className="h-4 w-4 text-blue-400" />
          Recientes
        </h3>
        {historialActividades.length === 0 && (
          <div className="rounded-xl p-8 text-center" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <Activity className="h-8 w-8 mx-auto mb-2 text-[#8B949E]" />
            <p className="text-[#8B949E] text-sm">No hay actividades sincronizadas aún</p>
            <p className="text-[#8B949E] text-xs mt-1">Sincroniza tu Garmin para ver tu historial aquí</p>
          </div>
        )}
        {historialActividades.map((act) => (
          <Card
            key={act.id}
            className="rounded-2xl transition-all hover:scale-[1.01] cursor-pointer"
            style={{ background: "#161B22", border: `1px solid ${act.color}20` }}
          >
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div
                    className="h-12 w-12 rounded-xl flex items-center justify-center shrink-0"
                    style={{ background: `${act.color}15`, border: `1px solid ${act.color}30` }}
                  >
                    <Activity className="h-6 w-6" style={{ color: act.color }} />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-white">{act.tipo}</p>
                    <span className="text-xs text-[#8B949E]">{act.fecha}</span>
                  </div>
                </div>
                <div className="flex items-center gap-6 text-right">
                  <div>
                    <p className="text-xs text-[#8B949E]">Tiempo</p>
                    <p className="text-sm font-bold text-white">{act.duracion}</p>
                  </div>
                  {act.distancia !== "—" && (
                    <div>
                      <p className="text-xs text-[#8B949E]">Distancia</p>
                      <p className="text-sm font-bold text-white">{act.distancia}</p>
                    </div>
                  )}
                  {act.pace !== "—" && (
                    <div>
                      <p className="text-xs text-[#8B949E]">Pace</p>
                      <p className="text-sm font-bold" style={{ color: act.color }}>{act.pace}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs text-[#8B949E]">FC Media</p>
                    <p className="text-sm font-bold text-pink-400">{act.fc_media}</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabla Sueño */}
      <Card className="rounded-2xl" style={{ background: "#161B22", border: "1px solid rgba(168,85,247,0.2)" }}>
        <CardHeader>
          <CardTitle className="text-white text-base flex items-center gap-2">
            <Moon className="h-4 w-4 text-purple-400" />
            Sueño (Últimos 30 días)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {sleepData.length === 0 ? (
            <div className="py-8 text-center">
              <Moon className="h-8 w-8 mx-auto mb-2 text-[#8B949E]" />
              <p className="text-[#8B949E] text-sm">Sin datos de sueño disponibles</p>
            </div>
          ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#30363D]">
                  {["Fecha", "Horas", "Score", "Profundo", "REM"].map(h => (
                    <th key={h} className="text-left text-xs font-semibold text-[#8B949E] py-3 px-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sleepData.map((row, i) => (
                  <tr key={i} className="border-b border-[#30363D]/40 hover:bg-[#30363D]/20 transition-colors">
                    <td className="text-sm text-white py-3 px-3">{row.fecha}</td>
                    <td className="text-sm text-cyan-400 py-3 px-3">{row.horas_totales}</td>
                    <td className="text-sm py-3 px-3" style={{ color: row.score >= 90 ? "#C9FF00" : row.score >= 80 ? "#00D4FF" : "#F97316" }}>{row.score}</td>
                    <td className="text-sm text-white py-3 px-3">{row.sleep_profundo_horas}</td>
                    <td className="text-sm text-white py-3 px-3">{row.sleep_rem_horas}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}
        </CardContent>
      </Card>

      {/* Tabla Biométricos */}
      <Card className="rounded-2xl" style={{ background: "#161B22", border: "1px solid rgba(0,212,255,0.2)" }}>
        <CardHeader>
          <CardTitle className="text-white text-base flex items-center gap-2">
            <Activity className="h-4 w-4 text-cyan-400" />
            Biométricos
          </CardTitle>
        </CardHeader>
        <CardContent>
          {biometricsData.length === 0 ? (
            <div className="py-8 text-center">
              <Activity className="h-8 w-8 mx-auto mb-2 text-[#8B949E]" />
              <p className="text-[#8B949E] text-sm">Sin datos biométricos disponibles</p>
            </div>
          ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#30363D]">
                  {["Fecha", "HRV", "FC Reposo", "Sleep Score", "Estrés"].map(h => (
                    <th key={h} className="text-left text-xs font-semibold text-[#8B949E] py-3 px-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {biometricsData.map((row, i) => (
                  <tr key={i} className="border-b border-[#30363D]/40 hover:bg-[#30363D]/20 transition-colors">
                    <td className="text-sm text-white py-3 px-3">{row.fecha}</td>
                    <td className="text-sm text-cyan-400 py-3 px-3">{row.hrv_ms}</td>
                    <td className="text-sm text-white py-3 px-3">{row.fc_reposo}</td>
                    <td className="text-sm text-white py-3 px-3">{row.sleep_score}</td>
                    <td className="text-sm text-white py-3 px-3">{row.estres_medio}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Editar Perfil (desplegable) ────────────────────────────────────────────────

function EditarPerfil({ userId, perfil, onSaved, open, onOpenChange }: { userId: number | null; perfil: PerfilUsuario | null; onSaved?: () => void; open: boolean; onOpenChange: (v: boolean) => void }) {
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [savingGarmin, setSavingGarmin] = useState(false);
  const [garminMsg, setGarminMsg] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [activitiesToSync, setActivitiesToSync] = useState(7);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [emailGarmin, setEmailGarmin] = useState("");
  const [passwordGarmin, setPasswordGarmin] = useState("");
  const [showGarminForm, setShowGarminForm] = useState(!perfil?.email_garmin);
  const [form, setForm] = useState({
    nombre: "", edad: "", peso: "", objetivo: "", ritmo: "", genero: "",
    objetivo_tipo: "", fecha_objetivo: "", fcmax: "", nivel: "",
  });

  useEffect(() => {
    if (!perfil) return;
    setForm({
      nombre: perfil.nombre || "",
      edad: String(perfil.edad || ""),
      peso: String(perfil.peso || ""),
      objetivo: perfil.objetivo || "",
      ritmo: perfil.ritmo || "",
      genero: perfil.genero || "",
      objetivo_tipo: perfil.objetivo_tipo || "",
      fecha_objetivo: perfil.fecha_objetivo || "",
      fcmax: String(perfil.fcmax || ""),
      nivel: perfil.nivel || "",
    });
    if (perfil.email_garmin) {
      setEmailGarmin(perfil.email_garmin);
      setShowGarminForm(false);
    } else {
      setShowGarminForm(true);
    }
  }, [perfil]);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(prev => ({ ...prev, [k]: e.target.value }));

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      await actualizarPerfil(userId, {
        nombre: form.nombre || undefined,
        edad: form.edad ? Number(form.edad) : undefined,
        peso: form.peso ? Number(form.peso) : undefined,
        objetivo: form.objetivo || undefined,
        ritmo: form.ritmo || undefined,
        genero: form.genero || undefined,
        objetivo_tipo: form.objetivo_tipo || undefined,
        fecha_objetivo: form.fecha_objetivo || undefined,
        fcmax: form.fcmax ? Number(form.fcmax) : undefined,
        nivel: form.nivel || undefined,
      });
      setSaveMsg({ ok: true, text: "Perfil guardado correctamente." });
      onSaved?.();
    } catch (err: unknown) {
      setSaveMsg({ ok: false, text: err instanceof Error ? err.message : "Error al guardar" });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveGarmin = async () => {
    if (!userId || !emailGarmin || !passwordGarmin) return;
    setSavingGarmin(true);
    setGarminMsg(null);
    try {
      await guardarCredencialesGarmin(userId, emailGarmin, passwordGarmin);
      setPasswordGarmin("");
      setShowGarminForm(false);
      onSaved?.();
    } catch (e: unknown) {
      setGarminMsg(e instanceof Error ? e.message : "Error al guardar credenciales");
    } finally {
      setSavingGarmin(false);
    }
  };

  return (
    <Card className="bg-[#161B22] border border-[#C9FF00]/30 rounded-xl">
      <CardContent className="pt-6">
        <form className="space-y-6" onSubmit={handleSave}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Columna Izquierda */}
              <div className="space-y-4">
                <div>
                  <Label className="text-white mb-2 block">Nombre</Label>
                  <Input value={form.nombre} onChange={set("nombre")} className="bg-[#0E1117] border-[#C9FF00]/30 text-white" />
                </div>
                <div>
                  <Label className="text-white mb-2 block">Edad</Label>
                  <Input type="number" value={form.edad} onChange={set("edad")} placeholder="Ej: 30" className="bg-[#0E1117] border-[#C9FF00]/30 text-white" />
                </div>
                <div>
                  <Label className="text-white mb-2 block">Sexo</Label>
                  <select value={form.genero} onChange={set("genero")} className="w-full bg-[#0E1117] border border-[#C9FF00]/30 rounded-lg px-3 py-2 text-white">
                    <option value="">Seleccionar</option>
                    <option value="F">Femenino</option>
                    <option value="M">Masculino</option>
                  </select>
                </div>
                <div>
                  <Label className="text-white mb-2 block">Peso actual (kg)</Label>
                  <Input type="number" value={form.peso} onChange={set("peso")} placeholder="Ej: 60" className="bg-[#0E1117] border-[#C9FF00]/30 text-white" />
                </div>
                <div>
                  <Label className="text-white mb-2 block">Objetivo</Label>
                  <Input value={form.objetivo} onChange={set("objetivo")} placeholder="Ej: Maratón Sub 3:45" className="bg-[#0E1117] border-[#C9FF00]/30 text-white" />
                </div>
              </div>

              {/* Columna Derecha */}
              <div className="space-y-4">
                <div>
                  <Label className="text-white mb-2 block">Ritmo Objetivo</Label>
                  <Input value={form.ritmo} onChange={set("ritmo")} placeholder="Ej: 5:15-5:45 /km" className="bg-[#0E1117] border-[#C9FF00]/30 text-white" />
                </div>
                <div>
                  <Label className="text-white mb-2 block">Tipo de Objetivo</Label>
                  <Input value={form.objetivo_tipo} onChange={set("objetivo_tipo")} placeholder="Ej: Maratón" className="bg-[#0E1117] border-[#C9FF00]/30 text-white" />
                </div>
                <div>
                  <Label className="text-white mb-2 block">Fecha objetivo</Label>
                  <Input type="date" value={form.fecha_objetivo} onChange={set("fecha_objetivo")} className="bg-[#0E1117] border-[#C9FF00]/30 text-white" />
                </div>
                <div>
                  <Label className="text-white mb-2 block">FC Máxima</Label>
                  <Input type="number" value={form.fcmax} onChange={set("fcmax")} placeholder="Ej: 185" className="bg-[#0E1117] border-[#C9FF00]/30 text-white" />
                </div>
                <div>
                  <Label className="text-white mb-2 block">Nivel</Label>
                  <select value={form.nivel} onChange={set("nivel")} className="w-full bg-[#0E1117] border border-[#C9FF00]/30 rounded-lg px-3 py-2 text-white">
                    <option value="">Seleccionar</option>
                    <option value="principiante">Principiante</option>
                    <option value="intermedio">Intermedio</option>
                    <option value="avanzado">Avanzado</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Garmin Connect */}
            <div className="border-t border-[#C9FF00]/30 pt-6">
              <h4 className="text-white font-semibold mb-4">Sincronización Garmin</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="bg-[#0E1117] border border-[#C9FF00]/20 rounded-xl">
                  <CardContent className="pt-6 pb-6 space-y-4">
                    <h5 className="text-[#C9FF00] font-bold uppercase text-xs mb-4">GARMIN CONNECT</h5>

                    {!showGarminForm ? (
                      /* ── Estado: conectado ── */
                      <div className="flex flex-col items-center gap-4 py-2">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-green-500/15 flex items-center justify-center">
                            <CheckCircle2 className="h-5 w-5 text-green-400" />
                          </div>
                          <div>
                            <p className="text-white font-semibold text-sm">Garmin Conectado</p>
                            <p className="text-[#8B949E] text-xs">{emailGarmin}</p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setShowGarminForm(true); setPasswordGarmin(""); setGarminMsg(null); }}
                          className="text-xs text-[#8B949E] hover:text-white underline underline-offset-2 transition-colors"
                        >
                          Cambiar credenciales
                        </button>
                      </div>
                    ) : (
                      /* ── Estado: formulario ── */
                      <>
                        <div>
                          <Label className="text-white mb-2 block text-sm">Email Garmin</Label>
                          <Input
                            type="email"
                            placeholder="tu@email.com"
                            value={emailGarmin}
                            onChange={(e) => setEmailGarmin(e.target.value)}
                            className="bg-[#161B22] border-[#C9FF00]/30 text-white"
                          />
                        </div>
                        <div className="relative">
                          <Label className="text-white mb-2 block text-sm flex items-center gap-2">
                            Contraseña Garmin
                            <HelpCircle className="h-3 w-3 text-[#8B949E]" />
                          </Label>
                          <div className="relative">
                            <Input
                              type={showPassword ? "text" : "password"}
                              placeholder="••••••••"
                              value={passwordGarmin}
                              onChange={(e) => setPasswordGarmin(e.target.value)}
                              className="bg-[#161B22] border-[#C9FF00]/30 text-white pr-10"
                            />
                            <button
                              type="button"
                              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8B949E] hover:text-white transition-colors"
                              onClick={() => setShowPassword(!showPassword)}
                            >
                              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            </button>
                          </div>
                        </div>
                        {garminMsg && (
                          <p className={`text-xs px-3 py-2 rounded-lg ${garminMsg.includes("Error") || garminMsg.includes("error") ? "bg-red-500/10 text-red-400 border border-red-500/20" : "bg-green-500/10 text-green-400 border border-green-500/20"}`}>
                            {garminMsg}
                          </p>
                        )}
                        <Button
                          type="button"
                          disabled={savingGarmin || !emailGarmin || !passwordGarmin}
                          onClick={handleSaveGarmin}
                          className="w-full bg-[#161B22] border border-[#C9FF00]/40 text-white hover:bg-[#C9FF00]/10 disabled:opacity-50"
                        >
                          {savingGarmin ? "Guardando..." : "Conectar Garmin"}
                        </Button>
                      </>
                    )}
                  </CardContent>
                </Card>

                <Card className="bg-[#0E1117] border border-[#C9FF00]/20 rounded-xl">
                  <CardContent className="pt-6 pb-6 space-y-4">
                    <h5 className="text-[#C9FF00] font-bold uppercase text-xs mb-4">SINCRONIZACIÓN MANUAL</h5>
                    <p className="text-[#8B949E] text-sm">Elige cuántas actividades quieres sincronizar manualmente.</p>
                    <div>
                      <Label className="text-white mb-2 block text-sm">Número de actividades</Label>
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={() => setActivitiesToSync(Math.max(1, activitiesToSync - 1))}
                          className="p-2 bg-[#161B22] border border-[#C9FF00]/30 rounded-lg text-white hover:bg-[#C9FF00]/10 transition-colors"
                        >
                          <Minus className="h-4 w-4" />
                        </button>
                        <Input
                          type="number"
                          value={activitiesToSync}
                          onChange={(e) => setActivitiesToSync(Math.max(1, parseInt(e.target.value) || 1))}
                          className="bg-[#161B22] border-[#C9FF00]/30 text-white text-center flex-1"
                        />
                        <button
                          type="button"
                          onClick={() => setActivitiesToSync(activitiesToSync + 1)}
                          className="p-2 bg-[#161B22] border border-[#C9FF00]/30 rounded-lg text-white hover:bg-[#C9FF00]/10 transition-colors"
                        >
                          <Plus className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                    {syncMsg && (
                      <p className={`text-xs px-3 py-2 rounded-lg ${syncMsg.includes("Error") || syncMsg.includes("error") || syncMsg.includes("incorrectas") ? "bg-red-500/10 text-red-400 border border-red-500/20" : "bg-green-500/10 text-green-400 border border-green-500/20"}`}>
                        {syncMsg}
                      </p>
                    )}
                    <Button
                      type="button"
                      disabled={syncing}
                      onClick={async () => {
                        if (!userId || syncing) return;
                        setSyncing(true);
                        setSyncMsg(null);
                        try {
                          const result = await sincronizarGarmin(userId);
                          let msg = `Sincronizado: ${result.actividades_importadas} actividades, ${result.dias_biometrico} días biométricos, ${result.dias_sueno} días sueño.`;
                          if (result.advertencias && result.advertencias.length > 0) {
                            msg += ` ⚠️ ${result.advertencias.join(" | ")}`;
                          }
                          setSyncMsg(msg);
                          onSaved?.();
                        } catch (e: unknown) {
                          const msg = e instanceof Error ? e.message : "Error al sincronizar";
                          setSyncMsg(msg);
                          const isAuthError = msg.includes("401") || msg.includes("Unauthorized") || msg.includes("caducada") || msg.includes("contraseña") || msg.includes("credenciales");
                          if (isAuthError) setShowGarminForm(true);
                        } finally {
                          setSyncing(false);
                        }
                      }}
                      className="w-full bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] hover:from-[#a8d600] hover:to-[#C9FF00] font-bold disabled:opacity-60"
                    >
                      {syncing ? "Sincronizando..." : "Sincronizar actividades ahora"}
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </div>

            <div className="flex flex-col gap-3">
              {saveMsg && (
                <p className={`text-xs px-3 py-2 rounded-lg ${saveMsg.ok ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`}>
                  {saveMsg.text}
                </p>
              )}
              <div className="flex justify-end">
                <Button
                  type="submit"
                  disabled={saving}
                  className="bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] hover:from-[#a8d600] hover:to-[#C9FF00] font-bold px-8 py-3 disabled:opacity-60"
                >
                  {saving ? "Guardando..." : "Guardar cambios de perfil"}
                </Button>
              </div>
            </div>
        </form>
      </CardContent>
    </Card>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function Profile() {
  const { userId, userName } = useUser();
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const tab = params.get("tab") || "sincronizacion";

  const [perfil, setPerfil] = useState<PerfilUsuario | null>(null);
  const [actividades, setActividades] = useState<ActividadGarmin[]>([]);
  const [biometrico, setBiometrico] = useState<EntradaBiometrica[]>([]);
  const [stats, setStats] = useState<GarminStats | null>(null);
  const [editOpen, setEditOpen] = useState(false);

  useEffect(() => {
    if (!userId) return;
    getPerfil(userId).then(setPerfil).catch(() => null);
    getActividades(userId, 90).then(setActividades).catch(() => null);
    getDiarioBiometrico(userId).then(setBiometrico).catch(() => null);
    getGarminStats(userId).then(setStats).catch(() => null);
  }, [userId]);


  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8 space-y-8">
        {/* Profile Hero — click para editar */}
        <button
          type="button"
          onClick={() => setEditOpen(!editOpen)}
          className="w-full text-left rounded-2xl p-8 relative overflow-hidden transition-all hover:brightness-110"
          style={{
            background: "linear-gradient(135deg, rgba(201,255,0,0.1), rgba(22,27,34,1))",
            border: `1px solid ${editOpen ? "rgba(201,255,0,0.5)" : "rgba(201,255,0,0.2)"}`,
            boxShadow: editOpen ? "0 0 40px rgba(201,255,0,0.12)" : "0 0 40px rgba(201,255,0,0.05)",
          }}
        >
          <div
            className="absolute -right-10 -top-10 w-60 h-60 rounded-full opacity-10 blur-3xl"
            style={{ background: "#C9FF00" }}
          />
          <div className="flex items-center justify-between gap-6 relative">
            <div className="flex items-center gap-6">
              <div
                className="h-20 w-20 rounded-2xl flex items-center justify-center shrink-0 text-2xl font-bold"
                style={{
                  background: "linear-gradient(135deg, rgba(201,255,0,0.2), rgba(201,255,0,0.05))",
                  border: "2px solid rgba(201,255,0,0.4)",
                  color: "#C9FF00",
                }}
              >
                {(perfil?.nombre || userName || "U")[0].toUpperCase()}
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">{perfil?.nombre || userName}</h2>
                <p className="text-[#8B949E] text-sm mt-1">
                  {[perfil?.nivel, perfil?.objetivo_tipo].filter(Boolean).join(" · ")}
                </p>
                {perfil?.fecha_objetivo && (
                  <p className="text-xs mt-1" style={{ color: "#C9FF00" }}>
                    Objetivo: {perfil.fecha_objetivo}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 text-[#8B949E] shrink-0">
              <span className="text-xs hidden sm:block">{editOpen ? "Cerrar" : "Editar perfil"}</span>
              {editOpen ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
            </div>
          </div>
        </button>

        {/* Editar Perfil (solo visible cuando el hero está abierto) */}
        {editOpen && (
          <EditarPerfil
            key={userId ?? 0}
            userId={userId}
            perfil={perfil}
            open={editOpen}
            onOpenChange={setEditOpen}
            onSaved={() => {
              if (!userId) return;
              getPerfil(userId).then(setPerfil).catch(() => null);
            }}
          />
        )}

        {/* Garmin content según subtab */}
        {tab === "sincronizacion" && (
          <Sincronizacion
            biometrico={biometrico}
            stats={stats}
            userId={userId}
            perfil={perfil}
            onSyncComplete={() => {
              if (!userId) return;
              getActividades(userId, 90).then(setActividades).catch(() => null);
              getDiarioBiometrico(userId).then(setBiometrico).catch(() => null);
              getGarminStats(userId).then(setStats).catch(() => null);
            }}
          />
        )}
        {tab === "historial" && (
          <Historial actividades={actividades} biometrico={biometrico} stats={stats} />
        )}
      </main>
    </div>
  );
}
