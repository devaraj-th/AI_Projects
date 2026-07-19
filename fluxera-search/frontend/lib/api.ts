import { Citation } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  return data.access_token;
}

export async function fetchDocuments(token: string) {
  const res = await fetch(`${API_BASE}/documents`, { headers: { Authorization: `Bearer ${token}` } });
  return res.json();
}

export async function fetchHistory(token: string) {
  const res = await fetch(`${API_BASE}/history`, { headers: { Authorization: `Bearer ${token}` } });
  return res.json();
}

export async function uploadDocument(token: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData
  });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function streamChat(
  token: string,
  payload: {
    question: string;
    conversation_id?: number;
    model: string;
    temperature: number;
    top_p: number;
    max_tokens: number;
    system_prompt?: string;
  },
  onToken: (token: string) => void,
  onDone: (meta: { conversation_id: number; citations: Citation[]; follow_ups: string[] }) => void
) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Chat request failed (${res.status}): ${body}`);
  }

  if (!res.body) throw new Error("No response stream");
  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let seenDone = false;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const event of events) {
      if (!event.startsWith("data:")) continue;
      const raw = event.replace("data:", "").trim();
      const parsed = JSON.parse(raw);
      if (parsed.type === "token") onToken(parsed.token);
      if (parsed.type === "error") throw new Error(parsed.error || "Chat stream failed.");
      if (parsed.type === "done") {
        seenDone = true;
        onDone(parsed);
      }
    }
  }

  if (!seenDone) {
    throw new Error("Chat stream ended unexpectedly. Verify selected model is available in Ollama.");
  }
}
