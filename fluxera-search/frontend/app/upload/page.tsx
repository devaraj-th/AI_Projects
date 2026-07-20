"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { login, uploadDocument } from "@/lib/api";

const ACCEPTED = ".pdf,.docx,.txt,.md,.py,.json,.csv,.rst,.yaml,.yml,.html,.htm";

export default function UploadPage() {
  const [token, setToken] = useState("");
  const [status, setStatus] = useState("Idle");
  const [uploadedDocs, setUploadedDocs] = useState<{ title: string; chunks: number }[]>([]);

  async function ensureToken() {
    if (!token) {
      const tk = await login("admin@fluxera.ai", "admin123");
      setToken(tk);
      return tk;
    }
    return token;
  }

  return (
    <Card className="p-5 fade-up">
      <h2 className="text-2xl font-semibold">Upload Knowledge</h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
        Supported: PDF, DOCX, TXT, MD, PY, JSON, CSV, RST, YAML, HTML
      </p>
      <div className="mt-4 flex items-center gap-3">
        <input
          type="file"
          accept={ACCEPTED}
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            setStatus(`Uploading "${file.name}" and generating embeddings…`);
            try {
              const tk = await ensureToken();
              const response = await uploadDocument(tk, file);
              const chunks = response.chunk_count ?? "?";
              setStatus(`✓ Embedded "${response.title}" — ${chunks} chunk${chunks === 1 ? "" : "s"} indexed`);
              setUploadedDocs((prev) => [{ title: response.title, chunks: response.chunk_count ?? 0 }, ...prev]);
            } catch (err) {
              const raw = err instanceof Error ? err.message : "Upload failed";
              // Surface structured backend error detail if present.
              const match = raw.match(/:\s*(.+)$/);
              setStatus(`✗ ${match ? match[1] : raw}`);
            }
          }}
          className="block w-full rounded-xl border border-line p-2"
        />
        <Button variant="outline" onClick={ensureToken}>Authenticate</Button>
      </div>
      <p className={`mt-4 text-sm ${status.startsWith("✗") ? "text-red-600" : status.startsWith("✓") ? "text-green-600" : "text-slate-600"}`}>
        Status: {status}
      </p>
      {uploadedDocs.length > 0 && (
        <div className="mt-5">
          <h3 className="text-sm font-medium mb-2">Uploaded this session</h3>
          <ul className="space-y-1">
            {uploadedDocs.map((d, i) => (
              <li key={i} className="text-xs text-slate-600 dark:text-slate-400">
                📄 {d.title} &mdash; {d.chunks} chunk{d.chunks === 1 ? "" : "s"}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
