// Chuyển tiếp tới API trên Modal. Khoá API chỉ nằm ở phía server, trình duyệt không thấy.
import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 60; // máy chủ Modal có thể cần thời gian khởi động

const ALLOWED = new Set(["meta", "samples", "analyze"]);

type Ctx = { params: Promise<{ path: string }> };

async function forward(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  const { MODAL_API_URL, MODAL_API_KEY } = process.env;
  if (!ALLOWED.has(path)) return NextResponse.json({ detail: "không tìm thấy" }, { status: 404 });
  if (!MODAL_API_URL || !MODAL_API_KEY) {
    return NextResponse.json({ detail: "máy chủ chưa cấu hình MODAL_API_URL, MODAL_API_KEY" }, { status: 500 });
  }
  const res = await fetch(`${MODAL_API_URL}/${path}${req.nextUrl.search}`, {
    method: req.method,
    headers: { "content-type": "application/json", "x-api-key": MODAL_API_KEY },
    body: req.method === "POST" ? await req.text() : undefined,
    cache: "no-store",
  });
  return new NextResponse(res.body, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}

export const GET = forward;
export const POST = forward;
