import { driver, type DriveStep } from "driver.js";
import "driver.js/dist/driver.css";

export const TOUR_KEY = "tour-da-xem";
type Tab = "live" | "batch" | "card";

const pick = <T extends HTMLElement>(s: string) => document.querySelector<T>(s);
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Chọn sẵn một sự cố, ưu tiên sự cố chờ duyệt, để bước giới thiệu chi tiết có nội dung. */
async function selectIncident() {
  const rows = () => [...document.querySelectorAll<HTMLElement>('[data-tour="incidents"] tbody tr')];
  if (!rows().length) pick('[data-tour="filter-all"]')?.click();
  await wait(60);
  (rows().find((r) => r.textContent?.includes("Chờ duyệt")) ?? rows()[0])?.click();
  await wait(60);
}

export async function startTour(setTab: (t: Tab) => void) {
  setTab("live");
  await wait(60);
  await selectIncident();

  const steps: DriveStep[] = [
    { popover: {
      title: "Chào mừng",
      description: "Hệ thống theo dõi lưu lượng mạng, phát hiện tấn công, kể cả loại chưa từng gặp, rồi đề xuất biện pháp ứng phó. Phần hướng dẫn này giới thiệu các chức năng chính.",
    } },
    { element: '[data-tour="status"]', popover: {
      title: "Trạng thái giám sát",
      description: "Hệ thống chạy liên tục trên máy chủ, kể cả khi không mở trang, và cập nhật mỗi phút. Dữ liệu là mô phỏng: phát lại flow thật của LYCOS-IDS2017 theo kịch bản tấn công giả lập.",
    } },
    { element: '[data-tour="stats"]', popover: {
      title: "Tổng quan",
      description: "Các chỉ số của 60 phút gần nhất. Ô màu đậm là số sự cố đang chờ chuyên viên quyết định, đây là con số cần chú ý trước tiên.",
    } },
    { element: '[data-tour="chart"]', popover: {
      title: "Cảnh báo theo phút",
      description: "Mỗi cột là số flow bị cảnh báo trong một phút. Mức nền thấp là báo nhầm thông thường. Cột tăng vọt và kéo dài là dấu hiệu cần xem xét. Di chuột lên cột để xem số liệu.",
    } },
    { element: '[data-tour="incidents"]', popover: {
      title: "Hàng đợi sự cố",
      description: "Cảnh báo được gom theo cặp nguồn và đích thành sự cố để tránh nhiễu. Mức M0 đến M4 càng cao càng nghiêm trọng. Dùng các nút lọc phía trên và bấm một dòng để xem chi tiết.",
      side: "top",
    } },
    { element: '[data-tour="detail"]', popover: {
      title: "Chi tiết và biện pháp ứng phó",
      description: "Tầng cho biết đây là tấn công đã biết, biến thể hay hành vi hoàn toàn mới. Rủi ro R = L × I quyết định mức ứng phó. Biện pháp cụ thể được lấy từ MITRE D3FEND.",
      side: "left",
    } },
  ];
  if (pick('[data-tour="decision"]')) {
    steps.push({ element: '[data-tour="decision"]', popover: {
      title: "Duyệt hành động",
      description: "Hành động mạnh hoặc khó đảo ngược không tự chạy mà chờ chuyên viên duyệt hoặc từ chối. Trong bản demo này, hành động chỉ là mô phỏng, chưa nối với tường lửa thật.",
      side: "top",
    } });
  }
  if (pick('[data-tour="notify"]')) {
    steps.push({ element: '[data-tour="notify"]', popover: {
      title: "Thông báo khi có xâm nhập",
      description: "Bật thông báo để trình duyệt báo ngay khi có sự cố mới, kể cả khi bạn đang ở tab khác. Trang cần được mở thì mới nhận được thông báo.",
    } });
  }
  const lastLive = steps.length - 1;
  steps.push(
    { element: '[data-tour="batch-input"]', popover: {
      title: "Phân tích file",
      description: "Tab này dùng để kiểm tra một tập lưu lượng có sẵn: chọn mô hình, dùng dữ liệu mẫu hoặc tải file CSV, rồi bấm Phân tích.",
      onPrevClick: async () => { setTab("live"); await wait(80); d.movePrevious(); },
    } },
    { element: '[data-tour="help"]', popover: {
      title: "Xem lại hướng dẫn",
      description: "Bấm nút này bất cứ lúc nào để xem lại phần hướng dẫn.",
      side: "bottom", align: "end",
    } },
  );
  steps[lastLive].popover!.onNextClick = async () => { setTab("batch"); await wait(80); d.moveNext(); };

  const d = driver({
    steps, showProgress: true, popoverClass: "tour", stagePadding: 6, stageRadius: 10, overlayOpacity: 0.6,
    nextBtnText: "Tiếp", prevBtnText: "Quay lại", doneBtnText: "Hoàn tất", progressText: "{{current}}/{{total}}",
    onDestroyed: () => { localStorage.setItem(TOUR_KEY, "1"); setTab("live"); },
  });
  d.drive();
}
