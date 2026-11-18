# Dò mật khẩu Telnet (`telnet_bruteforce`)

Nhóm chiến thuật của mô hình: `credential_access`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Như dò mật khẩu SSH nhưng vào Telnet (cổng 23), giao thức không mã hoá thường gặp trên thiết bị IoT.

## Cách gán nhãn
Chạm máy tấn công, trong khung thời gian, đầu kia là mục tiêu.

## Biến thể gốc trong bộ dữ liệu
dictionary-telnet

## ATT&CK T1110.001: Password Guessing
Chiến thuật: credential-access. Cập nhật 2026-11-03. https://attack.mitre.org/techniques/T1110/001
- D3FEND Detect: Application Exception Monitoring (D3-AEM); Credential Compromise Scope Analysis (D3-CCSA); Operational Process Monitoring (D3-OPM)
- D3FEND Harden: Change Default Password (D3-CDP); Credential Hardening (D3-CH); Credential Rotation (D3-CRO); Multi-factor Authentication (D3-MFA); One-time Password (D3-OTP); Password Rotation (D3-PR); Password Authentication (D3-PWA); Strong Password Policy (D3-SPP)
- D3FEND Evict: Authentication Cache Invalidation (D3-ANCI); Credential Revocation (D3-CR)
- D3FEND Restore: Reissue Credential (D3-RIC)
- D3FEND Isolate: Credential Transmission Scoping (D3-CTS)
- D3FEND Deceive: Decoy User Credential (D3-DUC)

## Số đo trên dữ liệu (trung vị)
2065 flow từ 3 tệp PCAP; 2 gói, 100 byte, 1 ms mỗi flow; cổng đích hay gặp [23]; giao thức {6: 1.0}.
