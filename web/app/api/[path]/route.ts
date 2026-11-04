// Chuyển tiếp tới API trên Modal. Khoá API chỉ nằm ở phía server, trình duyệt không thấy.
import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 60; // máy chủ Modal có thể cần thời gian khởi động

// đường dẫn công khai -> biến chứa địa chỉ API và đường dẫn trên API
const ROUTES: Record<string, [string, string]> = {
  meta: ["MODAL_API_URL", "meta"], samples: ["MODAL_API_URL", "samples"], analyze: ["MODAL_API_URL", "analyze"],
  live: ["MODAL_LIVE_URL", "state"], decide: ["MODAL_LIVE_URL", "decide"],
};

type Ctx = { params: Promise<{ path: string }> };

async function forward(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  const route = ROUTES[path];
  if (!route) return NextResponse.json({ detail: "không tìm thấy" }, { status: 404 });
  const base = process.env[route[0]];
  const key = process.env.MODAL_API_KEY;
  if (!base || !key) {
    return NextResponse.json({ detail: `máy chủ chưa cấu hình ${route[0]}, MODAL_API_KEY` }, { status: 500 });
  }
  const res = await fetch(`${base}/${route[1]}${req.nextUrl.search}`, {
    method: req.method,
    headers: { "content-type": "application/json", "x-api-key": key },
    body: req.method === "POST" ? await req.text() : undefined,
    cache: "no-store",
  });
  const headers: Record<string, string> = { "content-type": res.headers.get("content-type") ?? "application/json" };
  if (path === "live") headers["cache-control"] = "public, s-maxage=10"; // nhiều người xem chỉ gọi Modal một lần
  return new NextResponse(res.body, { status: res.status, headers });
}

export const GET = forward;
export const POST = forward;
