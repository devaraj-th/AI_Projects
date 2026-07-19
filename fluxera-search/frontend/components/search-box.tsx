"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

export function SearchBox({ onSearch }: { onSearch: (value: string) => void }) {
  const [value, setValue] = useState("Explain WAFL Snapshot architecture");
  return (
    <div className="rounded-2xl border border-line bg-white p-3 shadow-soft dark:bg-slate-900">
      <div className="flex flex-col gap-3 md:flex-row">
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="h-12 flex-1 rounded-xl border border-line px-4 outline-none focus:border-accent"
          placeholder="Ask Fluxera Search anything about internal knowledge..."
        />
        <Button className="h-12" onClick={() => onSearch(value)}>
          Search
        </Button>
      </div>
    </div>
  );
}
