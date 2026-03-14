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
    <header className="relative bg-[#070B11] px-5 pb-8 pt-10">
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-r from-transparent via-[#0D8A10]/30 to-transparent" />
      <div className="mx-auto w-full max-w-[1880px]">
        <div
          className="relative rounded-[34px] border border-[#C9FF00]/45 bg-gradient-to-r from-[#0B121A] via-[#062015] to-[#06330E] px-6 py-5 backdrop-blur-md"
          style={{
            boxShadow:
              "0 0 36px rgba(27, 255, 0, 0.14), inset 0 1px 0 rgba(201, 255, 0, 0.16)",
          }}
        >
          <div className="flex items-center gap-6">
            <div className="flex shrink-0 items-center gap-4">
              <div className="flex h-[72px] w-[72px] items-center justify-center rounded-2xl bg-[#C9FF00] shadow-[0_8px_34px_rgba(201,255,0,0.45)]">
                <User className="h-8 w-8 text-[#0E1117]" strokeWidth={2.6} />
              </div>
              <div>
                <h1 className="text-[36px] font-extrabold leading-none text-white md:text-[38px]">
                  Proyecto Athlete
                </h1>
                <p className="mt-1 text-[29px] leading-none text-[#9DA6B2] md:text-[31px]">
                  Bienvenida, {userName}
                </p>
              </div>
            </div>

            <div className="flex min-w-0 flex-1 items-center justify-between gap-5">
              <nav className="no-scrollbar flex min-w-0 flex-1 items-center gap-2 overflow-x-auto pr-2">
                {navItems.map((item) => (
                  <Link key={item.path} to={item.path} className="shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      className={`h-12 rounded-2xl border px-6 text-[14px] font-semibold transition-all ${
                        isActive(item.path)
                          ? "border-[#B8F200] bg-gradient-to-b from-[#3E5A09]/85 to-[#304706]/90 text-white shadow-[0_0_26px_rgba(201,255,0,0.42)]"
                          : "border-transparent bg-transparent text-[#98A1AE] hover:border-[#B8F200]/45 hover:bg-[#162515]/60 hover:text-white"
                      }`}
                    >
                      {item.label}
                    </Button>
                  </Link>
                ))}
              </nav>

              <div className="flex shrink-0 items-center gap-4">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-12 w-12 rounded-full border border-[#B8F200]/70 bg-[#0E1B12]/70 text-[#C9FF00] shadow-[0_0_18px_rgba(201,255,0,0.2)] transition-all hover:border-[#C9FF00] hover:bg-[#1F3317]"
                  onClick={() => window.location.reload()}
                  title="Sincronizar Garmin"
                >
                  <RefreshCw className="h-[18px] w-[18px]" strokeWidth={2.1} />
                </Button>

                <Select
                  value={userName?.toLowerCase()}
                  onValueChange={handleUserChange}
                >
                  <SelectTrigger className="h-14 w-[190px] rounded-[20px] border-2 border-[#B8F200]/75 bg-[#10210F]/82 px-5 text-left text-[31px] font-semibold text-white shadow-[0_0_20px_rgba(201,255,0,0.2)] transition-all hover:border-[#C9FF00]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="border-[#C9FF00]/45 bg-[#161B22] backdrop-blur-xl">
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
      </div>
    </header>
  );
}