# Dò mật khẩu SSH (`ssh_bruteforce`)

Nhóm chiến thuật của mô hình: `credential_access`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Thử lần lượt các cặp tên đăng nhập, mật khẩu từ từ điển vào dịch vụ SSH (cổng 22). Nhiều phiên TCP lặp lại tới cùng một cổng, kích thước và thời lượng gần giống nhau.

## Cách gán nhãn
Chạm máy tấn công, trong khung thời gian, đầu kia là mục tiêu.

## Biến thể gốc trong bộ dữ liệu
dictionary-ssh

## ATT&CK T1110.001: Password Guessing
Chiến thuật: credential-access. Cập nhật 2026-11-03. https://attack.mitre.org/techniques/T1110/001
- D3FEND Detect: Application Exception Monitoring (D3-AEM); Credential Compromise Scope Analysis (D3-CCSA); Operational Process Monitoring (D3-OPM)
- D3FEND Harden: Change Default Password (D3-CDP); Credential Hardening (D3-CH); Credential Rotation (D3-CRO); Multi-factor Authentication (D3-MFA); One-time Password (D3-OTP); Password Rotation (D3-PR); Password Authentication (D3-PWA); Strong Password Policy (D3-SPP)
- D3FEND Evict: Authentication Cache Invalidation (D3-ANCI); Credential Revocation (D3-CR)
- D3FEND Restore: Reissue Credential (D3-RIC)
- D3FEND Isolate: Credential Transmission Scoping (D3-CTS)
- D3FEND Deceive: Decoy User Credential (D3-DUC)

## Số đo trên dữ liệu (trung vị)
1594 flow từ 5 tệp PCAP; 2 gói, 100 byte, 2 ms mỗi flow; cổng đích hay gặp [22]; giao thức {6: 1.0}.
