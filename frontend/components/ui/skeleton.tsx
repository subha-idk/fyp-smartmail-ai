import * as React from "react";
import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-md bg-slate-700/40",
        "bg-[linear-gradient(90deg,rgba(30,41,59,0.5)_25%,rgba(51,65,85,0.6)_50%,rgba(30,41,59,0.5)_75%)]",
        "bg-[length:200%_100%] animate-shimmer",
        className
      )}
      {...props}
    />
  );
}

export { Skeleton };
