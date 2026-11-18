"use client";

import type { ReactNode } from "react";
import { useState } from "react";
import type { Device, Point } from "./lib";
import { hm } from "./lib";

export function LevelBadge({ level }: { level: string }) {
  return <span className={`level ${level}`} title={`Mức ứng phó ${level}`}>{level}</span>;
}

export function Chip({ children, tone }: { children: ReactNode; tone?: "strong" | "muted" }) {
  return <span className={`chip ${tone ?? ""}`}>{children}</span>;
}

export function Stat({ label, value, hint }: { label: string; value?: ReactNode; hint?: string }) {
  return (
    <div className="stat">
      <span>{label}</span>
      {value === undefined ? <i className="skeleton" /> : <strong>{value}</strong>}
      {hint && <small>{hint}</small>}
    </div>
  );
}

export function Panel({ title, sub, actions, children, flush, id }: {
  title?: string; sub?: ReactNode; actions?: ReactNode; children: ReactNode; flush?: boolean; id?: string;
}) {
  return (
    <section className={flush ? "panel flush" : "panel"} id={id}>
      {(title || actions) && (
        <header className="panel-head">
          <div>{title && <h2>{title}</h2>}{sub && <p>{sub}</p>}</div>
          {actions && <div className="panel-actions">{actions}</div>}
        </header>
      )}
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function KV({ rows }: { rows: [string, ReactNode][] }) {
  return <dl className="kv">{rows.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>;
}

export function Ext({ href, children }: { href: string | null; children: ReactNode }) {
  return href ? <a href={href} target="_blank" rel="noreferrer">{children}</a> : <>{children}</>;
}

export function Segmented<T extends string>({ value, options, onChange }: {
  value: T; options: [T, string, number?][]; onChange: (v: T) => void;
}) {
  return (
    <div className="seg" role="tablist">
      {options.map(([k, label, n]) => (
        <button key={k} role="tab" aria-selected={value === k} onClick={() => onChange(k)}>
          {label}{n !== undefined && <b>{n}</b>}
        </button>
      ))}
    </div>
  );
}

/** Số cảnh báo và số flow mỗi phút trong 60 phút gần nhất. */
export function AlertChart({ points }: { points: Point[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const SLOTS = 60, W = 900, H = 150, slot = W / SLOTS, off = SLOTS - points.length;
  const top = Math.max(10, ...points.map((p) => p.flows));
  const shown = hover === null ? null : points[hover];
  return (
    <figure className="chart">
      <div className="legend"><span className="sw flows" />Flow<span className="sw alerts" />Cảnh báo
        {shown && <em>{hm(shown.t)}: {shown.alerts} cảnh báo / {shown.flows} flow</em>}</div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label="Flow và cảnh báo mỗi phút"
        onMouseLeave={() => setHover(null)}>
        {[0.25, 0.5, 0.75].map((f) => <line key={f} x1="0" x2={W} y1={H * f} y2={H * f} className="grid" />)}
        {points.map((p, i) => {
          const x = (i + off) * slot, hf = (p.flows / top) * (H - 6), ha = (p.alerts / top) * (H - 6);
          return (
            <g key={p.t} onMouseEnter={() => setHover(i)}>
              <rect x={x} y={0} width={slot} height={H} fill="transparent" />
              <rect x={x + 1} y={H - hf} width={slot - 2} height={hf} className="bar flows" />
              <rect x={x + 1} y={H - ha} width={slot - 2} height={ha} className={hover === i ? "bar alerts on" : "bar alerts"} />
            </g>
          );
        })}
      </svg>
      <div className="ticks"><span>60 phút trước</span><span>Đỉnh {top} flow/phút</span><span>Hiện tại</span></div>
    </figure>
  );
}

// ---------- sơ đồ mạng ----------
export type Link = { id: string; src: string; dst: string; on: boolean };
const GROUPS: [string, string, (d: Device) => boolean][] = [
  ["attacker", "Máy tấn công (testbed)", (d) => d.role === "attacker"],
  ["core", "Máy chủ MQTT, edge", (d) => d.role === "mqtt-broker" || d.role === "edge"],
  ["sensor", "Cảm biến", (d) => d.role === "sensor"],
  ["camera", "Camera", (d) => d.role === "camera"],
  ["plug", "Ổ cắm thông minh", (d) => d.role === "smart-plug"],
];

export function Topology({ devices, links, onPick, focus }: {
  devices: Device[]; links: Link[]; onPick?: (id: string) => void; focus?: string | null;
}) {
  const W = 1000, H = 360;
  const pos: Record<string, { x: number; y: number }> = {};
  const fixed: Record<string, [number, number]> = { cloud: [W / 2, 28], router: [W / 2, 92], switch: [W / 2 - 150, 150], ap: [W / 2 + 150, 150] };
  devices.forEach((d) => { if (fixed[d.role]) pos[d.ip] = { x: fixed[d.role][0], y: fixed[d.role][1] }; });
  const gw = (W - 40) / GROUPS.length - 12;
  const boxes = GROUPS.map(([key, title, test], g) => {
    const items = devices.filter(test), bx = 20 + g * (gw + 12), by = 200, cols = Math.max(1, Math.floor((gw - 20) / 32));
    items.forEach((d, i) => { pos[d.ip] = { x: bx + 22 + (i % cols) * 32, y: by + 40 + Math.floor(i / cols) * 36 }; });
    return { key, title, n: items.length, x: bx, y: by };
  });
  pos.outside = { x: W - 70, y: 92 };
  const name = Object.fromEntries(devices.map((d) => [d.ip, d.device_name]));
  const at = (ip: string) => pos[ip] ?? pos.outside;
  const hot = new Set(links.flatMap((l) => [l.src, l.dst]));
  const sw = devices.find((d) => d.role === "switch"), ap = devices.find((d) => d.role === "ap");
  return (
    <svg className="topo" viewBox={`0 0 ${W} ${H + 30}`} role="img" aria-label="Sơ đồ mạng và đường đi của sự cố">
      <line x1={W / 2} y1={28} x2={W / 2} y2={92} className="wire" />
      {sw && <line x1={W / 2} y1={92} x2={pos[sw.ip].x} y2={pos[sw.ip].y} className="wire" />}
      {ap && <line x1={W / 2} y1={92} x2={pos[ap.ip].x} y2={pos[ap.ip].y} className="wire" />}
      {boxes.map((b) => (
        <g key={b.key}>
          <line x1={b.x + gw / 2} y1={b.y} x2={b.x + gw / 2 < W / 2 ? W / 2 - 150 : W / 2 + 150} y2={150} className="wire" />
          <rect x={b.x} y={b.y} width={gw} height={H - b.y + 22} rx="8" className="group" />
          <text x={b.x + 12} y={b.y + 19} className="gtitle">{b.title} · {b.n}</text>
        </g>
      ))}
      {[...links.filter((l) => !l.on), ...links.filter((l) => l.on)].map((l) => {
        const a = at(l.src), b = at(l.dst), mx = (a.x + b.x) / 2, my = Math.min(a.y, b.y) - 50;
        return (
          <path key={l.id} d={`M${a.x},${a.y} Q${mx},${my} ${b.x},${b.y}`} className={l.on ? "flowline on" : "flowline"}
            onClick={() => onPick?.(l.id)}>
            <title>{`${l.src} (${name[l.src] ?? "ngoài danh mục"}) → ${l.dst} (${name[l.dst] ?? "ngoài danh mục"})`}</title>
          </path>
        );
      })}
      {devices.map((d) => {
        const p = pos[d.ip];
        if (!p) return null;
        const core = ["cloud", "router", "switch", "ap"].includes(d.role);
        const cls = `node ${hot.has(d.ip) ? "hot" : ""} ${focus === d.ip ? "focus" : ""}`;
        return (
          <g key={d.ip} className={cls}>
            <circle cx={p.x} cy={p.y} r={core ? 10 : 8} />
            <text x={p.x} y={p.y + (core ? 24 : 20)}>{core ? `${d.device_name} .${d.ip.split(".").pop()}` : `.${d.ip.split(".").pop()}`}</text>
            <title>{`${d.ip} · ${d.device_name} · ${d.role}`}</title>
          </g>
        );
      })}
      <g className={`node ${links.some((l) => !(l.src in name) || !(l.dst in name)) ? "hot" : ""}`}>
        <circle cx={pos.outside.x} cy={pos.outside.y} r={9} />
        <text x={pos.outside.x} y={pos.outside.y + 23}>IP ngoài danh mục</text>
        <title>IP giả mạo, multicast, broadcast hoặc máy ngoài testbed</title>
      </g>
    </svg>
  );
}
