"""
ASR 서비스 로깅 설정
모든 로그에 시간 정보를 포함하도록 설정
"""

import logging
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

class TimestampFormatter(logging.Formatter):
    """시간 정보를 포함한 커스텀 포매터 (한국 시간)"""
    
    def format(self, record):
        # 한국 시간으로 변환 (UTC+9)
        kst = timezone(timedelta(hours=9))
        kst_time = datetime.now(kst)
        record.timestamp = kst_time.strftime('%Y-%m-%d %H:%M:%S KST')
        return super().format(record)

def setup_comprehensive_logging():
    """포괄적인 로깅 설정"""
    
    # 로그 포맷 정의
    log_format = '%(timestamp)s - %(name)s - %(levelname)s - %(message)s'
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(TimestampFormatter(log_format))
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 추가 (선택적)
    try:
        log_dir = Path("/root/asr-service/logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_dir / "asr_service.log")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(TimestampFormatter(log_format))
        root_logger.addHandler(file_handler)
    except Exception as e:
        # 파일 로깅 실패 시 콘솔만 사용
        pass
    
    # uvicorn 관련 로거들 설정
    uvicorn_loggers = [
        'uvicorn',
        'uvicorn.access', 
        'uvicorn.error',
        'uvicorn.asgi',
        'fastapi'
    ]
    
    for logger_name in uvicorn_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        # 기존 핸들러 제거
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        # 새로운 핸들러 추가
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(TimestampFormatter(log_format))
        logger.addHandler(handler)
        logger.propagate = False  # 중복 방지
    
    # ASR 서비스 관련 로거들 설정
    service_loggers = [
        'app.services.asr_fw',
        'app.services.asr_ow',
        'app.services.policy_search',
        'app.services.edge_tts',
        'app.services.audio_io',
        'app.routers.pipeline'
    ]
    
    for logger_name in service_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.propagate = True
    
    # 외부 라이브러리 로거들 설정 (에러만 표시)
    external_loggers = [
        'httpx',
        'httpcore',
        'asyncio',
        'sentence_transformers',
        'qdrant_client',
        'edge_tts',
        'faster_whisper',
        'whisper'
    ]
    
    for logger_name in external_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)  # 에러만 표시
        logger.propagate = True

def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 반환"""
    return logging.getLogger(name)

# 로깅 설정 실행
setup_comprehensive_logging()
