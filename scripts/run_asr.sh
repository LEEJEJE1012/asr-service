#!/usr/bin/env bash
set -euo pipefail
BASE="/root/asr-service"
PY="/root/miniforge3/envs/server/bin/python"   # <-- 위에�
export PYTHONPATH="$BASE"
cd "$BASE"
mkdir -p "$BASE/logs" "$BASE/data/uploads" "$BASE/models/faster-whisper" "$BASE/models/whisper"
exec "$PY" -m uvicorn app.server:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
