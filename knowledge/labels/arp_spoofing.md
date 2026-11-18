# Đầu độc ARP (`arp_spoofing`)

Nhóm chiến thuật của mô hình: `credential_access`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Máy tấn công gửi bản tin ARP giả để đứng giữa hai thiết bị (ví dụ cảm biến và máy chủ MQTT). Trên flow IP chỉ thấy phần lưu lượng mà máy tấn công trực tiếp gửi hoặc nhận; bản thân gói ARP không tạo flow IP.

## Cách gán nhãn
Chạm IP hoặc MAC máy tấn công trong khung thời gian; nhận flow tới mọi máy (MITM).

## Biến thể gốc trong bộ dữ liệu
arp-spoofing

## ATT&CK T1557.002: ARP Cache Poisoning
Chiến thuật: collection, credential-access. Cập nhật 2025-10-24. https://attack.mitre.org/techniques/T1557/002
- D3FEND Isolate: Network Traffic Filtering (D3-NTF)
- D3FEND Detect: Application Protocol Command Analysis (D3-APCA); Client-server Payload Profiling (D3-CSPP); Network Traffic Community Deviation (D3-NTCD); Network Traffic Signature Analysis (D3-NTSA); Per Host Download-Upload Ratio Analysis (D3-PHDURA); Protocol Metadata Anomaly Detection (D3-PMAD); Remote Terminal Session Detection (D3-RTSD); User Geolocation Logon Pattern Analysis (D3-UGLPA)

## Số đo trên dữ liệu (trung vị)
281 flow từ 21 tệp PCAP; 2 gói, 112 byte, 3 ms mỗi flow; cổng đích hay gặp [0, 53, 5338]; giao thức {17: 0.456, 2: 0.374, 1: 0.089, 6: 0.082}.
