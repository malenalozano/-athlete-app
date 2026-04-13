import { User } from "lucide-react";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";

interface LoginProps {
  onSelectUser: (userId: number, userName: string) => void;
}

export function Login({ onSelectUser }: LoginProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0E1117] via-[#0A2E0A] to-[#0E1117] flex items-center justify-center">
      <div className="max-w-md w-full px-6">
        {/* Badge superior */}
        <div className="flex justify-center mb-6">
          <Badge className="bg-[#C9FF00]/20 text-[#C9FF00] border border-[#C9FF00]/40 px-4 py-2 rounded-full">
            <User className="h-4 w-4 mr-2 inline" />
            Athlete Dashboard
          </Badge>
        </div>

        {/* Contenedor principal */}
        <div 
          className="rounded-2xl border border-[#C9FF00]/40 bg-gradient-to-br from-[#161B22] to-[#0E1117] p-8 shadow-2xl backdrop-blur-xl"
          style={{
            boxShadow: '0 0 40px rgba(201, 255, 0, 0.15), inset 0 1px 0 rgba(201, 255, 0, 0.1)'
          }}
        >
          {/* Logo y título */}
          <div className="text-center mb-8">
            <div className="flex justify-center mb-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-[#C9FF00] shadow-lg shadow-[#C9FF00]/50">
                <User className="h-8 w-8 text-[#0E1117]" strokeWidth={2.5} />
              </div>
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">Proyecto Athlete</h1>
            <p className="text-[#8B949E]">Selecciona tu perfil de atleta</p>
          </div>

          {/* Botones de selección */}
          <div className="space-y-4">
            <Button
              onClick={() => onSelectUser(1, "Malena")}
              className="w-full h-14 bg-gradient-to-r from-[#C9FF00] to-[#a8d600] text-[#0E1117] hover:from-[#a8d600] hover:to-[#C9FF00] font-bold text-lg rounded-xl shadow-lg shadow-[#C9FF00]/30 transition-all"
            >
              Malena
            </Button>

            <Button
              onClick={() => onSelectUser(2, "Dani")}
              className="w-full h-14 bg-gradient-to-r from-[#30363D] to-[#161B22] text-white hover:from-[#3d4349] hover:to-[#30363D] font-bold text-lg rounded-xl border border-[#C9FF00]/30 shadow-lg transition-all"
            >
              Dani
            </Button>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-[#8B949E] mt-6">
          Sistema personalizado de entrenamiento y seguimiento
        </p>
      </div>
    </div>
  );
}
