# 🎤 ASR 복지정책 어시스턴트 배포 가이드

이 가이드는 AI 기반 음성 인식 및 복지정책 추천 시스템을 supervisorctl을 사용하여 배포하는 완전한 과정을 설명합니다.

> **통합 AI 파이프라인**: 음성 입력 → STT → 벡터 검색 → 정책 추천 → 음성 합성 → MP3 응답

## 📋 목차

1. [시스템 요구사항](#시스템-요구사항)
2. [프로젝트 클론 및 환경 설정](#프로젝트-클론-및-환경-설정)
3. [의존성 설치](#의존성-설치)
4. [모델 다운로드 및 워밍업](#모델-다운로드-및-워밍업)
5. [정책 인덱스 구축](#정책-인덱스-구축)
6. [Supervisor 설정](#supervisor-설정)
7. [서비스 배포](#서비스-배포)
8. [모니터링 및 관리](#모니터링-및-관리)
9. [문제 해결](#문제-해결)

## 🖥️ 시스템 요구사항

### 하드웨어
- **GPU**: NVIDIA GPU (CUDA 지원, 권장)
- **메모리**: 최소 8GB RAM (권장: 16GB+)
- **저장공간**: 최소 15GB 여유 공간
  - AI 모델: ~3GB (Faster-Whisper, BGE-M3)
  - 벡터 데이터베이스: ~500MB
  - 복지정책 데이터: ~10MB

### 소프트웨어
- **OS**: Ubuntu 18.04+ 또는 CentOS 7+
- **Python**: 3.8+
- **CUDA**: 11.8+ 또는 12.4+ (GPU 사용 시)
- **FFmpeg**: 오디오 처리용
- **Docker**: 선택사항

## 🚀 프로젝트 클론 및 환경 설정

### 1. 프로젝트 클론
```bash
# 프로젝트 디렉토리로 이동
cd /root

# Git 저장소 클론
git clone <repository-url> asr-service
cd asr-service

# 또는 압축 파일 해제
# wget <download-url>
# tar -xzf asr-service.tar.gz
# cd asr-service
```

### 2. 환경 변수 설정
```bash
# .env 파일 생성
cat > .env << 'EOF'
# 서버 설정
ASR_HOST=0.0.0.0
ASR_PORT=8000
CORS_ORIGINS=*

# ASR 엔진 설정
ASR_ENGINE_DEFAULT=fw
ASR_LANGUAGE=ko
ASR_FW_BEAM=1
ASR_MAX_AUDIO_SEC=15

# 디렉토리 설정
ASR_BASE_DIR=/root/asr-service
ASR_UPLOAD_DIR=/root/asr-service/data/uploads
ASR_LOG_DIR=/root/asr-service/logs
ASR_MODEL_DIR=/root/asr-service/models

# AI 모델 경로
FW_MODEL_DIR=/root/asr-service/models/faster-whisper/large-v3
OW_MODEL_DIR=/root/asr-service/models/whisper/medium

# FW 실행 옵션
FW_DEVICE=cuda
FW_COMPUTE=float16

# 정책 검색 설정
POLICY_CSV_PATH=/root/asr-service/data/csv/gov24_services_with_tags.csv
QDRANT_PATH=/root/asr-service/qdrant_db
EMBED_MODEL=BAAI/bge-m3
TOPK_DEFAULT=3

# TTS 설정
TTS_VOICE_DEFAULT=ko-KR-SunHiNeural
EOF
```

### 3. 디렉토리 구조 생성
```bash
# 필요한 디렉토리 생성
mkdir -p data/uploads
mkdir -p data/csv
mkdir -p logs
mkdir -p models/faster-whisper
mkdir -p models/whisper
mkdir -p qdrant_db
```

## 📦 의존성 설치

### 1. 시스템 패키지 설치
```bash
# Ubuntu/Debian
apt update
apt install -y python3 python3-pip python3-venv git curl wget

# CentOS/RHEL
yum update -y
yum install -y python3 python3-pip git curl wget
```

### 2. Python 환경 설정
```bash
# Python 가상환경 생성 (선택사항)
python3 -m venv /root/miniforge3/envs/server
source /root/miniforge3/envs/server/bin/activate

# 또는 기존 환경 사용
export PYTHONPATH=/root/asr-service
```

### 3. Python 패키지 설치
```bash
# Makefile을 사용한 설치 (권장)
make install

# 또는 수동 설치
pip install --upgrade pip wheel setuptools

# CUDA 지원 PyTorch 설치
pip install --index-url https://download.pytorch.org/whl/cu124 torch torchaudio

# 프로젝트 의존성 설치
pip install -r requirements.txt

# FFmpeg 설치
apt-get update && apt-get install -y ffmpeg
```

## 🤖 모델 다운로드 및 워밍업

### 1. 모델 워밍업 실행
```bash
# Makefile을 사용한 워밍업 (권장)
make warmup

# 또는 수동 실행
PYTHONPATH=/root/asr-service python scripts/warmup_models.py
```

### 2. 모델 다운로드 확인
```bash
# 모델 파일 확인
ls -la models/faster-whisper/
ls -la models/whisper/

# 모델 크기 확인
du -sh models/
```

## 🔍 정책 인덱스 구축

### 1. 정책 데이터 확인
```bash
# 정책 CSV 파일 확인
ls -la data/csv/gov24_services_with_tags.csv
wc -l data/csv/gov24_services_with_tags.csv
```

### 2. 벡터 인덱스 구축
```bash
# 정책 인덱스 구축 (최초 1회)
PYTHONPATH=/root/asr-service python scripts/build_policy_index.py

# 인덱스 파일 확인
ls -la qdrant_db/
```

> **참고**: 이 과정은 2,881개의 복지정책을 벡터 임베딩으로 변환하여 Qdrant 데이터베이스에 저장합니다. 약 2-3분 소요됩니다.

## ⚙️ Supervisor 설정

### 1. Supervisor 설치
```bash
# Ubuntu/Debian
apt install supervisor -y

# CentOS/RHEL
yum install supervisor -y

# Supervisor 서비스 시작
systemctl start supervisor
systemctl enable supervisor
```

### 2. ASR 서비스 설정 파일 생성
```bash
# Supervisor 설정 파일 생성
cat > /etc/supervisor/conf.d/asr-service.conf << 'EOF'
[program:asr-service]
command=/root/miniforge3/envs/server/bin/python -m uvicorn app.server:app --host 0.0.0.0 --port 8000 --workers 1
directory=/root/asr-service
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/root/asr-service/logs/supervisor.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
environment=PYTHONPATH="/root/asr-service"
stderr_logfile=/root/asr-service/logs/supervisor_error.log
stderr_logfile_maxbytes=50MB
stderr_logfile_backups=10
EOF
```

### 3. Supervisor 설정 검증
```bash
# 설정 파일 문법 검사
supervisorctl reread

# 설정 업데이트
supervisorctl update
```

## 🚀 서비스 배포

### 1. 서비스 시작
```bash
# ASR 서비스 시작
supervisorctl start asr-service

# 서비스 상태 확인
supervisorctl status asr-service
```

### 2. 서비스 테스트
```bash
# 헬스체크
curl http://localhost:8000/healthz

# API 문서 확인
curl http://localhost:8000/docs

# 서비스 로그 확인
supervisorctl tail asr-service
```

### 3. 자동 시작 설정
```bash
# Supervisor 자동 시작 확인
systemctl is-enabled supervisor

# 필요시 자동 시작 활성화
systemctl enable supervisor
```

## 📊 모니터링 및 관리

### 1. 서비스 상태 모니터링
```bash
# 서비스 상태 확인
supervisorctl status asr-service

# 실시간 로그 모니터링
supervisorctl tail -f asr-service

# 로그 파일 직접 확인
tail -f /root/asr-service/logs/supervisor.log
```

### 2. 서비스 관리 명령어
```bash
# 서비스 재시작
supervisorctl restart asr-service

# 서비스 중지
supervisorctl stop asr-service

# 서비스 시작
supervisorctl start asr-service

# 모든 서비스 상태 확인
supervisorctl status
```

### 3. 성능 모니터링
```bash
# 프로세스 모니터링
ps aux | grep uvicorn

# 메모리 사용량 확인
free -h

# GPU 사용량 확인 (NVIDIA GPU)
nvidia-smi

# 디스크 사용량 확인
df -h
```

### 4. 로그 관리
```bash
# 로그 로테이션 설정
cat > /etc/logrotate.d/asr-service << 'EOF'
/root/asr-service/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF

# 로그 로테이션 테스트
logrotate -d /etc/logrotate.d/asr-service
```

## 🔧 문제 해결

### 1. 일반적인 문제들

#### 서비스가 시작되지 않는 경우
```bash
# Supervisor 로그 확인
journalctl -u supervisor -f

# 설정 파일 문법 검사
supervisorctl reread

# 수동으로 서비스 실행 테스트
cd /root/asr-service
/root/miniforge3/envs/server/bin/python -m uvicorn app.server:app --host 0.0.0.0 --port 8000
```

#### 포트 충돌 문제
```bash
# 포트 사용 확인
netstat -tlnp | grep :8000
# 또는
lsof -i :8000

# 프로세스 종료
pkill -f uvicorn
```

#### 모델 로딩 실패
```bash
# 모델 파일 확인
ls -la models/faster-whisper/
ls -la models/whisper/

# 모델 재다운로드
rm -rf models/
make warmup
```

### 2. 로그 분석
```bash
# 에러 로그 확인
tail -f /root/asr-service/logs/supervisor_error.log

# 애플리케이션 로그 확인
tail -f /root/asr-service/logs/supervisor.log

# 시스템 로그 확인
journalctl -u supervisor -f
```

### 3. 성능 최적화
```bash
# GPU 메모리 최적화
export CUDA_VISIBLE_DEVICES=0

# Python 메모리 최적화
export PYTHONOPTIMIZE=1

# 워커 수 조정 (설정 파일에서)
# workers 1 → workers 2 (CPU 코어 수에 따라)
```

## 📝 배포 스크립트

### 자동 배포 스크립트
```bash
#!/bin/bash
# deploy.sh

set -e

echo "🚀 ASR 서비스 배포 시작..."

# 1. 프로젝트 업데이트
echo "📥 프로젝트 업데이트..."
cd /root/asr-service
git pull origin main

# 2. 의존성 업데이트
echo "📦 의존성 업데이트..."
make install

# 3. 모델 워밍업
echo "🤖 모델 워밍업..."
make warmup

# 4. Supervisor 설정 리로드
echo "⚙️ Supervisor 설정 리로드..."
supervisorctl reread
supervisorctl update

# 5. 서비스 재시작
echo "🔄 서비스 재시작..."
supervisorctl restart asr-service

# 6. 상태 확인
echo "✅ 상태 확인..."
sleep 5
supervisorctl status asr-service

# 7. 헬스체크
echo "🏥 헬스체크..."
curl -f http://localhost:8000/healthz && echo "✅ 서비스 정상 동작"

echo "🎉 배포 완료!"
```

### 사용법
```bash
chmod +x deploy.sh
./deploy.sh
```

## 🔗 API 엔드포인트

### 기본 엔드포인트
- **헬스체크**: `GET /healthz`
- **API 문서**: `GET /docs`
- **통합 파이프라인**: `POST /stt_search_tts` ⭐️
- **음성 변환**: `POST /transcribe`
- **음성 합성**: `POST /synthesize`

### 통합 파이프라인 사용 예시 (핵심 기능)
```bash
# 음성 → STT → 정책 검색 → TTS → MP3 응답
curl -X POST "http://localhost:8000/stt_search_tts" \
  -F "audio=@voice_input.wav" \
  -F "engine=fw" \
  -F "language=ko" \
  -F "topk=5" \
  -F "tts_engine=edge_tts" \
  -F "voice=ko-KR-SunHiNeural"
```

### 개별 서비스 사용 예시
```bash
# 헬스체크
curl http://localhost:8000/healthz

# 음성 변환만
curl -X POST "http://localhost:8000/transcribe" \
  -F "audio=@sample.wav" \
  -F "engine=fw" \
  -F "language=ko"

# 음성 합성만
curl -X POST "http://localhost:8000/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "안녕하세요. 복지정책 안내입니다.",
    "voice": "ko-KR-SunHiNeural"
  }'
```

### 응답 형식
```json
{
  "stt": {
    "text": "청년 주거 지원 정책 알려줘",
    "engine": "fw",
    "decode_s": 0.736,
    "audio_sec": 4.885
  },
  "search": {
    "query": "청년 주거 지원 정책 알려줘",
    "topk": 5,
    "results": [
      {
        "rank": 1,
        "service_name": "긴급복지 주거지원",
        "score": 0.583,
        "support": "위기사유 발생으로 생계유지가 곤란한 저소득층에게 주거지원",
        "tags": ["주거", "긴급복지", "저소득층"]
      }
    ]
  },
  "summary": "추천 정책은 긴급복지 주거지원입니다. 요약: 위기사유 발생으로...",
  "tts": {
    "voice": "ko-KR-SunHiNeural",
    "mp3_b64": "SUQzBAAAAAAAIlRTU0UAAAAOAAADTGF2ZjYyLjMuMTAw...",
    "duration_est_s": 22.5
  }
}
```

## 📞 지원

문제가 발생하면 다음을 확인하세요:
1. 로그 파일: `/root/asr-service/logs/`
2. Supervisor 상태: `supervisorctl status`
3. 시스템 리소스: `htop`, `nvidia-smi`

---

이 가이드를 따라하면 ASR 서비스를 안정적으로 배포하고 관리할 수 있습니다.
