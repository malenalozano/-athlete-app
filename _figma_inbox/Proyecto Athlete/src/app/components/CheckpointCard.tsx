import { Card, CardContent } from "./ui/card";
import { Badge } from "./ui/badge";

interface CheckpointCardProps {
  distance: string;
  time: string;
  description: string;
  status: "completed" | "pending";
}

export function CheckpointCard({
  distance,
  time,
  description,
  status,
}: CheckpointCardProps) {
  return (
    <Card className="bg-[#161B22] border-l-4 border-l-[#C9FF00] border-t border-r border-b border-[#C9FF00]/30 rounded-xl hover:shadow-lg hover:shadow-[#C9FF00]/20 transition-all">
      <CardContent className="pt-6">
        <div className="space-y-3">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-bold text-lg text-white">
                {distance} en {time}
              </h3>
              <p className="text-sm text-[#8B949E] mt-1">{description}</p>
            </div>
            <Badge
              variant={status === "completed" ? "default" : "secondary"}
              className={
                status === "pending"
                  ? "bg-transparent border border-[#D29922] text-[#D29922] hover:bg-[#D29922]/10 rounded-full px-3"
                  : "bg-[#C9FF00] text-[#0E1117] hover:bg-[#C9FF00]/90 rounded-full px-3"
              }
            >
              {status === "completed" ? "Completado" : "Pendiente"}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}