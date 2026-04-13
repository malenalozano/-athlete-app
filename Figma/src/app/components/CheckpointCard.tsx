import { Card, CardContent } from "./ui/card";
import { Badge } from "./ui/badge";
import { CheckCircle2, Clock } from "lucide-react";

interface CheckpointCardProps {
  distance: string;
  time: string;
  description: string;
  status: "completed" | "pending";
  bestMark?: string;
}

const distanceColors: Record<string, { border: string; text: string; bg: string }> = {
  "5K": { border: "border-green-500/40", text: "text-green-500", bg: "bg-green-500/10" },
  "10K": { border: "border-cyan-500/40", text: "text-cyan-500", bg: "bg-cyan-500/10" },
  "Media Maratón": { border: "border-purple-500/40", text: "text-purple-500", bg: "bg-purple-500/10" },
  default: { border: "border-[#C9FF00]/40", text: "text-[#C9FF00]", bg: "bg-[#C9FF00]/10" },
};

export function CheckpointCard({ distance, time, description, status, bestMark }: CheckpointCardProps) {
  const colors = distanceColors[distance] || distanceColors.default;

  return (
    <Card className={`bg-[#161B22] border-2 ${colors.border} rounded-xl hover:scale-105 transition-all ${status === "completed" ? "shadow-lg" : ""}`}>
      <CardContent className="pt-6">
        <div className="space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <h3 className={`text-2xl font-bold ${colors.text} mb-1`}>{distance}</h3>
              <p className="text-lg text-white font-semibold">{time}</p>
            </div>
            <Badge
              className={`${
                status === "completed"
                  ? `${colors.bg} ${colors.text} border-2 ${colors.border}`
                  : "bg-orange-500/20 text-orange-400 border-2 border-orange-500/40"
              } font-semibold flex items-center gap-1`}
            >
              {status === "completed" ? (
                <>
                  <CheckCircle2 className="h-3 w-3" />
                  HECHO
                </>
              ) : (
                <>
                  <Clock className="h-3 w-3" />
                  PENDIENTE
                </>
              )}
            </Badge>
          </div>

          <p className="text-sm text-[#8B949E] leading-relaxed">
            {description}
          </p>

          {bestMark && (
            <div className={`pt-3 border-t ${colors.border}`}>
              <p className="text-xs text-[#8B949E] mb-1">Mejor Marca</p>
              <div className="flex items-baseline gap-2">
                <p className={`text-lg font-bold ${colors.text}`}>{bestMark}</p>
                {status === "completed" && (
                  <span className="text-xs text-green-500 font-semibold">✓ Objetivo logrado</span>
                )}
                {status === "pending" && (
                  <span className="text-xs text-orange-400 font-semibold">Por mejorar</span>
                )}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}