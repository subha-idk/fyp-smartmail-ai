import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const variantStyles = {
      default:
        "bg-indigo-600 text-white hover:bg-indigo-500 focus-visible:ring-indigo-500",
      destructive:
        "bg-red-500 text-slate-50 hover:bg-red-500/90",
      outline:
        "border border-[rgba(99,102,241,0.3)] bg-transparent text-slate-300 hover:bg-[rgba(99,102,241,0.1)] hover:border-[rgba(99,102,241,0.5)] hover:text-slate-100",
      secondary:
        "bg-[rgba(30,41,59,0.8)] text-slate-300 hover:bg-[rgba(51,65,85,0.8)] hover:text-slate-100 border border-slate-700",
      ghost:
        "hover:bg-[rgba(99,102,241,0.1)] hover:text-slate-100 text-slate-400",
      link:
        "text-indigo-400 underline-offset-4 hover:underline hover:text-indigo-300",
    };

    const sizeStyles = {
      default: "h-10 px-4 py-2",
      sm: "h-8 rounded-md px-3 text-xs",
      lg: "h-11 rounded-md px-8",
      icon: "h-10 w-10",
    };

    return (
      <button
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium",
          "transition-all duration-200 cursor-pointer",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0f1e]",
          "disabled:pointer-events-none disabled:opacity-40",
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
