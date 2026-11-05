#!/usr/bin/env bash
# Dựng ứng dụng đích Flaskr (mã nguồn mở của dự án Flask) rồi chạy trung tâm giám sát. Dùng: bash demo/start.sh
set -e
cd "$(dirname "$0")/.."
if [ ! -d demo/target/flask ]; then
  mkdir -p demo/target
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/pallets/flask demo/target/flask
  git -C demo/target/flask sparse-checkout set examples/tutorial
  python3.12 -m venv demo/target/venv
  demo/target/venv/bin/pip install -q flask
  demo/target/venv/bin/pip install -q -e demo/target/flask/examples/tutorial
  (cd demo/target && venv/bin/flask --app flaskr init-db)
fi
(cd demo/target && exec venv/bin/flask --app flaskr run -p 5001 > flask.log 2>&1) &
trap 'kill %1 2>/dev/null' EXIT
sleep 2
python3 demo/soc.py
