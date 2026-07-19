"use client";

import { useState } from "react";

import { SearchBox } from "@/components/search-box";
import { Card } from "@/components/ui/card";

export default function HomePage() {
  const [query, setQuery] = useState("");

  return (
    <div className="space-y-6 fade-up">
      <section className="text-center">
        <h2 className="text-4xl font-semibold tracking-tight">Enterprise answers with citations</h2>
        <p className="mx-auto mt-3 max-w-2xl text-slate-600 dark:text-slate-300">
          Search across PDFs, docs, markdown, websites, and repositories with traceable evidence.
        </p>
      </section>
      <SearchBox onSearch={setQuery} />
      <Card className="p-5">
        <p className="text-sm text-slate-600 dark:text-slate-300">Prompt preview</p>
        <p className="mt-2 text-lg">{query || "Try: Explain WAFL Snapshot architecture"}</p>
      </Card>
    </div>
  );
}
