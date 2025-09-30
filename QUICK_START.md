# 🎤 ASR 복지정책 어시스턴트 빠른 시작 가이드

> **통합 AI 파이프라인**: 음성 입력 → STT → 벡터 검색 → 정책 추천 → 음성 합성 → MP3 응답

## 🚀 5분 만에 배포하기

### 1. 프로젝트 준비
```bash
# 환경 활성화
source /root/miniforge3/bin/activate base

# 프로젝트 디렉토리로 이동
cd /root/asr-service

# 실행 권한 부여
chmod +x deploy.sh
```

### 2. 자동 배포 실행
```bash
# 자동 배포 스크립트 실행
./deploy.sh
```

### 3. 서비스 확인
```bash
# 헬스체크
curl http://localhost:8000/healthz

# API 문서 확인
echo "🌐 API 문서: http://localhost:8000/docs"
echo "📱 Swagger UI: http://localhost:8000/docs"
echo "📖 ReDoc: http://localhost:8000/redoc"
```

## 📋 수동 배포 (단계별)

### 1. 의존성 설치
```bash
make install
```

### 2. 모델 워밍업
```bash
make warmup
```

### 2.5. 정책 인덱스 구축 (최초 1회)
```bash
# 복지정책 벡터 인덱스 구축
PYTHONPATH=/root/asr-service python scripts/build_policy_index.py
```

### 3. Supervisor 설정
```bash

which supervisorctl

apt update && apt install -y supervisor
# 설정 파일 생성
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
EOF

# 설정 적용
supervisorctl reread
supervisorctl update
supervisorctl start asr-service
```

### 4. 상태 확인
```bash
supervisorctl status asr-service
```

## 🔧 관리 명령어

### 서비스 관리
```bash
# 시작
supervisorctl start asr-service

# 중지
supervisorctl stop asr-service

# 재시작
supervisorctl restart asr-service

# 상태 확인
supervisorctl status asr-service
```

### 로그 확인
```bash
# 실시간 로그
supervisorctl tail -f asr-service

# 로그 파일 직접 확인
tail -f /root/asr-service/logs/supervisor.log
```

## 🌐 API 사용법

### 🎯 통합 파이프라인 (핵심 기능)
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

### 🔧 개별 서비스

#### 헬스체크
```bash
curl http://localhost:8000/healthz
```

#### 음성 변환만
```bash
curl -X POST "http://localhost:8000/transcribe" \
  -F "audio=@sample.wav" \
  -F "engine=fw" \
  -F "language=ko"
```

#### 음성 합성만
```bash
curl -X POST "http://localhost:8000/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "안녕하세요. 복지정책 안내입니다.",
    "voice": "ko-KR-SunHiNeural"
  }'
```

### 📊 주요 파라미터

#### STT 엔진
- `fw`: Faster-Whisper (빠름, 권장)
- `ow`: OpenAI Whisper (정확함)

#### TTS 음성
- `ko-KR-SunHiNeural`: 여성, 밝은 톤 (기본값)
- `ko-KR-InJoonNeural`: 남성, 중성 톤
- `ko-KR-HoYoungNeural`: 여성, 차분한 톤

#### 검색 옵션
- `topk`: 상위 N개 정책 추천 (1-10)
- `beam_size`: Faster-Whisper 빔 크기 (1-5)

### 📚 API 문서
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## ❗ 문제 해결

### 서비스가 시작되지 않는 경우
```bash
# 로그 확인
supervisorctl tail asr-service
tail -f /root/asr-service/logs/supervisor.log

# 수동 실행 테스트
cd /root/asr-service
PYTHONPATH=/root/asr-service /root/miniforge3/envs/server/bin/python -m uvicorn app.server:app --host 0.0.0.0 --port 8000
```

### 모델 로딩 실패
```bash
# 모델 재다운로드
make warmup

# GPU 메모리 확인
nvidia-smi
```

### 정책 검색이 안 되는 경우
```bash
# 정책 인덱스 재구축
PYTHONPATH=/root/asr-service python scripts/build_policy_index.py

# 인덱스 파일 확인
ls -la qdrant_db/
```

### 포트 충돌
```bash
# 포트 사용 확인
lsof -i :8000
netstat -tlnp | grep :8000

# 프로세스 종료
pkill -f uvicorn
supervisorctl stop asr-service
```

### 성능 이슈
```bash
# GPU 사용률 확인
watch -n 1 nvidia-smi

# 메모리 사용량 확인
free -h
ps aux | grep python
```

---

더 자세한 내용은 `DEPLOYMENT_GUIDE.md`를 참조하세요.
