"use client";

import type { Ctx } from "../ctx";
import type { Live } from "../lib";
import { hm, nf, pct, TACTIC } from "../lib";
import { AlertChart, LevelBadge, Panel, Stat, Topology } from "../ui";

export default function Overview({ ctx, live }: { ctx: Ctx; live: Live | null }) {
  const s = live?.summary;
  const open = ctx.incidents.filter((i) => i.status === "open");
  const pending = ctx.incidents.filter((i) => ctx.stateOf(i).pending);
  const devices = ctx.sources?.devices ?? ctx.card?.devices ?? [];
  const links = open.map((i) => ({ id: i.id, src: i.src, dst: i.dst, on: false }));
  return (
    <>
      <div className="page-head">
        <div><h1>Tổng quan</h1><p>Mạng IIoT 45 thiết bị của DataSense. Mỗi phút phát lại flow thật chưa dùng để huấn luyện, phân tích bằng HC-CLOSR.</p></div>
      </div>
      <section className="stats">
        <Stat label="Flow trong 60 phút" value={s ? nf(s.flows_60m) : undefined} />
        <Stat label="Flow bị cảnh báo" value={s ? pct(s.alerts_60m / Math.max(1, s.flows_60m)) : undefined} hint={s ? `${nf(s.alerts_60m)} flow` : undefined} />
        <Stat label="Sự cố đang mở" value={s ? open.length : undefined} />
        <Stat label="Chờ người duyệt" value={s ? pending.length : undefined} hint={`với vai trò ${ctx.policy?.roles[ctx.role].name ?? ""}`} />
        <Stat label="Chiến dịch phát hiện" value={s ? `${s.campaigns_found}/${s.campaigns_done}` : undefined} hint="từ đầu vòng phát lại" />
        <Stat label="Sự cố báo nhầm" value={s ? pct(s.false_24h / Math.max(1, s.incidents_24h)) : undefined} hint={s ? `${s.false_24h}/${s.incidents_24h} sự cố` : undefined} />
      </section>
      <div className="grid-2">
        <Panel title="Lưu lượng và cảnh báo" sub="Mỗi cột là một phút">
          {live && live.series.length > 0 ? <AlertChart points={live.series} /> : <p className="empty">Đang tải...</p>}
        </Panel>
        <Panel title="Sự cố mới nhất" flush actions={<button className="link" onClick={() => ctx.go("incidents")}>Xem tất cả</button>}>
          <ul className="feed">
            {ctx.incidents.slice(0, 7).map((i) => {
              const st = ctx.stateOf(i);
              return (
                <li key={i.id}>
                  <button onClick={() => ctx.go("incidents", i.id)}>
                    <LevelBadge level={i.level} />
                    <span className="feed-main"><b>{ctx.famName(i.family)}</b>
                      <small>{ctx.nameOf(i.src)} → {ctx.nameOf(i.dst)} · {TACTIC[i.tactic] ?? i.tactic}</small></span>
                    <span className="feed-side"><small>{hm(i.opened)}</small><small className={st.pending ? "wait" : ""}>{st.text}</small></span>
                  </button>
                </li>
              );
            })}
          </ul>
          {ctx.incidents.length === 0 && <p className="empty">Chưa có sự cố.</p>}
        </Panel>
      </div>
      <Panel title="Sơ đồ mạng" sub="Đường nối là các sự cố đang mở; bấm vào đường để xem chi tiết">
        <Topology devices={devices} links={links} onPick={(id) => ctx.go("incidents", id)} />
      </Panel>
    </>
  );
}
