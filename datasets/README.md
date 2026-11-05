# Dữ liệu

Repo không chứa dữ liệu. Tải và chuẩn bị bằng `bash scripts/prepare_data.sh`, kết quả nằm ở `data/`.

## Một dòng dữ liệu là gì

Mỗi dòng là một **flow**: toàn bộ gói tin có cùng IP nguồn, IP đích, cổng nguồn, cổng đích và giao thức trong một phiên kết nối. Bộ trích đặc trưng tổng hợp các gói đó thành số đo thống kê như số gói, số byte, thời lượng, khoảng cách giữa các gói và cờ TCP. Mô hình không thấy nội dung gói tin. Cột cuối là nhãn: lưu lượng bình thường hoặc một họ tấn công.

## Các tập dữ liệu

| Tập | Nguồn | Số flow gốc | Số lớp | Đặc trưng dùng | Vai trò |
|---|---|---:|---:|---:|---|
| LYCOS-IDS2017 | CIC-IDS2017 trích lại bằng LycoSTand ([Rosay 2022](https://lycos-ids.univ-lemans.fr/)) | 1.789.954 | 14 | 66 | Phát hiện họ OOD, chéo tập |
| LycoS-Unicas-IDS2018 | CSE-CIC-IDS2018 trích lại ([Cantone 2024](https://github.com/MarcoCantone/LycoS-Unicas-IDS2018)) | 13,7 triệu | 14 | 66 | Chéo tập |
| NF-ToN-IoT-v3 | NetFlow v3 ([Luay 2025](https://staff.itee.uq.edu.au/marius/NIDS_datasets/)) | 27.520.260 | 10 | 41 | Phát hiện họ OOD, chéo tập |
| NF-CICIDS2018-v3 | NetFlow v3 ([Luay 2025](https://staff.itee.uq.edu.au/marius/NIDS_datasets/)) | 20.115.529 | 15 | 40 | Phát hiện họ OOD, chéo tập |

NetFlow v3 được tải từ bản sao `athena21/netflow-v3-datasets` trên Kaggle. Số flow của NF-ToN-IoT-v3 khớp số công bố chính thức.

## Mẫu thật

Giá trị gốc, chưa chuẩn hoá. Mỗi cột là một flow có số gói gần trung vị của lớp đó, không phải ca đặc biệt. Bảng chỉ hiện một phần số cột.

### LYCOS-IDS2017

| Cột | Ý nghĩa | Bình thường | Slowloris | SSH-Patator | PortScan |
|---|---|---|---|---|---|
| `src_addr` | IP nguồn (không dùng) | 192.168.10.14 | 172.16.0.1 | 172.16.0.1 | 172.16.0.1 |
| `dst_addr` | IP đích (không dùng) | 192.168.10.3 | 192.168.10.50 | 192.168.10.50 | 192.168.10.50 |
| `dst_port` | Cổng đích (không dùng) | 53 | 80 | 22 | 8873 |
| `ip_prot` | Giao thức, 6 là TCP, 17 là UDP (không dùng) | 17 | 6 | 6 | 6 |
| `flow_duration` | Thời lượng, micro giây | 175 | 3003736 | 11459418 | 49 |
| `fwd_pkt_cnt` | Số gói chiều đi | 2 | 3 | 21 | 1 |
| `bwd_pkt_cnt` | Số gói chiều về | 2 | 0 | 32 | 1 |
| `fwd_pkt_len_tot` | Tổng byte dữ liệu chiều đi | 68 | 0 | 2008 | 0 |
| `bwd_pkt_len_tot` | Tổng byte dữ liệu chiều về | 182 | 0 | 2745 | 0 |
| `pkt_len_mean` | Độ dài dữ liệu trung bình mỗi gói | 62.5 | 0 | 89.6792 | 0 |
| `iat_mean` | Khoảng cách trung bình giữa hai gói, micro giây | 58.3333 | 1.50187e+06 | 220373 | 49 |
| `flag_SYN` | Số cờ SYN | 0 | 3 | 2 | 1 |
| `flag_ack` | Số cờ ACK | 0 | 0 | 52 | 1 |
| `flag_psh` | Số cờ PSH | 0 | 0 | 31 | 0 |
| `fwd_pkt_hdr_len_min` | Độ dài header nhỏ nhất (loại bỏ) | 8 | 40 | 32 | 40 |
| `fwd_tcp_init_win_bytes` | Cửa sổ TCP khởi tạo chiều đi (loại bỏ) | -1 | 29200 | 29200 | 29200 |
| `label` | Nhãn | benign | dos_slowloris | ssh_patator | portscan |

Có thể đọc được hành vi từ các số trên. Slowloris mở kết nối rồi giữ: thời lượng 3 giây, 3 gói SYN, không có dữ liệu, không có gói về. PortScan chỉ chạm cổng rồi đi: 49 micro giây, không có dữ liệu. SSH-Patator là phiên đăng nhập thật: hơn 50 gói, có dữ liệu cả hai chiều.

Ba flow tấn công có cùng IP nguồn `172.16.0.1` và cùng cửa sổ TCP khởi tạo 29200. Đây là ví dụ cụ thể của vấn đề ở mục dưới: các giá trị này nói về máy tấn công, không nói về hành vi.

### NF-ToN-IoT-v3

| Cột | Ý nghĩa | Bình thường | Backdoor | Scanning |
|---|---|---|---|---|
| `IPV4_SRC_ADDR` | IP nguồn (không dùng) | 192.168.1.31 | 192.168.1.193 | 192.168.1.32 |
| `IPV4_DST_ADDR` | IP đích (không dùng) | 192.168.1.1 | 192.168.1.33 | 192.168.35.231 |
| `L4_DST_PORT` | Cổng đích (không dùng) | 53 | 80 | 80 |
| `PROTOCOL` | Giao thức | 17 | 6 | 6 |
| `L7_PROTO` | Giao thức tầng ứng dụng | 5 | 0 | 7 |
| `IN_BYTES` | Byte chiều vào | 71 | 288 | 40 |
| `IN_PKTS` | Số gói chiều vào | 1 | 6 | 1 |
| `OUT_BYTES` | Byte chiều ra | 71 | 240 | 0 |
| `OUT_PKTS` | Số gói chiều ra | 1 | 6 | 0 |
| `TCP_FLAGS` | Tổng hợp cờ TCP | 0 | 22 | 16 |
| `FLOW_DURATION_MILLISECONDS` | Thời lượng, mili giây | 3 | 1531 | 1 |
| `LONGEST_FLOW_PKT` | Gói dài nhất | 71 | 48 | 40 |
| `SHORTEST_FLOW_PKT` | Gói ngắn nhất | 71 | 40 | 40 |
| `MIN_TTL` | TTL nhỏ nhất (loại bỏ) | 0 | 128 | 0 |
| `TCP_WIN_MAX_IN` | Cửa sổ TCP lớn nhất (loại bỏ) | 0 | 8192 | 1024 |
| `Attack` | Nhãn | Benign | Backdoor | scanning |

### NF-CICIDS2018-v3

| Cột | Ý nghĩa | Bình thường | HOIC | Bot |
|---|---|---|---|---|
| `IPV4_SRC_ADDR` | IP nguồn (không dùng) | 172.31.64.75 | 18.219.5.43 | 172.31.69.26 |
| `IPV4_DST_ADDR` | IP đích (không dùng) | 172.31.0.2 | 172.31.69.28 | 18.219.211.138 |
| `L4_DST_PORT` | Cổng đích (không dùng) | 53 | 80 | 8080 |
| `PROTOCOL` | Giao thức | 17 | 6 | 6 |
| `L7_PROTO` | Giao thức tầng ứng dụng | 5 | 7 | 7 |
| `IN_BYTES` | Byte chiều vào | 142 | 460 | 538 |
| `IN_PKTS` | Số gói chiều vào | 2 | 5 | 5 |
| `OUT_BYTES` | Byte chiều ra | 484 | 1147 | 341 |
| `OUT_PKTS` | Số gói chiều ra | 2 | 5 | 5 |
| `TCP_FLAGS` | Tổng hợp cờ TCP | 0 | 219 | 219 |
| `FLOW_DURATION_MILLISECONDS` | Thời lượng, mili giây | 202 | 48 | 12 |
| `LONGEST_FLOW_PKT` | Gói dài nhất | 242 | 975 | 366 |
| `SHORTEST_FLOW_PKT` | Gói ngắn nhất | 71 | 40 | 40 |
| `MIN_TTL` | TTL nhỏ nhất (loại bỏ) | 128 | 127 | 128 |
| `TCP_WIN_MAX_IN` | Cửa sổ TCP lớn nhất (loại bỏ) | 0 | 65535 | 8192 |
| `Attack` | Nhãn | Benign | DDOS_attack-HOIC | Bot |

## Các nhóm đặc trưng

| Nhóm | Ví dụ ở LYCOS | Ví dụ ở NetFlow v3 |
|---|---|---|
| Khối lượng | `fwd_pkt_cnt`, `bwd_pkt_len_tot` | `IN_BYTES`, `OUT_PKTS` |
| Độ dài gói | `pkt_len_mean`, `pkt_len_std` | `LONGEST_FLOW_PKT`, `NUM_PKTS_UP_TO_128_BYTES` |
| Thời gian | `flow_duration`, `iat_mean`, `active_mean`, `idle_mean` | `FLOW_DURATION_MILLISECONDS`, `SRC_TO_DST_IAT_AVG` |
| Tốc độ | `bytes_per_s`, `pkt_per_s` | `SRC_TO_DST_SECOND_BYTES`, `SRC_TO_DST_AVG_THROUGHPUT` |
| Cờ TCP | `flag_SYN`, `flag_ack`, `flag_psh` | `TCP_FLAGS`, `CLIENT_TCP_FLAGS` |

## Phân bố lớp

Dữ liệu mất cân bằng mạnh. Cột "Chiến thuật" theo bảng ở [README](../README.md#nhóm-chiến-thuật).

### LYCOS-IDS2017

| Lớp | Số flow | Chiến thuật |
|---|---:|---|
| benign | 1.341.169 | |
| dos_hulk | 158.988 | Impact |
| ddos | 95.683 | Impact |
| dos_goldeneye | 6.765 | Impact |
| dos_slowloris | 5.674 | Impact |
| dos_slowhttptest | 4.866 | Impact |
| portscan | 160.106 | Discovery |
| ftp_patator | 8.006 | Credential Access |
| ssh_patator | 5.918 | Credential Access |
| webattack_bruteforce | 1.360 | Credential Access |
| webattack_xss | 661 | Initial Access |
| webattack_sql_injection | 12 | Initial Access |
| heartbleed | 11 | Initial Access |
| bot | 735 | Command and Control |

### NF-ToN-IoT-v3

| Lớp | Số flow gốc | Chiến thuật |
|---|---:|---|
| Benign | 16.792.214 | |
| ddos | 4.141.256 | Impact |
| dos | 203.456 | Impact |
| ransomware | 3.971 | Impact |
| xss | 2.834.435 | Initial Access |
| injection | 381.777 | Initial Access |
| password | 1.594.777 | Credential Access |
| mitm | 6.013 | Credential Access |
| scanning | 1.358.977 | Discovery |
| Backdoor | 203.384 | Command and Control |

### NF-CICIDS2018-v3

| Lớp | Số flow gốc | Chiến thuật |
|---|---:|---|
| Benign | 17.514.626 | |
| DDOS_attack-HOIC | 1.032.311 | Impact |
| DDoS_attacks-LOIC-HTTP | 288.589 | Impact |
| DDOS_attack-LOIC-UDP | 3.450 | Impact |
| DoS_attacks-SlowHTTPTest | 105.550 | Impact |
| DoS_attacks-Hulk | 100.076 | Impact |
| DoS_attacks-GoldenEye | 61.300 | Impact |
| DoS_attacks-Slowloris | 36.040 | Impact |
| FTP-BruteForce | 386.720 | Credential Access |
| SSH-Bruteforce | 188.474 | Credential Access |
| Brute_Force_-Web | 1.618 | Credential Access |
| Brute_Force_-XSS | 480 | Initial Access |
| SQL_Injection | 440 | Initial Access |
| Bot | 207.703 | Command and Control |
| Infilteration | 188.152 | Lateral Movement |

LycoS-Unicas-IDS2018 chỉ dùng cho đánh giá chéo, gồm cùng các nhóm tấn công DoS, DDoS, Patator, Web và Bot.

## Từ dữ liệu thô tới đầu vào mô hình

1. **Bỏ cột định danh:** IP, cổng, mốc thời gian. Giữ các cột này thì mô hình học địa chỉ của testbed.
2. **NetFlow v3 (`src/netflow.py`):** biến đổi `log(1+x)`, lấy tối đa 900.000 flow bình thường và 300.000 flow mỗi họ.
3. **LycoS-Unicas-IDS2018:** chỉ giữ 15% flow bình thường vì tập quá lớn.
4. **Làm sạch:** bỏ dòng có NaN, Inf, bỏ cột hằng.
5. **Loại đặc trưng phụ thuộc ngăn xếp TCP** (`dataset.stack_features`).
6. **Chia dữ liệu:** với mỗi lớp đã biết, 50% cho kiểm thử, 5% cho kiểm định, phần còn lại cho huấn luyện, tối đa 100.000 flow mỗi lớp. Lớp dưới 100 mẫu bị bỏ.
7. **Giấu một họ:** toàn bộ flow của họ đó không xuất hiện khi huấn luyện, chỉ dùng khi kiểm thử.
8. **Chuẩn hoá z-score** theo trung bình và độ lệch chuẩn của tập huấn luyện.

## Vì sao loại đặc trưng phụ thuộc ngăn xếp TCP

Độ dài header và cửa sổ TCP khởi tạo (LYCOS), TTL và cửa sổ TCP (NetFlow) phụ thuộc vào hệ điều hành và công cụ của máy gửi. Trong testbed, tấn công được sinh từ một số ít máy, nên mô hình có thể học thuộc **máy tấn công** thay vì **hành vi tấn công**. Flood 2024 gọi đây là hiện vật mô phỏng và nêu đúng trường hợp TTL.

Các trường này vẫn đo được trong mạng thật. Chúng bị loại không phải vì thiếu dữ liệu, mà vì kẻ tấn công thật dùng máy khác và có thể đổi các giá trị này. Nếu giữ lại, số đẹp hơn nhưng lạc quan: một đặc trưng đơn lẻ đạt AUROC 0,924 với SSH của LYCOS, sau khi loại còn 0,025. Thêm `clean=false` khi chạy để giữ lại các cột này.

## Các tập đã kiểm tra nhưng không dùng

| Tập | Lý do |
|---|---|
| UWF-ZeekData | Benign và tấn công không thu cùng ngày, riêng cột giao thức đã đạt AUROC 0,96–0,999 |
| NF-UNSW-NB15-v3 | Riêng TTL đã đạt AUROC 0,998 |
| NF-BoT-IoT-v3 | Chỉ có 0,3% benign |
| AnoShift | Benign đổi đột ngột giữa các năm |
