"use client";

import Papa from "papaparse";
import { ChangeEvent, useEffect, useMemo, useState } from "react";

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

const APPROVAL = "chuyên viên duyệt";
const TIER: Record<number, string> = {
  1: "Tấn công đã biết",
  2: "Biến thể của chiến thuật đã biết",
  3: "Hành vi hoàn toàn mới",
};
const TACTIC: Record<string, string> = {
  impact: "Impact (làm gián đoạn dịch vụ)",
  credential_access: "Credential Access (lấy thông tin xác thực)",
  initial_access: "Initial Access (xâm nhập ban đầu)",
  command_and_control: "Command and Control (điều khiển từ xa)",
  discovery: "Discovery (dò quét)",
  unknown: "Chưa xác định",
};

const num = (x: number, d = 3) => x.toFixed(d).replace(".", ",");

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

export default function Page() {
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
    <>
      <header className="top">
        <h1>Giám sát xâm nhập mạng</h1>
        <p>Phát hiện tấn công Out-of-Domain (OOD) và đề xuất biện pháp ứng phó bằng mô hình HC-CLOSR</p>
      </header>
      <main>
        <section className="card">
          <h2>Nạp lưu lượng mạng</h2>
          <div className="actions">
            <label>
              Mô hình{" "}
              <select value={modelId} disabled={!!busy} onChange={(e) => { setModelId(e.target.value); reset(null, ""); }}>
                {meta?.models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
            </label>
            <button onClick={loadSamples} disabled={!!busy || !modelId}>Dùng lưu lượng mẫu</button>
            <label className="file">Tải file CSV<input type="file" accept=".csv" onChange={loadFile} /></label>
            <button className="primary" onClick={analyze} disabled={!table || !!busy || !modelId}>Phân tích</button>
            {table && (
              <span>
                {source}: {table.data.length} flow
                {table.data.length > limit && `, chỉ phân tích ${limit} flow đầu`}
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
              <div className="stat"><strong>{flows.length}</strong><span>Flow đã phân tích</span></div>
              <div className="stat"><strong>{counts.normal}</strong><span>Bình thường</span></div>
              <div className="stat"><strong>{counts.t1}</strong><span>Tầng 1: đã biết</span></div>
              {model?.has_tier2 && <div className="stat"><strong>{counts.t2}</strong><span>Tầng 2: biến thể</span></div>}
              <div className="stat"><strong>{counts.t3}</strong><span>Tầng 3: hoàn toàn mới</span></div>
              <div className="stat emph"><strong>{counts.pending}</strong><span>Chờ chuyên viên duyệt</span></div>
            </section>
            {counts.invalid > 0 && <p className="hint">Bỏ qua {counts.invalid} flow có giá trị không hợp lệ.</p>}

            <div className="workspace">
              <section className="card">
                <h2>Hàng đợi cảnh báo</h2>
                <div className="tabs">
                  {tabs.map(([key, label, n]) => (
                    <button key={key} aria-pressed={filter === key} onClick={() => setFilter(key)}>{label} ({n})</button>
                  ))}
                </div>
                <div className="scroll">
                  <table>
                    <thead>
                      <tr><th>Nguồn</th><th>Đích</th><th>Tầng</th><th>Chiến thuật</th><th>R</th><th>Mức</th><th>Trạng thái</th></tr>
                    </thead>
                    <tbody>
                      {shown.map(({ row, a }) => (
                        <tr key={row} tabIndex={0} aria-selected={row === selected} onClick={() => setSelected(row)}
                          onKeyDown={(e) => { if (e.key === "Enter") setSelected(row); }}>
                          <td className="addr">{endpoint(row, "src")}</td>
                          <td className="addr">{endpoint(row, "dst")}</td>
                          <td className="num">{a.tier}</td>
                          <td>{(TACTIC[a.tactic] ?? a.tactic).split(" (")[0]}</td>
                          <td className="num">{a.R}</td>
                          <td><span className={a.mode === APPROVAL ? "badge solid" : "badge"}>{a.level}</span></td>
                          <td>{stateText(row, a)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {shown.length === 0 && <p className="hint">Không có cảnh báo trong mục này.</p>}
                </div>
              </section>

              <section className="card detail">
                <h2>Chi tiết và biện pháp ứng phó</h2>
                {!current ? <p className="hint">Chọn một cảnh báo để xem biện pháp đề xuất.</p> : (
                  <>
                    <dl>
                      <dt>Kết nối</dt><dd className="addr">{endpoint(current.row, "src")} → {endpoint(current.row, "dst")}</dd>
                      <dt>Phân tầng</dt><dd>Tầng {current.a.tier}: {TIER[current.a.tier]}</dd>
                      <dt>Chiến thuật</dt><dd>{TACTIC[current.a.tactic] ?? current.a.tactic}</dd>
                      <dt>{current.a.tier === 1 ? "Họ tấn công" : "Họ gần nhất"}</dt><dd>{current.a.family}</dd>
                      <dt>Điểm OOD</dt><dd>{num(current.a.score, 2)}</dd>
                      <dt>Rủi ro</dt><dd>R = L × I = {current.a.L} × {current.a.I} = {current.a.R}</dd>
                      {value(current.row, "label") !== undefined && (
                        <><dt>Nhãn thật</dt><dd>{String(value(current.row, "label"))} (chỉ để đối chiếu, mô hình không dùng)</dd></>
                      )}
                    </dl>
                    <h3>Mức {current.a.level}: {current.a.action}</h3>
                    <p className="hint">
                      {current.a.reversible ? "Đảo ngược được" : "Khó đảo ngược"}. Thực hiện: {current.a.mode}.
                    </p>
                    <h3>Biện pháp ngay (D3FEND)</h3>
                    <ul>{current.a.d3fend_now.map((m) => <li key={m}>{m}</li>)}</ul>
                    {current.a.d3fend_later.length > 0 && (
                      <>
                        <h3>Củng cố sau</h3>
                        <ul>{current.a.d3fend_later.map((m) => <li key={m}>{m}</li>)}</ul>
                      </>
                    )}
                    {current.a.mode === APPROVAL && (
                      <div className="decision">
                        {decisions[current.row] ? (
                          <>
                            <span>{stateText(current.row, current.a)}</span>
                            <button onClick={() => setDecisions(({ [current.row]: _, ...rest }) => rest)}>Hoàn tác</button>
                          </>
                        ) : (
                          <>
                            <button className="primary" onClick={() => setDecisions((d) => ({ ...d, [current.row]: "approved" }))}>Duyệt</button>
                            <button onClick={() => setDecisions((d) => ({ ...d, [current.row]: "rejected" }))}>Từ chối</button>
                          </>
                        )}
                      </div>
                    )}
                  </>
                )}
              </section>
            </div>
          </>
        )}

        <footer className="notes">
          {model && (
            <p>
              {model.name}: lớp {model.ood_classes.join(", ")} không có trong tập huấn luyện. Trên dữ liệu kiểm thử, khi
              gặp lớp này: AUROC {num(model.metrics.auroc)}, tỉ lệ phát hiện {num(model.metrics.det_rate)}, tỉ lệ báo
              nhầm {num(model.metrics.fpr_thr)}.
              {!model.has_tier2 && " Mô hình này không có đầu chiến thuật nên không có tầng 2, flow lạ đều xếp tầng 3."}
            </p>
          )}
          <p>Các hành động chỉ là mô phỏng, chưa nối với tường lửa thật. Mức ứng phó và quy tắc phân tầng là thiết kế của đề tài, cần đối chiếu với chuyên gia.</p>
        </footer>
      </main>
    </>
  );
}
