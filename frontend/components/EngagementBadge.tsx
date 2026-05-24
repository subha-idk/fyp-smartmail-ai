import * as React from "react";

interface EngagementBadgeProps {
  score: number | null | undefined;
}

export default function EngagementBadge({ score }: EngagementBadgeProps) {
  if (score === null || score === undefined) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-700/50 text-slate-400 border border-slate-600/50">
        <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
        N/A
      </span>
    );
  }

  // These specific class names are required by vitest tests — do NOT change them
  let dotColorClass: string;
  let bgClass: string;
  let textClass: string;
  let label: string;

  if (score >= 70) {
    dotColorClass = "bg-emerald-500"; // test checks this
    bgClass = "bg-emerald-500/10 border-emerald-500/30";
    textClass = "text-emerald-400";
    label = "High";
  } else if (score >= 40) {
    dotColorClass = "bg-amber-500"; // test checks this
    bgClass = "bg-amber-500/10 border-amber-500/30";
    textClass = "text-amber-400";
    label = "Medium";
  } else {
    dotColorClass = "bg-red-500"; // test checks this
    bgClass = "bg-red-500/10 border-red-500/30";
    textClass = "text-red-400";
    label = "Low";
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${bgClass} ${textClass}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dotColorClass}`} />
      {score} ({label})
    </span>
  );
}
