# Dò hệ điều hành (`os_scan`)

Nhóm chiến thuật của mô hình: `discovery`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Gửi các gói TCP, UDP, ICMP có cờ và tuỳ chọn bất thường rồi so phản hồi để đoán hệ điều hành (kiểu nmap -O).

## Cách gán nhãn
Chạm máy tấn công trong khung thời gian; quét rộng.

## Biến thể gốc trong bộ dữ liệu
os-scan

## Ghi chú
ATT&CK Enterprise không có kỹ thuật riêng cho dò hệ điều hành từ xa; T1046 là gần nhất.

## ATT&CK T1046: Network Service Discovery
Chiến thuật: discovery. Cập nhật 2026-11-03. https://attack.mitre.org/techniques/T1046

## Số đo trên dữ liệu (trung vị)
82815 flow từ 29 tệp PCAP; 2 gói, 84 byte, 8 ms mỗi flow; cổng đích hay gặp [1, 53, 6668]; giao thức {6: 0.997, 17: 0.002, 2: 0.001, 1: 0.0}.
