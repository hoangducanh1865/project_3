# Demo khép kín trên máy

Minh hoạ một vòng ứng phó: tấn công vào web chạy trên máy, hệ thống phát hiện, báo Telegram, quản trị viên quyết định, nếu không phản hồi thì Gemini quyết định, sau đó cổng chặn nguồn tấn công. **Chỉ tấn công vào máy của mình.**

**Lưu ý khi trình bày:** tầng phát hiện ở đây là luật theo hành vi, không phải HC-CLOSR. Khi thử cho HC-CLOSR đọc lưu lượng localhost, mô hình báo động 100% flow và điểm gần như nhau giữa bình thường và tấn công, đúng với hạn chế chéo tập dữ liệu trong bài báo. Chiến thuật, mức rủi ro và biện pháp D3FEND dùng `src/response.py`.

## Thành phần

| Thành phần | Cổng | Vai trò |
|---|---|---|
| Flaskr (ứng dụng mẫu của Flask) | 5001 | Web cần bảo vệ, tải về khi chạy lần đầu |
| Cổng vào web (`soc.py`) | 8080 | Mọi truy cập đi qua đây, là nơi đếm hành vi và chặn |
| Cổng mồi (`soc.py`) | 2222, 3306, 5900... | Không có dịch vụ thật, ai chạm vào là đang dò quét |
| Bảng điều khiển | 9000 | Giám sát và quyết định |

| Hành vi | Dấu hiệu trong 10 giây | Chiến thuật | Lệnh tấn công |
|---|---|---|---|
| Quét cổng | Chạm từ 4 cổng mồi | Discovery | `python3 demo/attack.py scan` |
| Dò mật khẩu | Từ 15 lần đăng nhập | Credential Access | `python3 demo/attack.py brute` |
| Làm ngập HTTP | Từ 150 yêu cầu | Impact | `python3 demo/attack.py flood` |
| Slowloris | Từ 40 kết nối đang giữ | Impact | `python3 demo/attack.py slow` |

## Chạy

Cần `.env` có `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GEMINI_API_KEY`, và proxy Gemini ở `localhost:20128`.

```bash
bash demo/start.sh                          # chờ quản trị viên 180 giây
DECISION_TIMEOUT=30 bash demo/start.sh      # rút ngắn khi demo
```

Lần đầu tải Flaskr và cài Flask, cần mạng. Mở `http://127.0.0.1:8080` (web) và `http://localhost:9000` (bảng điều khiển).

## Kịch bản 5 phút

1. Mở web và bảng điều khiển. Bấm vài trang để thấy lưu lượng bình thường không gây sự cố.
2. Terminal khác: `python3 demo/attack.py brute`.
3. Telegram nhận sự cố kèm hành vi, chiến thuật, R, biện pháp D3FEND. Bấm **Chặn nguồn 10 phút**. Lệnh tấn công báo bị từ chối.
4. Bấm **Gỡ** trên bảng điều khiển.
5. Chạy `python3 demo/attack.py scan`, lần này không bấm gì. Hết giờ chờ, Gemini tự chọn hành động và báo lý do về Telegram.

Nguồn tấn công là IP mạng LAN của máy, nên cần có Wi-Fi. Nếu không có mạng: `sudo ifconfig lo0 alias 127.0.0.2`, sau đó các lệnh tấn công tự dùng địa chỉ này.

Gemini chỉ được chọn trong ba hành động có sẵn, đều có thời hạn: chặn, giới hạn, bỏ qua. Không gọi được Gemini thì hệ thống dùng giới hạn tốc độ.
