# Giả mạo IP nguồn (`ip_spoofing`)

Nhóm chiến thuật của mô hình: `credential_access`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Gửi dồn dập gói có IP nguồn của thiết bị khác (ví dụ camera) tới router. Trong dữ liệu, mỗi lần tấn công thường chỉ là một flow rất lớn (hàng triệu gói cùng 5-tuple).

## Cách gán nhãn
Flow tới mục tiêu trong khung thời gian, MAC là máy tấn công hoặc IP nguồn lạ.

## Biến thể gốc trong bộ dữ liệu
ip-spoofing

## Ghi chú
Bộ dữ liệu xếp vào nhóm MITM; hành vi thực tế gần ngập lụt. Chỉ có 45 flow, kết quả không ổn định.

## ATT&CK T1498.001: Direct Network Flood
Chiến thuật: impact. Cập nhật 2025-10-24. https://attack.mitre.org/techniques/T1498/001
- D3FEND Detect: Application Protocol Command Analysis (D3-APCA); Client-server Payload Profiling (D3-CSPP); Inbound Session Volume Analysis (D3-ISVA); Network Traffic Community Deviation (D3-NTCD); Network Traffic Signature Analysis (D3-NTSA); Per Host Download-Upload Ratio Analysis (D3-PHDURA); Protocol Metadata Anomaly Detection (D3-PMAD); Remote Terminal Session Detection (D3-RTSD); User Geolocation Logon Pattern Analysis (D3-UGLPA)
- D3FEND Isolate: Inbound Traffic Filtering (D3-ITF); Network Traffic Filtering (D3-NTF)

## Số đo trên dữ liệu (trung vị)
45 flow từ 25 tệp PCAP; 2.73607e+06 gói, 7.66099e+07 byte, 41124 ms mỗi flow; cổng đích hay gặp [0, 137, 58142]; giao thức {1: 0.622, 17: 0.378}.
