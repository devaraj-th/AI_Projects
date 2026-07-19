"use client";

import { useState } from "react";

import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function SettingsPage() {
  const [temperature, setTemperature] = useState("0.2");
  const [topP, setTopP] = useState("0.9");
  const [maxTokens, setMaxTokens] = useState("700");
  const [systemPrompt, setSystemPrompt] = useState("Answer from enterprise knowledge and always cite sources.");

  return (
    <Card className="p-5 fade-up">
      <h2 className="text-2xl font-semibold">Model Preferences</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <div>
          <p className="mb-1 text-sm">Temperature</p>
          <Input value={temperature} onChange={(e) => setTemperature(e.target.value)} />
        </div>
        <div>
          <p className="mb-1 text-sm">Top P</p>
          <Input value={topP} onChange={(e) => setTopP(e.target.value)} />
        </div>
        <div>
          <p className="mb-1 text-sm">Max Tokens</p>
          <Input value={maxTokens} onChange={(e) => setMaxTokens(e.target.value)} />
        </div>
      </div>
      <div className="mt-4">
        <p className="mb-1 text-sm">System Prompt</p>
        <textarea
          className="h-28 w-full rounded-xl border border-line bg-white p-3 text-sm outline-none focus:border-accent dark:bg-slate-900"
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
        />
      </div>
    </Card>
  );
}
