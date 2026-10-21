# Tri thức đã thu thập (cập nhật 2026-10-07)

Nhãn: **[ĐÃ KIỂM CHỨNG]** = đọc trực tiếp từ mã nguồn, PDF hoặc API; **[CHƯA KIỂM CHỨNG]** = từ trí nhớ/kết quả tìm kiếm.

## 1. Bài [16] Wilkie 2026 — CLAD/CLOSR (backbone chính)
- Mã: `github.com/jackwilkie/CLOSR`, Apache-2.0, đẩy lần cuối 2026-06-27, 7 sao, kèm `weights/` (~38 MB mỗi file). **[ĐÃ KIỂM CHỨNG]**
- Gồm: `losses/clad_loss.py`, `losses/closr_loss.py`, `train_*.py`, `eval_*.py`, `model/model.py` (CLOSRMLP), và `baseline_implementations/` với: autoencoder, DAE-LR, DUAD, Isolation Forest, RENOIR, Deep SVDD, SVM; open-set: CROSR, DOC, MultiStage NIDS, OpenMax, Siamese. **[ĐÃ KIỂM CHỨNG]**
- CLOSR: mỗi lớp có một không gian embedding riêng (đầu ra `batch × n_classes × d_out`), mất mát theo từng lớp trên khoảng cách cosine. Mặc định MLP 3×1024, `d_out=64`, `d_in=72`, `n_classes=12` (cứng trong `eval_closr.py`, phải sửa khi đổi dữ liệu). **[ĐÃ KIỂM CHỨNG]**
- Dữ liệu: **chỉ LYCOS-IDS2017**, file `data/lycos.csv`, cột nhãn `label`, lớp bình thường `benign`; cột bị bỏ: `flow_id,src_addr,src_port,dst_addr,dst_port,ip_prot,timestamp` (nghĩa là file có IP và timestamp). Chia 50/50 ngẫu nhiên phân tầng. **[ĐÃ KIỂM CHỨNG]**
- **"Zero-day" = lớp có < `sample_thres`=100 mẫu** (mặc định) → thực tế chỉ 2 lớp: Heartbleed (11 mẫu), Web Attack SQL Injection. Không chọn theo họ tấn công. **[ĐÃ KIỂM CHỨNG]** (README + `load_data.py`)
- Kết quả trong README (AUROC): CLAD closed-set trung bình 0,999855, open-set (2 lớp) 0,996627; CLOSR OpenAUC 0,969420 so với MultiStage 0,798537. Closed-set đã bão hoà. **[ĐÃ KIỂM CHỨNG]**
- Tương lai theo chính bài: kiểm tra độ bền với mẫu đối kháng và benign bị nhiễm trong tập huấn luyện. **[ĐÃ KIỂM CHỨNG]**
- Dữ liệu tiền xử lý: link Google Drive trong README (trang trả 200, chưa tải thử file). Trang LYCOS-IDS2017 (`lycos-ids.univ-lemans.fr`) không lộ link tải trực tiếp.

## 2. Bài [13] Corsini & Yang 2023 — OOD cho NIDS
- Mã: `github.com/AndreaCorsini1/CyberOOD`, **không có license**, README ghi "Work in progress", 193 KB, có checkpoint `ids2018`. Chứa: `OOD/confidence.py` (Confidence/MSP có nhiệt độ, MC-Dropout), `OOD/distance.py` (KNN, Silhouette), `OOD/gradient.py` (ODIN, Mahalanobis). **[ĐÃ KIỂM CHỨNG]**
- 6 bộ phát hiện: CONF, MCD, ODIN, MD, KNN, SIM. Mô hình là FNN, thử cross-entropy vs Center Loss, đa lớp vs nhị phân. **[ĐÃ KIỂM CHỨNG]**
- Kết luận: **KNN tốt nhất**, sau đó MCD và CONF; ODIN và MD thấp hơn (trái với thị giác máy tính); Center Loss **không luôn cải thiện**; kết hợp đơn giản vài bộ phát hiện đạt gần 100% trong các kịch bản thử. TPR phụ thuộc mạnh vào loại tấn công (từ 0% đến 100%). **[ĐÃ KIỂM CHỨNG]**
- Giao thức: train trên benign + vài tấn công của một dataset; test trên các tấn công còn lại của dataset đó và trên dataset khác (IDS2017/IDS2018, CICFlowMeter 80+ đặc trưng, 3 kịch bản trên IDS2018). **⇒ giao thức P1/P2 của ta không hoàn toàn mới.** **[ĐÃ KIỂM CHỨNG]**
- ODIN/Mahalanobis gọi `tune(in_data, ood_data)`: ngưỡng chỉnh bằng **dữ liệu OOD** — không thực tế khi triển khai. **[ĐÃ KIỂM CHỨNG]**

## 3. Dataset (xem thêm `references/papers/README.md`, `datasets/README.md`)
- LycoS-Unicas-IDS2018 (bản CSE-CIC-IDS2018 sửa theo LycoS, Cantone 2024 [5]): `github.com/MarcoCantone/LycoS-Unicas-IDS2018`. **[ĐÃ KIỂM CHỨNG]** (trích từ PDF [5]; chưa mở repo). Cùng bộ đặc trưng LycoSTand với LYCOS-IDS2017 → dùng được cho đánh giá chéo 2017↔2018.
- NetFlow v3 (UQ): kho `rdm.uq.edu.au` yêu cầu đăng nhập (API trả `unauthorized`); chưa tải được. Mẫu thay thế: NF-ToN-IoT-**v2** trên Hugging Face.
- CSE-CIC-IDS2018 bản sửa lỗi của Liu [3]: zip 10 GB, chỉ đọc tuần tự được, không lấy mẫu được.
- NF-BoT-IoT-v3: 99,7% là tấn công → không phù hợp học lưu lượng bình thường.

## 4. MITRE ATT&CK / D3FEND
- ID kỹ thuật đã xác minh tên trên attack.mitre.org: T1498 Network Denial of Service, T1499 Endpoint Denial of Service, T1046 Network Service Discovery, T1595 Active Scanning, T1110 Brute Force, T1190 Exploit Public-Facing Application, T1071 Application Layer Protocol, T1021 Remote Services. **[ĐÃ KIỂM CHỨNG]**
- API D3FEND `https://d3fend.mitre.org/api/offensive-technique/attack/<ID>.json`. Biện pháp **không phải Detect** (đã trả về): **[ĐÃ KIỂM CHỨNG]**
  - T1498 và T1499: Isolate = Inbound Traffic Filtering, Network Traffic Filtering.
  - T1110: Isolate = Credential Transmission Scoping, Network Traffic Filtering; Evict = Credential Revocation, Authentication Cache Invalidation; Harden = Multi-factor Authentication, One-time Password, Credential/Password Rotation, Strong Password Policy, Change Default Password…; Deceive = Decoy User Credential; Restore = Reissue Credential.
  - T1190: Isolate = Inbound Traffic Filtering, Network Traffic Filtering; Harden = Process Segment Execution Prevention, Segment Address Offset Randomization.
  - T1071: Isolate = Outbound Traffic Filtering, DNS Allowlisting/Denylisting, Forward Resolution Domain Denylisting, Reverse Resolution IP Denylisting, Content Filtering…; Network Traffic Filtering.
  - T1021: Evict = Session Termination; Isolate = Network Traffic Filtering.
  - **T1046, T1595 (và T1595.001/.002): D3FEND trả rỗng** → thám sát/quét cổng không có biện pháp trong D3FEND; phải tự đề xuất (đánh dấu rõ là quy tắc tự thiết kế).
- D3FEND thiên về nhóm Detect; nhóm hành động (Isolate/Evict/Harden/Deceive/Restore) ít hơn nhiều.
- NIST SP 800-61 Rev. 3 (04/2025) "Incident Response Recommendations and Considerations for Cybersecurity Risk Management: A CSF 2.0 Community Profile". **[ĐÃ KIỂM CHỨNG]** (trang CSRC).
- Energy-based OOD Detection (Liu et al.) có trên arXiv 2010.03759. **[ĐÃ KIỂM CHỨNG]** tiêu đề.
- Ánh xạ nhãn dataset → chiến thuật ATT&CK **do ta tự lập** (không có sẵn trong tài liệu đã đọc): DoS/DDoS → Impact; Patator, Web brute force → Credential Access; Web SQLi/XSS, Heartbleed → Initial Access (T1190); Botnet → Command and Control (T1071); PortScan → Discovery/Reconnaissance (T1046/T1595); Infiltration → Initial Access/Lateral Movement. **[CHƯA KIỂM CHỨNG — phải lập và đối chiếu ở tuần 3]**

## 5. Điều chỉnh các nhận định cũ của Claude
- Từng nói "chưa paper nào đánh giá OOD kiểu chéo mạng/loại họ tấn công". **Sai một phần**: [13] và [5] đã làm kiểu này trên CIC-IDS2017/2018. Điểm mới còn lại (chưa kiểm chứng): làm trên NetFlow v3 + giao thức theo **họ tấn công/chiến thuật**, và nối với phản ứng.
- Ý tưởng nhãn phân cấp theo chiến thuật ATT&CK cho OOD trong NIDS: **chưa khảo sát tài liệu**, không được khẳng định là mới.

## 6. Giới hạn của ý tưởng nhãn phân cấp
Nếu một họ tấn công là thành viên duy nhất của chiến thuật (Botnet → C2, PortScan → Discovery) thì khi giữ lại họ đó, chiến thuật không còn trong tập huấn luyện → không nhận ra được chiến thuật. Vì vậy phải tách hai loại kịch bản OOD: **biến thể mới của chiến thuật đã biết** và **hành vi hoàn toàn mới**.
