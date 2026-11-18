# Mirai (`mirai`)

Nhóm chiến thuật của mô hình: `impact`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Thiết bị IoT bị nhiễm Mirai cùng làm ngập SYN hoặc UDP vào máy edge và máy chủ MQTT.

## Cách gán nhãn
Chạm máy tấn công trong khung thời gian; nhận flow tới mọi máy (lây lan).

## Biến thể gốc trong bộ dữ liệu
mirai-syn-flood, mirai-udp-flood

## ATT&CK T1498: Network Denial of Service
Chiến thuật: impact. Cập nhật 2025-10-24. https://attack.mitre.org/techniques/T1498
- D3FEND Detect: Application Protocol Command Analysis (D3-APCA); Client-server Payload Profiling (D3-CSPP); Inbound Session Volume Analysis (D3-ISVA); Network Traffic Community Deviation (D3-NTCD); Network Traffic Signature Analysis (D3-NTSA); Per Host Download-Upload Ratio Analysis (D3-PHDURA); Protocol Metadata Anomaly Detection (D3-PMAD); Remote Terminal Session Detection (D3-RTSD); User Geolocation Logon Pattern Analysis (D3-UGLPA)
- D3FEND Isolate: Inbound Traffic Filtering (D3-ITF); Network Traffic Filtering (D3-NTF)

## Số đo trên dữ liệu (trung vị)
48000 flow từ 16 tệp PCAP; 2 gói, 100 byte, 1 ms mỗi flow; cổng đích hay gặp [23, 48101, 2323]; giao thức {6: 0.668, 17: 0.33, 2: 0.001, 1: 0.0}.
