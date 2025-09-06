#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/workspace/asr-service
uvicorn app.server:app --host 0.0.0.0 --port 8000 --workers 1
