# Ngập ICMP (`icmp_flood`)

Nhóm chiến thuật của mô hình: `impact`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Gửi dồn dập gói ICMP echo (có thể phân mảnh).

## Cách gán nhãn
Chạm máy tấn công, trong khung thời gian, đầu kia là mục tiêu.

## Biến thể gốc trong bộ dữ liệu
icmp-flood, icmp-frag-flood

## ATT&CK T1498.001: Direct Network Flood
Chiến thuật: impact. Cập nhật 2025-10-24. https://attack.mitre.org/techniques/T1498/001
- D3FEND Detect: Application Protocol Command Analysis (D3-APCA); Client-server Payload Profiling (D3-CSPP); Inbound Session Volume Analysis (D3-ISVA); Network Traffic Community Deviation (D3-NTCD); Network Traffic Signature Analysis (D3-NTSA); Per Host Download-Upload Ratio Analysis (D3-PHDURA); Protocol Metadata Anomaly Detection (D3-PMAD); Remote Terminal Session Detection (D3-RTSD); User Geolocation Logon Pattern Analysis (D3-UGLPA)
- D3FEND Isolate: Inbound Traffic Filtering (D3-ITF); Network Traffic Filtering (D3-NTF)

## Số đo trên dữ liệu (trung vị)
314 flow từ 106 tệp PCAP; 391797 gói, 4.13762e+07 byte, 48708.5 ms mỗi flow; cổng đích hay gặp [0]; giao thức {1: 1.0}.
