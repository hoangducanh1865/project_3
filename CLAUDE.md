# Claude — đọc đầu tiên mỗi phiên (cập nhật 2026-10-07)

## 1. Dự án
- Project 3 (HUST, kỳ 20261, 15 tuần: 21/09/2026 – 03/01/2027). Đề tài **C3** trong `references/Security.pdf` (mục 1.4.2).
- SV: Hoàng Đức Anh – 20230015 (KHMT 05 – K68). GVHD: TS Vũ Thị Hương Giang (BM Công nghệ Phần mềm, mảng Security).
- Hướng đã chốt: **học tương phản (contrastive) phân cấp trên nền bài [16] (CLAD/CLOSR) để phát hiện tấn công Out-of-Domain (OOD), đầu ra là biện pháp ứng phó (không chỉ con số rủi ro)**. Tên đề tài **chưa chốt**; ứng viên: "Hierarchical Contrastive Learning cho phát hiện tấn công mạng và đề xuất biện pháp ứng phó trước các tấn công Out-of-Domain (OOD)".
- Góp ý của cô (nhớ khi thiết kế): (1) tài liệu Security.pdf cũ, phải khảo sát dataset/benchmark/model mới; (2) benchmark cũ đạt gần 100%; (3) tập trung tấn công OOD; (4) ma trận rủi ro phải trả về **kịch bản phòng thủ chi tiết**, không chỉ con số.

## 2. Cấu trúc thư mục
- **Repo công khai** `github.com/hoangducanh1865/project_3` (nhánh `main`). Chỉ đẩy mã và ghi chép; xem `.gitignore`. **Không bao giờ đẩy** số điện thoại/email, file mẫu của bạn khác, PDF bài báo, báo cáo đã nộp.
- Quy trình: viết mã trên laptop → `git push` → notebook Colab `pull` và chạy → kết quả ghi lên Google Drive (`OUT_ROOT`), không vào repo. **Không chạy huấn luyện trên laptop** (người dùng đã yêu cầu dừng vì máy lag; chỉ chạy thử rất nhỏ, `nice`, 1 luồng).
- Tracked: `conf/` (Hydra: `dataset/`, `protocol/`, `model/`), `src/` (`data`, `models`, `metrics`, `run`, `report`), `notebooks/{baseline,colab}.ipynb`, `scripts/` (`colab_ssh.sh`, `kaggle/`, `recover_results.py`), `deploy/` (API Modal), `web/` (Next.js), `datasets/README.md` + `fetch_samples.py`, `agents/claude/{README,knowledge}.md`, `CLAUDE.md`, `README.md`, `requirements.txt`.
- Chỉ có trên máy (gitignore): `reports/` gồm `week_1/` (đã nộp, KHÔNG sửa), `week_2/` (slide + docx tuần 2, script sinh `week_2/.generator/`), `week_3/`, `week_4/`, `.de_cuong_generator/`, `my_information.txt`, `archive/` (`tuan5_ban_gop_cu`: bản gộp cũ, không dùng); `references/` (papers, `Security*.pdf`, template `ref/pda/`), `datasets/*` dữ liệu mẫu, `agents/claude/chat_history/`.
- **Nơi lưu (người dùng chốt 2026-10-30):** mã ở GitHub và Drive `MyDrive/hust/study_at_hust/semesters/20261/code/project_3`; dữ liệu và mọi kết quả ở Drive `.../20261/data/project_3` (dữ liệu trong `datasets/`, kết quả đặt thẳng ở gốc, **không** có thư mục `outputs`). Dữ liệu cũng đẩy lên HF dataset **private** `hoangducanh1865/project_3-data` (`HF_WRITE_TOKEN`) và Kaggle Dataset private `hoangducanh18650/project3-lycos-ids2017`.
- SSH vào Colab: `notebooks/colab.ipynb` (ô cuối chạy `scripts/colab_ssh.sh`, in `ssh xxx.trycloudflare.com`); máy đã có `cloudflared` và mục `*.trycloudflare.com` trong `~/.ssh/config`. Không có Kaggle CLI trên laptop: dùng trên Colab (`pip install kaggle`, `KAGGLE_API_TOKEN=$KAGGLE_ACCESS_TOKEN_0`). Token trong `.env` (gitignore) — gửi sang Colab qua stdin vào `/root/.secrets`, không in ra.
- Kaggle (2×T4, chạy nền): `kaggle kernels push -p scripts/kaggle` (kernel script, sửa `JOBS`), lấy kết quả `kaggle kernels output <user>/<slug> -p <dir>`.
- `reports/week_2/.generator/build_week2.py` sinh slide; docx tuần 2 là bản sao của file week_1 rồi sửa tại chỗ bằng `build_week2_docs.py` (không chạy lại trên file đã sửa).
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
- **Commit và PR không có dòng `Co-Authored-By` hay ghi công Claude**, chỉ người dùng là tác giả.

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

## 6. Việc đang dở (tuần 4, cập nhật 2026-10-30)
- Phiên Colab Pro ngày 30/10 chỉ có **1×T4** (không phải 2), RAM 50 GB.
- Đã chạy lại toàn bộ baseline P0/P1 (heldout slowloris, ssh, bot, portscan) và tái hiện [16] bằng trọng số gốc (cần `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` vì PyTorch ≥ 2.6). Lần chạy 21/10 bị trộn lần chạy thử vào báo cáo (2 dòng mlp_msp ở P0): đã tách.
- **HC-CLOSR** (phương pháp đề xuất, slide tuần 2 mục 2.3–4.2) đã có mã: `build_hc_closr` trong `src/models.py`, `src/response.py`, `conf/model/hc_closr.yaml`, bảng chiến thuật trong `conf/dataset/lycos.yaml`. Các quy tắc tự thiết kế: tầng 2 cần chiến thuật dự đoán khác benign; L từ phân vị điểm OOD so với val (chưa dùng tần suất cảnh báo); I theo chiến thuật (giả định).
- **Kết quả 30/10 (40/40 lần chạy, 1 seed)** ở Drive `data/project_3` (`results.csv`, `bao_cao_tuan4.md` — từ nay `src.report` ghi tên `bao_cao_ket_qua.md`, `tai_hien_16.txt`). XGBoost dẫn đầu mọi kịch bản; HC-CLOSR > CLOSR ở 4/5 kịch bản (thua PortScan); phân tầng yếu (SSH-Patator 99% bị xếp tầng 3 thay vì 2). Tái hiện [16] thấp hơn README ở cả 5 chỉ số (chưa rõ lý do).
- **Đánh số tuần (người dùng chốt 2026-10-30):** tuần 3 = kết quả baseline (`reports/week_3/Bao_cao_tuan3_…docx`, `reports/week_3/Slide_tuan3.pptx`, bảng không có dòng HC-CLOSR); tuần 4 = mô hình đề xuất HC-CLOSR và ứng phó (`reports/week_4/Bao_cao_tuan4_…docx`, `reports/week_4/Slide_tuan4.pptx`); **tuần 5 chưa làm**. Slide tuần 3, 4 tách từ slide người dùng đã sửa tay: **không sinh lại slide**, chỉ sửa trực tiếp. Docx sinh bằng `reports/week_4/.generator/build_week34.py` + `comments.py` (đọc `.generator/data/results.csv`; dùng lại `reports/week_2/.generator`).
- **Web demo (2026-11-04):** https://project3-ids.vercel.app (Vercel, dự án `project3-ids`, token `VERCEL_ACCESS_TOKEN`; CLI 46 trên máy không đọc biến này, dùng `npx vercel@latest`; thêm biến môi trường qua REST API). API Modal app `project3-hc-closr`, Volume `project3-model` (`/closr`, `/hc_closr`), secret `project3`, hồ sơ `hoangducanh1865` trong `~/.modal.toml` (người dùng xác nhận; `MODAL_API_TOKEN` trong `.env` chỉ là token id, không dùng được một mình). Tài khoản Modal chưa có phương thức thanh toán nên **không dùng được GPU**; train trên Kaggle rồi `modal volume put`. Sau khi đổi dữ liệu trong Volume phải dừng container đang chạy (`modal container stop -y <id>`).
- **Luồng giả lập 24/7 (2026-11-04):** Modal job `tick` (Cron mỗi phút, 1 CPU, 2 GB, máy tắt ngay sau mỗi lượt) phát lại flow chưa huấn luyện từ `/stream/pool.npz` theo `deploy/scenarios.json`, chạy HC-CLOSR, gom sự cố theo cặp nguồn và đích (`src/stream.py`: từ 5 cảnh báo trong 5 phút, tỉ lệ từ 30%; tự thiết kế), lưu vào Modal Dict `project3-live`. Web đọc qua function `live` (không nạp mô hình). `localhost:20128` chỉ dùng được trên máy nên Gemini chỉ soạn kịch bản một lần; model chạy được: `ag/gemini-3.8-flash-high` (các model `cl/` hết credit). Chưa có kênh báo ra ngoài web (Telegram, email). Giao diện: `web/app/ui.tsx` (thành phần chung), `web/app/tour.ts` (hướng dẫn bằng driver.js, tự mở một lần, khoá `tour-da-xem` trong localStorage), mức M0-M4 dùng thang một màu navy.
- Các thí nghiệm trước **không lưu trọng số** (chỉ `result.json`); từ nay `artifact_dir=<thư mục>` xuất `model.pt`, `samples.json`, `metrics.json`. Mô hình HC-CLOSR (P1, giấu Slowloris, 1 seed, train lại 2026-11-04 trên Kaggle, khớp số cũ: AUROC 0,9436 so với 0,9440) lưu ở Modal Volume `/hc_closr`, HF `hoangducanh1865/project_3-data` mục `models/hc_closr_slowloris/`, Drive `data/project_3/models/hc_closr_slowloris/`. Web dùng `HCDetector`/`CLOSRDetector`; tầng 1 dùng `L_KNOWN = 4` (quy tắc thiết kế mới, chưa đối chiếu).
- **Tuần 5, 6 (2026-11-04):** tuần 5 = đóng gói mô hình, gom sự cố, giả lập luồng; tuần 6 = triển khai demo. File ở `reports/week_5/`, `reports/week_6/`; bộ sinh `reports/week_6/.generator/` (`build_week56.py`, `week6.py`, đọc `data/`, ảnh web ở `img/`), slide dùng `reports/week_4/Slide_tuan4.pptx` làm nền. Đánh giá tăng tốc 72 giờ mô phỏng (`modal run deploy/modal_app.py::evaluate`): phát hiện 72/72 chiến dịch, 137 sự cố trong đó 43 báo nhầm (14,3 mỗi ngày), 7,1% flow bình thường bị cảnh báo, DoS Slowloris bỏ sót 18,5%. Con số 72/72 chưa phản ánh mạng thật vì flow cùng tập dữ liệu với lúc huấn luyện.
- Bài học: hai tiến trình Hydra bắt đầu cùng giây ghi đè thư mục kết quả → thư mục run/sweep giờ có tên giao thức, họ bị loại, mô hình; `scripts/recover_results.py` khôi phục `result.json` từ log.

(Cũ) 
Xem `agents/claude/chat_history/week_2_lam_ro_huong_di/task.md`. Tuần 3 dự kiến: tải LYCOS-IDS2017, chạy lại mã [16], lập ánh xạ họ tấn công → ATT&CK → D3FEND.

## 7. Quy tắc viết văn bản nộp (đề cương, phiếu)
- Người dùng yêu cầu **không có chi tiết trông như AI viết**: câu ngắn, giọng trung tính của sinh viên, ít dấu chấm phẩy nối chuỗi, không tính từ khoa trương (toàn diện, mạnh mẽ, tối ưu), không mũi tên `→` và không số liệu không có nguồn trong phần chữ; chỉ nêu điều đã kiểm chứng hoặc ghi rõ "dự kiến".
- **Luôn sửa trên bản sao của file người dùng đã chỉnh tay** (ví dụ week_1 đã bỏ màu đỏ/hồng ở As-is, đã xoá hình kiến trúc); đừng sinh lại từ template.
- Tên đề tài tạm dùng trong tuần 2: "Học tương phản phân cấp (Hierarchical Contrastive Learning) cho phát hiện tấn công mạng và đề xuất biện pháp ứng phó trước các tấn công Out-of-Domain (OOD)" — **chưa được người dùng xác nhận**.
