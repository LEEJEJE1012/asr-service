# 🎤 ASR Welfare Policy Assistant

> **AI 기반 음성 인식 및 복지정책 추천 시스템**

음성 입력을 통해 복지정책을 검색하고, AI가 음성으로 답변하는 통합 서비스입니다. Faster-Whisper/OpenAI Whisper를 활용한 고정밀 음성 인식, 벡터 검색 기반 정책 추천, 그리고 Edge TTS를 통한 자연스러운 음성 응답까지 완전한 파이프라인을 제공합니다.

## ✨ 주요 기능

### 🎯 **End-to-End AI 파이프라인**
```
음성 입력 → STT → 벡터 검색 → 정책 추천 → 음성 합성 → MP3 응답
```

### 🔧 **핵심 컴포넌트**

#### 1. **다중 ASR 엔진 지원**
- **Faster-Whisper**: 고성능 C++ 기반 음성 인식
- **OpenAI Whisper**: 정확도 우선 음성 인식
- **실시간 처리**: 16kHz 모노 오디오 최적화

#### 2. **지능형 정책 검색**
- **벡터 데이터베이스**: Qdrant 기반 고성능 검색
- **임베딩 모델**: BAAI/bge-m3 다국어 임베딩
- **의미 기반 검색**: 키워드가 아닌 의미 유사도 기반

#### 3. **자연스러운 음성 응답**
- **Edge TTS**: Microsoft Edge 음성 합성
- **SpeechT5**: Hugging Face 고품질 TTS (선택)
- **한국어 최적화**: 자연스러운 한국어 음성 생성

## 🏗️ 시스템 아키텍처

### **서비스 구조**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Audio Input   │───▶│   ASR Engine    │───▶│  Policy Search  │
│   (WAV/MP3)     │    │ (FW/OpenAI)     │    │   (Qdrant)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  MP3 Response   │◀───│   TTS Engine    │◀───│   Summary Gen   │
│   (Base64)      │    │ (Edge/SpeechT5) │    │   (Top Policy)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **기술 스택**
- **Backend**: FastAPI + Uvicorn
- **ASR**: Faster-Whisper, OpenAI Whisper
- **Vector DB**: Qdrant
- **Embedding**: BAAI/bge-m3
- **TTS**: Edge TTS, SpeechT5
- **Deployment**: Supervisor

## 🚀 빠른 시작

### **1. 자동 배포 (권장)**
```bash
# 프로젝트 클론
git clone <repository-url> asr-service
cd asr-service

# 자동 배포 실행
chmod +x deploy.sh
./deploy.sh
```

### **2. 수동 배포**
```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 설정
cp .env.example .env

# 정책 인덱스 구축
python scripts/build_policy_index.py

# 서버 실행
uvicorn app.server:app --host 0.0.0.0 --port 8000
```

## 📡 API 사용법

### **통합 파이프라인 엔드포인트**
```bash
curl -X POST "http://localhost:8000/stt_search_tts" \
  -F "audio=@voice_input.wav" \
  -F "engine=fw" \
  -F "language=ko" \
  -F "topk=5" \
  -F "tts_engine=edge_tts" \
  -F "voice=ko-KR-SunHiNeural"
```

### **Request Body 필드 상세 설명**

| 필드 | 타입 | 필수 | 권장 | 설명 | 지원 옵션 |
|------|------|------|--------|------|-----------|
| **`audio`** | `File` | ✅ | - | **음성 파일** (WAV, MP3, M4A 등) | 모든 오디오 형식 |
| **`engine`** | `string` | ✅  | `"fw"` | **STT 엔진 선택** | `"fw"` (Faster-Whisper)<br>`"ow"` (OpenAI Whisper) |
| **`language`** | `string` | ✅  | `"ko"` | **언어 코드** | `"ko"` (한국어)<br>`"en"` (영어)<br>`"ja"` (일본어) 등 |
| **`beam_size`** | `integer` | ✅  | `5` | **Faster-Whisper 빔 크기** | `1` ~ `5` (높을수록 정확하지만 느림) |
| **`topk`** | `integer` | ✅  | `5` | **검색 결과 개수** | `1` ~ `10` (상위 N개 정책 추천) |
| **`voice`** | `string` | ✅  | `"ko-KR-SunHiNeural"` | **TTS 음성** (Edge TTS만) | `"ko-KR-SunHiNeural"`<br>`"ko-KR-InJoonNeural"`<br>`"ko-KR-HoYoungNeural"` 등 |
| **`tts_engine`** | `string` | ✅ | `"edge_tts"` | **TTS 엔진 선택** | `"edge_tts"` (권장)<br>`"speecht5"` (실험적) |

### **필드별 상세 설명**

#### **🎤 `audio` (음성 파일)**
- **지원 형식**: WAV, MP3, M4A, FLAC, OGG 등
- **권장 형식**: WAV (16kHz, 모노)
- **최대 길이**: 15초 (설정 가능)
- **최대 크기**: 10MB

#### **🔧 `engine` (STT 엔진)**
- **`fw` (Faster-Whisper)**: 
  - ⚡ **빠른 처리**: C++ 기반 고성능
  - 🎯 **높은 정확도**: 95%+ 한국어 인식
  - 💾 **메모리 효율**: GPU 메모리 최적화
- **`ow` (OpenAI Whisper)**:
  - 🎯 **최고 정확도**: 98%+ 인식률
  - 🐌 **느린 처리**: Python 기반
  - 💾 **높은 메모리**: 더 많은 GPU 메모리 필요

#### **🌍 `language` (언어 설정)**
- **`ko`**: 한국어 (기본값)
- **`en`**: 영어
- **`ja`**: 일본어
- **`zh`**: 중국어
- **`auto`**: 자동 감지 (느림)

#### **⚙️ `beam_size` (빔 크기)**
- **`1`**: 빠른 처리, 기본 정확도
- **`3`**: 균형잡힌 성능
- **`5`**: 최고 정확도, 느린 처리

#### **🔍 `topk` (검색 결과 수)**
- **`1`**: 최고 정책만 추천
- **`3`**: 상위 3개 정책 (기본값)
- **`5`**: 상위 5개 정책 (권장)
- **`10`**: 상위 10개 정책 (상세 분석)

#### **🎵 `voice` (TTS 음성)**
- **`ko-KR-SunHiNeural`**: 여성, 밝은 톤 (기본값)
- **`ko-KR-InJoonNeural`**: 남성, 중성 톤
- **`ko-KR-HoYoungNeural`**: 여성, 차분한 톤
- **`ko-KR-YuJinNeural`**: 여성, 친근한 톤

#### **🔊 `tts_engine` (TTS 엔진)**
- **`edge_tts`**: 
  - ✅ **권장**: 안정적이고 빠름
  - 🎯 **높은 품질**: 자연스러운 한국어
  - ⚡ **빠른 처리**: 2-3초 내 합성
- **`speecht5`**: 
  - ⚠️ **실험적**: 품질 불안정
  - 🐌 **느린 처리**: 5-10초 소요
  - 🔧 **개발 중**: 한국어 최적화 필요

### **응답 구조**
```json
{
  "stt": {
    "text": "청년이 주거 관련해서 받을 수 있는 지원이 있어",
    "engine": "fw",
    "decode_s": 0.736,
    "audio_sec": 4.885
  },
  "search": {
    "query": "청년이 주거 관련해서 받을 수 있는 지원이 있어",
    "topk": 5,
    "results": [
      {
        "rank": 1,
        "service_name": "긴급복지 주거지원",
        "score": 0.583,
        "support": "○ 지원대상 : 위기사유의 발생으로..."
      }
    ]
  },
  "summary": "추천 정책은 긴급복지 주거지원 입니다. 요약: ○ 지원대상 : 위기사유의 발생으로...",
  "tts": {
    "voice": "ko-KR-SunHiNeural",
    "mp3_b64": "SUQzBAAAAAAAIlRTU0UAAAAOAAADTGF2ZjYyLjMuMTAw...",
    "duration_est_s": 22.5
  }
}
```

## ⚙️ 설정 옵션

### **ASR 엔진 설정**
```bash
# Faster-Whisper (기본값)
engine=fw
beam_size=1
language=ko

# OpenAI Whisper
engine=ow
language=ko
```

### **TTS 엔진 설정**
```bash
# Edge TTS (권장)
tts_engine=edge_tts
voice=ko-KR-SunHiNeural

# SpeechT5 (실험적)
tts_engine=speecht5
```

### **검색 설정**
```bash
topk=5          # 상위 5개 정책 추천
```

## 🔧 고급 설정

### **환경 변수**
```bash
# 서버 설정
ASR_HOST=0.0.0.0
ASR_PORT=8000
CORS_ORIGINS=*

# ASR 설정
ASR_ENGINE_DEFAULT=fw
ASR_LANGUAGE=ko
ASR_FW_BEAM=1
ASR_MAX_AUDIO_SEC=15

# 모델 경로
FW_MODEL_DIR=/root/asr-service/models/faster-whisper/large-v3
OW_MODEL_DIR=/root/asr-service/models/whisper/medium

# 정책 데이터
POLICY_CSV_PATH=/root/asr-service/data/csv/gov24_services_with_tags.csv
QDRANT_PATH=/root/asr-service/qdrant_db
EMBED_MODEL=BAAI/bge-m3

# TTS 설정
TTS_VOICE_DEFAULT=ko-KR-SunHiNeural
```

## 📊 성능 특성

### **처리 속도**
- **STT**: ~1초 (4초 오디오 기준)
- **검색**: ~0.5초 (벡터 검색)
- **TTS**: ~2초 (22초 음성 기준)
- **전체 파이프라인**: ~3.5초

### **정확도**
- **STT 정확도**: 95%+ (한국어)
- **검색 정확도**: 의미 기반 90%+
- **TTS 품질**: 자연스러운 한국어 음성

## 🛠️ 개발 및 배포

### **개발 환경**
```bash
# 개발 서버 실행
uvicorn app.server:app --reload --host 0.0.0.0 --port 8000

# API 문서 확인
http://localhost:8000/docs
```

### **프로덕션 배포**
```bash
# Supervisor 설정
supervisorctl start asr-service

# 로그 확인
tail -f /root/asr-service/logs/supervisor_output.log
```

### **모니터링**
```bash
# 서비스 상태
supervisorctl status asr-service

# 헬스체크
curl http://localhost:8000/healthz
```

## 📁 프로젝트 구조

```
asr-service/
├── app/
│   ├── core/
│   │   └── config.py          # 설정 관리
│   ├── routers/
│   │   └── pipeline.py       # 통합 파이프라인
│   ├── services/
│   │   ├── asr_fw.py         # Faster-Whisper
│   │   ├── asr_ow.py         # OpenAI Whisper
│   │   ├── policy_search.py  # 벡터 검색
│   │   ├── edge_tts.py       # Edge TTS
│   │   └── tts_speecht5.py   # SpeechT5
│   └── server.py             # FastAPI 앱
├── scripts/
│   └── build_policy_index.py # 정책 인덱스 구축
├── data/
│   └── csv/                   # 정책 데이터
├── models/                    # AI 모델
├── logs/                      # 로그 파일
└── requirements.txt           # 의존성
```

## 🔍 문제 해결

### **로그 확인**
```bash
# 서비스 로그
tail -f /root/asr-service/logs/supervisor_output.log

# 에러 로그
tail -f /root/asr-service/logs/supervisor_error.log
```

## 📞 지원

- **문서**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **빠른 시작**: [QUICK_START.md](QUICK_START.md)

---

**🎯 AI 기반 복지정책 어시스턴트로 더 나은 복지 서비스를 제공합니다.**
