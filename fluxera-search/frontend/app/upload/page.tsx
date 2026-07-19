"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { login, uploadDocument } from "@/lib/api";

export default function UploadPage() {
  const [token, setToken] = useState("");
  const [status, setStatus] = useState("Idle");

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
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">PDF, DOCX, TXT, and Markdown are supported.</p>
      <div className="mt-4 flex items-center gap-3">
        <input
          type="file"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            setStatus(`Uploading ${file.name} and generating embeddings...`);
            try {
              const tk = await ensureToken();
              const response = await uploadDocument(tk, file);
              setStatus(`Embedded: ${response.title}`);
            } catch (err) {
              const message = err instanceof Error ? err.message : "Upload failed";
              setStatus(message);
            }
          }}
          className="block w-full rounded-xl border border-line p-2"
        />
        <Button variant="outline" onClick={ensureToken}>Authenticate</Button>
      </div>
      <p className="mt-4 text-sm">Status: {status}</p>
    </Card>
  );
}
