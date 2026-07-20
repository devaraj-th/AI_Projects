/**
 * Dedicated auth/login proxy route.
 * Bypasses Next.js rewrites() for POST requests, which can socket-hang-up
 * on some hosting environments (Codespaces, etc.).
 */
import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.text();
    const upstream = await fetch(`${BACKEND}/auth/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    });
    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: { "content-type": "application/json" },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "unknown error";
    return NextResponse.json({ detail: `Auth proxy error: ${msg}` }, { status: 502 });
  }
}
