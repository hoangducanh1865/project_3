"use client";

import { useState } from "react";
import type { Ctx } from "../ctx";
import { attackUrl, d3fendByName, nf, TACTIC } from "../lib";
import { Chip, Ext, KV, Panel } from "../ui";

export default function LabelsView({ ctx }: { ctx: Ctx }) {
  const L = ctx.labels;
  const [sel, setSel] = useState("ssh_bruteforce");
  if (!L) return <p className="empty">Đang tải...</p>;
  const issues = L.report.split("\n").filter((l) => l.startsWith("- "));
  const f = L.families[sel];
  return (
    <>
      <div className="page-head">
        <div><h1>Nhãn và tri thức</h1>
          <p>Mỗi nhãn có mô tả hành vi, quy tắc gán nhãn, kỹ thuật ATT&CK và biện pháp D3FEND. Đây cũng là tài liệu mà trợ lý AI truy xuất (RAG).</p></div>
      </div>
      <Panel title="Đối chiếu chuẩn" sub="Chạy lại scripts/check_labels.py mỗi khi ATT&CK ra phiên bản mới">
        <KV rows={[
          ["Phiên bản ATT&CK", <span key="v">Enterprise v{L.attack_version} (bộ STIX chính thức của MITRE)</span>],
          ["Ngày kiểm tra", L.checked],
          ["Nguồn danh mục", <code key="c">conf/labels/datasense.yaml</code>],
          ["Chỗ lệch", issues.length ? <ul className="list" key="i">{issues.map((x) => <li key={x}>{x.slice(2).replaceAll("`", "")}</li>)}</ul> : "Không có"],
        ]} />
      </Panel>
      <div className="split">
        <Panel flush title="Danh mục nhãn">
          <div className="scroll tall">
            <table className="table">
              <thead><tr><th>Nhãn</th><th>Nhóm chiến thuật</th><th>ATT&CK</th><th className="r">Flow</th><th className="r">Tệp</th></tr></thead>
              <tbody>{Object.entries(L.families).map(([k, x]) => (
                <tr key={k} aria-selected={k === sel} onClick={() => setSel(k)}>
                  <td>{x.name}<small className="mono">{k}</small></td><td>{TACTIC[x.tactic] ?? x.tactic}</td>
                  <td className="mono">{x.techniques.join(", ") || "–"}</td>
                  <td className="r mono">{x.stats ? nf(x.stats.flows) : "–"}</td><td className="r mono">{x.stats ? x.stats.files : "–"}</td></tr>))}
              </tbody>
            </table>
          </div>
        </Panel>
        <div className="detail">{f && <>
          <Panel title={f.name} sub={<span className="mono">{sel}</span>}>
            <p>{f.behavior}</p>
            <KV rows={[
              ["Gán nhãn", f.labeling],
              ["Biến thể gốc", f.variants.join(", ")],
              ...(f.note ? [["Ghi chú", f.note] as [string, string]] : []),
              ...(f.stats ? [["Số đo (trung vị)", `${f.stats.median_packets} gói, ${nf(f.stats.median_bytes)} byte, ${f.stats.median_duration_ms} ms; cổng ${f.stats.top_dst_ports.join(", ")}`] as [string, string]] : []),
            ]} />
          </Panel>
          {f.attack.map((t) => (
            <Panel key={t.id} title={`${t.id} ${t.name ?? ""}`} sub={t.tactics ? `Chiến thuật ATT&CK: ${t.tactics.join(", ")} · cập nhật ${t.modified}` : undefined}
              actions={<Ext href={attackUrl(t.id)}>Mở trên ATT&CK</Ext>}>
              {Object.keys(f.d3fend[t.id] ?? {}).length === 0 ? <p className="fine">D3FEND chưa có biện pháp cho kỹ thuật này.</p> :
                Object.entries(f.d3fend[t.id]).map(([g, items]) => (
                  <div key={g} className="d3"><span>{g}</span><div className="chips">
                    {items.map(([id, n]) => <Ext key={id} href={d3fendByName(n)}><Chip>{n}</Chip></Ext>)}</div></div>))}
            </Panel>))}
          {f.ai && <Panel title="Nhận định của trợ lý AI" sub={`${f.ai.model}; nguồn: ${f.ai.retrieved.join(", ")}`}>
            <p>{f.ai.summary}</p>
            {f.ai.recommend.length > 0 && <ul className="list">{f.ai.recommend.map((r) => <li key={r.d3fend}><b>{r.d3fend}</b>: {r.why}</li>)}</ul>}
            <p className="fine">Mã D3FEND không có trong tài liệu truy xuất bị loại tự động ({f.ai.dropped} mã bị loại).</p>
          </Panel>}
        </>}</div>
      </div>
    </>
  );
}
