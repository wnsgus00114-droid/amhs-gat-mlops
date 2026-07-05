#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d .venv-mlops ]; then
    python3 -m venv .venv-mlops
fi

# EC2 lab instances are small, so the demo server uses the lightweight
# pandas-based fallback when PyTorch is not installed.
. .venv-mlops/bin/activate
python -m pip install --upgrade pip
python -m pip install -r mlops_k8s/requirements_ec2.txt

exec streamlit run mlops_k8s/app.py --server.address 0.0.0.0 --server.port 8501
