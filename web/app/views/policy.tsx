"use client";

import type { Ctx } from "../ctx";
import type { Level } from "../lib";
import { planFor } from "../lib";
import { KV, LevelBadge, Panel } from "../ui";

const LEVELS: Level[] = ["M0", "M1", "M2", "M3", "M4"];
const R_MAX: Record<Level, string> = { M0: "R ≤ 3", M1: "4–6", M2: "7–12", M3: "13–16", M4: "17–25" };

export default function PolicyView({ ctx }: { ctx: Ctx }) {
  const p = ctx.policy;
  if (!p) return <p className="empty">Đang tải...</p>;
  return (
    <>
      <div className="page-head">
        <div><h1>Phân quyền và cấu hình</h1>
          <p>AI chỉ đề xuất. Nó chỉ được tự làm hành động nhẹ, có thời hạn, đảo ngược được, khi người không phản hồi; không được làm gì có thể làm sập hệ thống.</p></div>
      </div>
      <Panel flush title="Ai được làm gì ở từng mức" sub={<span>Nguồn: <code>conf/policy.yaml</code>, cùng quy tắc với <code>src/policy.py</code></span>}>
        <div className="scroll">
          <table className="table">
            <thead><tr><th>Mức</th><th>Rủi ro</th><th>Hành động</th><th>Thời hạn</th><th>Đảo ngược</th><th>Thực hiện</th><th>Duyệt</th><th>Trợ lý AI</th></tr></thead>
            <tbody>{LEVELS.map((lv) => {
              const pl = planFor(p, lv);
              return (
                <tr key={lv}><td><LevelBadge level={lv} /></td><td className="mono">{R_MAX[lv]}</td>
                  <td>{pl.actionName}<small>{pl.actionDesc}</small></td><td>{pl.ttl ? `${pl.ttl} phút` : "Không giới hạn"}</td>
                  <td>{pl.reversible ? "Có" : "Không"}</td><td>{pl.executor}</td><td>{pl.approver ?? "Không cần"}</td><td>{pl.aiText}</td></tr>
              );
            })}</tbody>
          </table>
        </div>
      </Panel>
      <div className="grid-2">
        <Panel title="Giới hạn của trợ lý AI">
          <KV rows={[
            ["Chờ người duyệt", `${p.ai.timeout_min} phút, sau đó AI mới được thực hiện hành động cho phép ở mức M2`],
            ["Không bao giờ được", p.ai.forbidden_actions.map((a) => p.actions[a].name).join(", ") + ", thu hồi thông tin xác thực, tắt dịch vụ, đổi cấu hình vĩnh viễn"],
            ["Hạ tầng được bảo vệ", `${p.ai.protected_roles.join(", ")}: AI chỉ đề xuất khi máy đích thuộc nhóm này`],
            ["Dẫn nguồn", p.ai.must_cite ? "Bắt buộc. Đề xuất có mã D3FEND không nằm trong tài liệu truy xuất bị loại tự động" : "Không bắt buộc"],
          ]} />
        </Panel>
        <Panel title="Vai trò">
          <KV rows={Object.entries(p.roles).map(([k, r]) => [r.name, ({
            system: "Thực hiện M0, M1 theo luật cố định",
            ai: "Phân tích, đề xuất có dẫn nguồn; tự thực hiện M2 khi hết giờ chờ",
            analyst: "Duyệt M2, M3",
            lead: "Duyệt mọi mức, kể cả M4 (khó đảo ngược)",
          } as Record<string, string>)[k]])} />
          <p className="fine">Đổi vai trò ở góc trên để thấy nút duyệt khoá hoặc mở theo quyền.</p>
        </Panel>
      </div>
      <div className="grid-2">
        <Panel title="Quy tắc mở sự cố" sub={<span>Nguồn: <code>src/stream.py</code></span>}>
          <KV rows={[
            ["Cửa sổ", "5 phút gần nhất, gom theo cặp IP nguồn và đích"],
            ["Điều kiện mở", "Từ 5 cảnh báo và tỉ lệ cảnh báo từ 30% số flow của cặp"],
            ["Đóng", "Sau 10 phút không còn cảnh báo"],
            ["Báo ra ngoài", "Từ M3 (Telegram); mỗi phút tối đa 3 tin"],
          ]} />
          <p className="fine">Với dữ liệu IIoT, quy tắc này còn mở nhiều sự cố báo nhầm; đang chờ chốt ngưỡng mới.</p>
        </Panel>
        <Panel title="Tệp cấu hình">
          <KV rows={[
            ["Nguồn dữ liệu, cách tách", <code key="1">conf/dataset/datasense.yaml</code>],
            ["Danh mục nhãn", <code key="2">conf/labels/datasense.yaml</code>],
            ["Phân quyền", <code key="3">conf/policy.yaml</code>],
            ["Tác động I theo chiến thuật", <code key="4">conf/model/hc_closr.yaml</code>],
          ]} />
          <p className="fine">Bản demo là trang tĩnh: sửa cấu hình rồi chạy lại scripts/precompute_live.py để áp dụng.</p>
        </Panel>
      </div>
    </>
  );
}
