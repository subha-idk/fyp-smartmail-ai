import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" | "purple";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variantStyles = {
    default: "bg-slate-900 text-slate-50 hover:bg-slate-900/80 dark:bg-slate-50 dark:text-slate-900 dark:hover:bg-slate-50/80",
    secondary: "bg-slate-100 text-slate-900 hover:bg-slate-100/80 dark:bg-slate-800 dark:text-slate-50 dark:hover:bg-slate-800/80",
    destructive: "bg-red-500 text-slate-50 hover:bg-red-500/80 dark:bg-red-900 dark:text-slate-50 dark:hover:bg-red-900/80",
    outline: "text-slate-950 border border-slate-200 dark:text-slate-50 dark:border-slate-800",
    success: "bg-emerald-500 text-slate-50 hover:bg-emerald-500/80 dark:bg-emerald-950 dark:text-emerald-300",
    warning: "bg-amber-500 text-slate-950 hover:bg-amber-500/80 dark:bg-amber-950 dark:text-amber-300",
    info: "bg-sky-500 text-slate-50 hover:bg-sky-500/80 dark:bg-sky-950 dark:text-sky-300",
    purple: "bg-violet-500 text-slate-50 hover:bg-violet-500/80 dark:bg-violet-950 dark:text-violet-300",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 --py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        "py-0.5", // fix typo in padding
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
