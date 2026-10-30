#!/usr/bin/env bash
# Mở SSH server trên runtime Colab, truy cập từ máy qua Cloudflare quick tunnel (không cần tài khoản).
# Ô cuối của notebooks/colab.ipynb chạy script này; ô phải chạy liên tục, dừng ô là đóng tunnel.
# Đăng nhập: root bằng khoá công khai của tài khoản GitHub (https://github.com/<user>.keys), không mật khẩu.
# Colab chỉ cho SSH với gói trả phí còn compute unit (Colab FAQ).
#
# Tác giả: Hoàng Đức Anh
set -euo pipefail
GITHUB_USER=${GITHUB_USER:-hoangducanh1865}

apt-get -qq update > /dev/null
apt-get -qq install -y openssh-server tmux > /dev/null
mkdir -p /root/.ssh /run/sshd
chmod 700 /root/.ssh
curl -fsSL "https://github.com/${GITHUB_USER}.keys" > /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
ssh-keygen -A > /dev/null
# Cổng riêng: sshd_config của Colab ghi 2222 nhưng cổng đó đã bị dùng.
PORT=2022
pkill -f "sshd -p ${PORT}" || true   # chạy lại thì thay server cũ
rm -f /tmp/sshd.log
/usr/sbin/sshd -p "${PORT}" -E /tmp/sshd.log -o ListenAddress=127.0.0.1 -o PasswordAuthentication=no \
  -o PermitRootLogin=prohibit-password
sleep 1
if ! (exec 3<> "/dev/tcp/127.0.0.1/${PORT}") 2> /dev/null; then
  echo "sshd không nghe ở 127.0.0.1:${PORT}. Log:" && cat /tmp/sshd.log && exit 1
fi

# Phiên SSH bắt đầu với môi trường trống: chép PATH, CUDA và biến Colab của notebook.
export -p | grep -E '^declare -x (PATH|LD_LIBRARY_PATH|LIBRARY_PATH|PYTHONPATH|CUDA[A-Z_]*|NV[A-Z_]*|COLAB[A-Z_]*)=' \
  > /root/.colab_env
REPO=$(cd "$(dirname "$0")/.." && pwd)   # phiên SSH bắt đầu trong repo này
# Đặt ở đầu .bashrc: .bashrc của Ubuntu dừng sớm với lệnh không tương tác (ssh host 'lệnh').
grep -q colab_env /root/.bashrc || sed -i "1i source /root/.colab_env; cd '${REPO}'" /root/.bashrc

# Chạy lại trong cùng runtime: dừng tunnel cũ, giữ file cloudflared (không ghi đè được khi đang chạy).
pkill -f "cloudflared tunnel" || true
if [[ ! -x /usr/local/bin/cloudflared ]]; then
  curl -fsSL -o /usr/local/bin/cloudflared \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
  chmod +x /usr/local/bin/cloudflared
fi
rm -f /tmp/cloudflared.log
echo "Đang mở tunnel (log đầy đủ: /tmp/cloudflared.log)..."
cloudflared tunnel --no-autoupdate --url "ssh://127.0.0.1:${PORT}" 2>&1 | while read -r line; do
  echo "$line" >> /tmp/cloudflared.log
  if [[ -z ${host:-} && $line =~ https://([a-z0-9-]+\.trycloudflare\.com) ]]; then
    host=${BASH_REMATCH[1]}
    echo "SSH sẵn sàng. Trên máy:  ssh ${host}"
  fi
done
