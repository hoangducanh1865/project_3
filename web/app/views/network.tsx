"use client";

import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import type { Ctx } from "../ctx";
import { nf, utc } from "../lib";
import { Panel, Segmented, Stat, Topology } from "../ui";

const PAGE = 40;
type Tab = "files" | "devices";

export default function NetworkView({ ctx }: { ctx: Ctx }) {
  const src = ctx.sources;
  const [tab, setTab] = useState<Tab>("files");
  const [cat, setCat] = useState("all");
  const [q, setQ] = useState("");
  const [focus, setFocus] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const devices = src?.devices ?? [];
  const byName = useMemo(() => Object.fromEntries(devices.map((d) => [d.device_name, d.ip])), [devices]);
  const files = useMemo(() => (src?.files ?? []).filter((f) => {
    if (cat !== "all" && f.category !== cat) return false;
    if (focus && !f.targets.some((t) => byName[t] === focus)) return false;
    const text = `${f.file} ${f.attack} ${f.targets.join(" ")} ${f.family ?? ""}`.toLowerCase();
    return !q || text.includes(q.toLowerCase());
  }), [src, cat, q, focus, byName]);
  const cats = useMemo(() => [...new Set((src?.files ?? []).map((f) => f.category))].sort(), [src]);
  const targetCount = useMemo(() => {
    const c: Record<string, number> = {};
    (src?.files ?? []).forEach((f) => f.targets.forEach((t) => { const ip = byName[t]; if (ip) c[ip] = (c[ip] ?? 0) + 1; }));
    return c;
  }, [src, byName]);
  const openBy = useMemo(() => {
    const c: Record<string, number> = {};
    ctx.incidents.filter((i) => i.status === "open").forEach((i) => { c[i.dst] = (c[i.dst] ?? 0) + 1; c[i.src] = (c[i.src] ?? 0) + 1; });
    return c;
  }, [ctx.incidents]);
  const totals = (src?.files ?? []).reduce((a, f) => ({ flows: a.flows + f.flows, att: a.att + f.attack_flows }), { flows: 0, att: 0 });
  const links = ctx.incidents.filter((i) => i.status === "open").map((i) => ({ id: i.id, src: i.src, dst: i.dst, on: i.dst === focus || i.src === focus }));
  const shown = files.slice(page * PAGE, (page + 1) * PAGE);
  return (
    <>
      <div className="page-head">
        <div><h1>Mạng và nguồn dữ liệu</h1><p>{src?.capture}. Bấm vào một thiết bị trong bảng để lọc các tệp nhắm vào nó.</p></div>
      </div>
      <section className="stats">
        <Stat label="Thiết bị" value={src ? devices.length : undefined} hint={src ? `${devices.filter((d) => d.role === "attacker").length} máy tấn công của testbed` : undefined} />
        <Stat label="Tệp PCAP đã đọc" value={src ? nf(src.files.length) : undefined} hint={src ? `${src.unread} tệp DoS, DDoS chưa đọc` : undefined} />
        <Stat label="Flow đã trích" value={src ? nf(totals.flows) : undefined} />
        <Stat label="Flow tấn công sau gán nhãn lại" value={src ? nf(totals.att) : undefined} />
      </section>
      <Panel title="Sơ đồ mạng" sub={focus ? `Đang lọc theo ${focus}` : "Theo danh mục thiết bị công bố kèm bộ dữ liệu"}
        actions={focus && <button onClick={() => setFocus(null)}>Bỏ lọc</button>}>
        <Topology devices={devices} links={links} focus={focus} />
      </Panel>
      <Panel flush title={tab === "files" ? "Tệp nguồn" : "Thiết bị"} actions={
        <div className="toolbar">
          {tab === "files" && <>
            <label className="search"><Search size={14} aria-hidden="true" />
              <input value={q} onChange={(e) => { setQ(e.target.value); setPage(0); }} placeholder="Tên tệp, kiểu tấn công, mục tiêu" /></label>
            <select value={cat} onChange={(e) => { setCat(e.target.value); setPage(0); }} aria-label="Nhóm">
              <option value="all">Mọi nhóm</option>{cats.map((c) => <option key={c} value={c}>{c}</option>)}
            </select></>}
          <Segmented value={tab} onChange={setTab} options={[["files", "Tệp", files.length], ["devices", "Thiết bị", devices.length]]} />
        </div>}>
        {tab === "files" ? <>
          <div className="scroll tall">
            <table className="table">
              <thead><tr><th>Tệp PCAP</th><th>Nhóm</th><th>Họ</th><th>Mục tiêu</th><th>Bắt đầu (UTC)</th><th className="r">Giây</th>
                <th className="r">Flow</th><th className="r">Tấn công</th><th className="r">Nền</th><th className="r">Bỏ</th></tr></thead>
              <tbody>{shown.map((f) => (
                <tr key={f.file}><td className="mono small">{f.file}</td><td>{f.category}</td><td>{f.family ? ctx.famName(f.family) : "Bình thường"}</td>
                  <td>{f.targets.join(", ")}</td><td className="mono">{utc(f.start)}</td><td className="r mono">{Math.round((f.end - f.start) / 1000)}</td>
                  <td className="r mono">{nf(f.flows)}</td><td className="r mono">{nf(f.attack_flows)}</td>
                  <td className="r mono">{nf(f.benign_flows)}</td><td className="r mono">{nf(f.dropped)}</td></tr>))}
              </tbody>
            </table>
          </div>
          <div className="pager">
            <span>{files.length ? `${page * PAGE + 1}–${Math.min(files.length, (page + 1) * PAGE)} / ${nf(files.length)}` : "Không có tệp"}</span>
            <button disabled={page === 0} onClick={() => setPage(page - 1)}>Trước</button>
            <button disabled={(page + 1) * PAGE >= files.length} onClick={() => setPage(page + 1)}>Sau</button>
          </div></>
          : <div className="scroll tall">
            <table className="table">
              <thead><tr><th>IP</th><th>MAC</th><th>Tên</th><th>Vai trò</th><th>Loại</th><th className="r">Là mục tiêu trong</th><th className="r">Sự cố đang mở</th></tr></thead>
              <tbody>{devices.map((d) => (
                <tr key={d.ip} aria-selected={focus === d.ip} onClick={() => { setFocus(focus === d.ip ? null : d.ip); setTab("files"); setPage(0); }}>
                  <td className="mono">{d.ip}</td><td className="mono small">{d.mac}</td><td>{d.device_name}</td><td>{d.role}</td><td>{d.type}</td>
                  <td className="r mono">{targetCount[d.ip] ?? 0} tệp</td><td className="r mono">{openBy[d.ip] ?? 0}</td></tr>))}
              </tbody>
            </table>
          </div>}
      </Panel>
    </>
  );
}
