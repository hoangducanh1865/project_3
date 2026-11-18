"use client";

import type { Card } from "../lib";
import { nf, num, pct } from "../lib";
import { KV, Panel, Stat } from "../ui";

export default function Model({ card }: { card: Card | null }) {
  if (!card?.dataset) return <p className="empty">Đang tải...</p>;
  const { dataset: d, relabel: r, model: m } = card;
  const att = r.table.filter((x) => x.category !== "benign");
  const inAtt = att.reduce((a, x) => a + x.flows, 0), fixed = att.reduce((a, x) => a + x.benign + x.dropped, 0);
  return (
    <>
      <div className="page-head">
        <div><h1>Dữ liệu và mô hình</h1><p>Mọi số trên trang sinh tự động khi dựng kho dữ liệu, phiên bản {card.version}.</p></div>
      </div>
      <section className="stats">
        <Stat label="AUROC, họ bị giấu" value={m.metrics.auroc != null ? num(m.metrics.auroc) : "–"} hint={`OOD: ${m.heldout}`} />
        <Stat label="Phát hiện tại ngưỡng" value={pct(m.metrics.det_rate)} />
        <Stat label="Flow đã biết bị coi là OOD" value={pct(m.metrics.fpr_thr)} />
        <Stat label="Nhãn gốc sai hoặc không rõ" value={pct(fixed / Math.max(1, inAtt))} hint="trong các tệp tấn công" />
      </section>
      <div className="grid-2">
        <Panel title="Nguồn dữ liệu">
          <KV rows={[
            ["Bộ dữ liệu", <a key="u" href={d.url} target="_blank" rel="noreferrer">{d.name}</a>],
            ["Bài báo", d.paper], ["Thời gian thu", `${d.captured[0]} đến ${d.captured[1]}`],
            ["Mạng thử nghiệm", `${d.devices} thiết bị, ${d.attackers} máy tấn công`],
            ["Trích flow", `Tự trích từ PCAP gốc bằng ${d.extractor}`], ["Số flow sau gán nhãn", nf(d.flows)],
          ]} />
        </Panel>
        <Panel title="Mô hình đang chạy">
          <KV rows={[
            ["Mô hình", `${m.name}, huấn luyện ${m.trained}`], ["Họ bị giấu khi huấn luyện", m.heldout],
            ["Đầu vào", `${m.n_features} đặc trưng thống kê của flow; không dùng IP, MAC, cổng, thời điểm`],
            ["Ngưỡng cảnh báo", `${num(m.threshold.value)}: ${m.threshold.meaning}`],
            ["Cách tách dữ liệu", m.split ?? "Ngẫu nhiên theo flow (bản cũ)"],
          ]} />
        </Panel>
      </div>
      <Panel title="Gán nhãn lại" sub="Bản gốc gán nhãn theo cả tệp; đề tài gán theo từng flow dựa trên danh mục thiết bị và nhật ký tấn công">
        <ol className="list">{r.rules.map((x) => <li key={x}>{x}</li>)}</ol>
        <div className="scroll">
          <table className="table">
            <thead><tr><th>Nhóm tệp</th><th className="r">Tệp</th><th className="r">Flow</th><th className="r">Tấn công</th><th className="r">Thực ra bình thường</th><th className="r">Không rõ, bỏ</th></tr></thead>
            <tbody>{r.table.map((x) => (
              <tr key={x.category}><td>{x.category}</td><td className="r mono">{nf(x.files)}</td><td className="r mono">{nf(x.flows)}</td>
                <td className="r mono">{nf(x.attack)}</td><td className="r mono">{nf(x.benign)}</td><td className="r mono">{nf(x.dropped)}</td></tr>))}</tbody>
          </table>
        </div>
      </Panel>
      <Panel title="Đặc trưng đầu vào" sub="Tên theo NFStream: ps là kích thước gói, piat là khoảng cách giữa hai gói">
        <div className="chips">{m.features.map((f) => <code key={f} className="chip">{f}</code>)}</div>
      </Panel>
    </>
  );
}
