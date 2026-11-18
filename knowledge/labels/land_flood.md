# Land flood (`land_flood`)

Nhóm chiến thuật của mô hình: `impact`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Gói SYN có IP nguồn trùng IP đích, khiến mục tiêu tự trả lời chính nó.

## Cách gán nhãn
Flow tới mục tiêu có IP nguồn trùng IP đích hoặc lạ, trong khung thời gian.

## Biến thể gốc trong bộ dữ liệu
synonymousip-flood-port-80, synonymousip-flood-port-1883

## ATT&CK T1499.001: OS Exhaustion Flood
Chiến thuật: impact. Cập nhật 2025-10-24. https://attack.mitre.org/techniques/T1499/001

## Số đo trên dữ liệu (trung vị)
105000 flow từ 35 tệp PCAP; 44 gói, 1848 byte, 56678 ms mỗi flow; cổng đích hay gặp [1883, 80, 14331]; giao thức {6: 1.0, 1: 0.0}.
