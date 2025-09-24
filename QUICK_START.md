# ASR 서비스 빠른 시작 가이드

## 🚀 5분 만에 배포하기

### 1. 프로젝트 준비
```bash

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
curl http://localhost:8000/docs
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

### 헬스체크
```bash
curl http://localhost:8000/healthz
```

### 음성 변환
```bash
curl -X POST "http://localhost:8000/transcribe" \
  -F "audio=@sample.wav" \
  -F "engine=fw" \
  -F "language=ko"
```

### API 문서
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## ❗ 문제 해결

### 서비스가 시작되지 않는 경우
```bash
# 로그 확인
supervisorctl tail asr-service

# 수동 실행 테스트
cd /root/asr-service
/root/miniforge3/envs/server/bin/python -m uvicorn app.server:app --host 0.0.0.0 --port 8000
```

### 포트 충돌
```bash
# 포트 사용 확인
lsof -i :8000

# 프로세스 종료
pkill -f uvicorn
```

---

더 자세한 내용은 `DEPLOYMENT_GUIDE.md`를 참조하세요.
