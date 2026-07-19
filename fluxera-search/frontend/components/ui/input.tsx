import * as React from "react";

import { cn } from "@/lib/utils";

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-xl border border-line bg-white px-4 py-2 text-sm outline-none transition focus:border-accent dark:bg-slate-900",
        className
      )}
      {...props}
    />
  );
}
