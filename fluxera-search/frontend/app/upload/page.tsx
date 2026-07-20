"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { login, uploadDocument } from "@/lib/api";

const ACCEPTED = ".pdf,.docx,.txt,.md,.py,.json,.csv,.rst,.yaml,.yml,.html,.htm";

export default function UploadPage() {
  const [token, setToken] = useState("");
  const [authStatus, setAuthStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const [status, setStatus] = useState("");
  const [uploadedDocs, setUploadedDocs] = useState<{ title: string; chunks: number }[]>([]);

  // Auto-authenticate on page load.
  useEffect(() => {
    handleAuthenticate();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleAuthenticate() {
    setAuthStatus("loading");
    try {
      const tk = await login("admin@fluxera.ai", "admin123");
      setToken(tk);
      setAuthStatus("ok");
    } catch (err) {
      setAuthStatus("error");
      setStatus(`✗ Authentication failed: ${err instanceof Error ? err.message : "unknown error"}. Check backend is running.`);
    }
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    // Re-authenticate if token is missing.
    let activeToken = token;
    if (!activeToken) {
      try {
        activeToken = await login("admin@fluxera.ai", "admin123");
        setToken(activeToken);
        setAuthStatus("ok");
      } catch {
        setStatus("✗ Not authenticated. Click Authenticate and try again.");
        return;
      }
    }

    setStatus(`Uploading "${file.name}"…`);
    try {
      const response = await uploadDocument(activeToken, file);
      // Upload returns immediately with status "processing". Poll until embedded.
      setStatus(`Processing "${response.title}" — embedding chunks…`);
      const docId = response.id;
      let attempts = 0;
      while (attempts < 60) {
        await new Promise((r) => setTimeout(r, 2000));
        attempts++;
        try {
          const poll = await fetch(`/api/documents/${docId}`, {
            headers: { Authorization: `Bearer ${activeToken}` },
          });
          if (poll.ok) {
            const doc = await poll.json();
            if (doc.status === "embedded") {
              const chunks = doc.chunk_count ?? "?";
              setStatus(`✓ Embedded "${doc.title}" — ${chunks} chunk${chunks === 1 ? "" : "s"} indexed`);
              setUploadedDocs((prev) => [{ title: doc.title, chunks: doc.chunk_count ?? 0 }, ...prev]);
              return;
            }
            if (doc.status === "error") {
              setStatus(`✗ Embedding failed for "${doc.title}". Check Ollama is running.`);
              return;
            }
          }
        } catch { /* keep polling */ }
      }
      setStatus(`✗ Timed out waiting for embedding. Check backend logs.`);
    } catch (err) {
      setStatus(`✗ ${err instanceof Error ? err.message : "Upload failed"}`);
    }
  }

  const authLabel =
    authStatus === "loading" ? "Authenticating…" :
    authStatus === "ok"      ? "✓ Authenticated" :
    authStatus === "error"   ? "✗ Auth failed — Retry" :
                               "Authenticate";

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
          disabled={authStatus === "loading"}
          onChange={handleFileChange}
          className="block w-full rounded-xl border border-line p-2 disabled:opacity-50"
        />
        <Button
          variant="outline"
          onClick={handleAuthenticate}
          disabled={authStatus === "loading"}
          className={authStatus === "ok" ? "border-green-500 text-green-600" : authStatus === "error" ? "border-red-500 text-red-600" : ""}
        >
          {authLabel}
        </Button>
      </div>
      {status && (
        <p className={`mt-4 text-sm ${status.startsWith("✗") ? "text-red-600" : status.startsWith("✓") ? "text-green-600" : "text-slate-600"}`}>
          {status}
        </p>
      )}
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
