"use client";

import { CircleCheck, Clock, ShieldAlert } from "lucide-react";
import type { ReactNode } from "react";
import { APPROVAL } from "./labels";

export function LevelBadge({ level }: { level: string }) {
  return <span className={`level ${level}`}>{level}</span>;
}

export function Stat({ value, label, emph }: { value?: ReactNode; label: string; emph?: boolean }) {
  return (
    <div className={emph ? "stat emph" : "stat"}>
      <span>{label}</span>
      {value === undefined ? <i className="skeleton" /> : <strong>{value}</strong>}
    </div>
  );
}

/** Trạng thái xử lý của một cảnh báo hoặc sự cố: chữ đi kèm biểu tượng, không dựa vào màu. */
export function StateText({ text }: { text: string }) {
  const Icon = text.startsWith("Chờ") ? ShieldAlert : text.startsWith("Đã đóng") ? Clock : CircleCheck;
  return <span className={text.startsWith("Chờ") ? "state wait" : "state"}><Icon size={14} aria-hidden="true" />{text}</span>;
}

type Plan = {
  level: string; action: string; reversible: boolean; mode: string; L: number; I: number; R: number;
  d3fend_now: string[]; d3fend_later: string[];
};

/** Khối thông tin chung của một cảnh báo: dữ kiện, rủi ro, hành động và biện pháp D3FEND. */
export function ResponsePanel({ title, plan, facts, note, footer }: {
  title: string; plan: Plan; facts: [string, ReactNode][]; note?: ReactNode; footer?: ReactNode;
}) {
  const [name, ...rest] = plan.action.split(": ").map((x) => x[0].toUpperCase() + x.slice(1));
  return (
    <>
      <div className="detail-head">
        <LevelBadge level={plan.level} />
        <h3>{title}</h3>
      </div>
      <dl>{facts.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>

      <div className="risk" aria-label={`Rủi ro R bằng L nhân I, ${plan.L} nhân ${plan.I} bằng ${plan.R}`}>
        <div><span>Khả năng (L)</span><strong>{plan.L}</strong></div>
        <i aria-hidden="true">×</i>
        <div><span>Tác động (I)</span><strong>{plan.I}</strong></div>
        <i aria-hidden="true">=</i>
        <div><span>Rủi ro (R)</span><strong>{plan.R}</strong></div>
      </div>

      <div className="callout">
        <span>Hành động đề xuất</span>
        <strong>{name}</strong>
        <p>{rest.join(": ")}</p>
        <small>{plan.reversible ? "Đảo ngược được" : "Khó đảo ngược"} · Thực hiện: {plan.mode}</small>
      </div>

      <h4>Biện pháp ngay (D3FEND)</h4>
      <ul>{plan.d3fend_now.map((m) => <li key={m}>{m}</li>)}</ul>
      {plan.d3fend_later.length > 0 && (
        <>
          <h4>Củng cố sau</h4>
          <ul>{plan.d3fend_later.map((m) => <li key={m}>{m}</li>)}</ul>
        </>
      )}
      {note && <p className="note">{note}</p>}
      {plan.mode === APPROVAL && footer && <div className="decision" data-tour="decision">{footer}</div>}
    </>
  );
}
