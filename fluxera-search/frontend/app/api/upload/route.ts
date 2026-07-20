/**
 * Dedicated upload proxy route.
 * Next.js rewrites() cannot forward multipart/form-data bodies reliably (socket hang-up).
 * This Route Handler reads the raw body as ArrayBuffer and pipes it to the backend,
 * preserving the Content-Type boundary that multipart requires.
 */
import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";

export async function POST(req: NextRequest) {
  const auth = req.headers.get("authorization") ?? "";
  const contentType = req.headers.get("content-type") ?? "";

  try {
    const body = await req.arrayBuffer();

    const upstream = await fetch(`${BACKEND}/upload`, {
      method: "POST",
      headers: {
        authorization: auth,
        "content-type": contentType,
      },
      body,
    });

    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: { "content-type": "application/json" },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "unknown error";
    return NextResponse.json({ detail: `Upload proxy error: ${msg}` }, { status: 502 });
  }
}
