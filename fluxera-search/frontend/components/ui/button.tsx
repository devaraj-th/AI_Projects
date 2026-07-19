import * as React from "react";

import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline";
}

export function Button({ className, variant = "default", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-medium transition-all",
        variant === "default" && "bg-accent text-white hover:opacity-90",
        variant === "outline" && "border border-line bg-white text-fg hover:bg-blue-50 dark:bg-slate-900 dark:hover:bg-slate-800",
        className
      )}
      {...props}
    />
  );
}
