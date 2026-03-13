import { RefreshCw, User } from "lucide-react";
import { Link, useLocation } from "react-router";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Button } from "./ui/button";
import { useUser } from "../context/UserContext";

export function Header() {
  const location = useLocation();
  const { userId, userName, setUser } = useUser();

  const isActive = (path: string) => location.pathname === path;

  // Navegación base
  const baseNavItems = [
    { path: "/", label: "Inicio" },
    { path: "/perfil", label: "Perfil" },
  ];

  // Ciclo Menstrual solo para Malena (userId === 1)
  const cycleItem = userId === 1
    ? [{ path: "/ciclo-menstrual", label: "Ciclo Menstrual" }]
    : [];

  const restNavItems = [
    { path: "/biblioteca", label: "Biblioteca Científica" },
    { path: "/diario-fuerza", label: "Diario de Fuerza" },
    { path: "/entrenador", label: "Entrenador Personal" },
    { path: "/calendario", label: "Calendario" },
  ];

  const navItems = [...baseNavItems, ...cycleItem, ...restNavItems];

  const handleUserChange = (value: string) => {
    if (value === "malena") {
      setUser(1, "Malena");
    } else if (value === "dani") {
      setUser(2, "Dani");
    }
    // Forzar recarga para actualizar la navegación
    window.location.href = "/";
  };

  return (
    <header className="bg-gradient-to-b from-[#0E1117] to-[#0A2E0A] py-6">
      <div className="container mx-auto px-6">
        {/* Contenedor principal tipo pill con efecto cristal */}
        <div
          className="relative rounded-[20px] border border-[#C9FF00]/40 bg-gradient-to-r from-[#0E1117] to-[#0A2E0A] p-4 shadow-2xl backdrop-blur-[10px]"
          style={{
            boxShadow:
              "0 0 30px rgba(201, 255, 0, 0.1), inset 0 1px 0 rgba(201, 255, 0, 0.1)",
          }}
        >
          <div className="flex items-center justify-between gap-6">
            {/* Logo Box - Extremo Izquierdo */}
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#C9FF00] shadow-lg shadow-[#C9FF00]/50">
                <User className="h-6 w-6 text-[#0E1117]" strokeWidth={2.5} />
              </div>
              <div>
                <h1 className="text-sm font-bold text-white leading-tight">
                  Proyecto Athlete
                </h1>
                <p className="text-xs text-[#8B949E]">Bienvenida, {userName}</p>
              </div>
            </div>

            {/* Navegación Central - Botones tipo píldora */}
            <nav className="flex items-center gap-1.5">
              {navItems.map((item) => (
                <Link key={item.path} to={item.path}>
                  <Button
                    variant="ghost"
                    size="sm"
                    className={`rounded-lg px-4 py-2 text-xs font-medium transition-all ${
                      isActive(item.path)
                        ? "bg-[#C9FF00]/20 text-white border border-[#C9FF00]/60 shadow-lg shadow-[#C9FF00]/20"
                        : "text-[#8B949E] hover:bg-[#161B22] hover:text-white border border-transparent"
                    }`}
                  >
                    {item.label}
                  </Button>
                </Link>
              ))}
            </nav>

            {/* Controles - Extremo Derecho */}
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                className="h-9 w-9 rounded-full border border-[#C9FF00]/40 bg-[#161B22]/50 text-[#C9FF00] hover:bg-[#C9FF00]/20 hover:border-[#C9FF00]/80 transition-all shadow-lg shadow-[#C9FF00]/10"
                onClick={() => window.location.reload()}
                title="Sincronizar Garmin"
              >
                <RefreshCw className="h-4 w-4" strokeWidth={2} />
              </Button>

              <Select
                value={userName?.toLowerCase()}
                onValueChange={handleUserChange}
              >
                <SelectTrigger className="h-9 w-[120px] rounded-lg border border-[#C9FF00]/40 bg-[#161B22]/50 text-xs text-white hover:border-[#C9FF00]/80 transition-all">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#161B22] border-[#C9FF00]/40 backdrop-blur-xl">
                  <SelectItem value="malena" className="text-white hover:bg-[#30363D] focus:bg-[#30363D]">
                    Malena
                  </SelectItem>
                  <SelectItem value="dani" className="text-white hover:bg-[#30363D] focus:bg-[#30363D]">
                    Dani
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}