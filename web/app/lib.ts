"use client";

import { useCallback, useEffect, useState } from "react";

// ---------- kiểu dữ liệu (sinh bởi scripts/precompute_live.py, build_sources.py, check_labels.py) ----------
export type Evidence = {
  sport: number; dport: number; proto: number; t0: number; t1: number; file: string; score: number;
  feat: Record<string, number>; top: { name: string; value: number; median: number; z: number }[];
};
export type Incident = {
  id: string; src: string; dst: string; opened: number; last: number; flows: number; alerts: number;
  status: "open" | "closed"; truth: Record<string, number>; campaign: number | null; family: string;
  tier: number; tactic: string; L: number; I: number; R: number; level: Level; action: string; reversible: boolean;
  mode: string; d3fend_now: string[]; d3fend_later: string[]; evidence?: Evidence[]; files?: string[];
};
export type Level = "M0" | "M1" | "M2" | "M3" | "M4";
export type Point = { t: number; flows: number; alerts: number };
export type Summary = {
  flows_60m: number; alerts_60m: number; open: number; incidents_24h: number; false_24h: number;
  campaigns_done: number; campaigns_found: number; ttd_median: number | null;
};
export type Live = { updated: number; summary: Summary; series: Point[]; incidents: Incident[] };
export type Device = { ip: string; mac?: string; device_name: string; role: string; type: string };
export type SourceFile = {
  file: string; category: string; attack: string; family: string | null; targets: string[]; start: number; end: number;
  flows: number; attack_flows: number; benign_flows: number; dropped: number;
};
export type Sources = { dataset: string; capture: string; devices: Device[]; files: SourceFile[]; unread: number };
export type AiNote = {
  summary: string; check: string[]; recommend: { d3fend: string; why: string }[]; cites: string[]; dropped: number;
  model: string; retrieved: string[]; attack_version: string;
};
export type Family = {
  name: string; tactic: string; techniques: string[]; variants: string[]; behavior: string; labeling: string; note?: string;
  attack: { id: string; name?: string; url?: string; tactics?: string[]; modified?: string; revoked?: boolean }[];
  d3fend: Record<string, Record<string, [string, string][]>>;
  stats: { flows: number; files: number; median_packets: number; median_bytes: number; median_duration_ms: number;
    top_dst_ports: number[]; protocols: Record<string, number> } | null;
  ai: AiNote | null;
};
export type Labels = { attack_version: string; checked: string; dataset: string; families: Record<string, Family>; report: string };
export type Role = "system" | "ai" | "analyst" | "lead";
export type Policy = {
  roles: Record<Role, { name: string }>;
  levels: Record<Level, { action: string; ttl: number | null; executor: Role; approver: Role | null; ai: "suggest" | "act_on_timeout" }>;
  actions: Record<string, { name: string; reversible: boolean; desc: string }>;
  ai: { timeout_min: number; forbidden_actions: string[]; protected_roles: string[]; must_cite: boolean };
};
export type Card = {
  version: string;
  dataset: { name: string; url: string; paper: string; captured: [string, string]; devices: number; attackers: number;
    flows: number; classes: Record<string, number>; extractor: string };
  relabel: { rules: string[]; table: { category: string; files: number; flows: number; attack: number; benign: number; dropped: number }[] };
  model: { name: string; heldout: string; trained: string; split?: string; classes: string[]; n_features: number; features: string[];
    metrics: Record<string, number | null>; threshold: { quantile: number; value: number; meaning: string };
    tactics: Record<string, string> };
  devices: Device[];
};

// ---------- tải dữ liệu ----------
export function useStatic<T>(name: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    fetch(`/live/${name}.json`).then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Không tải được ${name} (${r.status}).`))))
      .then(setData).catch((e) => setError(e.message));
  }, [name]);
  return { data, error };
}

export function useLive(pollMs = 15000) {
  const [live, setLive] = useState<Live | null>(null);
  const [error, setError] = useState("");
  const poll = useCallback(async () => {
    try {
      const r = await fetch("/api/live", { cache: "no-store" });
      if (!r.ok) throw new Error(`Máy chủ trả lỗi ${r.status}.`);
      setLive(await r.json()); setError("");
    } catch (e) { setError((e as Error).message); }
  }, []);
  useEffect(() => { poll(); const id = setInterval(poll, pollMs); return () => clearInterval(id); }, [poll, pollMs]);
  return { live, error };
}

/** Giá trị lưu ở trình duyệt (vai trò đang dùng, quyết định đã ghi). Bọc try/catch vì có thể bị chặn. */
export function useStored<T>(key: string, init: T): [T, (v: T) => void] {
  const [v, setV] = useState<T>(init);
  useEffect(() => {
    try { const s = localStorage.getItem(key); if (s) setV(JSON.parse(s)); } catch { /* bỏ qua */ }
  }, [key]);
  const set = (x: T) => { setV(x); try { localStorage.setItem(key, JSON.stringify(x)); } catch { /* bỏ qua */ } };
  return [v, set];
}

// ---------- phân quyền: cùng quy tắc với src/policy.py ----------
export type Plan = {
  action: string; actionName: string; actionDesc: string; ttl: number | null; reversible: boolean;
  executor: string; approver: string | null; approverRole: Role | null; ai: "suggest" | "act_on_timeout"; aiText: string;
};
export function planFor(p: Policy, level: Level, targetRole?: string): Plan {
  const lv = p.levels[level];
  const act = p.actions[lv.action];
  const protectedTarget = !!targetRole && p.ai.protected_roles.includes(targetRole);
  const ai = p.ai.forbidden_actions.includes(lv.action) || protectedTarget ? "suggest" : lv.ai;
  let aiText = ai === "suggest" ? "Chỉ đề xuất" : `Được tự thực hiện nếu sau ${p.ai.timeout_min} phút chưa ai duyệt`;
  if (protectedTarget && lv.ai !== "suggest") aiText += " (máy đích là hạ tầng nên chỉ đề xuất)";
  return {
    action: lv.action, actionName: act.name, actionDesc: act.desc, ttl: lv.ttl, reversible: act.reversible,
    executor: p.roles[lv.executor].name, approver: lv.approver ? p.roles[lv.approver].name : null,
    approverRole: lv.approver, ai, aiText,
  };
}
const RANK: Record<Role, number> = { system: 0, ai: 0, analyst: 1, lead: 2 };
export function canDecide(p: Policy, level: Level, actor: Role): [boolean, string] {
  const lv = p.levels[level];
  const need = lv.approver ?? lv.executor;
  if (need === "system") return [false, "Mức này do hệ thống tự xử lý theo luật"];
  return RANK[actor] >= RANK[need] ? [true, ""] : [false, `Cần ${p.roles[need].name} duyệt`];
}

// ---------- định dạng ----------
export const nf = (x: number) => x.toLocaleString("vi-VN");
export const num = (x: number, d = 3) => x.toFixed(d).replace(".", ",");
export const pct = (x: number | null | undefined) => (x === null || x === undefined ? "–" : `${(100 * x).toFixed(1).replace(".", ",")}%`);
export const hm = (t: number) => new Date(t * 1000).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
export const utc = (ms: number) => new Date(ms).toISOString().replace("T", " ").slice(0, 19);
export const big = (x: number) => (Math.abs(x) >= 1000 ? Math.round(x).toLocaleString("vi-VN") : num(x, Number.isInteger(x) ? 0 : 2));
export const PROTO: Record<number, string> = { 1: "ICMP", 6: "TCP", 17: "UDP" };
export const TACTIC: Record<string, string> = {
  impact: "Impact", credential_access: "Credential Access", initial_access: "Initial Access", discovery: "Discovery",
  unknown: "Chưa xác định", benign: "Bình thường",
};
export const TIER: Record<number, string> = { 1: "Tấn công đã biết", 2: "Biến thể của chiến thuật đã biết", 3: "Hành vi hoàn toàn mới" };
export const attackUrl = (t: string) => `https://attack.mitre.org/techniques/${t.replace(".", "/")}/`;
export const d3fendByName = (m: string) =>
  /tự đề xuất|có thời hạn|bằng chứng/.test(m) ? null : `https://d3fend.mitre.org/technique/d3f:${m.replace(/[^A-Za-z]/g, "")}/`;
