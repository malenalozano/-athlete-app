import { useLocation, useNavigate, Link } from "react-router";
import { useUser } from "../context/UserContext";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import {
  Home,
  CalendarDays,
  BookOpen,
  ChevronDown,
  Zap,
  User,
  RefreshCw,
} from "lucide-react";
import { useState } from "react";
import { sincronizarGarmin } from "../api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface SubTab {
  key: string;
  label: string;
  onlyMalena?: boolean;
}

interface NavItem {
  path: string;
  label: string;
  icon: React.ElementType;
  color: string;
  glowColor: string;
  bgActive: string;
  borderActive: string;
  subTabs?: SubTab[];
}

// ── Nav Config ────────────────────────────────────────────────────────────────

const NAV_ITEMS: NavItem[] = [
  {
    path: "/",
    label: "Inicio",
    icon: Home,
    color: "text-[#C9FF00]",
    glowColor: "rgba(201,255,0,0.35)",
    bgActive: "bg-[#C9FF00]/15",
    borderActive: "border-[#C9FF00]/70",
    subTabs: undefined,
  },
  {
    path: "/plan-semanal",
    label: "Plan Semanal",
    icon: BookOpen,
    color: "text-cyan-400",
    glowColor: "rgba(34,211,238,0.35)",
    bgActive: "bg-cyan-500/15",
    borderActive: "border-cyan-400/70",
    subTabs: [
      { key: "generar", label: "Generar Plan" },
      { key: "datos", label: "Datos" },
    ],
  },
  {
    path: "/diario",
    label: "Diario",
    icon: BookOpen,
    color: "text-purple-400",
    glowColor: "rgba(168,85,247,0.35)",
    bgActive: "bg-purple-500/15",
    borderActive: "border-purple-400/70",
    subTabs: [
      { key: "libre", label: "Entreno Libre" },
      { key: "ciclo", label: "Ciclo Menstrual", onlyMalena: true },
      { key: "ejercicios", label: "Ejercicios" },
      { key: "lesiones", label: "Lesiones" },
    ],
  },
  {
    path: "/calendario",
    label: "Calendario",
    icon: CalendarDays,
    color: "text-orange-400",
    glowColor: "rgba(251,146,60,0.35)",
    bgActive: "bg-orange-500/15",
    borderActive: "border-orange-400/70",
    subTabs: undefined,
  },
  {
    path: "/perfil",
    label: "Perfil",
    icon: User,
    color: "text-blue-400",
    glowColor: "rgba(96,165,250,0.35)",
    bgActive: "bg-blue-500/15",
    borderActive: "border-blue-400/70",
    subTabs: [
      { key: "sincronizacion", label: "Sincronización" },
      { key: "historial", label: "Historial" },
    ],
  },
];

// ── Color dot for section indicator ──────────────────────────────────────────

const DOT_COLORS: Record<string, string> = {
  "/": "bg-[#C9FF00]",
  "/plan-semanal": "bg-cyan-400",
  "/diario": "bg-purple-400",
  "/calendario": "bg-orange-400",
  "/perfil": "bg-blue-400",
};

// ── Component ─────────────────────────────────────────────────────────────────

export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { userId, userName, setUser } = useUser();
  const [syncing, setSyncing] = useState(false);
  const [syncSuccess, setSyncSuccess] = useState(false);

  const handleSync = async () => {
    if (!userId || syncing) return;
    setSyncing(true);
    setSyncSuccess(false);
    try {
      await sincronizarGarmin(userId);
      setSyncSuccess(true);
      setTimeout(() => setSyncSuccess(false), 1500);
    } catch {
      // silent — no romper UI si falla
    } finally {
      setSyncing(false);
    }
  };

  const activeNav = NAV_ITEMS.find((item) => {
    if (item.path === "/") return location.pathname === "/";
    return location.pathname.startsWith(item.path);
  });

  const activeSubTabs = (activeNav?.subTabs ?? []).filter(
    (t) => !t.onlyMalena || userId === 1
  );

  const getActiveSubTab = () => {
    const params = new URLSearchParams(location.search);
    return params.get("tab") || (activeSubTabs[0]?.key ?? "");
  };
  const activeSubTab = getActiveSubTab();

  const handleUserChange = (value: string) => {
    if (value === "malena") setUser(1, "Malena");
    else if (value === "dani") setUser(2, "Dani");
    window.location.href = "/";
  };

  const handleSubTabClick = (key: string) => {
    if (!activeNav) return;
    navigate(`${activeNav.path}?tab=${key}`);
  };

  const isActive = (path: string) => {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  };

  return (
    <header className="sticky top-0 z-50 w-full">
      {/* ── Glassmorphism backdrop ── */}
      <div
        className="relative"
        style={{
          background:
            "linear-gradient(180deg, rgba(14,17,23,0.98) 0%, rgba(22,27,34,0.95) 100%)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        {/* ── Main nav row ── */}
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16 gap-4">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 shrink-0 group">
              <div
                className="relative flex h-9 w-9 items-center justify-center rounded-xl overflow-hidden"
                style={{
                  background:
                    "linear-gradient(135deg, #C9FF00 0%, #00D4FF 50%, #A855F7 100%)",
                  boxShadow: "0 0 20px rgba(201,255,0,0.4)",
                }}
              >
                <Zap className="h-5 w-5 text-[#0E1117]" strokeWidth={2.5} />
              </div>
              <div className="hidden sm:block">
                <p
                  className="text-sm font-bold leading-none"
                  style={{
                    background:
                      "linear-gradient(90deg, #C9FF00, #00D4FF)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                  }}
                >
                  Proyecto Athlete
                </p>
                <p className="text-[10px] text-[#8B949E] leading-none mt-0.5">
                  {userName} · Maratón 2026
                </p>
              </div>
            </Link>

            {/* Main navigation */}
            <nav className="flex items-center gap-1 flex-1 justify-center">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.path);
                return (
                  <Link key={item.path} to={item.path}>
                    <button
                      className={`
                        relative flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold
                        transition-all duration-200 border
                        ${
                          active
                            ? `${item.bgActive} ${item.borderActive} ${item.color}`
                            : "text-[#8B949E] border-transparent hover:text-white hover:bg-white/5"
                        }
                      `}
                      style={
                        active
                          ? { boxShadow: `0 0 16px ${item.glowColor}` }
                          : {}
                      }
                    >
                      {/* Active dot */}
                      {active && (
                        <span
                          className={`absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full ${DOT_COLORS[item.path]} border-2 border-[#0E1117]`}
                        />
                      )}
                      <Icon className="h-3.5 w-3.5" />
                      <span className="hidden md:inline">{item.label}</span>
                      {item.subTabs && (
                        <ChevronDown
                          className={`h-3 w-3 transition-transform ${active ? "rotate-180" : ""}`}
                        />
                      )}
                    </button>
                  </Link>
                );
              })}
            </nav>

            {/* Sync button + User selector */}
            <div className="flex items-center gap-2 shrink-0">
              {/* Garmin sync button */}
              <button
                onClick={handleSync}
                disabled={syncing}
                title="Sincronizar Garmin"
                className="h-8 w-8 rounded-lg flex items-center justify-center transition-all"
                style={{
                  background: syncSuccess
                    ? "rgba(34,197,94,0.25)"
                    : "rgba(48,54,61,0.6)",
                  border: syncSuccess
                    ? "1px solid rgba(34,197,94,0.6)"
                    : "1px solid rgba(255,255,255,0.1)",
                }}
              >
                <RefreshCw
                  className={`h-3.5 w-3.5 transition-colors ${syncing ? "animate-spin" : ""}`}
                  style={{ color: syncSuccess ? "#22C55E" : "#8B949E" }}
                />
              </button>

              <Select
                value={userName?.toLowerCase()}
                onValueChange={handleUserChange}
              >
                <SelectTrigger
                  className="h-8 w-[100px] rounded-lg border text-xs text-white transition-all"
                  style={{
                    background: "rgba(48,54,61,0.6)",
                    borderColor: "rgba(255,255,255,0.1)",
                  }}
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent
                  className="border"
                  style={{
                    background: "#161B22",
                    borderColor: "rgba(255,255,255,0.1)",
                  }}
                >
                  <SelectItem
                    value="malena"
                    className="text-white hover:bg-[#30363D] focus:bg-[#30363D] text-xs"
                  >
                    Malena
                  </SelectItem>
                  <SelectItem
                    value="dani"
                    className="text-white hover:bg-[#30363D] focus:bg-[#30363D] text-xs"
                  >
                    Dani
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {/* ── Sub-tabs row (visible only when active section has sub-tabs) ── */}
        {activeSubTabs.length > 0 && (
          <div
            className="border-t"
            style={{ borderColor: "rgba(255,255,255,0.05)" }}
          >
            <div className="container mx-auto px-4">
              <div className="flex items-center gap-1 py-2">
                {activeSubTabs.map((tab) => {
                  const isSubActive = activeSubTab === tab.key;
                  const navColor = activeNav?.color ?? "text-white";
                  const navBg = activeNav?.bgActive ?? "bg-white/10";
                  const navBorder = activeNav?.borderActive ?? "border-white/30";
                  const navGlow = activeNav?.glowColor ?? "rgba(255,255,255,0.2)";

                  return (
                    <button
                      key={tab.key}
                      onClick={() => handleSubTabClick(tab.key)}
                      className={`
                        px-4 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 border
                        ${
                          isSubActive
                            ? `${navBg} ${navBorder} ${navColor}`
                            : "text-[#8B949E] border-transparent hover:text-white hover:bg-white/5"
                        }
                      `}
                      style={
                        isSubActive
                          ? { boxShadow: `0 0 12px ${navGlow}` }
                          : {}
                      }
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── Colorful bottom gradient line ── */}
        <div
          className="h-[2px] w-full"
          style={{
            background:
              "linear-gradient(90deg, #C9FF00 0%, #00D4FF 25%, #A855F7 50%, #F97316 75%, #3B82F6 100%)",
            opacity: 0.5,
          }}
        />
      </div>
    </header>
  );
}