# Dò tìm thiết bị (`host_discovery`)

Nhóm chiến thuật của mô hình: `discovery`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Máy tấn công gửi gói thăm dò (TCP SYN, TCP ACK, UDP, ICMP echo) tới nhiều địa chỉ trong dải mạng để biết máy nào đang bật. Mỗi flow rất ngắn, 1 đến 2 gói, ít hoặc không có dữ liệu.

## Cách gán nhãn
Chạm máy tấn công trong khung thời gian của lần tấn công; không cần đầu kia là mục tiêu (quét rộng).

## Biến thể gốc trong bộ dữ liệu
host-disc-tcp-ack-ping, host-disc-tcp-syn-ping, host-disc-tcp-syn-stealth, host-disc-udp-ping, ping-sweep

## Ghi chú
host-disc-arp-ping chỉ có gói ARP, không tạo flow IP nên bị bỏ.

## ATT&CK T1018: Remote System Discovery
Chiến thuật: discovery. Cập nhật 2026-05-12. https://attack.mitre.org/techniques/T1018
- D3FEND Isolate: Content Filtering (D3-CF); Content Modification (D3-CM); Content Quarantine (D3-CQ); Executable Allowlisting (D3-EAL); Executable Denylisting (D3-EDL); Hardware-based Process Isolation (D3-HBPI); Local File Permissions (D3-LFP); Network Traffic Filtering (D3-NTF); Remote File Access Mediation (D3-RFAM); System Call Filtering (D3-SCF)
- D3FEND Detect: Application Protocol Command Analysis (D3-APCA); Client-server Payload Profiling (D3-CSPP); File Analysis (D3-FA); File Integrity Monitoring (D3-FIM); Network Traffic Community Deviation (D3-NTCD); Network Traffic Signature Analysis (D3-NTSA); Per Host Download-Upload Ratio Analysis (D3-PHDURA); Protocol Metadata Anomaly Detection (D3-PMAD); Process Spawn Analysis (D3-PSA); Remote Terminal Session Detection (D3-RTSD); System Call Analysis (D3-SCA); System File Analysis (D3-SFA); User Geolocation Logon Pattern Analysis (D3-UGLPA)
- D3FEND Harden: File Encryption (D3-FE)
- D3FEND Evict: File Eviction (D3-FEV)
- D3FEND Restore: Restore File (D3-RF)
- D3FEND Deceive: Decoy File (D3-DF)

## Số đo trên dữ liệu (trung vị)
318585 flow từ 117 tệp PCAP; 2 gói, 84 byte, 7 ms mỗi flow; cổng đích hay gặp [53, 88, 3878]; giao thức {6: 0.999, 17: 0.001, 2: 0.0, 1: 0.0}.
