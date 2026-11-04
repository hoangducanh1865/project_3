"use client";

import Papa from "papaparse";
import { Play, Upload } from "lucide-react";
import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { APPROVAL, num, TACTIC, TIER } from "./labels";
import { LevelBadge, ResponsePanel, Stat, StateText } from "./ui";

type Alert = {
  status: "alert"; tier: number; family: string; score: number; tactic: string; L: number; I: number; R: number;
  level: string; action: string; reversible: boolean; mode: string; d3fend_now: string[]; d3fend_later: string[];
};
type Flow = Alert | { status: "normal"; tier: number; family: string; score: number } | { status: "invalid" };
type Table = { columns: string[]; data: unknown[][] };
type Model = {
  id: string; name: string; has_tier2: boolean; n_columns: number; ood_classes: string[];
  metrics: { auroc: number; det_rate: number; fpr_thr: number };
};
type Meta = { max_flows: number; models: Model[] };
type Filter = "pending" | "all" | 1 | 2 | 3;
type Decision = "approved" | "rejected";

function errorText(status: number, body: { detail?: unknown } | null) {
  const d = body?.detail as { missing_columns?: string[] } | string | undefined;
  if (typeof d === "object" && d?.missing_columns) {
    const m = d.missing_columns;
    return `File thiếu ${m.length} cột đặc trưng, ví dụ: ${m.slice(0, 5).join(", ")}.`;
  }
  return typeof d === "string" ? `Lỗi: ${d}.` : `Máy chủ trả lỗi ${status}.`;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/${path}`, init);
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorText(res.status, body));
  return body as T;
}

export default function Batch() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [modelId, setModelId] = useState("");
  const [table, setTable] = useState<Table | null>(null);
  const [source, setSource] = useState("");
  const [flows, setFlows] = useState<Flow[] | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [selected, setSelected] = useState<number | null>(null);
  const [decisions, setDecisions] = useState<Record<number, Decision>>({});

  useEffect(() => {
    call<Meta>("meta")
      .then((m) => { setMeta(m); setModelId(m.models[0]?.id ?? ""); })
      .catch((e) => setError(e.message));
  }, []);

  const model = meta?.models.find((m) => m.id === modelId);

  const reset = (t: Table | null, name: string) => {
    setTable(t); setSource(name); setFlows(null); setSelected(null); setDecisions({}); setError("");
  };

  const loadSamples = async () => {
    setBusy("Đang tải lưu lượng mẫu..."); setError("");
    try {
      reset(await call<Table>(`samples?model=${modelId}`), "Lưu lượng mẫu");
    } catch (e) {
      setError((e as Error).message);
    }
    setBusy("");
  };

  const loadFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    Papa.parse<string[]>(file, {
      skipEmptyLines: true,
      complete: ({ data }) => {
        if (data.length < 2) return setError("File không có dòng dữ liệu nào.");
        reset({ columns: data[0].map((c) => c.trim()), data: data.slice(1) }, file.name);
      },
      error: () => setError("Không đọc được file CSV."),
    });
  };

  const limit = meta?.max_flows ?? 2000;
  const analyze = async () => {
    if (!table) return;
    setBusy("Đang phân tích. Lần đầu có thể mất khoảng một phút vì máy chủ cần khởi động."); setError("");
    try {
      const body = JSON.stringify({ columns: table.columns, rows: table.data.slice(0, limit) });
      const res = await call<{ flows: Flow[] }>(`analyze?model=${modelId}`, {
        method: "POST", headers: { "content-type": "application/json" }, body,
      });
      setFlows(res.flows); setFilter("all"); setSelected(null); setDecisions({});
    } catch (e) {
      setError((e as Error).message);
    }
    setBusy("");
  };

  const value = (row: number, name: string) => {
    const i = table?.columns.indexOf(name) ?? -1;
    return i < 0 ? undefined : table?.data[row]?.[i];
  };
  const endpoint = (row: number, side: "src" | "dst") => {
    const addr = value(row, `${side}_addr`);
    return addr === undefined ? "–" : `${addr}:${value(row, `${side}_port`)}`;
  };

  const alerts = useMemo(() => {
    const list: { row: number; a: Alert }[] = [];
    flows?.forEach((f, row) => { if (f.status === "alert") list.push({ row, a: f }); });
    return list.sort((x, y) => y.a.R - x.a.R || y.a.score - x.a.score);
  }, [flows]);

  const isPending = (row: number, a: Alert) => a.mode === APPROVAL && !decisions[row];
  const counts = useMemo(() => ({
    normal: flows?.filter((f) => f.status === "normal").length ?? 0,
    invalid: flows?.filter((f) => f.status === "invalid").length ?? 0,
    t1: alerts.filter(({ a }) => a.tier === 1).length,
    t2: alerts.filter(({ a }) => a.tier === 2).length,
    t3: alerts.filter(({ a }) => a.tier === 3).length,
    pending: alerts.filter(({ row, a }) => isPending(row, a)).length,
  }), [flows, alerts, decisions]); // eslint-disable-line react-hooks/exhaustive-deps

  const shown = alerts.filter(({ row, a }) =>
    filter === "all" ? true : filter === "pending" ? isPending(row, a) : a.tier === filter);
  const current = alerts.find(({ row }) => row === selected) ?? null;

  const stateText = (row: number, a: Alert) => {
    if (decisions[row] === "approved") return "Đã duyệt (mô phỏng)";
    if (decisions[row] === "rejected") return "Đã từ chối";
    return a.mode === APPROVAL ? "Chờ duyệt" : "Tự động (mô phỏng)";
  };

  const tabs: [Filter, string, number][] = [
    ["all", "Tất cả cảnh báo", alerts.length], ["pending", "Chờ duyệt", counts.pending],
    [1, "Tầng 1", counts.t1], ...(model?.has_tier2 ? [[2, "Tầng 2", counts.t2] as [Filter, string, number]] : []),
    [3, "Tầng 3", counts.t3],
  ];

  return (
    <main>
      <div className="page-head">
        <div>
          <h1>Phân tích file</h1>
          <p>Kiểm tra một tập lưu lượng có sẵn bằng mô hình đã huấn luyện</p>
        </div>
      </div>

      <section className="card" data-tour="batch-input">
        <div className="actions">
          <label className="field">
            <span>Mô hình</span>
            <select value={modelId} disabled={!!busy} onChange={(e) => { setModelId(e.target.value); reset(null, ""); }}>
              {meta?.models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
          </label>
          <button onClick={loadSamples} disabled={!!busy || !modelId}>Dùng lưu lượng mẫu</button>
          <label className="file"><Upload size={15} aria-hidden="true" />Tải file CSV<input type="file" accept=".csv" onChange={loadFile} /></label>
          <button className="primary" onClick={analyze} disabled={!table || !!busy || !modelId}>
            <Play size={14} aria-hidden="true" />Phân tích
          </button>
          {table && (
            <span className="hint">
              {source}: {table.data.length} flow{table.data.length > limit && `, chỉ phân tích ${limit} flow đầu`}
            </span>
          )}
        </div>
        <p className="hint">File CSV cần có {model?.n_columns ?? 72} cột đặc trưng theo định dạng LYCOS-IDS2017.</p>
        {busy && <p className="hint" role="status">{busy}</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </section>

      {flows && (
        <>
          <section className="stats" aria-label="Tổng quan">
            <Stat label="Flow đã phân tích" value={flows.length} />
            <Stat label="Bình thường" value={counts.normal} />
            <Stat label="Tầng 1: đã biết" value={counts.t1} />
            {model?.has_tier2 && <Stat label="Tầng 2: biến thể" value={counts.t2} />}
            <Stat label="Tầng 3: hoàn toàn mới" value={counts.t3} />
            <Stat label="Chờ chuyên viên duyệt" value={counts.pending} emph />
          </section>
          {counts.invalid > 0 && <p className="hint">Bỏ qua {counts.invalid} flow có giá trị không hợp lệ.</p>}

          <div className="workspace">
            <section className="card flush">
              <div className="card-head">
                <h2>Hàng đợi cảnh báo</h2>
                <div className="tabs">
                  {tabs.map(([key, label, n]) => (
                    <button key={key} aria-pressed={filter === key} onClick={() => setFilter(key)}>{label} <b>{n}</b></button>
                  ))}
                </div>
              </div>
              <div className="scroll">
                <table>
                  <thead>
                    <tr><th>Mức</th><th>Nguồn</th><th>Đích</th><th>Phân loại</th><th className="right">R</th><th>Trạng thái</th></tr>
                  </thead>
                  <tbody>
                    {shown.map(({ row, a }) => (
                      <tr key={row} tabIndex={0} aria-selected={row === selected} onClick={() => setSelected(row)}
                        onKeyDown={(e) => { if (e.key === "Enter") setSelected(row); }}>
                        <td><LevelBadge level={a.level} /></td>
                        <td className="addr">{endpoint(row, "src")}</td>
                        <td className="addr">{endpoint(row, "dst")}</td>
                        <td>Tầng {a.tier} · {(TACTIC[a.tactic] ?? a.tactic).split(" (")[0]}</td>
                        <td className="num right">{a.R}</td>
                        <td><StateText text={stateText(row, a)} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {shown.length === 0 && <p className="empty">Không có cảnh báo trong mục này.</p>}
              </div>
            </section>

            <section className="card detail">
              {!current ? <p className="empty">Chọn một cảnh báo để xem biện pháp đề xuất.</p> : (
                <ResponsePanel
                  title={TACTIC[current.a.tactic] ?? current.a.tactic}
                  plan={current.a}
                  facts={[
                    ["Kết nối", <span className="addr" key="k">{endpoint(current.row, "src")} → {endpoint(current.row, "dst")}</span>],
                    ["Phân tầng", `Tầng ${current.a.tier}: ${TIER[current.a.tier]}`],
                    [current.a.tier === 1 ? "Họ tấn công" : "Họ gần nhất", current.a.family],
                    ["Điểm OOD", num(current.a.score, 2)],
                  ]}
                  note={value(current.row, "label") !== undefined
                    ? `Nhãn thật: ${String(value(current.row, "label"))} (chỉ để đối chiếu, mô hình không dùng)` : undefined}
                  footer={decisions[current.row] ? (
                    <>
                      <StateText text={stateText(current.row, current.a)} />
                      <button onClick={() => setDecisions(({ [current.row]: _, ...rest }) => rest)}>Hoàn tác</button>
                    </>
                  ) : (
                    <>
                      <button className="primary" onClick={() => setDecisions((d) => ({ ...d, [current.row]: "approved" }))}>Duyệt</button>
                      <button onClick={() => setDecisions((d) => ({ ...d, [current.row]: "rejected" }))}>Từ chối</button>
                    </>
                  )}
                />
              )}
            </section>
          </div>
        </>
      )}

      {model && (
        <footer className="notes">
          <p>
            {model.name}: lớp {model.ood_classes.join(", ")} không có trong tập huấn luyện. Trên dữ liệu kiểm thử, khi gặp
            lớp này: AUROC {num(model.metrics.auroc)}, tỉ lệ phát hiện {num(model.metrics.det_rate)}, tỉ lệ báo nhầm{" "}
            {num(model.metrics.fpr_thr)}.
            {!model.has_tier2 && " Mô hình này không có đầu chiến thuật nên không có tầng 2, flow lạ đều xếp tầng 3."}
          </p>
          <p>Các hành động chỉ là mô phỏng, chưa nối với tường lửa thật. Mức ứng phó và quy tắc phân tầng là thiết kế của đề tài, cần đối chiếu với chuyên gia.</p>
        </footer>
      )}
    </main>
  );
}
