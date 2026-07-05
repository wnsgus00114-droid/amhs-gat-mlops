#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d .venv-mlops ]; then
    python3 -m venv .venv-mlops
fi

. .venv-mlops/bin/activate
python -m pip install --upgrade pip
python -m pip install -r mlops_k8s/requirements_ec2.txt

python -m http.server 8091 --directory oht_3d > .oht3d.log 2>&1 &
STATIC_PID="$!"
trap 'kill "$STATIC_PID" >/dev/null 2>&1 || true' EXIT

export AMHS_3D_URL="${AMHS_3D_URL:-http://127.0.0.1:8091/index.html}"
exec streamlit run mlops_k8s/app.py --server.address 0.0.0.0 --server.port 8501
