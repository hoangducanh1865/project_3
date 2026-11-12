// Phục vụ luồng giám sát từ file tĩnh: 24 giờ luồng giả lập đã tính sẵn bằng HC-CLOSR (scripts/precompute_live.py),
// phát lại vòng theo giờ trong ngày. Không cần máy chủ chạy liên tục.
import { readFile } from "fs/promises";
import path from "path";
import { NextRequest, NextResponse } from "next/server";

type Inc = { id: string; opened: number; last: number; status: string; truth?: Record<string, number> };
type Point = { t: number; flows: number; alerts: number };
type Timeline = { minutes: number; series: Point[]; incidents: Inc[]; campaigns: { start: number; end?: number; detected?: number }[] };

let cache: { tl: Timeline; card: unknown } | null = null;
async function load() {
  if (!cache) {
    const dir = path.join(process.cwd(), "public", "live");
    cache = {
      tl: JSON.parse(await readFile(path.join(dir, "timeline.json"), "utf8")),
      card: JSON.parse(await readFile(path.join(dir, "card.json"), "utf8")),
    };
  }
  return cache;
}

function view(tl: Timeline) {
  const nowMin = Math.floor(Date.now() / 60000);
  const m = nowMin % tl.minutes;                 // phút hiện tại trong vòng 24 giờ
  const base = (nowMin - m) * 60;                 // giây tuyệt đối của phút 0 trong vòng này
  const series = tl.series.filter((p) => p.t / 60 <= m).slice(-60).map((p) => ({ ...p, t: p.t + base }));
  const all = tl.incidents.filter((i) => i.opened / 60 <= m).map((i) => {
    const last = Math.min(i.last, m * 60);
    return { ...i, opened: i.opened + base, last: last + base, status: m * 60 - last > 600 ? "closed" : "open", decision: null };
  }).reverse();
  const incidents = all.slice(0, 100);
  const day = all;
  const camps = tl.campaigns.filter((c) => c.end !== undefined && c.end <= m);
  const found = camps.filter((c) => c.detected !== undefined && c.detected <= m);
  const ttd = found.map((c) => c.detected! - c.start).sort((a, b) => a - b);
  const summary = {
    flows_60m: series.reduce((a, p) => a + p.flows, 0), alerts_60m: series.reduce((a, p) => a + p.alerts, 0),
    open: all.filter((i) => i.status === "open").length, incidents_24h: day.length,
    false_24h: day.filter((i) => !i.truth || Object.keys(i.truth).length === 0).length,
    campaigns_done: camps.length, campaigns_found: found.length, ttd_median: ttd.length ? ttd[Math.floor(ttd.length / 2)] : null,
  };
  return { updated: (nowMin) * 60, summary, series, incidents };
}

type Ctx = { params: Promise<{ path: string }> };

async function handle(req: NextRequest, ctx: Ctx) {
  const { path: p } = await ctx.params;
  const { tl, card } = await load();
  if (p === "live") return NextResponse.json(view(tl), { headers: { "cache-control": "no-store" } });
  if (p === "card") return NextResponse.json(card, { headers: { "cache-control": "public, s-maxage=300" } });
  if (p === "decide") return NextResponse.json({ ok: true });   // quyết định lưu ở trình duyệt
  return NextResponse.json({ detail: "chức năng phân tích file tạm ngừng: chưa có máy chủ suy luận" }, { status: 503 });
}

export const GET = handle;
export const POST = handle;
