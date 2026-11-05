#!/usr/bin/env bash
# Tải và chuẩn bị dữ liệu vào data/. Cần gdown, kaggle (đặt KAGGLE_API_TOKEN). Xem datasets/README.md.
set -euo pipefail
mkdir -p data
gdown -q 1PUMAbjz5L0MKiL3P-bEFTYYOcB6zPYB2 -O data/lycos.csv      # LYCOS-IDS2017, khoảng 860 MB
gdown -q 12dQPcqRDJFeJGmqqshzdYN8M5t5tMXbQ -O data/lycos18.csv    # LycoS-Unicas-IDS2018, khoảng 5,5 GB
kaggle datasets download athena21/netflow-v3-datasets -p data/nf_raw --unzip -q
python -m src.netflow data/nf_raw data/nf
