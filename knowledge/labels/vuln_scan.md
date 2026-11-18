# Quét lỗ hổng (`vuln_scan`)

Nhóm chiến thuật của mô hình: `discovery`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Công cụ quét lỗ hổng gửi các yêu cầu tới dịch vụ đang mở để so với chữ ký lỗ hổng đã biết; flow dài hơn quét cổng, có dữ liệu ứng dụng.

## Cách gán nhãn
Chạm máy tấn công trong khung thời gian; quét rộng.

## Biến thể gốc trong bộ dữ liệu
vuln-scan

## ATT&CK T1595.002: Vulnerability Scanning
Chiến thuật: reconnaissance. Cập nhật 2026-05-12. https://attack.mitre.org/techniques/T1595/002

## Số đo trên dữ liệu (trung vị)
65023 flow từ 29 tệp PCAP; 2 gói, 84 byte, 7 ms mỗi flow; cổng đích hay gặp [80, 53, 443]; giao thức {6: 0.998, 17: 0.001, 2: 0.001}.
