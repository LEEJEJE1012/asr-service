#!/bin/bash
# ASR 서비스 자동 배포 스크립트

set -e

echo "🚀 ASR 서비스 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 에러 처리 함수
handle_error() {
    log_error "배포 중 오류가 발생했습니다. 라인 $1에서 실패했습니다."
    exit 1
}

trap 'handle_error $LINENO' ERR

# 1. 프로젝트 업데이트
log_info "📥 프로젝트 업데이트..."
cd /root/asr-service

# Git 저장소가 있는 경우에만 pull 실행
if [ -d ".git" ]; then
    git pull origin main || log_warning "Git pull 실패 (로컬 변경사항이 있을 수 있음)"
else
    log_warning "Git 저장소가 아닙니다. 수동으로 코드를 업데이트하세요."
fi

# 2. 의존성 업데이트
log_info "📦 의존성 업데이트..."
if [ -f "Makefile" ]; then
    make install
else
    log_warning "Makefile이 없습니다. 수동으로 의존성을 설치하세요."
    pip install -r requirements.txt
fi

# 3. 디렉토리 생성
log_info "📁 필요한 디렉토리 생성..."
mkdir -p data/uploads
mkdir -p logs
mkdir -p models/faster-whisper
mkdir -p models/whisper

# 4. 모델 워밍업
log_info "🤖 모델 워밍업..."
if [ -f "Makefile" ]; then
    make warmup
else
    log_warning "Makefile이 없습니다. 수동으로 모델을 워밍업하세요."
    PYTHONPATH=/root/asr-service python scripts/warmup_models.py
fi

# 5. Supervisor 설정 파일 생성
log_info "⚙️ Supervisor 설정 파일 생성..."
cat > /etc/supervisor/conf.d/asr-service.conf << 'EOF'
[program:asr-service]
command=/root/miniforge3/envs/server/bin/python -m uvicorn app.server:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
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

# 6. Supervisor 서비스 시작 (필요시)
log_info "🔧 Supervisor 서비스 확인..."
if ! systemctl is-active --quiet supervisor; then
    log_info "Supervisor 서비스 시작..."
    systemctl start supervisor
    systemctl enable supervisor
fi

# 7. Supervisor 설정 리로드
log_info "🔄 Supervisor 설정 리로드..."
supervisorctl reread
supervisorctl update

# 8. 서비스 재시작
log_info "🚀 서비스 재시작..."
supervisorctl restart asr-service

# 9. 상태 확인
log_info "✅ 상태 확인..."
sleep 5

# 서비스 상태 확인
if supervisorctl status asr-service | grep -q "RUNNING"; then
    log_success "ASR 서비스가 정상적으로 실행 중입니다."
else
    log_error "ASR 서비스가 실행되지 않았습니다."
    supervisorctl status asr-service
    exit 1
fi

# 10. 헬스체크
log_info "🏥 헬스체크..."
for i in {1..5}; do
    if curl -f -s http://localhost:8000/healthz > /dev/null; then
        log_success "헬스체크 성공!"
        break
    else
        log_warning "헬스체크 실패 (시도 $i/5)..."
        sleep 2
    fi
    
    if [ $i -eq 5 ]; then
        log_error "헬스체크 실패. 서비스 로그를 확인하세요."
        supervisorctl tail asr-service
        exit 1
    fi
done

# 11. 최종 상태 출력
log_info "📊 최종 상태:"
echo "----------------------------------------"
supervisorctl status asr-service
echo "----------------------------------------"
echo "🌐 API 문서: http://localhost:8000/docs"
echo "🏥 헬스체크: http://localhost:8000/healthz"
echo "📝 로그 파일: /root/asr-service/logs/supervisor.log"
echo "----------------------------------------"

log_success "🎉 ASR 서비스 배포가 완료되었습니다!"
