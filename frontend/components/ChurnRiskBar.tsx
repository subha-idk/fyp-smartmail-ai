import * as React from "react";

interface ChurnRiskBarProps {
  risk: number | null | undefined;
}

export default function ChurnRiskBar({ risk }: ChurnRiskBarProps) {
  if (risk === null || risk === undefined) {
    return <span className="text-xs text-slate-500">N/A</span>;
  }

  const percentage = Math.round(risk * 100);

  return (
    <div className="flex items-center gap-2 w-full max-w-[120px]">
      {/* Track: bg-slate-700 (dark glass style, h-1.5 = 6px slim bar) */}
      <div className="h-1.5 w-full bg-slate-700 rounded-full overflow-hidden">
        {/* Fill: bg-red-500 — class name preserved for Vitest assertions */}
        <div
          className="h-full bg-red-500 rounded-full transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs font-semibold text-slate-400 min-w-[30px] text-right">
        {percentage}%
      </span>
    </div>
  );
}
