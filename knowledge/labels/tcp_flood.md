# Ngập TCP (`tcp_flood`)

Nhóm chiến thuật của mô hình: `impact`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Gửi dồn dập gói TCP với các tổ hợp cờ ACK, PSH, RST, FIN hoặc mở kết nối đầy đủ liên tục.

## Cách gán nhãn
Chạm máy tấn công, trong khung thời gian, đầu kia là mục tiêu.

## Biến thể gốc trong bộ dữ liệu
ack-frag-flood, push-ack-flood, rst-fin-flood, tcp-flood, connect-flood

## ATT&CK T1499.001: OS Exhaustion Flood
Chiến thuật: impact. Cập nhật 2025-10-24. https://attack.mitre.org/techniques/T1499/001

## Số đo trên dữ liệu (trung vị)
600000 flow từ 200 tệp PCAP; 10 gói, 960 byte, 32902.5 ms mỗi flow; cổng đích hay gặp [1883, 80, 554]; giao thức {6: 1.0}.
