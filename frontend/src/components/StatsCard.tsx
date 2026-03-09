import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface StatsCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  color?: "blue" | "emerald" | "violet" | "amber";
  sub?: string;
}

const colorMap = {
  blue:    { bg: "bg-blue-50",    icon: "bg-blue-600",    text: "text-blue-600" },
  emerald: { bg: "bg-emerald-50", icon: "bg-emerald-600", text: "text-emerald-600" },
  violet:  { bg: "bg-violet-50",  icon: "bg-violet-600",  text: "text-violet-600" },
  amber:   { bg: "bg-amber-50",   icon: "bg-amber-500",   text: "text-amber-600" },
};

export default function StatsCard({ label, value, icon: Icon, color = "blue", sub }: StatsCardProps) {
  const c = colorMap[color];
  return (
    <div className="card p-5 flex items-start gap-4">
      <div className={cn("w-11 h-11 rounded-xl flex items-center justify-center shrink-0", c.icon)}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-slate-500 font-medium">{label}</p>
        <p className="text-2xl font-bold text-slate-900 mt-0.5">{value}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}
