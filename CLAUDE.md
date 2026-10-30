# Claude — đọc đầu tiên mỗi phiên (cập nhật 2026-10-07)

## 1. Dự án
- Project 3 (HUST, kỳ 20261, 15 tuần: 21/09/2026 – 03/01/2027). Đề tài **C3** trong `references/Security.pdf` (mục 1.4.2).
- SV: Hoàng Đức Anh – 20230015 (KHMT 05 – K68). GVHD: TS Vũ Thị Hương Giang (BM Công nghệ Phần mềm, mảng Security).
- Hướng đã chốt: **học tương phản (contrastive) phân cấp trên nền bài [16] (CLAD/CLOSR) để phát hiện tấn công Out-of-Domain (OOD), đầu ra là biện pháp ứng phó (không chỉ con số rủi ro)**. Tên đề tài **chưa chốt**; ứng viên: "Hierarchical Contrastive Learning cho phát hiện tấn công mạng và đề xuất biện pháp ứng phó trước các tấn công Out-of-Domain (OOD)".
- Góp ý của cô (nhớ khi thiết kế): (1) tài liệu Security.pdf cũ, phải khảo sát dataset/benchmark/model mới; (2) benchmark cũ đạt gần 100%; (3) tập trung tấn công OOD; (4) ma trận rủi ro phải trả về **kịch bản phòng thủ chi tiết**, không chỉ con số.

## 2. Cấu trúc thư mục
- **Repo công khai** `github.com/hoangducanh1865/project_3` (nhánh `main`). Chỉ đẩy mã và ghi chép; xem `.gitignore`. **Không bao giờ đẩy** số điện thoại/email, file mẫu của bạn khác, PDF bài báo, báo cáo đã nộp.
- Quy trình: viết mã trên laptop → `git push` → notebook Colab `pull` và chạy → kết quả ghi lên Google Drive (`OUT_ROOT`), không vào repo. **Không chạy huấn luyện trên laptop** (người dùng đã yêu cầu dừng vì máy lag; chỉ chạy thử rất nhỏ, `nice`, 1 luồng).
- Tracked: `conf/` (Hydra: `dataset/`, `protocol/`, `model/`), `src/` (`data`, `models`, `metrics`, `run`, `report`), `notebooks/week_4_baseline.ipynb`, `datasets/README.md` + `fetch_samples.py`, `agents/claude/{README,knowledge}.md`, `CLAUDE.md`, `README.md`, `requirements.txt`.
- Chỉ có trên máy (gitignore): `week_1/` (đã nộp, KHÔNG sửa), `week_2/` (slide + docx tuần 2, script sinh `week_2/.generator/`), `.de_cuong_generator/`, `references/` (papers, `Security*.pdf`, template `ref/pda/`), `datasets/*` dữ liệu mẫu, `my_information.txt`, `agents/claude/chat_history/`.
- SSH vào Colab: `notebooks/colab.ipynb` (mã trên Drive, ô cuối chạy `scripts/colab_ssh.sh`, in `ssh xxx.trycloudflare.com`); máy đã có `cloudflared` và mục `*.trycloudflare.com` trong `~/.ssh/config`.
- `week_2/.generator/build_week2.py` sinh slide; docx tuần 2 là bản sao của file week_1 rồi sửa tại chỗ bằng `build_week2_docs.py` (không chạy lại trên file đã sửa).
- Mã của [16] không vendoring: notebook clone vào `third_party/CLOSR` (gitignore), biến `CLOSR_DIR`.

## 3. Quy ước người dùng đã yêu cầu (bắt buộc)
- **Viết toàn bộ bằng tiếng Việt**, kể cả tin nhắn ngắn giữa các bước (từng bị nhắc vì có câu tiếng Anh). Thuật ngữ giữ tiếng Anh: Out-of-Domain (OOD), open-set, zero-day, benchmark, baseline, Hierarchical Contrastive Learning…
- Không dùng "ngoài miền"; dùng thẳng **Out-of-Domain (OOD)**. Không dùng "sinh kịch bản"; dùng **"đề xuất biện pháp ứng phó"** / "hỗ trợ ra quyết định phòng thủ".
- Giọng văn **trang trọng, ngắn gọn, logic**; tiêu đề phần chuẩn hoá (không khẩu ngữ).
- **Slide:** nội dung chỉ là bullet, bullet con và dấu ⇒ **trong cùng một ô text**; chữ **đen**, không in đậm bừa; chữ to (≥20pt bullet chính); sơ đồ khối/bảng được phép; **tài liệu tham khảo gom ở slide cuối**, không để trong từng slide; dùng template HUST ở `references/ref/pda/Slide giới thiệu đề tài prj 3.pptx`.
- **Màu sắc đồng bộ (đã bị nhắc 2 lần):** chỉ navy (viền/nền hộp, đầu thẻ), xám nhạt, trắng. Mọi thẻ/hộp cùng loại phải **cùng một kiểu** — không để thẻ đầu tiên xám, không ô đỏ/hồng "lạc loài" (người dùng chê "trông rất AI"). Nhấn mạnh bằng nền navy. Tiêu đề slide bìa dùng **đỏ đô `9E1B32`**, không dùng đỏ tươi. **Trước khi báo xong phải rà từng slide xem có phần tử nào khác màu/kiểu so với các phần tử cùng loại.**
- Không dùng ký tự `↔` (hiện thành emoji trên máy người dùng); viết "và"/"hai chiều". Các ký tự `→`, `⇒`, `①…⑧` hiển thị bình thường.
- **Mục lục tối đa ~5 mục**; slide đánh số theo mục `1.1, 1.2, …`; slide tài liệu tham khảo không đánh số (người dùng chê mục lục 19 mục).
- Slide/đề cương trích dẫn bằng số `[n]` thống nhất với danh sách 20 tài liệu (xem `references/papers/README.md`).
- Chỉ ghi nhận định có nguồn; chỗ chưa kiểm chứng phải nói rõ. Không tự khẳng định "mới" khi chưa khảo sát.
- Nhắn cuối mỗi lượt: ngắn, nêu rõ việc đã làm, việc cần bạn kiểm tra.

## 4. Kỹ thuật (đã gặp lỗi, tránh lặp lại)
- Python: `python3 -m venv` (3.14) lỗi ensurepip → dùng `python3.12 -m venv`, cài `python-docx python-pptx lxml pillow defusedxml`. Venv nằm trong scratchpad và **mất khi đổi phiên** → tạo lại.
- Không có pandoc/markitdown. Đọc docx/pptx: `soffice --headless --convert-to txt/pdf` rồi `pdftotext`/`pdftoppm` xem hình. Render trước khi báo xong.
- Validate: `python <skill>/docx|pptx/scripts/office/validate.py file --original gốc` (cần `defusedxml`).
- Mạng/ghi ngoài sandbox cần `dangerouslyDisableSandbox: true` (curl, pip).
- arXiv API hay bị giới hạn tần suất → lấy tiêu đề từ trang `arxiv.org/abs/<id>` (meta `citation_title`).
- zsh: `echo "=====TEXT"` gây lỗi `not found` → luôn đặt dấu nháy.
- Mẫu pptx: runs có `err="1"` bị PowerPoint gạch đỏ → đặt `lang="vi-VN" noProof="1"`, xoá `err/dirty`.
- File khoá `~$*` nghĩa là app đang mở file; app Save sẽ **ghi đè** bản mới → nhắc người dùng đóng không Save.

## 5. Tri thức cốt lõi đã kiểm chứng (chi tiết: `agents/claude/knowledge.md`)
- [16] Wilkie 2026 (CLAD/CLOSR): chỉ dùng LYCOS-IDS2017, chia 50/50 ngẫu nhiên, "zero-day" chỉ **2 lớp rất nhỏ** (Heartbleed 11 mẫu, Web SQLi). Mã: github.com/jackwilkie/CLOSR (Apache-2.0, đẩy 2026-06, có CLAD/CLOSR + ~12 baseline + weights).
- [13] Corsini 2023: KNN là bộ phát hiện OOD tốt nhất, sau đó MC-Dropout và Confidence; ODIN/Mahalanobis kém trên NetFlow; Center Loss không luôn giúp. Giao thức của họ: train trên vài tấn công, test trên tấn công còn lại cùng dataset và dataset khác (nên giao thức P1/P2 của ta **không hoàn toàn mới**). Mã: github.com/AndreaCorsini1/CyberOOD (**không có license**, "work in progress").
- Dataset: CIC-IDS2017/2018 có lỗi (Engelen: >20% traffic sửa/gán lại) → dùng bản sửa; NetFlow v3 (UQ) cần đăng nhập kho `rdm.uq.edu.au`; mẫu đã tải ở `datasets/`.
- ATT&CK/D3FEND: ID kỹ thuật T1498, T1499, T1046, T1110, T1190, T1071, T1595, T1021 đã xác minh trên attack.mitre.org; API `d3fend.mitre.org/api/offensive-technique/attack/<ID>.json` trả danh sách biện pháp phòng thủ (T1046 trả rỗng).

## 6. Việc đang dở (tuần 4)
- Notebook `notebooks/week_4_baseline.ipynb` đã viết, **chưa chạy trên Colab/dữ liệu thật**. Đã chạy thử pipeline trên dữ liệu giả nhỏ (CPU): 6/7 mô hình chạy; **XGBoost chưa thử** (máy thiếu libomp). Đã sửa 2 lỗi bắt được khi thử (cache nhãn object, `torch.flatnonzero`). Nhãn LYCOS thật chưa biết tên chính xác → `HELDOUT` trong notebook có thể phải chỉnh.
- Cần người dùng: chạy notebook, gửi `bao_cao_tuan4.md`; sau đó viết báo cáo tuần 4.

(Cũ) 
Xem `agents/claude/chat_history/week_2_lam_ro_huong_di/task.md`. Tuần 3 dự kiến: tải LYCOS-IDS2017, chạy lại mã [16], lập ánh xạ họ tấn công → ATT&CK → D3FEND.

## 7. Quy tắc viết văn bản nộp (đề cương, phiếu)
- Người dùng yêu cầu **không có chi tiết trông như AI viết**: câu ngắn, giọng trung tính của sinh viên, ít dấu chấm phẩy nối chuỗi, không tính từ khoa trương (toàn diện, mạnh mẽ, tối ưu), không mũi tên `→` và không số liệu không có nguồn trong phần chữ; chỉ nêu điều đã kiểm chứng hoặc ghi rõ "dự kiến".
- **Luôn sửa trên bản sao của file người dùng đã chỉnh tay** (ví dụ week_1 đã bỏ màu đỏ/hồng ở As-is, đã xoá hình kiến trúc); đừng sinh lại từ template.
- Tên đề tài tạm dùng trong tuần 2: "Học tương phản phân cấp (Hierarchical Contrastive Learning) cho phát hiện tấn công mạng và đề xuất biện pháp ứng phó trước các tấn công Out-of-Domain (OOD)" — **chưa được người dùng xác nhận**.
