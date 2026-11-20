"use client";

import { BookOpen, Crosshair, Database, LayoutDashboard, Network, ShieldAlert, ShieldCheck, UserCog } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { Ctx, Decision, Page } from "./ctx";
import type { Attacks, AttackScenario, Card, Incident, Labels, Live, Policy, Role, Sources } from "./lib";
import { hm, planFor, useLive, useStatic, useStored } from "./lib";
import AttackConsole from "./views/attack";
import Incidents from "./views/incidents";
import LabelsView from "./views/labels";
import Model from "./views/model";
import NetworkView from "./views/network";
import Overview from "./views/overview";
import PolicyView from "./views/policy";

const NAV: [Page, string, typeof LayoutDashboard][] = [
  ["overview", "Tổng quan", LayoutDashboard], ["incidents", "Sự cố", ShieldAlert], ["network", "Mạng và nguồn dữ liệu", Network],
  ["attack", "Diễn tập tấn công", Crosshair],
  ["labels", "Nhãn và tri thức", BookOpen], ["policy", "Phân quyền và cấu hình", UserCog], ["model", "Dữ liệu và mô hình", Database],
];

export default function App() {
  const [page, setPage] = useState<Page>("overview");
  const [selected, setSelected] = useState<string | null>(null);
  const { live, error } = useLive();
  const labels = useStatic<Labels>("labels").data;
  const policy = useStatic<Policy>("policy").data;
  const sources = useStatic<Sources>("sources").data;
  const card = useStatic<Card>("card").data;
  const attacks = useStatic<Attacks>("attacks").data;
  const [role, setRole] = useStored<Role>("vai-tro", "analyst");
  const [decisions, setDecisions] = useStored<Record<string, Decision>>("quyet-dinh", {});
  const [injected, setInjected] = useStored<Incident[]>("dien-tap", []);
  const [now, setNow] = useState(() => Date.now() / 1000);

  useEffect(() => {
    const read = () => { const h = location.hash.slice(1) as Page; if (NAV.some(([k]) => k === h)) setPage(h); };
    read(); window.addEventListener("hashchange", read);
    const id = setInterval(() => setNow(Date.now() / 1000), 15000);
    return () => { window.removeEventListener("hashchange", read); clearInterval(id); };
  }, []);

  const devices = useMemo(() => sources?.devices ?? card?.devices ?? [], [sources, card]);
  const byIp = useMemo(() => Object.fromEntries(devices.map((d) => [d.ip, d])), [devices]);
  const incidents = useMemo(() => [...injected, ...(live?.incidents ?? [])], [injected, live]);
  // Sự cố diễn tập do người dùng phát động được cộng vào luồng phát lại để hiện trên biểu đồ và sơ đồ mạng.
  const livePlus: Live | null = useMemo(() => {
    if (!live) return null;
    if (!injected.length) return live;
    const a = injected.reduce((n, i) => n + i.alerts, 0), f = injected.reduce((n, i) => n + i.flows, 0);
    const series = live.series.map((p, k) => (k === live.series.length - 1 ? { ...p, flows: p.flows + f, alerts: p.alerts + a } : p));
    return { ...live, series, summary: { ...live.summary, flows_60m: live.summary.flows_60m + f, alerts_60m: live.summary.alerts_60m + a } };
  }, [live, injected]);
  const ctx: Ctx = {
    incidents, labels, policy, sources, card, attacks, role, decisions, selected, setSelected, now, simCount: injected.length,
    decide: (id, d) => {
      const next = { ...decisions };
      if (d) next[id] = { decision: d, by: role, at: Date.now() / 1000 }; else delete next[id];
      setDecisions(next);
    },
    launch: (s, dstIp) => {
      const t = Date.now() / 1000;
      const inc: Incident = { ...s.incident, id: `sim-${Date.now()}`, src: s.src_ip, dst: dstIp, opened: t, last: t,
        status: "open", campaign: null, sim: true };
      setInjected([inc, ...injected].slice(0, 12));
      setSelected(inc.id); setPage("incidents"); location.hash = "incidents";
    },
    clearSim: () => setInjected([]),
    roleOf: (ip) => byIp[ip]?.role,
    nameOf: (ip) => byIp[ip]?.device_name ?? "ngoài danh mục",
    famName: (f) => labels?.families[f]?.name ?? f,
    stateOf: (i) => {
      const d = decisions[i.id];
      if (d) return { text: `${d.decision === "approved" ? "Đã duyệt" : "Đã từ chối"} lúc ${hm(d.at)}`, pending: false, by: policy?.roles[d.by].name };
      if (!policy) return { text: "", pending: false };
      const pl = planFor(policy, i.level, byIp[i.dst]?.role);
      if (!pl.approverRole) return { text: "Hệ thống tự xử lý", pending: false };
      if (i.status === "closed") return { text: "Đã đóng, không ai duyệt", pending: false };
      if (pl.ai === "act_on_timeout" && now - i.opened > policy.ai.timeout_min * 60)
        return { text: `AI đã ${pl.actionName.toLowerCase()} ${pl.ttl} phút (hết giờ chờ)`, pending: false, by: "Trợ lý AI" };
      return { text: `Chờ ${pl.approver} duyệt`, pending: true };
    },
    go: (p, inc) => { setPage(p); location.hash = p; if (inc) setSelected(inc); },
  };
  const pending = ctx.incidents.filter((i) => ctx.stateOf(i).pending).length;
  const stale = live ? now - live.updated > 180 : false;

  return (
    <div className="app">
      <aside className="side">
        <div className="brand"><span className="mark"><ShieldCheck size={18} aria-hidden="true" /></span>
          <div><strong>IIoT SOC</strong><small>HC-CLOSR · DataSense 2025</small></div></div>
        <nav aria-label="Trang">
          {NAV.map(([k, label, Icon]) => (
            <a key={k} href={`#${k}`} aria-current={page === k ? "page" : undefined} onClick={() => setPage(k)}>
              <Icon size={16} aria-hidden="true" /><span>{label}</span>
              {k === "incidents" && pending > 0 && <b>{pending}</b>}
            </a>
          ))}
        </nav>
        <p className="side-note">Đồ án Project 3, HUST 20261. Luồng là phát lại có tính sẵn trên flow thật của DataSense; mọi hành động chỉ là mô phỏng.</p>
      </aside>
      <div className="main">
        <header className="top">
          <div className="status">
            <span className={stale || error ? "dot off" : "dot"} aria-hidden="true" />
            {error ? error : live ? `Đang phát lại · cập nhật ${hm(live.updated)}` : "Đang tải..."}
          </div>
          <label className="role">Vai trò
            <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              <option value="analyst">{policy?.roles.analyst.name ?? "Chuyên viên trực (L1)"}</option>
              <option value="lead">{policy?.roles.lead.name ?? "Trưởng ca (L2)"}</option>
            </select>
          </label>
        </header>
        <main className="content">
          {page === "overview" && <Overview ctx={ctx} live={livePlus} />}
          {page === "incidents" && <Incidents ctx={ctx} />}
          {page === "network" && <NetworkView ctx={ctx} />}
          {page === "attack" && <AttackConsole ctx={ctx} />}
          {page === "labels" && <LabelsView ctx={ctx} />}
          {page === "policy" && <PolicyView ctx={ctx} />}
          {page === "model" && <Model card={card} />}
        </main>
      </div>
    </div>
  );
}
