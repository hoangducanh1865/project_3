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

// Họ tấn công của DataSense (src/datasense.py: FAMILIES) và kỹ thuật ATT&CK gần nhất. Bảng do đề tài lập.
export const FAMILY: Record<string, [string, string]> = {
  benign: ["Bình thường", ""],
  host_discovery: ["Dò tìm thiết bị", "T1018"],
  port_scan: ["Quét cổng", "T1046"],
  os_scan: ["Dò hệ điều hành", "T1046"],
  vuln_scan: ["Quét lỗ hổng", "T1595.002"],
  ssh_bruteforce: ["Dò mật khẩu SSH", "T1110.001"],
  telnet_bruteforce: ["Dò mật khẩu Telnet", "T1110.001"],
  web_attack: ["Tấn công web (SQLi, XSS, chèn lệnh)", "T1190"],
  arp_spoofing: ["Đầu độc ARP", "T1557.002"],
  impersonation: ["Giả mạo thiết bị", "T1557"],
  ip_spoofing: ["Giả mạo IP nguồn", "T1557"],
  mirai: ["Mirai", "T1498"],
  syn_flood: ["Làm ngập SYN", "T1498.001"],
  land_flood: ["Land flood (IP nguồn trùng đích)", "T1498.001"],
  tcp_flood: ["Làm ngập TCP", "T1498.001"],
  udp_flood: ["Làm ngập UDP", "T1498.001"],
  icmp_flood: ["Làm ngập ICMP", "T1498.001"],
  http_flood: ["Làm ngập HTTP", "T1499.002"],
  mqtt_flood: ["Làm ngập MQTT", "T1499.002"],
  slowloris: ["Slowloris", "T1499.002"],
};
export const famName = (f: string) => FAMILY[f]?.[0] ?? f;
export const attackUrl = (t: string) => `https://attack.mitre.org/techniques/${t.replace(".", "/")}/`;
/** Liên kết tới trang D3FEND của một biện pháp; mục tự đề xuất không có liên kết. */
export const d3fendUrl = (m: string) =>
  /tự đề xuất|có thời hạn|bằng chứng/.test(m) ? null : `https://d3fend.mitre.org/technique/d3f:${m.replace(/[^A-Za-z]/g, "")}/`;
export const PROTO: Record<number, string> = { 1: "ICMP", 6: "TCP", 17: "UDP" };
