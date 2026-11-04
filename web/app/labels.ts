export const APPROVAL = "chuyên viên duyệt";
export const TIER: Record<number, string> = {
  1: "Tấn công đã biết",
  2: "Biến thể của chiến thuật đã biết",
  3: "Hành vi hoàn toàn mới",
};
export const TACTIC: Record<string, string> = {
  impact: "Impact (làm gián đoạn dịch vụ)",
  credential_access: "Credential Access (lấy thông tin xác thực)",
  initial_access: "Initial Access (xâm nhập ban đầu)",
  command_and_control: "Command and Control (điều khiển từ xa)",
  discovery: "Discovery (dò quét)",
  unknown: "Chưa xác định",
};

export const num = (x: number, d = 3) => x.toFixed(d).replace(".", ",");
