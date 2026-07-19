"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { login } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AdminPage() {
  const [stats, setStats] = useState<any>(null);

  async function load() {
    const token = await login("admin@fluxera.ai", "admin123");
    const res = await fetch(`${API_BASE}/admin/stats`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    setStats(await res.json());
  }

  return (
    <div className="space-y-4 fade-up">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Admin Dashboard</h2>
        <Button onClick={load}>Load Stats</Button>
      </div>
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        {["documents", "chunks", "users", "conversations"].map((key) => (
          <Card key={key} className="p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">{key}</p>
            <p className="mt-1 text-2xl font-semibold">{stats?.[key] ?? "-"}</p>
          </Card>
        ))}
      </div>
      <Card className="p-4">
        <p className="text-sm font-medium">Embedding status</p>
        <pre className="mt-2 overflow-auto rounded-xl bg-slate-900 p-3 text-xs text-slate-100">
          {JSON.stringify(stats?.embedding_status || {}, null, 2)}
        </pre>
      </Card>
    </div>
  );
}
