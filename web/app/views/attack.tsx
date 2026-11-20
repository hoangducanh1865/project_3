"use client";

import { Crosshair, Info, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import type { Ctx } from "../ctx";
import type { AttackScenario } from "../lib";
import { num, planFor, TACTIC, TIER } from "../lib";
import { Chip, KV, LevelBadge, Panel, Stat } from "../ui";

function meanScore(s: AttackScenario) {
  const ev = s.incident.evidence ?? [];
  return ev.length ? ev.reduce((a, e) => a + e.score, 0) / ev.length : 0;
}

export default function AttackConsole({ ctx }: { ctx: Ctx }) {
  const a = ctx.attacks;
  const devices = ctx.sources?.devices ?? ctx.card?.devices ?? [];
  const targets = useMemo(() => devices.filter((d) => d.role !== "attacker"), [devices]);
  const [famIdx, setFamIdx] = useState(0);
  const [dstIp, setDstIp] = useState("");
  if (!a || !ctx.policy) return <p className="empty">Đang tải...</p>;

  const scenarios = a.scenarios;
  const sc = scenarios[Math.min(famIdx, scenarios.length - 1)];
  const defDst = devices.some((d) => d.ip === sc.dst_ip) ? sc.dst_ip : targets[0]?.ip ?? sc.dst_ip;
  const target = dstIp || defDst;
  const plan = planFor(ctx.policy, sc.incident.level, ctx.roleOf(target));
  const thr = ctx.card?.model.threshold.value;
  const sims = ctx.incidents.filter((i) => i.sim);

  return (
    <>
      <div className="page-head">
        <div><h1>Diễn tập tấn công</h1>
          <p>Chọn một loại tấn công và máy mục tiêu rồi phát động để xem HC-CLOSR phát hiện và đề xuất ứng phó ngay trên luồng.</p></div>
        {sims.length > 0 && <button onClick={ctx.clearSim}><Trash2 size={14} aria-hidden="true" /> Xoá {sims.length} sự cố diễn tập</button>}
      </div>

      <Panel>
        <p className="perm"><Info size={14} aria-hidden="true" /> {a.note}</p>
      </Panel>

      <div className="split">
        <Panel flush title="Chọn loại tấn công" sub={`${scenarios.length} họ có flow trong kho phát lại`}>
          <div className="scroll tall">
            <div className="atk-grid">
              {scenarios.map((s, i) => (
                <button key={s.family} className={`atk-opt ${i === famIdx ? "on" : ""}`} onClick={() => { setFamIdx(i); setDstIp(""); }}>
                  <span className="atk-name">{ctx.famName(s.family)}</span>
                  <span className="atk-meta">
                    <LevelBadge level={s.incident.level} />
                    <Chip tone={s.known ? "muted" : "strong"}>{s.known ? `Tầng ${s.incident.tier}` : "OOD, bị giấu"}</Chip>
                  </span>
                </button>
              ))}
            </div>
          </div>
        </Panel>

        <div className="detail">
          <Panel title={ctx.famName(sc.family)} sub={sc.known ? "Họ có trong tập huấn luyện" : `Họ bị giấu khi huấn luyện (OOD): ${a.heldout}`}>
            <div className="tgt">
              <span>Máy mục tiêu</span>
              <select value={target} onChange={(e) => setDstIp(e.target.value)} aria-label="Máy mục tiêu">
                {targets.map((d) => <option key={d.ip} value={d.ip}>{d.device_name} · {d.ip} ({d.role})</option>)}
              </select>
              <small>Nguồn: máy tấn công {sc.src_ip} · tệp PCAP gốc {sc.file}</small>
            </div>
            <button className="primary big" onClick={() => ctx.launch(sc, target)}>
              <Crosshair size={16} aria-hidden="true" /> Phát động tấn công
            </button>
          </Panel>

          <section className="stats">
            <Stat label="Phân loại" value={<LevelBadge level={sc.incident.level} />} hint={`${TIER[sc.incident.tier]}`} />
            <Stat label="Chiến thuật" value={TACTIC[sc.incident.tactic] ?? sc.incident.tactic} hint={`R = L×I = ${sc.incident.L}×${sc.incident.I} = ${sc.incident.R}`} />
            <Stat label="Điểm OOD trung bình" value={num(meanScore(sc), 2)} hint={thr !== undefined ? `ngưỡng ${num(thr)}` : undefined} />
            <Stat label="Cảnh báo" value={`${sc.incident.alerts}/${sc.incident.flows}`} hint="flow bị cảnh báo" />
          </section>

          <Panel title="Ứng phó nếu phát động vào máy này">
            <KV rows={[
              ["Hành động", `${plan.actionName}${plan.ttl ? ` (${plan.ttl} phút)` : ""}`],
              ["Người duyệt", plan.approver ?? "Không cần, hệ thống tự xử lý"],
              ["Trợ lý AI", plan.aiText],
            ]} />
            <p className="fine">Đổi máy mục tiêu để thấy cùng một tấn công nhưng được xử lý khác nhau: tấn công vào hạ tầng (router, máy chủ MQTT, edge) thì AI chỉ được đề xuất.</p>
          </Panel>
        </div>
      </div>
    </>
  );
}
