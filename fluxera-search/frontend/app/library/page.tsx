"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fetchDocuments, login } from "@/lib/api";

export default function LibraryPage() {
  const [docs, setDocs] = useState<any[]>([]);

  async function load() {
    const token = await login("admin@fluxera.ai", "admin123");
    const data = await fetchDocuments(token);
    setDocs(data);
  }

  return (
    <Card className="p-5 fade-up">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Knowledge Library</h2>
        <Button onClick={load}>Refresh</Button>
      </div>
      <div className="space-y-3">
        {docs.length === 0 && <p className="text-sm text-slate-500">No documents yet.</p>}
        {docs.map((d) => (
          <div key={d.id} className="rounded-xl border border-line p-3">
            <p className="font-medium">{d.title}</p>
            <p className="text-xs text-slate-500">{d.source_type} · {d.status}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}
