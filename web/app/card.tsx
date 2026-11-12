"use client";

import { useEffect, useState } from "react";
import { famName, FAMILY, attackUrl, num } from "./labels";
import type { Device } from "./topology";

type Row = { category: string; files: number; flows: number; attack: number; benign: number; dropped: number };
export type Card = {
  version: string;
  dataset: { name: string; url: string; paper: string; captured: [string, string]; devices: number; attackers: number;
    flows: number; classes: Record<string, number>; extractor: string };
  relabel: { rules: string[]; table: Row[] };
  model: { name: string; heldout: string; trained: string; classes: string[]; n_features: number; features: string[];
    metrics: Record<string, number | null>; threshold: { quantile: number; value: number; meaning: string };
    tactics: Record<string, string> };
  devices: Device[];
};

const pct = (x: number | null | undefined) => (x === null || x === undefined ? "–" : `${(100 * x).toFixed(1).replace(".", ",")}%`);
const n = (x: number) => x.toLocaleString("vi-VN");

export function useCard() {
  const [card, setCard] = useState<Card | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    fetch("/api/card").then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Máy chủ trả lỗi ${r.status}.`))))
      .then(setCard).catch((e) => setError(e.message));
  }, []);
  return { card, error };
}

export default function CardPage({ card, error }: { card: Card | null; error: string }) {
  if (error) return <main><p className="error">{error}</p></main>;
  if (!card?.dataset) return <main><p className="empty">Đang tải...</p></main>;
  const { dataset: d, relabel: r, model: m } = card;
  const tot = r.table.reduce((a, x) => ({ flows: a.flows + x.flows, benign: a.benign + x.benign, dropped: a.dropped + x.dropped }),
    { flows: 0, benign: 0, dropped: 0 });
  const attackRows = r.table.filter((x) => x.category !== "benign");
  const inAttack = attackRows.reduce((a, x) => a + x.flows, 0);
  const fixed = attackRows.reduce((a, x) => a + x.benign + x.dropped, 0);
  return (
    <main className="doc">
      <div className="page-head"><div><h1>Dữ liệu và mô hình</h1>
        <p>Mọi số trên trang này sinh tự động khi dựng kho dữ liệu, phiên bản {card.version}</p></div></div>

      <section className="card">
        <h2>1. Nguồn dữ liệu</h2>
        <table><tbody>
          <tr><td>Bộ dữ liệu</td><td><a href={d.url} target="_blank" rel="noreferrer">{d.name}</a></td></tr>
          <tr><td>Bài báo</td><td>{d.paper}</td></tr>
          <tr><td>Thời gian thu</td><td>{d.captured[0]} đến {d.captured[1]}</td></tr>
          <tr><td>Mạng thử nghiệm</td><td>{d.devices} thiết bị, trong đó {d.attackers} máy tấn công (xem sơ đồ ở trang Giám sát)</td></tr>
          <tr><td>Trích flow</td><td>Tự trích từ PCAP gốc bằng {d.extractor}, không dùng file CSV có sẵn</td></tr>
          <tr><td>Số flow sau gán nhãn</td><td>{n(d.flows)}</td></tr>
        </tbody></table>
      </section>

      <section className="card">
        <h2>2. Gán nhãn lại</h2>
        <p>Bản gốc gán nhãn theo cả tệp PCAP, nên lưu lượng bình thường của thiết bị trong lúc bị tấn công cũng mang nhãn
          tấn công. Đề tài gán nhãn từng flow theo danh mục thiết bị (IP, MAC) và nhật ký tấn công (mục tiêu, thời điểm
          bắt đầu, kết thúc) công bố kèm bộ dữ liệu:</p>
        <ol>{r.rules.map((x) => <li key={x}>{x}</li>)}</ol>
        <p style={{ marginTop: 10 }}>Trong các tệp tấn công, <b>{n(fixed)}</b> trên {n(inAttack)} flow ({pct(fixed / inAttack)}) mang nhãn tấn công
          theo bản gốc nhưng thực ra là lưu lượng nền hoặc không rõ nguồn.</p>
        <div className="scroll" style={{ maxHeight: 360 }}>
          <table>
            <thead><tr><th>Nhóm tệp</th><th className="right">Số tệp</th><th className="right">Flow</th><th className="right">Tấn công</th>
              <th className="right">Bình thường (sửa nhãn)</th><th className="right">Bỏ (không rõ)</th></tr></thead>
            <tbody>
              {r.table.map((x) => (
                <tr key={x.category}><td>{x.category}</td><td className="num right">{n(x.files)}</td><td className="num right">{n(x.flows)}</td>
                  <td className="num right">{n(x.attack)}</td><td className="num right">{n(x.benign)}</td><td className="num right">{n(x.dropped)}</td></tr>
              ))}
              <tr><td><b>Tổng</b></td><td /><td className="num right">{n(tot.flows)}</td><td /><td className="num right">{n(tot.benign)}</td>
                <td className="num right">{n(tot.dropped)}</td></tr>
            </tbody>
          </table>
        </div>
        <p className="muted">Mỗi tệp chỉ giữ ngẫu nhiên tối đa 3.000 flow tấn công và 1.500 flow nền; tệp ngập lụt chỉ đọc 3 triệu gói đầu.</p>
      </section>

      <section className="card">
        <h2>3. Mô hình đang chạy</h2>
        <table><tbody>
          <tr><td>Mô hình</td><td>{m.name}, huấn luyện ngày {m.trained}</td></tr>
          <tr><td>Họ bị giấu khi huấn luyện (OOD)</td><td>{famName(m.heldout)}</td></tr>
          <tr><td>Họ đã học</td><td><div className="chips">{m.classes.map((c) => <code key={c}>{famName(c)}</code>)}</div></td></tr>
          <tr><td>Đầu vào</td><td>{m.n_features} đặc trưng thống kê của flow; không dùng IP, cổng, MAC, thời điểm</td></tr>
          <tr><td>Ngưỡng cảnh báo</td><td>{num(m.threshold.value)}: {m.threshold.meaning}</td></tr>
        </tbody></table>
        <h2 style={{ marginTop: 14 }}>Chỉ số trên tập kiểm thử (flow chưa dùng để huấn luyện)</h2>
        <table><tbody>
          <tr><td>AUROC phân biệt flow đã biết và họ bị giấu</td><td className="num">{m.metrics.auroc === null || m.metrics.auroc === undefined ? "–" : num(m.metrics.auroc)}</td></tr>
          <tr><td>Tỉ lệ phát hiện họ bị giấu tại ngưỡng</td><td className="num">{pct(m.metrics.det_rate)}</td></tr>
          <tr><td>Tỉ lệ flow đã biết bị coi là OOD tại ngưỡng</td><td className="num">{pct(m.metrics.fpr_thr)}</td></tr>
          <tr><td>Độ chính xác phân loại họ đã biết</td><td className="num">{pct(m.metrics.acc)}</td></tr>
        </tbody></table>
        <p className="muted">Ngưỡng và chỉ số tính trên phép tách cố định (50% kiểm thử, 5% val); kho flow phát lại trên web chỉ gồm phần kiểm thử.</p>
      </section>

      <section className="card">
        <h2>4. Họ tấn công và kỹ thuật ATT&amp;CK</h2>
        <table>
          <thead><tr><th>Họ</th><th className="right">Số flow</th><th>Chiến thuật</th><th>Kỹ thuật gần nhất</th></tr></thead>
          <tbody>{Object.entries(d.classes).sort((a, b) => b[1] - a[1]).map(([c, k]) => (
            <tr key={c}><td>{famName(c)}</td><td className="num right">{n(k)}</td><td>{m.tactics[c] ?? (c === "benign" ? "" : "–")}</td>
              <td>{FAMILY[c]?.[1] ? <a href={attackUrl(FAMILY[c][1])} target="_blank" rel="noreferrer">{FAMILY[c][1]}</a> : ""}</td></tr>
          ))}</tbody>
        </table>
        <p className="muted">Bảng ánh xạ họ sang kỹ thuật do đề tài lập, chưa đối chiếu chuyên gia.</p>
      </section>

      <section className="card">
        <h2>5. Đặc trưng đầu vào</h2>
        <div className="chips">{m.features.map((f) => <code key={f}>{f}</code>)}</div>
        <p className="muted" style={{ marginTop: 8 }}>Tên theo NFStream: ps là kích thước gói, piat là khoảng cách giữa hai gói, src2dst và dst2src là hai chiều của flow.</p>
      </section>
    </main>
  );
}
