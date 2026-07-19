"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const nav = [
  ["/", "Search"],
  ["/chat", "Chat"],
  ["/upload", "Upload"],
  ["/library", "Library"],
  ["/admin", "Admin"],
  ["/settings", "Settings"]
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="mx-auto min-h-screen max-w-6xl px-5 pb-10">
      <header className="sticky top-3 z-20 mt-3 rounded-2xl border border-line bg-white/85 p-3 shadow-soft backdrop-blur dark:bg-slate-950/80">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Image src="/logo.png" alt="Fluxera logo" width={36} height={36} className="h-9 w-9 rounded-md object-contain" />
            <h1 className="text-lg font-semibold tracking-tight">Fluxera Search</h1>
          </div>
          <nav className="flex flex-wrap gap-2 text-sm">
            {nav.map(([href, label]) => (
              <Link
                key={href}
                href={href}
                className={cn(
                  "rounded-full px-3 py-1.5 transition",
                  pathname === href ? "bg-accent text-white" : "text-slate-600 hover:bg-blue-50 dark:text-slate-300 dark:hover:bg-slate-800"
                )}
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mt-8">{children}</main>
    </div>
  );
}
