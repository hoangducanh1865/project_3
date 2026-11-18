# Ngập HTTP (`http_flood`)

Nhóm chiến thuật của mô hình: `impact`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Gửi dồn dập yêu cầu HTTP hợp lệ để làm cạn tài nguyên của dịch vụ web.

## Cách gán nhãn
Chạm máy tấn công, trong khung thời gian, đầu kia là mục tiêu.

## Biến thể gốc trong bộ dữ liệu
http-flood-port-80, http-flood-port-1883, http-flood-port-443, http-flood-port-554, http-flood-port-6668, http-flood-port-9595

## ATT&CK T1499.002: Service Exhaustion Flood
Chiến thuật: impact. Cập nhật 2026-11-04. https://attack.mitre.org/techniques/T1499/002
- D3FEND Detect: Application Protocol Command Analysis (D3-APCA); Client-server Payload Profiling (D3-CSPP); Inbound Session Volume Analysis (D3-ISVA); Network Traffic Community Deviation (D3-NTCD); Network Traffic Signature Analysis (D3-NTSA); Per Host Download-Upload Ratio Analysis (D3-PHDURA); Protocol Metadata Anomaly Detection (D3-PMAD); Remote Terminal Session Detection (D3-RTSD); User Geolocation Logon Pattern Analysis (D3-UGLPA)
- D3FEND Isolate: Inbound Traffic Filtering (D3-ITF); Network Traffic Filtering (D3-NTF)

## Số đo trên dữ liệu (trung vị)
97238 flow từ 39 tệp PCAP; 6 gói, 300 byte, 8114 ms mỗi flow; cổng đích hay gặp [1883, 80, 9595]; giao thức {6: 1.0}.
