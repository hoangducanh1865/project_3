"use client";

import { Bot, CheckCircle2, FileSearch, Search, ShieldQuestion } from "lucide-react";
import { useMemo, useState } from "react";
import type { Ctx } from "../ctx";
import type { Incident } from "../lib";
import { attackUrl, big, canDecide, d3fendByName, hm, num, planFor, PROTO, TACTIC, TIER, utc } from "../lib";
import { Chip, Ext, KV, LevelBadge, Panel, Segmented } from "../ui";

type Filter = "pending" | "open" | "all";

export default function Incidents({ ctx }: { ctx: Ctx }) {
  const [filter, setFilter] = useState<Filter>("open");
  const [q, setQ] = useState("");
  const list = useMemo(() => ctx.incidents.filter((i) => {
    if (filter === "open" && i.status !== "open") return false;
    if (filter === "pending" && !ctx.stateOf(i).pending) return false;
    const text = `${i.src} ${i.dst} ${ctx.nameOf(i.src)} ${ctx.nameOf(i.dst)} ${ctx.famName(i.family)} ${i.level}`.toLowerCase();
    return !q || text.includes(q.toLowerCase());
  }), [ctx, filter, q]);
  const current = ctx.incidents.find((i) => i.id === ctx.selected) ?? null;
  const counts = {
    pending: ctx.incidents.filter((i) => ctx.stateOf(i).pending).length,
    open: ctx.incidents.filter((i) => i.status === "open").length, all: ctx.incidents.length,
  };
  return (
    <>
      <div className="page-head">
        <div><h1>Sự cố</h1><p>Một sự cố mở khi một cặp nguồn, đích có từ 5 cảnh báo trong 5 phút và tỉ lệ cảnh báo từ 30%.</p></div>
      </div>
      <div className="split">
        <Panel flush title="Hàng đợi" actions={
          <div className="toolbar">
            <label className="search"><Search size={14} aria-hidden="true" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="IP, thiết bị, họ tấn công" /></label>
            <Segmented value={filter} onChange={setFilter}
              options={[["pending", "Chờ duyệt", counts.pending], ["open", "Đang mở", counts.open], ["all", "Tất cả", counts.all]]} />
          </div>}>
          <div className="scroll tall">
            <table className="table">
              <thead><tr><th>Mức</th><th>Mở lúc</th><th>Nguồn</th><th>Đích</th><th>Phân loại</th><th className="r">Cảnh báo</th><th>Xử lý</th></tr></thead>
              <tbody>
                {list.map((i) => {
                  const st = ctx.stateOf(i);
                  return (
                    <tr key={i.id} tabIndex={0} aria-selected={i.id === ctx.selected} onClick={() => ctx.setSelected(i.id)}
                      onKeyDown={(e) => { if (e.key === "Enter") ctx.setSelected(i.id); }}>
                      <td><LevelBadge level={i.level} /></td>
                      <td className="mono">{hm(i.opened)}</td>
                      <td><span className="mono">{i.src}</span><small>{ctx.nameOf(i.src)}</small></td>
                      <td><span className="mono">{i.dst}</span><small>{ctx.nameOf(i.dst)}</small></td>
                      <td>{ctx.famName(i.family)} {i.sim && <Chip tone="strong">diễn tập</Chip>}<small>Tầng {i.tier} · {TACTIC[i.tactic] ?? i.tactic}</small></td>
                      <td className="r mono">{i.alerts}/{i.flows}</td>
                      <td className={st.pending ? "wait" : "muted"}>{st.text}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {list.length === 0 && <p className="empty">Không có sự cố trong mục này.</p>}
          </div>
        </Panel>
        <div className="detail">{current ? <Detail ctx={ctx} inc={current} /> : <Panel><p className="empty">Chọn một sự cố để xem kế hoạch ứng phó và bằng chứng.</p></Panel>}</div>
      </div>
    </>
  );
}

function Detail({ ctx, inc }: { ctx: Ctx; inc: Incident }) {
  const fam = ctx.labels?.families[inc.family];
  const plan = ctx.policy ? planFor(ctx.policy, inc.level, ctx.roleOf(inc.dst)) : null;
  const [ok, why] = ctx.policy ? canDecide(ctx.policy, inc.level, ctx.role) : [false, ""];
  const st = ctx.stateOf(inc);
  const dec = ctx.decisions[inc.id];
  const truth = Object.keys(inc.truth ?? {});
  const d3name = (id: string) => {
    for (const groups of Object.values(fam?.d3fend ?? {})) for (const items of Object.values(groups)) {
      const hit = items.find(([x]) => x === id); if (hit) return hit[1];
    }
    return id;
  };
  return (
    <>
      <Panel>
        <div className="d-head"><LevelBadge level={inc.level} /><div><h3>{ctx.famName(inc.family)} {inc.sim && <Chip tone="strong">diễn tập</Chip>}</h3>
          <p>{TIER[inc.tier]} · {TACTIC[inc.tactic] ?? inc.tactic}</p></div></div>
        {inc.sim && <p className="fine">Sự cố diễn tập: flow tấn công thật chưa dùng khi huấn luyện, điểm do HC-CLOSR chấm sẵn; bạn phát động từ trang Diễn tập tấn công.</p>}
        <KV rows={[
          ["Kết nối", <span key="k"><span className="mono">{inc.src}</span> {ctx.nameOf(inc.src)} → <span className="mono">{inc.dst}</span> {ctx.nameOf(inc.dst)}</span>],
          ["Thời gian", `${hm(inc.opened)} đến ${hm(inc.last)}${inc.status === "closed" ? ", đã đóng" : ""}`],
          ["Cảnh báo", `${inc.alerts} trên ${inc.flows} flow`],
          ["ATT&CK", fam?.attack.length ? <span key="a">{fam.attack.map((t) => <Ext key={t.id} href={attackUrl(t.id)}>{t.id} {t.name}</Ext>)}</span> : "Không có kỹ thuật tương ứng"],
          ["Nhãn đối chiếu", truth.length ? truth.map(ctx.famName).join(", ") : "Bình thường: đây là báo nhầm"],
        ]} />
        <p className="fine">Nhãn đối chiếu là nhãn đã gán lại của các flow, chỉ để kiểm tra; mô hình không dùng.</p>
      </Panel>

      <Panel title="Kế hoạch ứng phó" sub={`R = L × I = ${inc.L} × ${inc.I} = ${inc.R}`}>
        {plan && <>
          <div className="plan">
            <div><span>Hành động</span><strong>{plan.actionName}</strong><small>{plan.actionDesc}</small></div>
            <div><span>Thời hạn</span><strong>{plan.ttl ? `${plan.ttl} phút` : "Không giới hạn"}</strong><small>{plan.reversible ? "Đảo ngược được" : "Khó đảo ngược"}</small></div>
            <div><span>Người duyệt</span><strong>{plan.approver ?? "Không cần"}</strong><small>Thực hiện: {plan.executor}</small></div>
          </div>
          <p className="perm"><Bot size={14} aria-hidden="true" /> Trợ lý AI: {plan.aiText.toLowerCase()}.</p>
        </>}
        <h4>Biện pháp D3FEND</h4>
        <div className="chips">{inc.d3fend_now.map((m) => <Ext key={m} href={d3fendByName(m)}><Chip>{m}</Chip></Ext>)}</div>
        {inc.d3fend_later.length > 0 && <><h4>Củng cố sau</h4>
          <div className="chips">{inc.d3fend_later.map((m) => <Ext key={m} href={d3fendByName(m)}><Chip tone="muted">{m}</Chip></Ext>)}</div></>}
        <div className="decide">
          <span className={st.pending ? "wait" : "muted"}>{dec ? `${st.text}, ${st.by}` : st.text}</span>
          {dec ? <button onClick={() => ctx.decide(inc.id, null)}>Hoàn tác</button> : plan?.approver && inc.status === "open" && (
            ok ? <><button className="primary" onClick={() => ctx.decide(inc.id, "approved")}><CheckCircle2 size={14} aria-hidden="true" />Duyệt</button>
              <button onClick={() => ctx.decide(inc.id, "rejected")}>Từ chối</button></>
              : <span className="lock"><ShieldQuestion size={14} aria-hidden="true" />{why}. Đổi vai trò ở góc trên.</span>)}
        </div>
      </Panel>

      {fam?.ai && (
        <Panel title="Trợ lý AI" sub={`${fam.ai.model}, đọc tài liệu nhãn ATT&CK v${fam.ai.attack_version}; chỉ đề xuất`}>
          {inc.tier === 3 && <p className="fine">Tầng 3: hành vi mới, nhận định dưới đây là của họ gần nhất và chỉ để tham khảo.</p>}
          <p>{fam.ai.summary}</p>
          <h4>Cần kiểm tra</h4>
          <ul className="list">{fam.ai.check.map((c) => <li key={c}>{c}</li>)}</ul>
          {fam.ai.recommend.length > 0 ? <><h4>Đề xuất</h4>
            <ul className="list">{fam.ai.recommend.map((r) => <li key={r.d3fend}>
              <Ext href={d3fendByName(d3name(r.d3fend))}>{d3name(r.d3fend)} ({r.d3fend})</Ext>: {r.why}</li>)}</ul></>
            : <p className="fine">D3FEND chưa có biện pháp cho kỹ thuật này; AI không đề xuất.</p>}
          <p className="fine">Nguồn đã truy xuất: {fam.ai.retrieved.join(", ")}. Trích dẫn: {fam.ai.cites.join(", ") || "không"}.</p>
        </Panel>
      )}

      <Evidence inc={inc} thr={ctx.card?.model.threshold.value} />
    </>
  );
}

function Evidence({ inc, thr }: { inc: Incident; thr?: number }) {
  const ev = inc.evidence ?? [];
  if (!ev.length) return null;
  const t0 = Math.min(...ev.map((e) => e.t0)), t1 = Math.max(...ev.map((e) => e.t1));
  const filter = `ip.addr==${inc.src} && ip.addr==${inc.dst} && frame.time_epoch>=${(t0 / 1000).toFixed(3)} && frame.time_epoch<=${(t1 / 1000 + 0.001).toFixed(3)}`;
  return (
    <Panel title="Bằng chứng kỹ thuật" sub={`${ev.length} flow bị cảnh báo gần nhất`}>
      <div className="scroll">
        <table className="table compact">
          <thead><tr><th>Thời điểm gốc (UTC)</th><th>Cổng</th><th className="r">Gói</th><th className="r">Byte</th><th className="r">ms</th><th className="r">SYN/RST/FIN</th><th className="r">Điểm OOD</th></tr></thead>
          <tbody>{ev.map((e, k) => (
            <tr key={k}><td className="mono">{utc(e.t0)}</td><td className="mono">{PROTO[e.proto] ?? e.proto} {e.sport}→{e.dport}</td>
              <td className="r mono">{big(e.feat.bidirectional_packets)}</td><td className="r mono">{big(e.feat.bidirectional_bytes)}</td>
              <td className="r mono">{big(e.feat.bidirectional_duration_ms)}</td>
              <td className="r mono">{e.feat.bidirectional_syn_packets}/{e.feat.bidirectional_rst_packets}/{e.feat.bidirectional_fin_packets}</td>
              <td className="r mono">{num(e.score, 2)}</td></tr>))}
          </tbody>
        </table>
      </div>
      {thr !== undefined && <p className="fine">Ngưỡng điểm OOD {num(thr)}: phân vị 95 trên flow đã biết ở tập val.</p>}
      <h4>Đặc trưng lệch nhiều nhất so với flow bình thường</h4>
      <ul className="list">{ev[0].top.map((t) => (
        <li key={t.name}><code>{t.name}</code> = {big(t.value)}, trung vị bình thường {big(t.median)}, lệch {num(t.z, 1)} IQR</li>))}</ul>
      <h4><FileSearch size={14} aria-hidden="true" /> Kiểm chứng trên gói tin gốc</h4>
      <p className="fine">Mở tệp PCAP của DataSense bằng Wireshark và dán bộ lọc:</p>
      <code className="code">{(inc.files ?? []).map((f) => `${f}.pcap`).join(", ")}</code>
      <code className="code">{filter}</code>
    </Panel>
  );
}
