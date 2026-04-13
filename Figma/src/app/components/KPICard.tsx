import { Card, CardContent } from "./ui/card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface KPICardProps {
  label: string;
  value: string | number;
  period?: string;
  delta?: number;
  color?: "green" | "blue" | "purple" | "orange" | "yellow";
  icon?: React.ReactNode;
}

const colorClasses = {
  green: {
    border: "border-l-green-500",
    shadow: "hover:shadow-green-500/20",
    text: "text-green-500",
    bg: "bg-green-500/10",
  },
  blue: {
    border: "border-l-blue-500",
    shadow: "hover:shadow-blue-500/20",
    text: "text-blue-500",
    bg: "bg-blue-500/10",
  },
  purple: {
    border: "border-l-purple-500",
    shadow: "hover:shadow-purple-500/20",
    text: "text-purple-500",
    bg: "bg-purple-500/10",
  },
  orange: {
    border: "border-l-orange-500",
    shadow: "hover:shadow-orange-500/20",
    text: "text-orange-500",
    bg: "bg-orange-500/10",
  },
  yellow: {
    border: "border-l-[#C9FF00]",
    shadow: "hover:shadow-[#C9FF00]/20",
    text: "text-[#C9FF00]",
    bg: "bg-[#C9FF00]/10",
  },
};

export function KPICard({ label, value, period = "7D", delta, color = "yellow", icon }: KPICardProps) {
  const colors = colorClasses[color];

  return (
    <Card className={`bg-[#161B22] border-l-4 ${colors.border} border-t-0 border-r-0 border-b-0 rounded-xl hover:shadow-lg ${colors.shadow} transition-all`}>
      <CardContent className="pt-6">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {icon && <div className={colors.text}>{icon}</div>}
              <p className="text-sm text-[#8B949E] font-semibold">{label}</p>
            </div>
            <span className="text-xs text-[#8B949E] bg-[#30363D] px-2 py-1 rounded">
              {period}
            </span>
          </div>
          <div className="flex items-end justify-between">
            <p className="text-3xl font-bold text-white">{value}</p>
            {delta !== undefined && (
              <div className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded ${colors.bg} ${colors.text}`}>
                {delta > 0 ? (
                  <TrendingUp className="h-3 w-3" />
                ) : delta < 0 ? (
                  <TrendingDown className="h-3 w-3" />
                ) : (
                  <Minus className="h-3 w-3" />
                )}
                <span>{delta > 0 ? "+" : ""}{delta}</span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}