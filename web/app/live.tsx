"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { APPROVAL, TACTIC, TIER } from "./labels";

type Incident = {
  id: string; src: string; dst: string; opened: number; last: number; flows: number; alerts: number;
  status: "open" | "closed"; truth: Record<string, number>; campaign: number | null; family: string;
  tier: number; tactic: string; L: number; I: number; R: number; level: string; action: string; reversible: boolean;
  mode: string; d3fend_now: string[]; d3fend_later: string[]; decision: Decision | null;
};
type Decision = "approved" | "rejected";
type Point = { t: number; flows: number; alerts: number };
type Summary = {
  flows_60m: number; alerts_60m: number; open: number; incidents_24h: number; false_24h: number;
  campaigns_done: number; campaigns_found: number; ttd_median: number | null;
};
type State = { updated: number | null; summary: Summary | null; series: Point[]; incidents: Incident[] };
type Filter = "open" | "pending" | "all";

const POLL_MS = 15000;
const SLOTS = 60;
const STALE_S = 180;

const clock = (t: number) => new Date(t * 1000).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
const short = (t: string) => (TACTIC[t] ?? t).split(" (")[0];

function AlertChart({ points }: { points: Point[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 720, H = 120, slot = W / SLOTS, offset = SLOTS - points.length;   // phút mới nhất luôn ở bên phải
  const top = Math.max(10, ...points.map((p) => p.alerts));
  const shown = hover === null ? null : points[hover];
  return (
    <figure className="chart">
      <figcaption>
        Cảnh báo mỗi phút, 60 phút gần nhất
        <span>{shown ? ` · ${clock(shown.t)}: ${shown.alerts} cảnh báo trên ${shown.flows} flow` : ` · cao nhất ${top}`}</span>
      </figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label="Số cảnh báo mỗi phút"
        onMouseLeave={() => setHover(null)}>
        <line x1="0" y1={H - 0.5} x2={W} y2={H - 0.5} className="axis" />
        {points.map((p, i) => {
          const h = Math.max(p.alerts ? 2 : 0, (p.alerts / top) * (H - 4));
          const w = Math.max(slot - 2, 1);
          return (
            <g key={p.t} onMouseEnter={() => setHover(i)}>
              <rect x={(i + offset) * slot} y="0" width={slot} height={H} fill="transparent" />
              <rect x={(i + offset) * slot} y={H - h - 1} width={w} height={h} rx="2" className={hover === i ? "bar on" : "bar"} />
            </g>
          );
        })}
      </svg>
      <div className="ticks"><span>60 phút trước</span><span>Hiện tại</span></div>
    </figure>
  );
}

export default function Live() {
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<Filter>("open");
  const [selected, setSelected] = useState<string | null>(null);
  const [local, setLocal] = useState<Record<string, Decision | null>>({});
  const [banner, setBanner] = useState<Incident | null>(null);
  const [permission, setPermission] = useState("unsupported");
  const seen = useRef<Set<string> | null>(null);

  const poll = useCallback(async () => {
    try {
      const res = await fetch("/api/live");
      if (!res.ok) throw new Error(`Máy chủ trả lỗi ${res.status}.`);
      const data: State = await res.json();
      setState(data); setError("");
      if (seen.current === null) {
        seen.current = new Set(data.incidents.map((i) => i.id));     // sự cố cũ không báo lại
        return;
      }
      const fresh = data.incidents.filter((i) => !seen.current!.has(i.id));
      fresh.forEach((i) => seen.current!.add(i.id));
      if (fresh.length) {
        const worst = fresh.reduce((a, b) => (b.R > a.R ? b : a));
        setBanner(worst);
        if ("Notification" in window && Notification.permission === "granted") {
          new Notification(`Phát hiện xâm nhập, mức ${worst.level}`, { body: `${worst.src} → ${worst.dst}: ${short(worst.tactic)}` });
        }
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    if ("Notification" in window) setPermission(Notification.permission);
    poll();
    const id = setInterval(poll, POLL_MS);
    return () => clearInterval(id);
  }, [poll]);

  const decisionOf = (i: Incident) => (i.id in local ? local[i.id] : i.decision);
  const isPending = (i: Incident) => i.mode === APPROVAL && i.status === "open" && !decisionOf(i);

  const decide = async (i: Incident, d: Decision | null) => {
    setLocal((l) => ({ ...l, [i.id]: d }));
    const res = await fetch("/api/decide", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ id: i.id, decision: d ?? "undo" }),
    }).catch(() => null);
    if (!res?.ok) setError("Chưa lưu được quyết định, hãy thử lại.");
  };

  const stateText = (i: Incident) => {
    const d = decisionOf(i);
    if (d === "approved") return "Đã duyệt (mô phỏng)";
    if (d === "rejected") return "Đã từ chối";
    if (i.status === "closed") return "Đã đóng";
    return i.mode === APPROVAL ? "Chờ duyệt" : "Tự động (mô phỏng)";
  };

  const incidents = state?.incidents ?? [];
  const pending = incidents.filter(isPending).length;
  const openCount = incidents.filter((i) => i.status === "open").length;
  const shown = incidents.filter((i) => filter === "all" || (filter === "open" ? i.status === "open" : isPending(i)));
  const current = incidents.find((i) => i.id === selected) ?? null;
  const s = state?.summary;
  const stale = state?.updated ? Date.now() / 1000 - state.updated > STALE_S : false;

  const tabs: [Filter, string, number][] = [
    ["open", "Đang mở", openCount], ["pending", "Chờ duyệt", pending], ["all", "Tất cả", incidents.length],
  ];

  return (
    <main>
      <section className="card status">
        <span className={stale ? "dot off" : "dot"} aria-hidden="true" />
        <span>
          {state?.updated
            ? `${stale ? "Luồng đang tạm dừng" : "Đang giám sát"} · cập nhật lúc ${clock(state.updated)}`
            : "Đang kết nối..."}
        </span>
        <span className="badge">Dữ liệu mô phỏng</span>
        {permission === "default" && (
          <button onClick={() => Notification.requestPermission().then(setPermission)}>Bật thông báo trình duyệt</button>
        )}
      </section>
      {error && <p className="error" role="alert">{error}</p>}

      {banner && (
        <section className="banner" role="alert">
          <div>
            <strong>Phát hiện xâm nhập lúc {clock(banner.opened)}, mức {banner.level}</strong>
            <span>{banner.src} → {banner.dst}: {short(banner.tactic)}, tầng {banner.tier}</span>
          </div>
          <div className="actions">
            <button onClick={() => { setFilter("all"); setSelected(banner.id); setBanner(null); }}>Xem chi tiết</button>
            <button onClick={() => setBanner(null)}>Đóng</button>
          </div>
        </section>
      )}

      {s && (
        <section className="stats" aria-label="Tổng quan">
          <div className="stat"><strong>{s.flows_60m.toLocaleString("vi-VN")}</strong><span>Flow trong 60 phút</span></div>
          <div className="stat"><strong>{s.alerts_60m.toLocaleString("vi-VN")}</strong><span>Cảnh báo trong 60 phút</span></div>
          <div className="stat"><strong>{openCount}</strong><span>Sự cố đang mở</span></div>
          <div className="stat">
            <strong>{s.campaigns_found}/{s.campaigns_done}</strong><span>Chiến dịch đã phát hiện</span>
          </div>
          <div className="stat">
            <strong>{s.ttd_median === null ? "–" : `${s.ttd_median} phút`}</strong><span>Thời gian phát hiện (trung vị)</span>
          </div>
          <div className="stat emph"><strong>{pending}</strong><span>Chờ chuyên viên duyệt</span></div>
        </section>
      )}

      {state && state.series.length > 0 && <section className="card"><AlertChart points={state.series} /></section>}

      <div className="workspace">
        <section className="card">
          <h2>Sự cố</h2>
          <div className="tabs">
            {tabs.map(([key, label, n]) => (
              <button key={key} aria-pressed={filter === key} onClick={() => setFilter(key)}>{label} ({n})</button>
            ))}
          </div>
          <div className="scroll">
            <table>
              <thead>
                <tr><th>Mở lúc</th><th>Nguồn</th><th>Đích</th><th>Tầng</th><th>Chiến thuật</th><th>Cảnh báo</th><th>Mức</th><th>Trạng thái</th></tr>
              </thead>
              <tbody>
                {shown.map((i) => (
                  <tr key={i.id} tabIndex={0} aria-selected={i.id === selected} onClick={() => setSelected(i.id)}
                    onKeyDown={(e) => { if (e.key === "Enter") setSelected(i.id); }}>
                    <td className="num">{clock(i.opened)}</td>
                    <td className="addr">{i.src}</td>
                    <td className="addr">{i.dst}</td>
                    <td className="num">{i.tier}</td>
                    <td>{short(i.tactic)}</td>
                    <td className="num">{i.alerts}/{i.flows}</td>
                    <td><span className={i.mode === APPROVAL ? "badge solid" : "badge"}>{i.level}</span></td>
                    <td>{stateText(i)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {shown.length === 0 && <p className="hint">Không có sự cố trong mục này.</p>}
          </div>
        </section>

        <section className="card detail">
          <h2>Chi tiết và biện pháp ứng phó</h2>
          {!current ? <p className="hint">Chọn một sự cố để xem biện pháp đề xuất.</p> : (
            <>
              <dl>
                <dt>Kết nối</dt><dd className="addr">{current.src} → {current.dst}</dd>
                <dt>Thời gian</dt><dd>{clock(current.opened)} đến {clock(current.last)}</dd>
                <dt>Phân tầng</dt><dd>Tầng {current.tier}: {TIER[current.tier]}</dd>
                <dt>Chiến thuật</dt><dd>{TACTIC[current.tactic] ?? current.tactic}</dd>
                <dt>{current.tier === 1 ? "Họ tấn công" : "Họ gần nhất"}</dt><dd>{current.family}</dd>
                <dt>Cảnh báo</dt><dd>{current.alerts} trên {current.flows} flow</dd>
                <dt>Rủi ro</dt><dd>R = L × I = {current.L} × {current.I} = {current.R}</dd>
                <dt>Nhãn giả lập</dt>
                <dd>
                  {Object.keys(current.truth).length ? Object.keys(current.truth).join(", ") : "không có tấn công, đây là báo nhầm"}
                  {" "}(chỉ để đối chiếu, mô hình không dùng)
                </dd>
              </dl>
              <h3>Mức {current.level}: {current.action}</h3>
              <p className="hint">{current.reversible ? "Đảo ngược được" : "Khó đảo ngược"}. Thực hiện: {current.mode}.</p>
              <h3>Biện pháp ngay (D3FEND)</h3>
              <ul>{current.d3fend_now.map((m) => <li key={m}>{m}</li>)}</ul>
              {current.d3fend_later.length > 0 && (
                <>
                  <h3>Củng cố sau</h3>
                  <ul>{current.d3fend_later.map((m) => <li key={m}>{m}</li>)}</ul>
                </>
              )}
              {current.mode === APPROVAL && (
                <div className="decision">
                  {decisionOf(current) ? (
                    <>
                      <span>{stateText(current)}</span>
                      <button onClick={() => decide(current, null)}>Hoàn tác</button>
                    </>
                  ) : current.status === "open" && (
                    <>
                      <button className="primary" onClick={() => decide(current, "approved")}>Duyệt</button>
                      <button onClick={() => decide(current, "rejected")}>Từ chối</button>
                    </>
                  )}
                </div>
              )}
            </>
          )}
        </section>
      </div>

      <footer className="notes">
        <p>
          Dữ liệu mô phỏng chạy 24/7 trên máy chủ, tính cả khi không mở trang: mỗi phút phát lại flow thật của
          LYCOS-IDS2017 chưa dùng để huấn luyện, theo kịch bản tấn công do Gemini soạn. Trình tự tấn công và địa chỉ IP là
          giả lập. Mô hình: HC-CLOSR.
        </p>
        <p>
          Sự cố chỉ mở khi một cặp nguồn và đích có từ 5 cảnh báo trong 5 phút và tỉ lệ cảnh báo từ 30% trở lên. Trong
          24 giờ: {s?.incidents_24h ?? 0} sự cố, {s?.false_24h ?? 0} báo nhầm. Các hành động chỉ là mô phỏng, chưa nối với
          tường lửa thật. Ngưỡng và mức ứng phó là thiết kế của đề tài, cần đối chiếu với chuyên gia.
        </p>
      </footer>
    </main>
  );
}
