# Quét cổng (`port_scan`)

Nhóm chiến thuật của mô hình: `discovery`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Máy tấn công thử kết nối tới nhiều cổng của một máy để tìm dịch vụ đang mở. Nhiều flow ngắn tới các cổng đích khác nhau, phần lớn bị RST.

## Cách gán nhãn
Chạm máy tấn công trong khung thời gian; quét rộng.

## Biến thể gốc trong bộ dữ liệu
port-scan

## ATT&CK T1046: Network Service Discovery
Chiến thuật: discovery. Cập nhật 2026-11-03. https://attack.mitre.org/techniques/T1046

## Số đo trên dữ liệu (trung vị)
81542 flow từ 29 tệp PCAP; 2 gói, 84 byte, 7 ms mỗi flow; cổng đích hay gặp [53, 32773, 7999]; giao thức {6: 0.998, 17: 0.001, 2: 0.001}.
