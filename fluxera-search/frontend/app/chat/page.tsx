"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { login, streamChat } from "@/lib/api";
import { Citation } from "@/lib/types";

const modelOptions = ["Fluxera AI", "Qwen", "Llama", "DeepSeek", "GPT", "Claude"];

export default function ChatPage() {
  const [token, setToken] = useState<string>("");
  const [question, setQuestion] = useState("Explain WAFL Snapshot architecture");
  const [model, setModel] = useState("Fluxera AI");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [conversationId, setConversationId] = useState<number | undefined>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const followUps = useMemo(
    () => ["Explain simply", "Give example", "Show diagram", "Compare alternatives"],
    []
  );

  async function handleLogin() {
    try {
      const tk = await login("admin@fluxera.ai", "admin123");
      setToken(tk);
      setError("");
    } catch {
      setError("Login failed. Check backend logs and credentials.");
    }
  }

  async function ask() {
    if (!token || !question.trim()) return;
    setLoading(true);
    setError("");
    setAnswer("");
    setCitations([]);
    try {
      await streamChat(
        token,
        {
          question,
          model,
          conversation_id: conversationId,
          temperature: 0.2,
          top_p: 0.9,
          max_tokens: 700
        },
        (tk) => setAnswer((prev) => prev + tk),
        (meta) => {
          setConversationId(meta.conversation_id);
          setCitations(meta.citations);
        }
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr] fade-up">
      <Card className="p-5">
        <div className="mb-4 flex items-center gap-3">
          <Button variant="outline" onClick={handleLogin}>
            {token ? "Authenticated" : "Quick Login"}
          </Button>
          <select
            className="rounded-xl border border-line bg-white px-3 py-2 text-sm dark:bg-slate-900"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          >
            {modelOptions.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-3">
          <Input value={question} onChange={(e) => setQuestion(e.target.value)} />
          <Button onClick={ask} disabled={loading || !token}>
            {loading ? "Generating..." : "Ask Fluxera"}
          </Button>
        </div>

        <div className="mt-5 rounded-xl border border-line bg-blue-50/50 p-4 dark:bg-slate-800/50">
          <h3 className="font-medium">Answer</h3>
          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
          <div className="mt-2 whitespace-pre-wrap text-sm leading-7">{answer || "Response will stream here..."}</div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {followUps.map((f) => (
            <button
              key={f}
              onClick={() => setQuestion(f + " for: " + question)}
              className="rounded-full border border-line px-3 py-1 text-xs hover:bg-blue-50 dark:hover:bg-slate-800"
            >
              {f}
            </button>
          ))}
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="text-lg font-medium">Citations</h3>
        <div className="mt-3 space-y-3 text-sm">
          {citations.length === 0 && <p className="text-slate-500">No citations yet.</p>}
          {citations.map((c) => (
            <a
              href={c.source_uri || "#"}
              key={c.id}
              className="block rounded-xl border border-line p-3 hover:border-accent"
            >
              <p className="font-medium">[{c.id}] {c.title}</p>
              <p className="text-xs text-slate-500">Chunk {c.chunk_index} · Score {c.score.toFixed(3)}</p>
              <p className="mt-1 line-clamp-4 text-xs">{c.excerpt}</p>
            </a>
          ))}
        </div>
      </Card>
    </div>
  );
}
