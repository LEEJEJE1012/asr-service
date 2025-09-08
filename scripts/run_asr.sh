#!/usr/bin/env bash
set -euo pipefail

BASE="/root/asr-service"
export PYTHONPATH="$BASE"
cd "$BASE"

# 콘다가 있으면 'server' 환경 활성화
if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
  conda activate server
fi

# 필수 폴더
mkdir -p "$BASE/logs" "$BASE/data/uploads" \
         "$BASE/models/faster-whisper" "$BASE/models/whisper"

# 패키지 점검(없으면 자동 설치) — 최초 1회만 시간 조금 걸릴 수 있음
python -c "import faster_whisper" 2>/dev/null || python -m pip install -r requirements.txt

# 콘다 활성화 후 PATH에 들어온 uvicorn 사용
exec uvicorn app.server:app --host 0.0.0.0 --port 8000 --workers 1