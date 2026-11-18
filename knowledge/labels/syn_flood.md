# Ngập SYN (`syn_flood`)

Nhóm chiến thuật của mô hình: `impact`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Gửi dồn dập gói TCP SYN không hoàn tất bắt tay để làm đầy bảng kết nối của mục tiêu.

## Cách gán nhãn
Chạm máy tấn công, trong khung thời gian, đầu kia là mục tiêu.

## Biến thể gốc trong bộ dữ liệu
syn-flood-port-80, syn-flood-port-1883, syn-flood-port-22, syn-flood-port-23, syn-flood-port-443, syn-flood-port-554

## ATT&CK T1499.001: OS Exhaustion Flood
Chiến thuật: impact. Cập nhật 2025-10-24. https://attack.mitre.org/techniques/T1499/001

## Số đo trên dữ liệu (trung vị)
177000 flow từ 59 tệp PCAP; 16 gói, 640 byte, 27731 ms mỗi flow; cổng đích hay gặp [1883, 80, 554]; giao thức {6: 1.0}.
