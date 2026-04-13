import { Card, CardContent } from "./ui/card";
import { Progress } from "./ui/progress";
import { CheckCircle2, Circle, Clock } from "lucide-react";

interface MacrocicloPhase {
  name: string;
  progress: number;
  status: "completed" | "in-progress" | "pending";
  color: "green" | "blue" | "cyan" | "purple" | "orange";
}

interface MacrocicloCardProps {
  title: string;
  phases: MacrocicloPhase[];
  globalProgress: number;
}

const phaseColors = {
  green: {
    border: "border-green-500",
    bg: "bg-green-500/10",
    text: "text-green-500",
    progress: "bg-green-500",
  },
  blue: {
    border: "border-blue-500",
    bg: "bg-blue-500/10",
    text: "text-blue-500",
    progress: "bg-blue-500",
  },
  cyan: {
    border: "border-cyan-500",
    bg: "bg-cyan-500/10",
    text: "text-cyan-500",
    progress: "bg-cyan-500",
  },
  purple: {
    border: "border-purple-500",
    bg: "bg-purple-500/10",
    text: "text-purple-500",
    progress: "bg-purple-500",
  },
  orange: {
    border: "border-orange-500",
    bg: "bg-orange-500/10",
    text: "text-orange-500",
    progress: "bg-orange-500",
  },
};

const statusIcons = {
  completed: CheckCircle2,
  "in-progress": Clock,
  pending: Circle,
};

export function MacrocicloCard({ title, phases, globalProgress }: MacrocicloCardProps) {
  return (
    <div className="space-y-6">
      {/* Título y Progreso Global */}
      <div className="bg-[#161B22] rounded-xl border border-[#30363D] p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-bold text-white">{title}</h3>
          <span className="text-sm font-bold text-[#C9FF00]">
            {globalProgress.toFixed(0)}% Completado
          </span>
        </div>
        <Progress value={globalProgress} className="h-2 bg-[#30363D]" />
      </div>

      {/* Fases */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {phases.map((phase, index) => {
          const colors = phaseColors[phase.color];
          const StatusIcon = statusIcons[phase.status];

          return (
            <Card
              key={index}
              className={`bg-[#161B22] border-2 ${colors.border} rounded-xl overflow-hidden hover:shadow-lg transition-all ${phase.status === "in-progress" ? "ring-2 ring-offset-2 ring-offset-[#0E1117]" : ""}`}
              style={phase.status === "in-progress" ? { ringColor: colors.border } : {}}
            >
              <CardContent className="pt-5 pb-4">
                <div className="space-y-3">
                  {/* Header con status */}
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className={`text-xs font-bold uppercase tracking-wider ${colors.text} mb-1`}>
                        {phase.name}
                      </p>
                      <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md ${colors.bg} mt-2`}>
                        <StatusIcon className={`h-3 w-3 ${colors.text}`} />
                        <span className={`text-xs font-semibold ${colors.text}`}>
                          {phase.status === "completed"
                            ? "Completada"
                            : phase.status === "in-progress"
                            ? "En Progreso"
                            : "Pendiente"}
                        </span>
                      </div>
                    </div>
                    <span className={`text-2xl font-bold ${colors.text}`}>
                      {phase.progress}%
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div className="relative w-full h-2 bg-[#30363D] rounded-full overflow-hidden">
                    <div
                      className={`h-full ${colors.progress} rounded-full transition-all duration-500`}
                      style={{ width: `${phase.progress}%` }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
