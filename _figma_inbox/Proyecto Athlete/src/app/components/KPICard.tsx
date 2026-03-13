import { Card, CardContent } from "./ui/card";

interface KPICardProps {
  label: string;
  value: string | number;
  period?: string;
}

export function KPICard({ label, value, period = "7D" }: KPICardProps) {
  return (
    <Card className="bg-[#161B22] border-l-4 border-l-[#C9FF00] border-t-0 border-r-0 border-b-0 rounded-xl hover:shadow-lg hover:shadow-[#C9FF00]/20 transition-all">
      <CardContent className="pt-6">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm text-[#8B949E] font-semibold">{label}</p>
            <span className="text-xs text-[#8B949E] bg-[#30363D] px-2 py-1 rounded">
              {period}
            </span>
          </div>
          <p className="text-3xl font-bold text-white">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}