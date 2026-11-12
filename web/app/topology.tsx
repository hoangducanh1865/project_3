"use client";

/** Sơ đồ mạng của testbed DataSense theo devices.csv, vẽ đường đi của các sự cố đang mở. */
export type Device = { ip: string; device_name: string; role: string; type: string };
export type Link = { id: string; src: string; dst: string; on: boolean };

const W = 980, H = 330;
const GROUPS: [string, string, (d: Device) => boolean][] = [
  ["attacker", "Máy tấn công", (d) => d.role === "attacker"],
  ["core", "Máy chủ MQTT, edge", (d) => d.role === "mqtt-broker" || d.role === "edge"],
  ["sensor", "Cảm biến", (d) => d.role === "sensor"],
  ["camera", "Camera", (d) => d.role === "camera"],
  ["plug", "Ổ cắm thông minh", (d) => d.role === "smart-plug"],
];

function layout(devices: Device[]) {
  const pos: Record<string, { x: number; y: number }> = {};
  const fixed: Record<string, [number, number]> = { cloud: [W / 2, 26], router: [W / 2, 84], switch: [W / 2 - 120, 140], ap: [W / 2 + 120, 140] };
  devices.forEach((d) => { if (fixed[d.role]) pos[d.ip] = { x: fixed[d.role][0], y: fixed[d.role][1] }; });
  const boxes = GROUPS.map(([key, title, test], g) => {
    const items = devices.filter(test);
    const bw = (W - 40) / GROUPS.length - 12, bx = 20 + g * (bw + 12), by = 188;
    const cols = Math.max(1, Math.floor((bw - 16) / 30));
    items.forEach((d, i) => { pos[d.ip] = { x: bx + 18 + (i % cols) * 30, y: by + 34 + Math.floor(i / cols) * 34 }; });
    return { key, title, n: items.length, x: bx, y: by, w: bw };
  });
  pos["outside"] = { x: W - 60, y: 84 };
  return { pos, boxes };
}

export default function Topology({ devices, links, onPick }: { devices: Device[]; links: Link[]; onPick: (id: string) => void }) {
  const { pos, boxes } = layout(devices);
  const name = Object.fromEntries(devices.map((d) => [d.ip, d.device_name]));
  const at = (ip: string) => pos[ip] ?? pos["outside"];
  const hot = new Set(links.flatMap((l) => [l.src, l.dst]));
  return (
    <figure className="topo">
      <figcaption>
        <h2>Sơ đồ mạng</h2>
        <span>{devices.length} thiết bị theo danh mục của DataSense · đường đậm là sự cố đang chọn</span>
      </figcaption>
      <svg viewBox={`0 0 ${W} ${H + 40}`} role="img" aria-label="Sơ đồ mạng và đường đi của sự cố">
        {["switch", "ap"].map((r) => {
          const d = devices.find((x) => x.role === r);
          const p = d && pos[d.ip];
          return p && <line key={r} x1={W / 2} y1={84} x2={p.x} y2={p.y} className="wire" />;
        })}
        <line x1={W / 2} y1={26} x2={W / 2} y2={84} className="wire" />
        {boxes.map((b) => (
          <g key={b.key}>
            <line x1={b.x + b.w / 2} y1={b.y} x2={W / 2 + (b.x + b.w / 2 < W / 2 ? -120 : 120)} y2={140} className="wire" />
            <rect x={b.x} y={b.y} width={b.w} height={H - b.y + 30} rx="8" className="group" />
            <text x={b.x + 10} y={b.y + 16} className="gtitle">{b.title} ({b.n})</text>
          </g>
        ))}
        {links.filter((l) => !l.on).concat(links.filter((l) => l.on)).map((l) => {
          const a = at(l.src), b = at(l.dst);
          const mx = (a.x + b.x) / 2, my = Math.min(a.y, b.y) - 40;
          return (
            <path key={l.id} d={`M${a.x},${a.y} Q${mx},${my} ${b.x},${b.y}`} className={l.on ? "flowline on" : "flowline"}
              onClick={() => onPick(l.id)}>
              <title>{`${l.src} (${name[l.src] ?? "ngoài danh mục"}) → ${l.dst} (${name[l.dst] ?? "ngoài danh mục"})`}</title>
            </path>
          );
        })}
        {devices.map((d) => {
          const p = pos[d.ip];
          if (!p) return null;
          const big = ["cloud", "router", "switch", "ap"].includes(d.role);
          return (
            <g key={d.ip} className={hot.has(d.ip) ? "node hot" : "node"}>
              <circle cx={p.x} cy={p.y} r={big ? 9 : 7} />
              <text x={p.x} y={p.y + (big ? 22 : 18)}>{big ? `${d.device_name} .${d.ip.split(".").pop()}` : `.${d.ip.split(".").pop()}`}</text>
              <title>{`${d.ip} · ${d.device_name} · ${d.role}`}</title>
            </g>
          );
        })}
        <g className={links.some((l) => !(l.src in name) || !(l.dst in name)) ? "node hot" : "node"}>
          <circle cx={pos.outside.x} cy={pos.outside.y} r={8} />
          <text x={pos.outside.x} y={pos.outside.y + 21}>IP ngoài danh mục</text>
          <title>IP giả mạo, multicast, broadcast hoặc máy ngoài testbed</title>
        </g>
      </svg>
    </figure>
  );
}
