# Giả mạo thiết bị (`impersonation`)

Nhóm chiến thuật của mô hình: `credential_access`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Máy tấn công giả danh một cảm biến để gửi bản tin MQTT giả tới máy chủ MQTT.

## Cách gán nhãn
Chạm máy tấn công trong khung thời gian; nhận flow tới mọi máy (đầu kia là máy chủ MQTT, không phải mục tiêu).

## Biến thể gốc trong bộ dữ liệu
impersonation

## Ghi chú
ATT&CK Enterprise không có kỹ thuật khớp; ATT&CK for ICS có T0856 (Spoof Reporting Message) sát hơn.

## ATT&CK T1557: Adversary-in-the-Middle
Chiến thuật: collection, credential-access. Cập nhật 2026-11-03. https://attack.mitre.org/techniques/T1557
- D3FEND Detect: Application Protocol Command Analysis (D3-APCA); Connection Attempt Analysis (D3-CAA); Client-server Payload Profiling (D3-CSPP); Network Traffic Community Deviation (D3-NTCD); Network Traffic Signature Analysis (D3-NTSA); Per Host Download-Upload Ratio Analysis (D3-PHDURA); Protocol Metadata Anomaly Detection (D3-PMAD); Remote Terminal Session Detection (D3-RTSD); User Geolocation Logon Pattern Analysis (D3-UGLPA)
- D3FEND Isolate: Network Traffic Filtering (D3-NTF)

## Số đo trên dữ liệu (trung vị)
199 flow từ 14 tệp PCAP; 191 gói, 10912 byte, 56083 ms mỗi flow; cổng đích hay gặp [1883, 0, 123]; giao thức {6: 0.704, 2: 0.231, 17: 0.065}.
