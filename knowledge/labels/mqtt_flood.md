# Ngập MQTT (`mqtt_flood`)

Nhóm chiến thuật của mô hình: `impact`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Gửi dồn dập bản tin MQTT publish tới máy chủ MQTT.

## Cách gán nhãn
Chạm máy tấn công, trong khung thời gian, đầu kia là mục tiêu.

## Biến thể gốc trong bộ dữ liệu
mqtt-publish-flood

## ATT&CK T1499.002: Service Exhaustion Flood
Chiến thuật: impact. Cập nhật 2026-11-04. https://attack.mitre.org/techniques/T1499/002
- D3FEND Detect: Application Protocol Command Analysis (D3-APCA); Client-server Payload Profiling (D3-CSPP); Inbound Session Volume Analysis (D3-ISVA); Network Traffic Community Deviation (D3-NTCD); Network Traffic Signature Analysis (D3-NTSA); Per Host Download-Upload Ratio Analysis (D3-PHDURA); Protocol Metadata Anomaly Detection (D3-PMAD); Remote Terminal Session Detection (D3-RTSD); User Geolocation Logon Pattern Analysis (D3-UGLPA)
- D3FEND Isolate: Inbound Traffic Filtering (D3-ITF); Network Traffic Filtering (D3-NTF)

## Số đo trên dữ liệu (trung vị)
3100 flow từ 2 tệp PCAP; 42 gói, 3626 byte, 22348 ms mỗi flow; cổng đích hay gặp [1883, 47538, 45710]; giao thức {6: 1.0}.
