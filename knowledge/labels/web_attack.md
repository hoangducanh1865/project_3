# Tấn công web (`web_attack`)

Nhóm chiến thuật của mô hình: `initial_access`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Gửi yêu cầu HTTP chứa chuỗi khai thác (SQL injection, XSS, chèn lệnh, tải lên web shell) tới ứng dụng web của máy edge. Mô hình chỉ thấy số đo của flow, không thấy nội dung yêu cầu.

## Cách gán nhãn
Chạm máy tấn công, trong khung thời gian, đầu kia là mục tiêu.

## Biến thể gốc trong bộ dữ liệu
sql-injection, sql-injection-blind, xss, command-injection, backdoor-upload

## Ghi chú
backdoor-upload gần T1505.003 (Web Shell, Persistence) hơn; gom vào web_attack vì chỉ có 1 tệp.

## ATT&CK T1190: Exploit Public-Facing Application
Chiến thuật: initial-access. Cập nhật 2026-05-12. https://attack.mitre.org/techniques/T1190
- D3FEND Detect: Application Protocol Command Analysis (D3-APCA); Client-server Payload Profiling (D3-CSPP); Database Query String Analysis (D3-DQSA); Inbound Session Volume Analysis (D3-ISVA); Network Traffic Community Deviation (D3-NTCD); Network Traffic Signature Analysis (D3-NTSA); Per Host Download-Upload Ratio Analysis (D3-PHDURA); Protocol Metadata Anomaly Detection (D3-PMAD); Remote Terminal Session Detection (D3-RTSD); User Geolocation Logon Pattern Analysis (D3-UGLPA)
- D3FEND Isolate: Inbound Traffic Filtering (D3-ITF); Network Traffic Filtering (D3-NTF)
- D3FEND Harden: Process Segment Execution Prevention (D3-PSEP); Segment Address Offset Randomization (D3-SAOR)

## Số đo trên dữ liệu (trung vị)
7543 flow từ 5 tệp PCAP; 11 gói, 2867 byte, 41 ms mỗi flow; cổng đích hay gặp [4280]; giao thức {6: 1.0}.
