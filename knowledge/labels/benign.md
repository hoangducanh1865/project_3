# Bình thường (`benign`)

Nhóm chiến thuật của mô hình: `benign`. Kiểm tra với ATT&CK v20.1 ngày 2026-11-18.

## Hành vi
Lưu lượng vận hành của mạng IIoT: cảm biến gửi bản tin MQTT lên máy chủ MQTT (cổng 1883), máy chủ MQTT đẩy dữ liệu lên đám mây, camera truyền hình ảnh, router và điểm truy cập gửi bản tin quản trị, DNS, NTP, mDNS.

## Cách gán nhãn
Tệp benign không chạm máy tấn công; hoặc flow trong tệp tấn công không chạm IP, MAC máy tấn công.

## Biến thể gốc trong bộ dữ liệu
benign_whole-network3, lưu lượng nền trong tệp tấn công

## Số đo trên dữ liệu (trung vị)
120255 flow từ 862 tệp PCAP; 2 gói, 328 byte, 63 ms mỗi flow; cổng đích hay gặp [1883, 6667, 5353]; giao thức {17: 0.523, 6: 0.411, 1: 0.045, 2: 0.019, 58: 0.002, 145: 0.0, 19: 0.0, 52: 0.0, 20: 0.0, 115: 0.0, 248: 0.0, 228: 0.0, 163: 0.0}.
