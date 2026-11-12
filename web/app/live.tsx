"use client";

import { Bell, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { APPROVAL, attackUrl, FAMILY, famName, num, PROTO, TACTIC, TIER } from "./labels";
import Topology, { type Device } from "./topology";
import { LevelBadge, ResponsePanel, Stat, StateText } from "./ui";

type Incident = {
  id: string; src: string; dst: string; opened: number; last: number; flows: number; alerts: number;
  status: "open" | "closed"; truth: Record<string, number>; campaign: number | null; family: string;
  tier: number; tactic: string; L: number; I: number; R: number; level: string; action: string; reversible: boolean;
  mode: string; d3fend_now: string[]; d3fend_later: string[]; decision: Decision | null;
  evidence?: Evidence[]; files?: string[];
};
type Evidence = {
  sport: number; dport: number; proto: number; t0: number; t1: number; file: string; score: number;
  feat: Record<string, number>; top: { name: string; value: number; median: number; z: number }[];
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
  const W = 720, H = 132, slot = W / SLOTS, offset = SLOTS - points.length;   // phút mới nhất luôn ở bên phải
  const top = Math.max(10, ...points.map((p) => p.alerts));
  const shown = hover === null ? null : points[hover];
  return (
    <figure className="chart">
      <figcaption>
        <h2>Cảnh báo mỗi phút</h2>
        <span>60 phút gần nhất · cao nhất {top}</span>
      </figcaption>
      <div className="plot">
        {shown && (
          <div className="tip" style={{ left: `${((hover! + offset + 0.5) / SLOTS) * 100}%` }}>
            <b>{clock(shown.t)}</b> {shown.alerts} cảnh báo / {shown.flows} flow
          </div>
        )}
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label="Số cảnh báo mỗi phút"
          onMouseLeave={() => setHover(null)}>
          <line x1="0" y1="0.5" x2={W} y2="0.5" className="grid" />
          <line x1="0" y1={H / 2} x2={W} y2={H / 2} className="grid" />
          <line x1="0" y1={H - 0.5} x2={W} y2={H - 0.5} className="axis" />
          {points.map((p, i) => {
            const h = Math.max(p.alerts ? 2 : 0, (p.alerts / top) * (H - 4));
            const x = (i + offset) * slot;
            return (
              <g key={p.t} onMouseEnter={() => setHover(i)}>
                <rect x={x} y="0" width={slot} height={H} fill="transparent" />
                <rect x={x + 1} y={H - h - 1} width={Math.max(slot - 2, 1)} height={h} rx="2" className={hover === i ? "bar on" : "bar"} />
              </g>
            );
          })}
        </svg>
      </div>
      <div className="ticks"><span>60 phút trước</span><span>Hiện tại</span></div>
    </figure>
  );
}

const utc = (ms: number) => new Date(ms).toISOString().replace("T", " ").slice(0, 23);
const big = (x: number) => (Math.abs(x) >= 1000 ? Math.round(x).toLocaleString("vi-VN") : num(x, Number.isInteger(x) ? 0 : 2));

/** Bằng chứng kỹ thuật: flow gốc, điểm so với ngưỡng, đặc trưng lệch nhiều nhất, cách tự kiểm chứng bằng Wireshark. */
function EvidencePanel({ inc, thr }: { inc: Incident; thr?: number }) {
  const ev = inc.evidence ?? [];
  if (!ev.length) return null;
  const t0 = Math.min(...ev.map((e) => e.t0)), t1 = Math.max(...ev.map((e) => e.t1));
  const filter = `ip.addr==${inc.src} && ip.addr==${inc.dst} && frame.time_epoch>=${(t0 / 1000).toFixed(3)} && frame.time_epoch<=${(t1 / 1000 + 0.001).toFixed(3)}`;
  const top = ev[0].top;
  return (
    <div className="ev-block">
      <h4>Bằng chứng kỹ thuật ({ev.length} flow bị cảnh báo gần nhất)</h4>
      <div className="scroll" style={{ maxHeight: 220 }}>
        <table className="evidence">
          <thead><tr><th>Thời điểm gốc (UTC)</th><th>Cổng</th><th>Gói</th><th>Byte</th><th>ms</th><th>SYN/RST/FIN</th><th>Điểm OOD</th></tr></thead>
          <tbody>{ev.map((e, k) => (
            <tr key={k}>
              <td className="addr">{utc(e.t0)}</td>
              <td className="addr">{PROTO[e.proto] ?? e.proto} {e.sport}→{e.dport}</td>
              <td className="num">{big(e.feat.bidirectional_packets)}</td>
              <td className="num">{big(e.feat.bidirectional_bytes)}</td>
              <td className="num">{big(e.feat.bidirectional_duration_ms)}</td>
              <td className="num">{e.feat.bidirectional_syn_packets}/{e.feat.bidirectional_rst_packets}/{e.feat.bidirectional_fin_packets}</td>
              <td className="num">{num(e.score, 2)}</td>
            </tr>))}
          </tbody>
        </table>
      </div>
      {thr !== undefined && <p className="note">Ngưỡng điểm OOD: {num(thr)} (phân vị 95 trên flow đã biết). Điểm lớn hơn ngưỡng là hành vi chưa học.</p>}
      <h4>Đặc trưng lệch nhiều nhất so với flow bình thường</h4>
      <ul>{top.map((t) => (
        <li key={t.name}><code>{t.name}</code> = {big(t.value)}, trung vị bình thường {big(t.median)} (lệch {num(t.z, 1)} IQR)</li>
      ))}</ul>
      <h4>Tự kiểm chứng trên gói tin gốc</h4>
      <p className="note" style={{ marginTop: 2 }}>Mở tệp PCAP của DataSense bằng Wireshark, dán bộ lọc:</p>
      <code className="code">{inc.files?.map((f) => `${f}.pcap`).join(", ")}</code>
      <code className="code">{filter}</code>
    </div>
  );
}

export default function Live({ devices, thr }: { devices: Device[]; thr?: number }) {
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
  const names = Object.fromEntries(devices.map((d) => [d.ip, d.device_name]));
  const links = incidents.filter((i) => i.status === "open" || i.id === selected)
    .map((i) => ({ id: i.id, src: i.src, dst: i.dst, on: i.id === selected }));
  const stale = state?.updated ? Date.now() / 1000 - state.updated > STALE_S : false;

  const tabs: [Filter, string, number][] = [
    ["open", "Đang mở", openCount], ["pending", "Chờ duyệt", pending], ["all", "Tất cả", incidents.length],
  ];

  return (
    <main>
      <div className="page-head" data-tour="status">
        <div>
          <h1>Giám sát trực tiếp</h1>
          <p>
            <span className={stale ? "live off" : "live"} aria-hidden="true" />
            {state?.updated
              ? `${stale ? "Luồng đang tạm dừng" : "Đang giám sát"} · cập nhật lúc ${clock(state.updated)}`
              : "Đang kết nối..."}
            <span className="tag">Dữ liệu mô phỏng</span>
          </p>
        </div>
        {permission === "default" && (
          <button data-tour="notify" onClick={() => Notification.requestPermission().then(setPermission)}>
            <Bell size={15} aria-hidden="true" />Bật thông báo
          </button>
        )}
      </div>
      {error && <p className="error" role="alert">{error}</p>}

      {banner && (
        <aside className="toast" role="alert">
          <div>
            <strong>Phát hiện xâm nhập lúc {clock(banner.opened)}</strong>
            <span className="addr">{banner.src} → {banner.dst}</span>
            <span>{short(banner.tactic)} · Tầng {banner.tier} · Mức {banner.level}</span>
            <button onClick={() => { setFilter("all"); setSelected(banner.id); setBanner(null); }}>Xem chi tiết</button>
          </div>
          <button className="close" aria-label="Đóng" onClick={() => setBanner(null)}><X size={16} /></button>
        </aside>
      )}

      <section className="stats" aria-label="Tổng quan" data-tour="stats">
        <Stat label="Flow trong 60 phút" value={s?.flows_60m.toLocaleString("vi-VN")} />
        <Stat label="Cảnh báo trong 60 phút" value={s?.alerts_60m.toLocaleString("vi-VN")} />
        <Stat label="Sự cố đang mở" value={s ? openCount : undefined} />
        <Stat label="Chiến dịch đã phát hiện" value={s ? `${s.campaigns_found}/${s.campaigns_done}` : undefined} />
        <Stat label="Thời gian phát hiện (trung vị)" value={s ? (s.ttd_median === null ? "–" : `${s.ttd_median} phút`) : undefined} />
        <Stat label="Chờ chuyên viên duyệt" value={s ? pending : undefined} emph />
      </section>

      {state && state.series.length > 0 && <section className="card" data-tour="chart"><AlertChart points={state.series} /></section>}

      {devices.length > 0 && (
        <section className="card" data-tour="topology">
          <Topology devices={devices} links={links} onPick={(id) => { setFilter("all"); setSelected(id); }} />
        </section>
      )}

      <div className="workspace">
        <section className="card flush" data-tour="incidents">
          <div className="card-head">
            <h2>Hàng đợi sự cố</h2>
            <div className="tabs">
              {tabs.map(([key, label, n]) => (
                <button key={key} aria-pressed={filter === key} onClick={() => setFilter(key)}
                  data-tour={key === "all" ? "filter-all" : undefined}>{label} <b>{n}</b></button>
              ))}
            </div>
          </div>
          <div className="scroll">
            <table>
              <thead>
                <tr><th>Mức</th><th>Mở lúc</th><th>Nguồn</th><th>Đích</th><th>Phân loại</th><th className="right">Cảnh báo</th><th>Trạng thái</th></tr>
              </thead>
              <tbody>
                {shown.map((i) => (
                  <tr key={i.id} tabIndex={0} aria-selected={i.id === selected} onClick={() => setSelected(i.id)}
                    onKeyDown={(e) => { if (e.key === "Enter") setSelected(i.id); }}>
                    <td><LevelBadge level={i.level} /></td>
                    <td className="num">{clock(i.opened)}</td>
                    <td className="addr" title={names[i.src]}>{i.src}</td>
                    <td className="addr" title={names[i.dst]}>{i.dst}</td>
                    <td>Tầng {i.tier} · {short(i.tactic)}</td>
                    <td className="num right">{i.alerts}/{i.flows}</td>
                    <td><StateText text={stateText(i)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {shown.length === 0 && <p className="empty">Không có sự cố trong mục này.</p>}
          </div>
        </section>

        <section className="card detail" data-tour="detail">
          {!current ? <p className="empty">Chọn một sự cố để xem biện pháp đề xuất.</p> : (
            <ResponsePanel
              title={TACTIC[current.tactic] ?? current.tactic}
              plan={current}
              facts={[
                ["Kết nối", <span key="k"><span className="addr">{current.src}</span> ({names[current.src] ?? "ngoài danh mục"}) → <span className="addr">{current.dst}</span> ({names[current.dst] ?? "ngoài danh mục"})</span>],
                ["Thời gian", `${clock(current.opened)} đến ${clock(current.last)}`],
                ["Phân tầng", `Tầng ${current.tier}: ${TIER[current.tier]}`],
                [current.tier === 1 ? "Họ tấn công" : "Họ gần nhất", <span key="f">{famName(current.family)}{FAMILY[current.family]?.[1] && <> · <a href={attackUrl(FAMILY[current.family][1])} target="_blank" rel="noreferrer">ATT&amp;CK {FAMILY[current.family][1]}</a></>}</span>],
                ["Cảnh báo", `${current.alerts} trên ${current.flows} flow`],
              ]}
              note={<>
                <EvidencePanel inc={current} thr={thr} />
                <p className="note">Nhãn đã gán lại của các flow này: {Object.keys(current.truth).length ? Object.keys(current.truth).map(famName).join(", ") : "bình thường, đây là báo nhầm"} (chỉ để đối chiếu, mô hình không dùng).</p>
              </>}
              footer={decisionOf(current) ? (
                <>
                  <StateText text={stateText(current)} />
                  <button onClick={() => decide(current, null)}>Hoàn tác</button>
                </>
              ) : current.status === "open" ? (
                <>
                  <button className="primary" onClick={() => decide(current, "approved")}>Duyệt</button>
                  <button onClick={() => decide(current, "rejected")}>Từ chối</button>
                </>
              ) : undefined}
            />
          )}
        </section>
      </div>

      <footer className="notes">
        <p>
          Luồng chạy 24/7 trên máy chủ: mỗi phút phát lại flow thật của DataSense (CIC IIoT 2025) chưa dùng để huấn
          luyện. IP, cổng, thời điểm gốc và tệp PCAP của từng flow giữ nguyên nên kiểm chứng được bằng Wireshark; chỉ
          thời điểm phát lại và trình tự các pha tấn công là giả lập. Mô hình: HC-CLOSR. Xem trang Dữ liệu và mô hình.
        </p>
        <p>
          Sự cố chỉ mở khi một cặp nguồn và đích có từ 5 cảnh báo trong 5 phút và tỉ lệ cảnh báo từ 30% trở lên. Trong 24
          giờ: {s?.incidents_24h ?? 0} sự cố, {s?.false_24h ?? 0} báo nhầm. Các hành động chỉ là mô phỏng, chưa nối với
          tường lửa thật. Ngưỡng và mức ứng phó là thiết kế của đề tài, cần đối chiếu với chuyên gia.
        </p>
      </footer>
    </main>
  );
}
